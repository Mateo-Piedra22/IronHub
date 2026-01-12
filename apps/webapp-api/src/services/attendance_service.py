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

    def validar_token_y_registrar_sin_sesion(self, token: str) -> Tuple[bool, str]:
        """Validate token and register attendance without requiring session user_id.
        Gets user_id from the token itself."""
        try:
            # Get user_id from token
            status = self.obtener_estado_token(token)
            
            if not status.get('exists'):
                return False, "Token no encontrado"
            
            if status.get('expired'):
                return False, "Token expirado"
            
            if status.get('used'):
                return False, "Token ya utilizado"
            
            usuario_id = status.get('usuario_id')
            if not usuario_id:
                return False, "Token no asociado a usuario"
            
            # Check if user is active
            is_active, reason = self.verificar_usuario_activo(usuario_id)
            if not is_active:
                return False, reason
            
            # Get user name for response
            result = self.db.execute(
                text("SELECT nombre FROM usuarios WHERE id = :id LIMIT 1"),
                {'id': usuario_id}
            )
            row = result.fetchone()
            nombre = row[0] if row else ""
            
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
            return True, nombre or "Asistencia registrada"
        except Exception as e:
            logger.error(f"Error validating token without session: {e}")
            self.db.rollback()
            return False, str(e)

    def registrar_asistencia_por_dni(self, dni: str) -> Tuple[bool, str]:
        """Register attendance for a user by DNI lookup."""
        try:
            # Find user by DNI
            result = self.db.execute(
                text("SELECT id, nombre, activo FROM usuarios WHERE dni = :dni LIMIT 1"),
                {'dni': dni}
            )
            row = result.fetchone()
            
            if not row:
                return False, "DNI no encontrado"
            
            usuario_id = row[0]
            nombre = row[1] or ""
            activo = bool(row[2]) if row[2] is not None else True
            
            if not activo:
                return False, "Usuario inactivo"
            
            # Check if already attended today
            check = self.db.execute(
                text("""
                    SELECT 1 FROM asistencias 
                    WHERE usuario_id = :id AND fecha::date = CURRENT_DATE LIMIT 1
                """),
                {'id': usuario_id}
            )
            if check.fetchone():
                return True, f"{nombre} - Ya registrado hoy"
            
            # Register attendance
            self.db.execute(
                text("""
                    INSERT INTO asistencias (usuario_id, fecha, hora_registro)
                    VALUES (:id, CURRENT_DATE, CURRENT_TIME)
                    ON CONFLICT (usuario_id, fecha) DO NOTHING
                """),
                {'id': usuario_id}
            )
            
            self.db.commit()
            return True, nombre
        except Exception as e:
            logger.error(f"Error registering attendance by DNI: {e}")
            self.db.rollback()
            return False, str(e)

    def registrar_asistencia_por_dni_y_pin(self, dni: str, pin: str) -> Tuple[bool, str]:
        """Register attendance for a user by DNI + PIN verification (more secure)."""
        try:
            # Find user by DNI and verify PIN
            result = self.db.execute(
                text("SELECT id, nombre, activo, pin FROM usuarios WHERE dni = :dni LIMIT 1"),
                {'dni': dni}
            )
            row = result.fetchone()
            
            if not row:
                return False, "DNI no encontrado"
            
            usuario_id = row[0]
            nombre = row[1] or ""
            activo = bool(row[2]) if row[2] is not None else True
            stored_pin = row[3] or ""
            
            if not activo:
                return False, "Usuario inactivo"
            
            # Verify PIN
            if not stored_pin:
                return False, "Usuario sin PIN configurado"
            
            if stored_pin != pin:
                return False, "PIN incorrecto"
            
            # Check if already attended today
            check = self.db.execute(
                text("""
                    SELECT 1 FROM asistencias 
                    WHERE usuario_id = :id AND fecha::date = CURRENT_DATE LIMIT 1
                """),
                {'id': usuario_id}
            )
            if check.fetchone():
                return True, f"{nombre} - Ya registrado hoy"
            
            # Register attendance
            self.db.execute(
                text("""
                    INSERT INTO asistencias (usuario_id, fecha, hora_registro)
                    VALUES (:id, CURRENT_DATE, CURRENT_TIME)
                    ON CONFLICT (usuario_id, fecha) DO NOTHING
                """),
                {'id': usuario_id}
            )
            
            self.db.commit()
            return True, nombre
        except Exception as e:
            logger.error(f"Error registering attendance by DNI+PIN: {e}")
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

    # ========== Station QR Check-in ==========

    def _ensure_station_tables(self) -> None:
        """Ensure station tables exist."""
        try:
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS checkin_station_tokens (
                    id SERIAL PRIMARY KEY,
                    gym_id INTEGER NOT NULL,
                    token VARCHAR(64) UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    used_by INTEGER,
                    used_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_station_tokens_token ON checkin_station_tokens(token);
                CREATE INDEX IF NOT EXISTS idx_station_tokens_gym ON checkin_station_tokens(gym_id);
            """))
            self.db.commit()
        except Exception as e:
            logger.warning(f"Station tables may already exist: {e}")
            self.db.rollback()

    def generar_station_key(self, gym_id: int) -> str:
        """Generate or get existing station key for a gym (stored in admin DB)."""
        try:
            import os
            from src.database.raw_manager import RawPostgresManager
            
            admin_params = {
                "host": os.getenv("ADMIN_DB_HOST", os.getenv("DB_HOST", "localhost")),
                "port": int(os.getenv("ADMIN_DB_PORT", os.getenv("DB_PORT", 5432))),
                "database": os.getenv("ADMIN_DB_NAME", "ironhub_admin"),
                "user": os.getenv("ADMIN_DB_USER", os.getenv("DB_USER", "postgres")),
                "password": os.getenv("ADMIN_DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
                "sslmode": os.getenv("ADMIN_DB_SSLMODE", os.getenv("DB_SSLMODE", "require")),
            }
            
            db = RawPostgresManager(connection_params=admin_params)
            with db.get_connection_context() as conn:
                cur = conn.cursor()
                
                # Auto-migrate: ensure station_key column exists
                cur.execute("""
                    ALTER TABLE gyms ADD COLUMN IF NOT EXISTS station_key VARCHAR(64)
                """)
                conn.commit()
                
                # Check if gym already has a station key
                cur.execute("SELECT station_key FROM gyms WHERE id = %s LIMIT 1", (gym_id,))
                row = cur.fetchone()
                if row and row[0]:
                    return row[0]
                
                # Generate new station key
                station_key = secrets.token_urlsafe(16)
                
                # Update station key in gyms table
                cur.execute(
                    "UPDATE gyms SET station_key = %s WHERE id = %s",
                    (station_key, gym_id)
                )
                conn.commit()
                return station_key
        except Exception as e:
            logger.error(f"Error generating station key: {e}")
            # Fallback to simple key (won't persist but at least returns something)
            return secrets.token_urlsafe(16)

    def validar_station_key(self, station_key: str) -> Optional[int]:
        """Validate station key and return gym_id, or None if invalid (checks admin DB)."""
        try:
            import os
            from src.database.raw_manager import RawPostgresManager
            
            admin_params = {
                "host": os.getenv("ADMIN_DB_HOST", os.getenv("DB_HOST", "localhost")),
                "port": int(os.getenv("ADMIN_DB_PORT", os.getenv("DB_PORT", 5432))),
                "database": os.getenv("ADMIN_DB_NAME", "ironhub_admin"),
                "user": os.getenv("ADMIN_DB_USER", os.getenv("DB_USER", "postgres")),
                "password": os.getenv("ADMIN_DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
                "sslmode": os.getenv("ADMIN_DB_SSLMODE", os.getenv("DB_SSLMODE", "require")),
            }
            
            db = RawPostgresManager(connection_params=admin_params)
            with db.get_connection_context() as conn:
                cur = conn.cursor()
                
                # Auto-migrate: ensure station_key column exists
                cur.execute("""
                    ALTER TABLE gyms ADD COLUMN IF NOT EXISTS station_key VARCHAR(64)
                """)
                conn.commit()
                
                cur.execute("SELECT id FROM gyms WHERE station_key = %s LIMIT 1", (station_key,))
                row = cur.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Error validating station key: {e}")
            return None

    def crear_station_token(self, gym_id: int, expires_seconds: int = 300) -> Dict[str, Any]:
        """Create a new station token for the gym's QR display."""
        try:
            self._ensure_station_tables()
            
            # Invalidate any existing active tokens for this gym
            self.db.execute(
                text("DELETE FROM checkin_station_tokens WHERE gym_id = :gym_id AND used_by IS NULL"),
                {'gym_id': gym_id}
            )
            
            # Create new token
            token = secrets.token_urlsafe(16)
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_seconds)
            
            self.db.execute(
                text("""
                    INSERT INTO checkin_station_tokens (gym_id, token, expires_at)
                    VALUES (:gym_id, :token, :expires_at)
                """),
                {'gym_id': gym_id, 'token': token, 'expires_at': expires_at}
            )
            self.db.commit()
            
            return {
                'token': token,
                'expires_at': expires_at.isoformat(),
                'expires_in': expires_seconds
            }
        except Exception as e:
            logger.error(f"Error creating station token: {e}")
            self.db.rollback()
            raise

    def obtener_station_token_activo(self, gym_id: int) -> Optional[Dict[str, Any]]:
        """Get active (unused, non-expired) station token for gym, or create new one."""
        try:
            self._ensure_station_tables()
            
            # Look for active token
            result = self.db.execute(
                text("""
                    SELECT token, expires_at 
                    FROM checkin_station_tokens 
                    WHERE gym_id = :gym_id AND used_by IS NULL AND expires_at > NOW()
                    ORDER BY created_at DESC LIMIT 1
                """),
                {'gym_id': gym_id}
            )
            row = result.fetchone()
            
            if row:
                expires_at = row[1]
                now = datetime.now(timezone.utc)
                if expires_at.tzinfo is None:
                    now = now.replace(tzinfo=None)
                remaining = int((expires_at - now).total_seconds())
                
                return {
                    'token': row[0],
                    'expires_at': expires_at.isoformat() if hasattr(expires_at, 'isoformat') else str(expires_at),
                    'expires_in': max(0, remaining)
                }
            
            # No active token, create new one
            return self.crear_station_token(gym_id)
        except Exception as e:
            logger.error(f"Error getting active station token: {e}")
            return self.crear_station_token(gym_id)

    def validar_station_scan(self, token: str, usuario_id: int) -> Tuple[bool, str, Optional[Dict]]:
        """
        Validate a station token scan and register attendance.
        Returns (success, message, user_data).
        """
        try:
            # Check token exists and is valid
            result = self.db.execute(
                text("""
                    SELECT id, gym_id, expires_at, used_by 
                    FROM checkin_station_tokens 
                    WHERE token = :token LIMIT 1
                """),
                {'token': token}
            )
            row = result.fetchone()
            
            if not row:
                return False, "Código QR inválido", None
            
            token_id, gym_id, expires_at, used_by = row
            
            # Check if already used
            if used_by:
                return False, "Código QR ya utilizado", None
            
            # Check expiration
            now = datetime.now(timezone.utc)
            if expires_at.tzinfo is None:
                now = now.replace(tzinfo=None)
            if expires_at < now:
                return False, "Código QR expirado", None
            
            # Get user info
            user_result = self.db.execute(
                text("SELECT nombre, dni, activo FROM usuarios WHERE id = :id LIMIT 1"),
                {'id': usuario_id}
            )
            user_row = user_result.fetchone()
            
            if not user_row:
                return False, "Usuario no encontrado", None
            
            nombre, dni, activo = user_row
            
            if not activo:
                return False, "Usuario inactivo", None
            
            # Check if already attended today
            check = self.db.execute(
                text("""
                    SELECT 1 FROM asistencias 
                    WHERE usuario_id = :id AND fecha::date = CURRENT_DATE LIMIT 1
                """),
                {'id': usuario_id}
            )
            if check.fetchone():
                return True, f"{nombre} - Ya registrado hoy", {
                    'nombre': nombre,
                    'dni': dni,
                    'already_checked': True
                }
            
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
            self.db.execute(
                text("""
                    UPDATE checkin_station_tokens 
                    SET used_by = :user_id, used_at = NOW() 
                    WHERE id = :token_id
                """),
                {'user_id': usuario_id, 'token_id': token_id}
            )
            
            self.db.commit()
            
            return True, "Check-in exitoso", {
                'nombre': nombre,
                'dni': dni,
                'hora': datetime.now().strftime('%H:%M:%S'),
                'already_checked': False
            }
        except Exception as e:
            logger.error(f"Error validating station scan: {e}")
            self.db.rollback()
            return False, str(e), None

    def obtener_station_checkins_recientes(self, gym_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent check-ins for the station display."""
        try:
            result = self.db.execute(
                text("""
                    SELECT u.nombre, u.dni, a.hora_registro
                    FROM asistencias a
                    JOIN usuarios u ON u.id = a.usuario_id
                    WHERE a.fecha::date = CURRENT_DATE
                    ORDER BY a.hora_registro DESC
                    LIMIT :limit
                """),
                {'limit': limit}
            )
            return [
                {
                    'nombre': row[0] or '',
                    'dni': row[1] or '',
                    'hora': str(row[2])[:8] if row[2] else ''
                }
                for row in result.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting recent station check-ins: {e}")
            return []

    def obtener_station_stats(self, gym_id: int) -> Dict[str, int]:
        """Get today's check-in stats for station display."""
        try:
            result = self.db.execute(
                text("""
                    SELECT COUNT(*) FROM asistencias WHERE fecha::date = CURRENT_DATE
                """)
            )
            total_hoy = result.scalar() or 0
            
            return {
                'total_hoy': total_hoy
            }
        except Exception as e:
            logger.error(f"Error getting station stats: {e}")
            return {'total_hoy': 0}

