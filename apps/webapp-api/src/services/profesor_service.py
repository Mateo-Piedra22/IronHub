"""Profesor Service - SQLAlchemy ORM Implementation for profesores.py"""
from typing import Optional, Dict, Any, List
from datetime import datetime, date, timedelta, timezone
from calendar import monthrange
import logging

from sqlalchemy.orm import Session
from sqlalchemy import text

from src.services.base import BaseService

logger = logging.getLogger(__name__)


class ProfesorService(BaseService):
    """Service for professor management operations."""

    def __init__(self, db: Session):
        super().__init__(db)
        self.ensure_tables()

    def ensure_tables(self) -> None:
        """Ensure profesor-related tables exist."""
        try:
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS profesor_horarios (
                    id SERIAL PRIMARY KEY, profesor_id INTEGER NOT NULL, dia VARCHAR(20) NOT NULL,
                    hora_inicio TIME NOT NULL, hora_fin TIME NOT NULL, disponible BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS profesor_config (
                    id SERIAL PRIMARY KEY, profesor_id INTEGER NOT NULL UNIQUE, usuario_vinculado_id INTEGER,
                    monto DECIMAL(10,2), monto_tipo VARCHAR(20) DEFAULT 'mensual', especialidad TEXT,
                    experiencia_anios INTEGER, certificaciones TEXT, notas TEXT,
                    created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            self.db.commit()
        except Exception as e:
            logger.error(f"Error ensuring profesor tables: {e}")
            self.db.rollback()

    # ========== CRUD ==========
    def obtener_profesores(self) -> List[Dict[str, Any]]:
        try:
            result = self.db.execute(text("SELECT id, nombre, email, telefono, activo, created_at FROM profesores ORDER BY nombre"))
            return [{'id': r[0], 'nombre': r[1], 'email': r[2], 'telefono': r[3], 'activo': r[4], 'created_at': r[5].isoformat() if r[5] else None} for r in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting profesores: {e}")
            return []

    def crear_profesor(self, nombre: str, email: Optional[str], telefono: Optional[str]) -> Optional[Dict[str, Any]]:
        try:
            result = self.db.execute(text("INSERT INTO profesores (nombre, email, telefono, activo) VALUES (:n, :e, :t, TRUE) RETURNING id, nombre, email, telefono, activo"),
                {'n': nombre, 'e': email, 't': telefono})
            row = result.fetchone()
            self.db.commit()
            return {'id': row[0], 'nombre': row[1], 'email': row[2], 'telefono': row[3], 'activo': row[4]} if row else None
        except Exception as e:
            logger.error(f"Error creating profesor: {e}")
            self.db.rollback()
            return None

    def obtener_profesor(self, profesor_id: int) -> Optional[Dict[str, Any]]:
        try:
            result = self.db.execute(text("SELECT id, nombre, email, telefono, activo, created_at FROM profesores WHERE id = :id"), {'id': profesor_id})
            row = result.fetchone()
            return {'id': row[0], 'nombre': row[1], 'email': row[2], 'telefono': row[3], 'activo': row[4], 'created_at': row[5].isoformat() if row[5] else None} if row else None
        except Exception as e:
            logger.error(f"Error getting profesor: {e}")
            return None

    def actualizar_profesor(self, profesor_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            sets, params = [], {'id': profesor_id}
            if 'nombre' in updates: sets.append("nombre = :nombre"); params['nombre'] = (updates['nombre'] or '').strip()
            if 'email' in updates: sets.append("email = :email"); params['email'] = (updates['email'] or '').strip() or None
            if 'telefono' in updates: sets.append("telefono = :telefono"); params['telefono'] = (updates['telefono'] or '').strip() or None
            if 'activo' in updates: sets.append("activo = :activo"); params['activo'] = bool(updates['activo'])
            if not sets: return {'ok': True}
            result = self.db.execute(text(f"UPDATE profesores SET {', '.join(sets)} WHERE id = :id RETURNING *"), params)
            row = result.fetchone()
            self.db.commit()
            return dict(zip(result.keys(), row)) if row else {'ok': True}
        except Exception as e:
            logger.error(f"Error updating profesor: {e}")
            self.db.rollback()
            return None

    def eliminar_profesor(self, profesor_id: int) -> bool:
        try:
            self.db.execute(text("DELETE FROM profesores WHERE id = :id"), {'id': profesor_id})
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting profesor: {e}")
            self.db.rollback()
            return False

    # ========== Sesiones ==========
    def obtener_sesiones(self, profesor_id: int, desde: Optional[str] = None, hasta: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            query = "SELECT id, profesor_id, inicio, fin, duracion_minutos, notas FROM sesiones WHERE profesor_id = :pid"
            params = {'pid': profesor_id}
            if desde: query += " AND DATE(inicio) >= :desde"; params['desde'] = desde
            if hasta: query += " AND DATE(inicio) <= :hasta"; params['hasta'] = hasta
            query += " ORDER BY inicio DESC LIMIT 100"
            result = self.db.execute(text(query), params)
            return [{'id': r[0], 'profesor_id': r[1], 'inicio': r[2].isoformat() if r[2] else None, 'fin': r[3].isoformat() if r[3] else None, 'duracion_minutos': r[4], 'notas': r[5]} for r in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting sesiones: {e}")
            return []

    def iniciar_sesion(self, profesor_id: int) -> Dict[str, Any]:
        try:
            active = self.db.execute(text("SELECT id FROM sesiones WHERE profesor_id = :pid AND fin IS NULL LIMIT 1"), {'pid': profesor_id}).fetchone()
            if active: return {'error': 'Ya hay una sesión activa', 'active_id': active[0]}
            now = datetime.now(timezone.utc)
            result = self.db.execute(text("INSERT INTO sesiones (profesor_id, inicio) VALUES (:pid, :now) RETURNING id, profesor_id, inicio, fin, duracion_minutos"),
                {'pid': profesor_id, 'now': now})
            row = result.fetchone()
            self.db.commit()
            return {'id': row[0], 'profesor_id': row[1], 'inicio': row[2].isoformat() if row[2] else None, 'fin': None, 'duracion_minutos': None} if row else {}
        except Exception as e:
            logger.error(f"Error starting session: {e}")
            self.db.rollback()
            return {'error': str(e)}

    def finalizar_sesion(self, profesor_id: int, sesion_id: int) -> Dict[str, Any]:
        try:
            row = self.db.execute(text("SELECT id, inicio FROM sesiones WHERE id = :sid AND profesor_id = :pid AND fin IS NULL"), {'sid': sesion_id, 'pid': profesor_id}).fetchone()
            if not row: return {'error': 'Sesión no encontrada o ya finalizada'}
            inicio = row[1]
            now = datetime.now(timezone.utc)
            duracion = int((now - inicio).total_seconds() / 60) if inicio else 0
            result = self.db.execute(text("UPDATE sesiones SET fin = :fin, duracion_minutos = :dur WHERE id = :sid RETURNING id, profesor_id, inicio, fin, duracion_minutos"),
                {'fin': now, 'dur': duracion, 'sid': sesion_id})
            updated = result.fetchone()
            self.db.commit()
            return {'id': updated[0], 'profesor_id': updated[1], 'inicio': updated[2].isoformat() if updated[2] else None, 'fin': updated[3].isoformat() if updated[3] else None, 'duracion_minutos': updated[4]} if updated else {}
        except Exception as e:
            logger.error(f"Error ending session: {e}")
            self.db.rollback()
            return {'error': str(e)}

    def eliminar_sesion(self, sesion_id: int) -> bool:
        try:
            self.db.execute(text("DELETE FROM sesiones WHERE id = :id"), {'id': sesion_id})
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            self.db.rollback()
            return False

    # ========== Horarios ==========
    def obtener_horarios(self, profesor_id: int) -> List[Dict[str, Any]]:
        try:
            result = self.db.execute(text("""
                SELECT id, profesor_id, dia, TO_CHAR(hora_inicio, 'HH24:MI') as hora_inicio, TO_CHAR(hora_fin, 'HH24:MI') as hora_fin, disponible
                FROM profesor_horarios WHERE profesor_id = :pid
                ORDER BY CASE dia WHEN 'lunes' THEN 1 WHEN 'martes' THEN 2 WHEN 'miércoles' THEN 3 WHEN 'jueves' THEN 4 WHEN 'viernes' THEN 5 WHEN 'sábado' THEN 6 WHEN 'domingo' THEN 7 END, hora_inicio
            """), {'pid': profesor_id})
            return [{'id': r[0], 'profesor_id': r[1], 'dia': r[2], 'hora_inicio': r[3], 'hora_fin': r[4], 'disponible': r[5]} for r in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting horarios: {e}")
            return []

    def crear_horario(self, profesor_id: int, dia: str, hora_inicio: str, hora_fin: str, disponible: bool = True) -> Optional[Dict[str, Any]]:
        try:
            result = self.db.execute(text("""
                INSERT INTO profesor_horarios (profesor_id, dia, hora_inicio, hora_fin, disponible)
                VALUES (:pid, :dia, :hi, :hf, :disp)
                RETURNING id, profesor_id, dia, TO_CHAR(hora_inicio, 'HH24:MI') as hora_inicio, TO_CHAR(hora_fin, 'HH24:MI') as hora_fin, disponible
            """), {'pid': profesor_id, 'dia': dia.lower(), 'hi': hora_inicio, 'hf': hora_fin, 'disp': disponible})
            row = result.fetchone()
            self.db.commit()
            return {'id': row[0], 'profesor_id': row[1], 'dia': row[2], 'hora_inicio': row[3], 'hora_fin': row[4], 'disponible': row[5]} if row else None
        except Exception as e:
            logger.error(f"Error creating horario: {e}")
            self.db.rollback()
            return None

    def actualizar_horario(self, profesor_id: int, horario_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            sets, params = [], {'id': horario_id, 'pid': profesor_id}
            if 'dia' in updates: sets.append("dia = :dia"); params['dia'] = (updates['dia'] or '').lower()
            if 'hora_inicio' in updates: sets.append("hora_inicio = :hi"); params['hi'] = updates['hora_inicio']
            if 'hora_fin' in updates: sets.append("hora_fin = :hf"); params['hf'] = updates['hora_fin']
            if 'disponible' in updates: sets.append("disponible = :disp"); params['disp'] = bool(updates['disponible'])
            if not sets: return {'ok': True}
            result = self.db.execute(text(f"""
                UPDATE profesor_horarios SET {', '.join(sets)} WHERE id = :id AND profesor_id = :pid
                RETURNING id, profesor_id, dia, TO_CHAR(hora_inicio, 'HH24:MI') as hora_inicio, TO_CHAR(hora_fin, 'HH24:MI') as hora_fin, disponible
            """), params)
            row = result.fetchone()
            self.db.commit()
            return {'id': row[0], 'profesor_id': row[1], 'dia': row[2], 'hora_inicio': row[3], 'hora_fin': row[4], 'disponible': row[5]} if row else {'ok': True}
        except Exception as e:
            logger.error(f"Error updating horario: {e}")
            self.db.rollback()
            return None

    def eliminar_horario(self, profesor_id: int, horario_id: int) -> bool:
        try:
            self.db.execute(text("DELETE FROM profesor_horarios WHERE id = :id AND profesor_id = :pid"), {'id': horario_id, 'pid': profesor_id})
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting horario: {e}")
            self.db.rollback()
            return False

    # ========== Config ==========
    def obtener_config(self, profesor_id: int) -> Dict[str, Any]:
        try:
            result = self.db.execute(text("""
                SELECT pc.id, pc.profesor_id, pc.usuario_vinculado_id, pc.monto, pc.monto_tipo, pc.especialidad,
                       pc.experiencia_anios, pc.certificaciones, pc.notas, u.nombre as usuario_vinculado_nombre
                FROM profesor_config pc LEFT JOIN usuarios u ON pc.usuario_vinculado_id = u.id WHERE pc.profesor_id = :pid
            """), {'pid': profesor_id})
            row = result.fetchone()
            if not row:
                return {'id': None, 'profesor_id': profesor_id, 'usuario_vinculado_id': None, 'usuario_vinculado_nombre': None,
                        'monto': None, 'monto_tipo': 'mensual', 'especialidad': None, 'experiencia_anios': None, 'certificaciones': None, 'notas': None}
            return {'id': row[0], 'profesor_id': row[1], 'usuario_vinculado_id': row[2], 'monto': float(row[3]) if row[3] else None,
                    'monto_tipo': row[4], 'especialidad': row[5], 'experiencia_anios': row[6], 'certificaciones': row[7], 'notas': row[8], 'usuario_vinculado_nombre': row[9]}
        except Exception as e:
            logger.error(f"Error getting config: {e}")
            return {}

    def actualizar_config(self, profesor_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = self.db.execute(text("""
                INSERT INTO profesor_config (profesor_id, usuario_vinculado_id, monto, monto_tipo, especialidad, experiencia_anios, certificaciones, notas)
                VALUES (:pid, :uv, :m, :mt, :e, :ea, :c, :n)
                ON CONFLICT (profesor_id) DO UPDATE SET usuario_vinculado_id = COALESCE(EXCLUDED.usuario_vinculado_id, profesor_config.usuario_vinculado_id),
                    monto = COALESCE(EXCLUDED.monto, profesor_config.monto), monto_tipo = COALESCE(EXCLUDED.monto_tipo, profesor_config.monto_tipo),
                    especialidad = COALESCE(EXCLUDED.especialidad, profesor_config.especialidad), experiencia_anios = COALESCE(EXCLUDED.experiencia_anios, profesor_config.experiencia_anios),
                    certificaciones = COALESCE(EXCLUDED.certificaciones, profesor_config.certificaciones), notas = COALESCE(EXCLUDED.notas, profesor_config.notas), updated_at = NOW()
                RETURNING *
            """), {'pid': profesor_id, 'uv': data.get('usuario_vinculado_id'), 'm': data.get('monto'), 'mt': data.get('monto_tipo', 'mensual'),
                   'e': data.get('especialidad'), 'ea': data.get('experiencia_anios'), 'c': data.get('certificaciones'), 'n': data.get('notas')})
            row = result.fetchone()
            self.db.commit()
            return dict(zip(result.keys(), row)) if row else {}
        except Exception as e:
            logger.error(f"Error updating config: {e}")
            self.db.rollback()
            return {}

    # ========== Resumen ==========
    def resumen_mensual(self, profesor_id: int, mes: int, anio: int) -> Dict[str, Any]:
        try:
            _, last_day = monthrange(anio, mes)
            start_date, end_date = date(anio, mes, 1), date(anio, mes, last_day)
            total = self.db.execute(text("SELECT COALESCE(SUM(duracion_minutos), 0) FROM sesiones WHERE profesor_id = :pid AND DATE(inicio) >= :s AND DATE(inicio) <= :e AND fin IS NOT NULL"),
                {'pid': profesor_id, 's': start_date, 'e': end_date}).fetchone()
            horas_trabajadas = round((total[0] or 0) / 60, 1)
            horarios = self.db.execute(text("SELECT hora_inicio, hora_fin FROM profesor_horarios WHERE profesor_id = :pid AND disponible = TRUE"), {'pid': profesor_id}).fetchall()
            horas_semana = sum((datetime.strptime(str(h[1]), "%H:%M:%S") - datetime.strptime(str(h[0]), "%H:%M:%S")).seconds / 3600 for h in horarios if h[0] and h[1])
            horas_proyectadas = round(horas_semana * 4.3, 1)
            return {'horas_trabajadas': horas_trabajadas, 'horas_proyectadas': horas_proyectadas, 'horas_extra': max(0, round(horas_trabajadas - horas_proyectadas, 1)), 'horas_totales': horas_trabajadas}
        except Exception as e:
            logger.error(f"Error calculating monthly summary: {e}")
            return {'horas_trabajadas': 0, 'horas_proyectadas': 0, 'horas_extra': 0, 'horas_totales': 0}

    def resumen_semanal(self, profesor_id: int, ref_date: date) -> Dict[str, Any]:
        try:
            start = ref_date - timedelta(days=ref_date.weekday())
            end = start + timedelta(days=6)
            total = self.db.execute(text("SELECT COALESCE(SUM(duracion_minutos), 0) FROM sesiones WHERE profesor_id = :pid AND DATE(inicio) >= :s AND DATE(inicio) <= :e AND fin IS NOT NULL"),
                {'pid': profesor_id, 's': start, 'e': end}).fetchone()
            horas_trabajadas = round((total[0] or 0) / 60, 1)
            horarios = self.db.execute(text("SELECT hora_inicio, hora_fin FROM profesor_horarios WHERE profesor_id = :pid AND disponible = TRUE"), {'pid': profesor_id}).fetchall()
            horas_proyectadas = round(sum((datetime.strptime(str(h[1]), "%H:%M:%S") - datetime.strptime(str(h[0]), "%H:%M:%S")).seconds / 3600 for h in horarios if h[0] and h[1]), 1)
            return {'horas_trabajadas': horas_trabajadas, 'horas_proyectadas': horas_proyectadas, 'horas_extra': max(0, round(horas_trabajadas - horas_proyectadas, 1)), 'horas_totales': horas_trabajadas}
        except Exception as e:
            logger.error(f"Error calculating weekly summary: {e}")
            return {'horas_trabajadas': 0, 'horas_proyectadas': 0, 'horas_extra': 0, 'horas_totales': 0}
