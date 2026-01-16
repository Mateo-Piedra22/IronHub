"""Profesor Service - SQLAlchemy ORM Implementation"""
from typing import Optional, Dict, Any, List
from datetime import datetime, date, timedelta, timezone, time
from calendar import monthrange
import logging
import os
from threading import Lock

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

from sqlalchemy.orm import Session
from sqlalchemy import text, select, or_, and_, func, update, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import NoResultFound

from src.services.base import BaseService
from src.database.orm_models import (
    Profesor, 
    HorarioProfesor, 
    ProfesorHoraTrabajada, 
    ProfesorEspecialidad, 
    ProfesorCertificacion,
    Especialidad,
    Usuario,
    Configuracion
)

logger = logging.getLogger(__name__)

_ACTIVE_SESSION_INDEX_LOCK = Lock()
_ACTIVE_SESSION_INDEX_READY = False


class ProfesorService(BaseService):
    """
    Service for professor management operations.
    Uses official ORM models: Profesor, HorarioProfesor, ProfesorHoraTrabajada.
    """

    def __init__(self, db: Session):
        super().__init__(db)
        self._ensure_unique_active_session_index()

    def _active_session_index_exists(self) -> bool:
        try:
            row = self.db.execute(
                text(
                    """
                    SELECT 1
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                      AND indexname = 'uniq_sesion_activa_por_profesor'
                    LIMIT 1
                    """
                )
            ).fetchone()
            return bool(row)
        except Exception:
            return False

    def _heal_duplicate_active_sessions(self) -> None:
        rows = self.db.execute(
            text(
                """
                SELECT profesor_id, array_agg(id ORDER BY hora_inicio DESC NULLS LAST, id DESC) AS ids
                FROM profesor_horas_trabajadas
                WHERE hora_fin IS NULL
                GROUP BY profesor_id
                HAVING COUNT(*) > 1
                """
            )
        ).fetchall()
        if not rows:
            return
        for profesor_id, ids in rows:
            if not ids or len(ids) <= 1:
                continue
            to_close = list(ids[1:])
            self.db.execute(
                text(
                    """
                    UPDATE profesor_horas_trabajadas
                    SET hora_fin = hora_inicio,
                        minutos_totales = 0,
                        horas_totales = 0
                    WHERE id = ANY(:ids)
                      AND hora_fin IS NULL
                    """
                ),
                {"ids": to_close},
            )

    def _ensure_unique_active_session_index(self) -> None:
        global _ACTIVE_SESSION_INDEX_READY
        if _ACTIVE_SESSION_INDEX_READY:
            return
        with _ACTIVE_SESSION_INDEX_LOCK:
            if _ACTIVE_SESSION_INDEX_READY:
                return
            if self._active_session_index_exists():
                _ACTIVE_SESSION_INDEX_READY = True
                return
            try:
                self.db.execute(
                    text(
                        """
                        CREATE UNIQUE INDEX IF NOT EXISTS uniq_sesion_activa_por_profesor
                        ON profesor_horas_trabajadas(profesor_id)
                        WHERE hora_fin IS NULL
                        """
                    )
                )
                self.db.commit()
            except Exception:
                self.db.rollback()
                try:
                    self._heal_duplicate_active_sessions()
                    self.db.commit()
                except Exception:
                    self.db.rollback()
                try:
                    self.db.execute(
                        text(
                            """
                            CREATE UNIQUE INDEX IF NOT EXISTS uniq_sesion_activa_por_profesor
                            ON profesor_horas_trabajadas(profesor_id)
                            WHERE hora_fin IS NULL
                            """
                        )
                    )
                    self.db.commit()
                except Exception:
                    self.db.rollback()
            _ACTIVE_SESSION_INDEX_READY = self._active_session_index_exists()

    def _get_app_timezone(self):
        tz_name = (
            os.getenv("APP_TIMEZONE")
            or os.getenv("TIMEZONE")
            or os.getenv("TZ")
            or "America/Argentina/Buenos_Aires"
        )
        if ZoneInfo is not None:
            try:
                return ZoneInfo(tz_name)
            except Exception:
                pass
        return timezone(timedelta(hours=-3))

    def _now_utc_naive(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def _now_local(self) -> datetime:
        tz = self._get_app_timezone()
        return datetime.now(timezone.utc).astimezone(tz)

    def _today_local_date(self) -> date:
        return self._now_local().date()

    def _as_utc_naive(self, dt: Optional[datetime]) -> Optional[datetime]:
        if dt is None:
            return None
        if getattr(dt, "tzinfo", None) is None:
            return dt
        try:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            return dt.replace(tzinfo=None)

    def _local_naive_iso(self, dt: Optional[datetime]) -> Optional[str]:
        if dt is None:
            return None
        tz = self._get_app_timezone()
        utc_naive = self._as_utc_naive(dt)
        if utc_naive is None:
            return None
        try:
            local_dt = utc_naive.replace(tzinfo=timezone.utc).astimezone(tz).replace(tzinfo=None)
            return local_dt.isoformat(timespec='seconds')
        except Exception:
            return utc_naive.isoformat(timespec='seconds')

    def _local_time_hhmm(self, dt: Optional[datetime]) -> Optional[str]:
        if dt is None:
            return None
        iso = self._local_naive_iso(dt)
        if not iso:
            return None
        try:
            if "T" in iso:
                return iso.split("T", 1)[1][:5]
            if " " in iso:
                return iso.split(" ", 1)[1][:5]
        except Exception:
            return None
        return None

    def _cfg_key(self, profesor_id: int, name: str) -> str:
        return f"profesor:{int(profesor_id)}:{name}"

    def _get_cfg(self, key: str) -> Optional[str]:
        try:
            row = (
                self.db.execute(
                    select(Configuracion.valor).where(Configuracion.clave == key).limit(1)
                )
                .first()
            )
            return row[0] if row else None
        except Exception:
            return None

    def _set_cfg(self, key: str, value: Any) -> None:
        try:
            try:
                val_str = str(value if value is not None else '')
            except Exception:
                val_str = ''
            stmt = insert(Configuracion).values(clave=key, valor=val_str).on_conflict_do_update(
                index_elements=['clave'],
                set_={'valor': val_str}
            )
            self.db.execute(stmt)
        except Exception:
            pass

    # ========== CRUD ==========

    def obtener_profesores(self) -> List[Dict[str, Any]]:
        """Get basics of all professors."""
        try:
            stmt = select(Profesor).order_by(Profesor.id)
            profesores = self.db.scalars(stmt).all()
            return [
                {
                    'id': p.id,
                    'nombre': p.usuario.nombre if p.usuario else "Unknown",
                    'email': None, 
                    'telefono': p.usuario.telefono if p.usuario else None,
                    'activo': p.usuario.activo if p.usuario else False,
                    'created_at': p.fecha_creacion.isoformat() if p.fecha_creacion else None,
                    'usuario_id': p.usuario_id,
                    'tipo': p.tipo
                } 
                for p in profesores
            ]
        except Exception as e:
            logger.error(f"Error getting profesores: {e}")
            return []

    def crear_profesor(self, nombre: str, email: Optional[str], telefono: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Create a new profesor by creating a Usuario (role='profesor') and then a Profesor profile.
        """
        try:
            # 1. Create Usuario
            # We assume a default pin or handled elsewhere. DNI is required by model usually, 
            # but if not provided we might need to generate one or fail?
            # Model: dni: Mapped[Optional[str]] = mapped_column(String(20), unique=True) -> Optional! Good.
            
            usuario = Usuario(
                nombre=nombre.upper(),
                telefono=telefono or "",
                rol='profesor',
                activo=True
            )
            # If email was provided, where does it go? Usuario model doesn't show email.
            # Maybe it's not stored or stored in notes? We'll ignore email for now as per model view.
            
            self.db.add(usuario)
            self.db.commit() # commit to get ID
            self.db.refresh(usuario)
            
            # 2. Create Profesor
            profesor = Profesor(
                usuario_id=usuario.id,
                fecha_contratacion=self._today_local_date()
            )
            self.db.add(profesor)
            self.db.commit()
            self.db.refresh(profesor)
            
            return {
                'id': profesor.id,
                'nombre': usuario.nombre,
                'email': email,
                'telefono': usuario.telefono,
                'activo': usuario.activo,
                'usuario_id': usuario.id
            }
        except Exception as e:
            logger.error(f"Error creating profesor: {e}")
            self.db.rollback()
            return None

    def crear_perfil_profesor(self, usuario_id: int, data: Dict[str, Any]) -> int:
        """Create a profesor profile for an existing user."""
        profesor = Profesor(
            usuario_id=usuario_id,
            especialidades=data.get('especialidades'),
            certificaciones=data.get('certificaciones'),
            experiencia_años=data.get('experiencia_anios', 0),
            tarifa_por_hora=data.get('tarifa_por_hora', 0.0),
            biografia=data.get('biografia'),
            telefono_emergencia=data.get('telefono_emergencia'),
            fecha_contratacion=self._today_local_date()
        )
        self.db.add(profesor)
        self.db.commit()
        self.db.refresh(profesor)
        return profesor.id

    def obtener_profesor(self, profesor_id: int) -> Optional[Dict[str, Any]]:
        try:
            p = self.db.get(Profesor, profesor_id)
            if not p:
                return None
            return {
                'id': p.id,
                'usuario_id': p.usuario_id,
                'nombre': p.usuario.nombre if p.usuario else None,
                'email': None,
                'telefono': p.usuario.telefono if p.usuario else None,
                'activo': p.usuario.activo if p.usuario else None,
                'tipo': p.tipo,
                'especialidades': p.especialidades,
                'certificaciones': p.certificaciones,
                'experiencia_anios': p.experiencia_años,
                'tarifa_por_hora': float(p.tarifa_por_hora) if p.tarifa_por_hora else 0.0,
                'fecha_contratacion': p.fecha_contratacion.isoformat() if p.fecha_contratacion else None,
                'biografia': p.biografia,
                'telefono_emergencia': p.telefono_emergencia,
                'created_at': p.fecha_creacion.isoformat() if p.fecha_creacion else None
            }
        except Exception as e:
            logger.error(f"Error getting profesor: {e}")
            return None

    def actualizar_profesor(self, profesor_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            p = self.db.get(Profesor, profesor_id)
            if not p:
                return None
            
            # Update Profesor fields
            if 'especialidades' in updates: p.especialidades = updates['especialidades']
            if 'certificaciones' in updates: p.certificaciones = updates['certificaciones']
            if 'experiencia_anios' in updates: p.experiencia_años = updates['experiencia_anios']
            if 'tarifa_por_hora' in updates: p.tarifa_por_hora = updates['tarifa_por_hora']
            if 'biografia' in updates: p.biografia = updates['biografia']
            if 'telefono_emergencia' in updates: p.telefono_emergencia = updates['telefono_emergencia']
            
            # Update Usuario fields
            if p.usuario:
                if 'nombre' in updates: p.usuario.nombre = updates['nombre']
                if 'telefono' in updates: p.usuario.telefono = updates['telefono']
                if 'activo' in updates: p.usuario.activo = updates['activo']

            self.db.commit()
            return self.obtener_profesor(profesor_id)
        except Exception as e:
            logger.error(f"Error updating profesor: {e}")
            self.db.rollback()
            return None

    def eliminar_profesor(self, profesor_id: int) -> bool:
        try:
            p = self.db.get(Profesor, profesor_id)
            if p:
                self.db.delete(p)
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting profesor: {e}")
            self.db.rollback()
            return False

    # ========== Consolidating TeacherRepository Functionality ==========

    def list_teachers_basic(self) -> List[Dict]:
        """Replacement for TeacherRepository.obtener_profesores_basico_con_ids"""
        stmt = select(Profesor.id, Usuario.id.label("usuario_id"), Usuario.nombre)\
            .join(Usuario)\
            .where(Usuario.activo == True)\
            .order_by(Usuario.nombre)
        results = self.db.execute(stmt).all()
        return [{'profesor_id': r.id, 'nombre': r.nombre} for r in results]

    def get_teacher_details_list(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Dict]:
        """
        Complex query replacement for TeacherRepository.obtener_detalle_profesores.
        """
        hoy = self._today_local_date()
        mes_actual = hoy.month
        anio_actual = hoy.year
        
        sql = text("""
            WITH sesiones AS (
                SELECT profesor_id,
                       COUNT(*) AS sesiones_mes,
                       COALESCE(SUM(minutos_totales) / 60.0, 0) AS horas_mes
                FROM profesor_horas_trabajadas
                WHERE hora_fin IS NOT NULL
                  AND (
                    ( :start_date IS NOT NULL AND :end_date IS NOT NULL AND fecha BETWEEN :start_date AND :end_date )
                    OR ( (:start_date IS NULL OR :end_date IS NULL) AND EXTRACT(MONTH FROM fecha) = :mes_actual AND EXTRACT(YEAR FROM fecha) = :anio_actual )
                  )
                GROUP BY profesor_id
            ),
            horarios AS (
                SELECT hp.profesor_id,
                       COUNT(hp.id) AS horarios_count,
                       JSON_AGG(
                           JSON_BUILD_OBJECT(
                               'dia', hp.dia_semana,
                               'inicio', CAST(hp.hora_inicio AS TEXT),
                               'fin', CAST(hp.hora_fin AS TEXT)
                           )
                           ORDER BY CASE hp.dia_semana 
                               WHEN 'Lunes' THEN 1 
                               WHEN 'Martes' THEN 2 
                               WHEN 'Miércoles' THEN 3 
                               WHEN 'Jueves' THEN 4 
                               WHEN 'Viernes' THEN 5 
                               WHEN 'Sábado' THEN 6 
                               WHEN 'Domingo' THEN 7 
                           END, hp.hora_inicio
                       ) AS horarios
                FROM horarios_profesores hp
                GROUP BY hp.profesor_id
            )
            SELECT p.id AS id,
                   COALESCE(u.nombre,'') AS nombre,
                   '' AS email,
                   COALESCE(u.telefono,'') AS telefono,
                   COALESCE(h.horarios_count, 0) AS horarios_count,
                   COALESCE(h.horarios, '[]'::json) AS horarios,
                   COALESCE(s.sesiones_mes, 0) AS sesiones_mes,
                   COALESCE(s.horas_mes, 0) AS horas_mes
            FROM profesores p
            JOIN usuarios u ON u.id = p.usuario_id
            LEFT JOIN horarios h ON h.profesor_id = p.id
            LEFT JOIN sesiones s ON s.profesor_id = p.id
            ORDER BY p.id
        """)
        
        result = self.db.execute(sql, {
            "start_date": start_date, 
            "end_date": end_date, 
            "mes_actual": mes_actual, 
            "anio_actual": anio_actual
        }).fetchall()

        results_dict = []
        for row in result:
            # Calculate projected hours from schedule
            horarios_json = row.horarios
            horas_semana = 0.0

            def _parse_time_any(v: Any) -> Optional[time]:
                try:
                    if v is None:
                        return None
                    if isinstance(v, time):
                        return v
                    s = str(v).strip()
                    if not s:
                        return None
                    fmt = "%H:%M:%S" if len(s) > 5 else "%H:%M"
                    try:
                        return datetime.strptime(s, fmt).time()
                    except ValueError:
                        alt = "%H:%M" if fmt == "%H:%M:%S" else "%H:%M:%S"
                        return datetime.strptime(s, alt).time()
                except Exception:
                    return None

            def _duration_hours(start_t: time, end_t: time) -> float:
                try:
                    start_sec = start_t.hour * 3600 + start_t.minute * 60 + start_t.second
                    end_sec = end_t.hour * 3600 + end_t.minute * 60 + end_t.second
                    if end_sec < start_sec:
                        end_sec += 24 * 3600
                    return max(0.0, (end_sec - start_sec) / 3600.0)
                except Exception:
                    return 0.0
            
            if horarios_json and isinstance(horarios_json, list):
                for h in horarios_json:
                    try:
                        # h is a dict like {'dia': 'Lunes', 'inicio': '10:00:00', 'fin': '11:00:00'}
                        # Note: SQL JSON_BUILD_OBJECT might return strings for times
                        if h.get('inicio') and h.get('fin'):
                             start_t = _parse_time_any(h.get('inicio'))
                             end_t = _parse_time_any(h.get('fin'))
                             if start_t and end_t:
                                 horas_semana += _duration_hours(start_t, end_t)
                    except Exception:
                        pass # Ignore malformed times
            
            horas_proyectadas = round(horas_semana * 4.3, 1)

            results_dict.append({
                "id": row.id,
                "nombre": row.nombre,
                "email": row.email,
                "telefono": row.telefono,
                "horarios_count": row.horarios_count,
                "horarios": row.horarios,
                "sesiones_mes": row.sesiones_mes,
                "horas_mes": row.horas_mes,
                "horas_proyectadas": horas_proyectadas
            })
            
        return results_dict
        
    def get_teacher_sessions(self, profesor_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None):
        """Replacement for TeacherRepository.obtener_horas_trabajadas_profesor"""
        return self.obtener_sesiones(profesor_id, 
                                     desde=start_date.isoformat() if start_date else None, 
                                     hasta=end_date.isoformat() if end_date else None)

    # ========== Sesiones (ProfesorHoraTrabajada) ==========
    def obtener_sesion_activa(self, profesor_id: int) -> Optional[Dict[str, Any]]:
        try:
            s = (
                self.db.execute(
                    select(ProfesorHoraTrabajada)
                    .where(
                        ProfesorHoraTrabajada.profesor_id == int(profesor_id),
                        ProfesorHoraTrabajada.hora_fin == None,
                    )
                    .order_by(ProfesorHoraTrabajada.hora_inicio.desc())
                    .limit(1)
                )
                .scalars()
                .first()
            )
            if not s:
                return None
            return {
                'id': s.id,
                'profesor_id': s.profesor_id,
                'inicio': self._local_naive_iso(s.hora_inicio),
                'fin': None,
                'hora_inicio': self._local_time_hhmm(s.hora_inicio),
                'hora_fin': None,
                'already_active': True,
            }
        except Exception:
            return None

    def obtener_sesiones(self, profesor_id: int, desde: Optional[str] = None, hasta: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            stmt = select(ProfesorHoraTrabajada).where(ProfesorHoraTrabajada.profesor_id == profesor_id)
            if desde: stmt = stmt.where(ProfesorHoraTrabajada.fecha >= datetime.strptime(desde, '%Y-%m-%d').date())
            if hasta: stmt = stmt.where(ProfesorHoraTrabajada.fecha <= datetime.strptime(hasta, '%Y-%m-%d').date())
            stmt = stmt.order_by(ProfesorHoraTrabajada.fecha.desc(), ProfesorHoraTrabajada.hora_inicio.desc())
            
            results = self.db.scalars(stmt).all()
            return [
                {
                    'id': s.id,
                    'profesor_id': s.profesor_id,
                    'inicio': self._local_naive_iso(s.hora_inicio),
                    'fin': self._local_naive_iso(s.hora_fin),
                    'hora_inicio': self._local_time_hhmm(s.hora_inicio),
                    'hora_fin': self._local_time_hhmm(s.hora_fin),
                    'minutos': int(s.minutos_totales or 0),
                    'tipo': 'extra' if str(getattr(s, 'tipo_actividad', '') or '').strip().lower() == 'extra' else 'normal',
                    'notas': s.notas,
                    'fecha': s.fecha.isoformat()
                } for s in results
            ]
        except Exception as e:
            logger.error(f"Error getting sesiones: {e}")
            return []

    def iniciar_sesion(self, profesor_id: int) -> Dict[str, Any]:
        try:
            self._ensure_unique_active_session_index()
            now_utc = self._now_utc_naive()
            fecha_local = self._today_local_date()

            row = self.db.execute(
                text(
                    """
                    INSERT INTO profesor_horas_trabajadas (profesor_id, fecha, hora_inicio, hora_fin)
                    VALUES (:pid, :fecha, :inicio, NULL)
                    ON CONFLICT (profesor_id) WHERE hora_fin IS NULL DO NOTHING
                    RETURNING id, hora_inicio
                    """
                ),
                {"pid": int(profesor_id), "fecha": fecha_local, "inicio": now_utc},
            )
            inserted = row.fetchone()
            if inserted:
                self.db.commit()
                inicio_dt = inserted[1] or now_utc
                return {
                    'id': int(inserted[0]),
                    'profesor_id': int(profesor_id),
                    'inicio': self._local_naive_iso(inicio_dt),
                    'fin': None,
                    'hora_inicio': self._local_time_hhmm(inicio_dt),
                    'hora_fin': None,
                    'already_active': False,
                }

            active_row = (
                self.db.execute(
                    select(ProfesorHoraTrabajada).where(
                        ProfesorHoraTrabajada.profesor_id == profesor_id,
                        ProfesorHoraTrabajada.hora_fin == None
                    )
                    .order_by(ProfesorHoraTrabajada.hora_inicio.desc())
                    .limit(1)
                )
                .scalars()
                .first()
            )
            if not active_row:
                self.db.rollback()
                return {'error': 'No se pudo iniciar la sesión'}
            return {
                'id': active_row.id,
                'profesor_id': active_row.profesor_id,
                'already_active': True,
                'inicio': self._local_naive_iso(active_row.hora_inicio),
                'fin': None,
                'hora_inicio': self._local_time_hhmm(active_row.hora_inicio),
                'hora_fin': None,
            }
        except Exception as e:
            logger.error(f"Error starting session: {e}")
            self.db.rollback()
            return {'error': str(e)}

    def finalizar_sesion(self, profesor_id: int, sesion_id: int) -> Dict[str, Any]:
        try:
            sesion = self.db.get(ProfesorHoraTrabajada, sesion_id)
            if not sesion or sesion.profesor_id != profesor_id or sesion.hora_fin is not None:
                return {'error': 'Sesión no encontrada o ya finalizada'}
            
            now_utc = self._now_utc_naive()
            sesion.hora_fin = now_utc
            
            diff = sesion.hora_fin - sesion.hora_inicio
            sesion.minutos_totales = int(diff.total_seconds() / 60)
            sesion.horas_totales = round(sesion.minutos_totales / 60.0, 2)
            
            self.db.commit()
            self.db.refresh(sesion)
            return {
                'id': sesion.id,
                'profesor_id': sesion.profesor_id,
                'inicio': self._local_naive_iso(sesion.hora_inicio),
                'fin': self._local_naive_iso(sesion.hora_fin),
                'hora_inicio': self._local_time_hhmm(sesion.hora_inicio),
                'hora_fin': self._local_time_hhmm(sesion.hora_fin),
                'minutos': int(sesion.minutos_totales or 0),
                'tipo': 'extra' if str(getattr(sesion, 'tipo_actividad', '') or '').strip().lower() == 'extra' else 'normal',
            }
        except Exception as e:
            logger.error(f"Error ending session: {e}")
            self.db.rollback()
            return {'error': str(e)}

    def eliminar_sesion(self, sesion_id: int) -> bool:
        try:
            sesion = self.db.get(ProfesorHoraTrabajada, sesion_id)
            if sesion:
                self.db.delete(sesion)
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            self.db.rollback()
            return False

    # ========== Horarios (HorarioProfesor) ==========

    def obtener_horarios(self, profesor_id: int) -> List[Dict[str, Any]]:
        try:
            stmt = select(HorarioProfesor).where(HorarioProfesor.profesor_id == profesor_id)
            # Custom sorting logic by day
            results = self.db.scalars(stmt).all()
            
            # Helper for sorting
            days_map = {'lunes': 1, 'martes': 2, 'miércoles': 3, 'miercoles': 3, 'jueves': 4, 'viernes': 5, 'sábado': 6, 'sabado': 6, 'domingo': 7}
            
            def sort_key(h):
                d = str(h.dia_semana).lower()
                return (days_map.get(d, 8), h.hora_inicio)

            results.sort(key=sort_key)
            
            return [
                {
                    'id': h.id,
                    'profesor_id': h.profesor_id,
                    'dia': h.dia_semana,
                    'hora_inicio': h.hora_inicio.strftime('%H:%M') if h.hora_inicio else None,
                    'hora_fin': h.hora_fin.strftime('%H:%M') if h.hora_fin else None,
                    'disponible': h.disponible
                } for h in results
            ]
        except Exception as e:
            logger.error(f"Error getting horarios: {e}")
            return []

    def crear_horario(self, profesor_id: int, dia: str, hora_inicio: str, hora_fin: str, disponible: bool = True) -> Optional[Dict[str, Any]]:
        try:
            # Parse times
            hi = datetime.strptime(hora_inicio, '%H:%M').time() if isinstance(hora_inicio, str) else hora_inicio
            hf = datetime.strptime(hora_fin, '%H:%M').time() if isinstance(hora_fin, str) else hora_fin
            
            h = HorarioProfesor(
                profesor_id=profesor_id,
                dia_semana=dia.capitalize(),
                hora_inicio=hi,
                hora_fin=hf,
                disponible=disponible
            )
            self.db.add(h)
            self.db.commit()
            self.db.refresh(h)
            return {
                'id': h.id, 'profesor_id': h.profesor_id, 'dia': h.dia_semana,
                'hora_inicio': h.hora_inicio.strftime('%H:%M'), 'hora_fin': h.hora_fin.strftime('%H:%M'),
                'disponible': h.disponible
            }
        except Exception as e:
            logger.error(f"Error creating horario: {e}")
            self.db.rollback()
            return None

    def actualizar_horario(self, profesor_id: int, horario_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            h = self.db.get(HorarioProfesor, horario_id)
            if not h or h.profesor_id != profesor_id:
                return None
            
            if 'dia' in updates: h.dia_semana = updates['dia'].capitalize()
            if 'hora_inicio' in updates:
                 h.hora_inicio = datetime.strptime(updates['hora_inicio'], '%H:%M').time() if isinstance(updates['hora_inicio'], str) else updates['hora_inicio']
            if 'hora_fin' in updates:
                 h.hora_fin = datetime.strptime(updates['hora_fin'], '%H:%M').time() if isinstance(updates['hora_fin'], str) else updates['hora_fin']
            if 'disponible' in updates: h.disponible = bool(updates['disponible'])
            
            self.db.commit()
            self.db.refresh(h)
            return {
                'id': h.id, 'profesor_id': h.profesor_id, 'dia': h.dia_semana,
                'hora_inicio': h.hora_inicio.strftime('%H:%M'), 'hora_fin': h.hora_fin.strftime('%H:%M'),
                'disponible': h.disponible
            }
        except Exception as e:
            logger.error(f"Error updating horario: {e}")
            self.db.rollback()
            return None

    def eliminar_horario(self, profesor_id: int, horario_id: int) -> bool:
        try:
            h = self.db.get(HorarioProfesor, horario_id)
            if h and h.profesor_id == profesor_id:
                self.db.delete(h)
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting horario: {e}")
            self.db.rollback()
            return False

    # ========== Config / Extras ==========
    
    def obtener_config(self, profesor_id: int) -> Dict[str, Any]:
        """Get config-like data from Profesor model."""
        p = self.obtener_profesor(profesor_id)
        if not p: return {}
        link_key = self._cfg_key(profesor_id, 'usuario_vinculado_id')
        mt_key = self._cfg_key(profesor_id, 'monto_tipo')
        linked_raw = self._get_cfg(link_key)
        monto_tipo_raw = self._get_cfg(mt_key)
        usuario_vinculado_id = None
        try:
            if linked_raw is not None and str(linked_raw).strip().isdigit():
                usuario_vinculado_id = int(str(linked_raw).strip())
        except Exception:
            usuario_vinculado_id = None

        usuario_vinculado_nombre = None
        try:
            if usuario_vinculado_id is not None:
                u = self.db.get(Usuario, int(usuario_vinculado_id))
                if u:
                    usuario_vinculado_nombre = getattr(u, 'nombre', None)
        except Exception:
            usuario_vinculado_nombre = None

        monto_tipo = 'mensual'
        try:
            mt = str(monto_tipo_raw or '').strip().lower()
            if mt in ('mensual', 'hora'):
                monto_tipo = mt
        except Exception:
            monto_tipo = 'mensual'
        # Mapping to match what frontend might expect
        return {
            'id': p['id'],
            'profesor_id': p['id'],
            'usuario_vinculado_id': usuario_vinculado_id,
            'usuario_vinculado_nombre': usuario_vinculado_nombre,
            'monto': p['tarifa_por_hora'],
            'monto_tipo': monto_tipo,
            'especialidad': p['especialidades'],
            'experiencia_anios': p['experiencia_anios'],
            'certificaciones': p['certificaciones'],
            'notas': p['biografia'] 
        }

    def actualizar_config(self, profesor_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update config-like data mapping to Profesor model."""
        updates = {}
        if 'monto' in data: updates['tarifa_por_hora'] = data['monto']
        if 'especialidad' in data: updates['especialidades'] = data['especialidad']
        if 'experiencia_anios' in data: updates['experiencia_anios'] = data['experiencia_anios']
        if 'certificaciones' in data: updates['certificaciones'] = data['certificaciones']
        if 'notas' in data: updates['biografia'] = data['notas']

        if 'usuario_vinculado_id' in data:
            self._set_cfg(self._cfg_key(profesor_id, 'usuario_vinculado_id'), data.get('usuario_vinculado_id') or '')

        if 'monto_tipo' in data:
            mt = str(data.get('monto_tipo') or '').strip().lower()
            if mt not in ('mensual', 'hora'):
                mt = 'mensual'
            self._set_cfg(self._cfg_key(profesor_id, 'monto_tipo'), mt)
        
        self.actualizar_profesor(profesor_id, updates)
        try:
            self.db.commit()
        except Exception:
            try:
                self.db.rollback()
            except Exception:
                pass
        return self.obtener_config(profesor_id)

    # ========== Resumen ==========

    def resumen_mensual(self, profesor_id: int, mes: int, anio: int) -> Dict[str, Any]:
        """Monthly summary using ProfesorHoraTrabajada."""
        try:
            _, last_day = monthrange(anio, mes)
            start_date = date(anio, mes, 1)
            end_date = date(anio, mes, last_day)
            
            # Sum minutes
            stmt = select(func.sum(ProfesorHoraTrabajada.minutos_totales))\
                .where(ProfesorHoraTrabajada.profesor_id == profesor_id)\
                .where(ProfesorHoraTrabajada.fecha >= start_date)\
                .where(ProfesorHoraTrabajada.fecha <= end_date)
            
            minutes = self.db.scalar(stmt) or 0
            horas_trabajadas = round(minutes / 60, 1)
            
            # Projected
            horarios = self.obtener_horarios(profesor_id)
            horas_semana = 0
            for h in horarios:
                if h['hora_inicio'] and h['hora_fin'] and h['disponible']:
                    start = datetime.strptime(h['hora_inicio'], "%H:%M")
                    end = datetime.strptime(h['hora_fin'], "%H:%M")
                    horas_semana += (end - start).seconds / 3600
                    
            horas_proyectadas = round(horas_semana * 4.3, 1)
            
            return {
                'horas_trabajadas': horas_trabajadas,
                'horas_proyectadas': horas_proyectadas,
                'horas_extra': max(0, round(horas_trabajadas - horas_proyectadas, 1)),
                'horas_totales': horas_trabajadas
            }
        except Exception as e:
            logger.error(f"Error calculating monthly summary: {e}")
            return {'horas_trabajadas': 0, 'horas_proyectadas': 0, 'horas_extra': 0, 'horas_totales': 0}

    def resumen_semanal(self, profesor_id: int, ref_date: date) -> Dict[str, Any]:
        """Weekly summary."""
        try:
            start_date = ref_date - timedelta(days=ref_date.weekday())
            end_date = start_date + timedelta(days=6)
            
            stmt = select(func.sum(ProfesorHoraTrabajada.minutos_totales))\
                .where(ProfesorHoraTrabajada.profesor_id == profesor_id)\
                .where(ProfesorHoraTrabajada.fecha >= start_date)\
                .where(ProfesorHoraTrabajada.fecha <= end_date)
                
            minutes = self.db.scalar(stmt) or 0
            horas_trabajadas = round(minutes / 60, 1)
            
            horarios = self.obtener_horarios(profesor_id)
            horas_semana = 0
            for h in horarios:
                if h['hora_inicio'] and h['hora_fin'] and h['disponible']:
                    start = datetime.strptime(h['hora_inicio'], "%H:%M")
                    end = datetime.strptime(h['hora_fin'], "%H:%M")
                    horas_semana += (end - start).seconds / 3600
                    
            return {
                'horas_trabajadas': horas_trabajadas,
                'horas_proyectadas': round(horas_semana, 1),
                'horas_extra': max(0, round(horas_trabajadas - horas_semana, 1)),
                'horas_totales': horas_trabajadas
            }
        except Exception as e:
            logger.error(f"Error calculating weekly summary: {e}")
            return {'horas_trabajadas': 0, 'horas_proyectadas': 0, 'horas_extra': 0, 'horas_totales': 0}
