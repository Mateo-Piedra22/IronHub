"""
Attendance Service - SQLAlchemy ORM Implementation

Provides check-in and attendance tracking operations using SQLAlchemy.
Replaces raw SQL usage in attendance.py with proper ORM queries.
"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, date, timedelta, timezone
import logging
import secrets

from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete, text

from src.services.base import BaseService

logger = logging.getLogger(__name__)


class AttendanceService(BaseService):
    """Service for attendance and check-in operations using SQLAlchemy."""

    def __init__(self, db: Session):
        super().__init__(db)

    # ========== User Status Check ==========

    def verificar_usuario_activo(self, usuario_id: int) -> Tuple[bool, str]:
        """Check if user is active. Returns (is_active, reason_if_inactive)."""
        try:
            result = self.db.execute(
                text("""
                    SELECT activo, LOWER(COALESCE(rol,'socio')) AS rol, 
                           COALESCE(cuotas_vencidas,0) AS cuotas_vencidas
                    FROM usuarios WHERE id = :id LIMIT 1
                """),
                {'id': usuario_id}
            )
            row = result.fetchone()
            if not row:
                return False, "Usuario no encontrado"
            
            activo = bool(row[0]) if row[0] is not None else True
            rol = (row[1] or 'socio').lower()
            cuotas_vencidas = int(row[2] or 0)
            
            # Exempt roles
            if rol in ('profesor', 'owner', 'dueño', 'dueno'):
                return True, ""
            
            if not activo:
                if cuotas_vencidas >= 3:
                    return False, "Desactivado por falta de pagos"
                return False, "Desactivado por administración"
            
            return True, ""
        except Exception as e:
            logger.error(f"Error checking user active status: {e}")
            return True, ""  # Fail open

    # ========== Token Management ==========

    def crear_checkin_token(self, usuario_id: int, expires_minutes: int = 5) -> str:
        """Create a check-in token for a user."""
        try:
            token = secrets.token_urlsafe(12)
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
            
            self.db.execute(
                text("""
                    INSERT INTO checkin_pending (usuario_id, token, expires_at, used)
                    VALUES (:usuario_id, :token, :expires_at, FALSE)
                """),
                {
                    'usuario_id': usuario_id,
                    'token': token,
                    'expires_at': expires_at
                }
            )
            self.db.commit()
            return token
        except Exception as e:
            logger.error(f"Error creating check-in token: {e}")
            self.db.rollback()
            raise

    def obtener_estado_token(self, token: str) -> Dict[str, Any]:
        """Get token status: exists, used, expired."""
        try:
            result = self.db.execute(
                text("""
                    SELECT usuario_id, used, expires_at 
                    FROM checkin_pending 
                    WHERE token = :token LIMIT 1
                """),
                {'token': token}
            )
            row = result.fetchone()
            
            if not row:
                return {'exists': False, 'used': False, 'expired': True}
            
            usuario_id = row[0]
            used_flag = bool(row[1]) if row[1] is not None else False
            expires_at = row[2]
            
            now = datetime.now(timezone.utc)
            if expires_at and expires_at.tzinfo is None:
                now = now.replace(tzinfo=None)
            
            expired = bool(expires_at and expires_at < now)
            
            # Check if user already attended today
            attended_today = False
            if usuario_id:
                check = self.db.execute(
                    text("""
                        SELECT 1 FROM asistencias 
                        WHERE usuario_id = :id AND fecha::date = CURRENT_DATE LIMIT 1
                    """),
                    {'id': usuario_id}
                )
                attended_today = check.fetchone() is not None
            
            used = used_flag or attended_today
            
            return {
                'exists': True,
                'used': used,
                'expired': expired,
                'usuario_id': usuario_id
            }
        except Exception as e:
            logger.error(f"Error getting token status: {e}")
            return {'exists': False, 'used': False, 'expired': True, 'error': str(e)}

    def marcar_token_usado(self, token: str) -> bool:
        """Mark a token as used."""
        try:
            self.db.execute(
                text("UPDATE checkin_pending SET used = TRUE WHERE token = :token"),
                {'token': token}
            )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error marking token used: {e}")
            self.db.rollback()
            return False

    def validar_token_y_registrar(self, token: str, usuario_id: int) -> Tuple[bool, str]:
        """Validate token and register attendance."""
        try:
            # Check token exists and is valid
            status = self.obtener_estado_token(token)
            
            if not status.get('exists'):
                return False, "Token no encontrado"
            
            if status.get('expired'):
                return False, "Token expirado"
            
            if status.get('used'):
                return False, "Token ya utilizado o asistencia ya registrada hoy"
            
            # Register attendance
            self.db.execute(
                text("""
                    INSERT INTO asistencias (usuario_id, fecha, hora_registro)
                    VALUES (:id, CURRENT_DATE, CURRENT_TIME)
                    ON CONFLICT (usuario_id, fecha) DO NOTHING
                """),
                {'id': usuario_id}
            )
            
            # Mark token as used
            self.marcar_token_usado(token)
            
            self.db.commit()
            return True, "Asistencia registrada correctamente"
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            self.db.rollback()
            return False, str(e)

    # ========== Attendance Registration ==========

    def registrar_asistencia(self, usuario_id: int, fecha: Optional[date] = None) -> Optional[int]:
        """Register attendance for a user."""
        try:
            if fecha is None:
                fecha = date.today()
            
            result = self.db.execute(
                text("""
                    INSERT INTO asistencias (usuario_id, fecha, hora_registro)
                    VALUES (:id, :fecha, CURRENT_TIME)
                    ON CONFLICT (usuario_id, fecha) DO NOTHING
                    RETURNING id
                """),
                {'id': usuario_id, 'fecha': fecha}
            )
            row = result.fetchone()
            self.db.commit()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Error registering attendance: {e}")
            self.db.rollback()
            raise

    def eliminar_asistencia(self, usuario_id: int, fecha: Optional[date] = None) -> bool:
        """Delete attendance for a user on a specific date."""
        try:
            if fecha is None:
                fecha = date.today()
            
            self.db.execute(
                text("DELETE FROM asistencias WHERE usuario_id = :id AND fecha = :fecha"),
                {'id': usuario_id, 'fecha': fecha}
            )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting attendance: {e}")
            self.db.rollback()
            raise

    # ========== Attendance Reporting ==========

    def obtener_asistencias_por_dia(self, days: int = 30) -> List[Tuple[str, int]]:
        """Get daily attendance counts for the past N days."""
        try:
            result = self.db.execute(
                text("""
                    SELECT fecha::date, COUNT(*) as count
                    FROM asistencias
                    WHERE fecha >= CURRENT_DATE - :days * INTERVAL '1 day'
                    GROUP BY fecha::date
                    ORDER BY fecha::date
                """),
                {'days': days}
            )
            return [(str(row[0]), int(row[1])) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting daily attendance: {e}")
            return []

    def obtener_asistencias_por_rango(self, start: str, end: str) -> List[Tuple[str, int]]:
        """Get daily attendance counts for a date range."""
        try:
            result = self.db.execute(
                text("""
                    SELECT fecha::date, COUNT(*) as count
                    FROM asistencias
                    WHERE fecha BETWEEN :start AND :end
                    GROUP BY fecha::date
                    ORDER BY fecha::date
                """),
                {'start': start, 'end': end}
            )
            return [(str(row[0]), int(row[1])) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting attendance by range: {e}")
            return []

    def obtener_asistencias_por_hora(self, days: int = 30, start: Optional[str] = None, end: Optional[str] = None) -> List[Tuple[int, int]]:
        """Get hourly attendance distribution."""
        try:
            if start and end:
                result = self.db.execute(
                    text("""
                        SELECT EXTRACT(HOUR FROM hora_registro)::INT as hour, COUNT(*) as count
                        FROM asistencias
                        WHERE fecha BETWEEN :start AND :end
                        GROUP BY hour
                        ORDER BY hour
                    """),
                    {'start': start, 'end': end}
                )
            else:
                result = self.db.execute(
                    text("""
                        SELECT EXTRACT(HOUR FROM hora_registro)::INT as hour, COUNT(*) as count
                        FROM asistencias
                        WHERE fecha >= CURRENT_DATE - :days * INTERVAL '1 day'
                        GROUP BY hour
                        ORDER BY hour
                    """),
                    {'days': days}
                )
            return [(int(row[0]), int(row[1])) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting hourly attendance: {e}")
            return []

    def obtener_asistencias_hoy_ids(self) -> List[int]:
        """Get list of user IDs who attended today."""
        try:
            result = self.db.execute(
                text("SELECT DISTINCT usuario_id FROM asistencias WHERE fecha::date = CURRENT_DATE")
            )
            return [int(row[0]) for row in result.fetchall() if row[0]]
        except Exception as e:
            logger.error(f"Error getting today's attendees: {e}")
            return []

    def obtener_asistencias_detalle(
        self, 
        start: Optional[str] = None, 
        end: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 500,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get detailed attendance list with user names."""
        try:
            params = {'limit': limit, 'offset': offset}
            
            if start and end:
                if q:
                    query = """
                        SELECT a.fecha::date, a.hora_registro, u.nombre
                        FROM asistencias a
                        JOIN usuarios u ON u.id = a.usuario_id
                        WHERE a.fecha BETWEEN :start AND :end AND (u.nombre ILIKE :q)
                        ORDER BY a.fecha DESC, a.hora_registro DESC
                        LIMIT :limit OFFSET :offset
                    """
                    params['start'] = start
                    params['end'] = end
                    params['q'] = f"%{q}%"
                else:
                    query = """
                        SELECT a.fecha::date, a.hora_registro, u.nombre
                        FROM asistencias a
                        JOIN usuarios u ON u.id = a.usuario_id
                        WHERE a.fecha BETWEEN :start AND :end
                        ORDER BY a.fecha DESC, a.hora_registro DESC
                        LIMIT :limit OFFSET :offset
                    """
                    params['start'] = start
                    params['end'] = end
            else:
                if q:
                    query = """
                        SELECT a.fecha::date, a.hora_registro, u.nombre
                        FROM asistencias a
                        JOIN usuarios u ON u.id = a.usuario_id
                        WHERE a.fecha >= CURRENT_DATE - INTERVAL '30 days' AND (u.nombre ILIKE :q)
                        ORDER BY a.fecha DESC, a.hora_registro DESC
                        LIMIT :limit OFFSET :offset
                    """
                    params['q'] = f"%{q}%"
                else:
                    query = """
                        SELECT a.fecha::date, a.hora_registro, u.nombre
                        FROM asistencias a
                        JOIN usuarios u ON u.id = a.usuario_id
                        WHERE a.fecha >= CURRENT_DATE - INTERVAL '30 days'
                        ORDER BY a.fecha DESC, a.hora_registro DESC
                        LIMIT :limit OFFSET :offset
                    """
            
            result = self.db.execute(text(query), params)
            return [
                {
                    'fecha': str(row[0]) if row[0] else None,
                    'hora': str(row[1]) if row[1] else None,
                    'usuario': row[2] or ''
                }
                for row in result.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting attendance details: {e}")
            return []
