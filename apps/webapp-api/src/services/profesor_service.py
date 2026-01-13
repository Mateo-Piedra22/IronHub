"""Profesor Service - SQLAlchemy ORM Implementation"""
from typing import Optional, Dict, Any, List
from datetime import datetime, date, timedelta, timezone, time
from calendar import monthrange
import logging

from sqlalchemy.orm import Session
from sqlalchemy import text, select, or_, and_, func, update, delete
from sqlalchemy.exc import NoResultFound

from src.services.base import BaseService
from src.database.orm_models import (
    Profesor, 
    HorarioProfesor, 
    ProfesorHoraTrabajada, 
    ProfesorEspecialidad, 
    ProfesorCertificacion,
    Especialidad,
    Usuario
)

logger = logging.getLogger(__name__)


class ProfesorService(BaseService):
    """
    Service for professor management operations.
    Uses official ORM models: Profesor, HorarioProfesor, ProfesorHoraTrabajada.
    """

    def __init__(self, db: Session):
        super().__init__(db)

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
                fecha_contratacion=date.today()
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
            fecha_contratacion=date.today()
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
        return [{'profesor_id': r.id, 'usuario_id': r.usuario_id, 'nombre': r.nombre} for r in results]

    def get_teacher_details_list(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Dict]:
        """
        Complex query replacement for TeacherRepository.obtener_detalle_profesores.
        """
        now = datetime.now()
        mes_actual = now.month
        anio_actual = now.year
        
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

        return [
            {
                "id": row.id,
                "nombre": row.nombre,
                "email": row.email,
                "telefono": row.telefono,
                "horarios_count": row.horarios_count,
                "horarios": row.horarios,
                "sesiones_mes": row.sesiones_mes,
                "horas_mes": row.horas_mes
            }
            for row in result
        ]
        
    def get_teacher_sessions(self, profesor_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None):
        """Replacement for TeacherRepository.obtener_horas_trabajadas_profesor"""
        return self.obtener_sesiones(profesor_id, 
                                     desde=start_date.isoformat() if start_date else None, 
                                     hasta=end_date.isoformat() if end_date else None)

    # ========== Sesiones (ProfesorHoraTrabajada) ==========

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
                    'inicio': s.hora_inicio.isoformat() if s.hora_inicio else None,
                    'fin': s.hora_fin.isoformat() if s.hora_fin else None,
                    'duracion_minutos': s.minutos_totales,
                    'notas': s.notas,
                    'fecha': s.fecha.isoformat()
                } for s in results
            ]
        except Exception as e:
            logger.error(f"Error getting sesiones: {e}")
            return []

    def iniciar_sesion(self, profesor_id: int) -> Dict[str, Any]:
        try:
            # Check for active session
            active = self.db.execute(select(ProfesorHoraTrabajada).where(ProfesorHoraTrabajada.profesor_id == profesor_id, ProfesorHoraTrabajada.hora_fin == None)).first()
            if active:
                return {'error': 'Ya hay una sesión activa'}

            now = datetime.now()
            sesion = ProfesorHoraTrabajada(
                profesor_id=profesor_id,
                fecha=now.date(),
                hora_inicio=now,
                hora_fin=None
            )
            self.db.add(sesion)
            self.db.commit()
            self.db.refresh(sesion)
            return {
                'id': sesion.id, 
                'profesor_id': sesion.profesor_id, 
                'inicio': sesion.hora_inicio.isoformat(), 
                'fin': None
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
            
            now = datetime.now()
            sesion.hora_fin = now
            
            diff = sesion.hora_fin - sesion.hora_inicio
            sesion.minutos_totales = int(diff.total_seconds() / 60)
            sesion.horas_totales = round(sesion.minutos_totales / 60.0, 2)
            
            self.db.commit()
            self.db.refresh(sesion)
            return {
                'id': sesion.id,
                'profesor_id': sesion.profesor_id,
                'inicio': sesion.hora_inicio.isoformat(),
                'fin': sesion.hora_fin.isoformat(),
                'duracion_minutos': sesion.minutos_totales
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
        # Mapping to match what frontend might expect
        return {
            'id': p['id'],
            'profesor_id': p['id'],
            'monto': p['tarifa_por_hora'],
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
        
        self.actualizar_profesor(profesor_id, updates)
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
