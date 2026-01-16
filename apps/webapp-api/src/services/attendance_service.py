"""
Attendance Service - SQLAlchemy ORM Implementation

Provides check-in and attendance tracking operations using SQLAlchemy.
Replaces raw SQL usage in attendance.py with proper ORM queries.
"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, date, timedelta, timezone
import logging
import secrets
import os

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete, text

from src.services.base import BaseService
from src.database.repositories.attendance_repository import AttendanceRepository
from src.database.orm_models import Usuario, Asistencia

logger = logging.getLogger(__name__)


class AttendanceService(BaseService):
    """Service for attendance and check-in operations using SQLAlchemy."""

    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = AttendanceRepository(self.db, None, None)

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

    def _registrar_asistencia_si_no_existe(self, usuario_id: int, fecha: date) -> Optional[int]:
        return self.repo.registrar_asistencia_comun(usuario_id, fecha)

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
            token = secrets.token_urlsafe(24)[:64]
            self.repo.crear_checkin_token(usuario_id, token, expires_minutes)
            return token
        except Exception as e:
            logger.error(f"Error creating check-in token: {e}")
            raise

    def obtener_estado_token(self, token: str) -> Dict[str, Any]:
        """Get token status: exists, used, expired."""
        try:
            cp = self.repo.obtener_checkin_por_token(token)
            if not cp:
                return {'exists': False, 'used': False, 'expired': True}

            usuario_id = cp.get('usuario_id')
            used_flag = bool(cp.get('used'))
            expires_at = self._as_utc_naive(cp.get('expires_at'))
            now = self._now_utc_naive()
            expired = bool(expires_at and expires_at < now)

            attended_today = False
            if usuario_id:
                hoy = self._today_local_date()
                attended_today = (
                    self.db.scalar(
                        select(Asistencia.id).where(Asistencia.usuario_id == int(usuario_id), Asistencia.fecha == hoy).limit(1)
                    )
                    is not None
                )

            used = used_flag or attended_today
            return {'exists': True, 'used': used, 'expired': expired, 'usuario_id': usuario_id}
        except Exception as e:
            logger.error(f"Error getting token status: {e}")
            return {'exists': False, 'used': False, 'expired': True, 'error': str(e)}

    def marcar_token_usado(self, token: str) -> bool:
        """Mark a token as used."""
        try:
            self.repo.marcar_checkin_usado(token)
            return True
        except Exception as e:
            logger.error(f"Error marking token used: {e}")
            return False

    def validar_token_y_registrar(self, token: str, usuario_id: int) -> Tuple[bool, str]:
        """Validate token and register attendance."""
        try:
            status = self.obtener_estado_token(token)

            if not status.get('exists'):
                return False, "Token no encontrado"

            if status.get('expired'):
                return False, "Token expirado"

            if status.get('used'):
                return False, "Token ya utilizado o asistencia ya registrada hoy"

            token_usuario_id = status.get('usuario_id')
            if not token_usuario_id:
                return False, "Token no asociado a usuario"
            if int(token_usuario_id) != int(usuario_id):
                return False, "Token no corresponde al usuario"

            try:
                self.repo.registrar_asistencia(int(usuario_id), self._today_local_date())
            except ValueError:
                return False, "Token ya utilizado o asistencia ya registrada hoy"

            self.marcar_token_usado(token)
            return True, "Asistencia registrada correctamente"
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return False, str(e)

    def validar_token_y_registrar_sin_sesion(self, token: str) -> Tuple[bool, str]:
        """Validate token and register attendance without requiring session user_id.
        Gets user_id from the token itself."""
        try:
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

            is_active, reason = self.verificar_usuario_activo(int(usuario_id))
            if not is_active:
                return False, reason

            user = self.db.get(Usuario, int(usuario_id))
            nombre = (user.nombre or "") if user else ""

            try:
                self.repo.registrar_asistencia(int(usuario_id), self._today_local_date())
            except ValueError:
                return False, "Token ya utilizado"

            self.marcar_token_usado(token)
            return True, nombre or "Asistencia registrada"
        except Exception as e:
            logger.error(f"Error validating token without session: {e}")
            return False, str(e)

    def registrar_asistencia_por_dni(self, dni: str) -> Tuple[bool, str]:
        """Register attendance for a user by DNI lookup."""
        try:
            user = self.db.scalar(select(Usuario).where(Usuario.dni == str(dni)).limit(1))
            if not user:
                return False, "DNI no encontrado"

            usuario_id = int(user.id)
            nombre = user.nombre or ""

            is_active, reason = self.verificar_usuario_activo(usuario_id)
            if not is_active:
                return False, reason or "Usuario inactivo"

            hoy = self._today_local_date()
            if self.db.scalar(select(Asistencia.id).where(Asistencia.usuario_id == usuario_id, Asistencia.fecha == hoy).limit(1)) is not None:
                return True, f"{nombre} - Ya registrado hoy"

            self.repo.registrar_asistencia(usuario_id, hoy)
            return True, nombre
        except Exception as e:
            logger.error(f"Error registering attendance by DNI: {e}")
            return False, str(e)

    def registrar_asistencia_por_dni_y_pin(self, dni: str, pin: str) -> Tuple[bool, str]:
        """Register attendance for a user by DNI + PIN verification (more secure)."""
        try:
            user = self.db.scalar(select(Usuario).where(Usuario.dni == str(dni)).limit(1))
            if not user:
                return False, "DNI no encontrado"

            usuario_id = int(user.id)
            nombre = user.nombre or ""

            is_active, reason = self.verificar_usuario_activo(usuario_id)
            if not is_active:
                return False, reason or "Usuario inactivo"

            stored_pin = str(getattr(user, 'pin', '') or '').strip()
            if not stored_pin:
                return False, "Usuario sin PIN configurado"

            pin_ok = False
            try:
                if stored_pin.startswith('$2'):
                    import bcrypt
                    pin_ok = bool(bcrypt.checkpw(str(pin).encode('utf-8'), stored_pin.encode('utf-8')))
                else:
                    pin_ok = (stored_pin == str(pin).strip())
            except Exception:
                pin_ok = False

            if not pin_ok:
                return False, "PIN incorrecto"

            hoy = self._today_local_date()
            if self.db.scalar(select(Asistencia.id).where(Asistencia.usuario_id == usuario_id, Asistencia.fecha == hoy).limit(1)) is not None:
                return True, f"{nombre} - Ya registrado hoy"

            self.repo.registrar_asistencia(usuario_id, hoy)
            return True, nombre
        except Exception as e:
            logger.error(f"Error registering attendance by DNI+PIN: {e}")
            return False, str(e)


    # ========== Attendance Registration ==========

    def registrar_asistencia(self, usuario_id: int, fecha: Optional[date] = None) -> Optional[int]:
        """Register attendance for a user."""
        try:
            if fecha is None:
                fecha = self._today_local_date()

            is_active, reason = self.verificar_usuario_activo(int(usuario_id))
            if not is_active:
                raise PermissionError(reason or "Usuario inactivo")

            return self.repo.registrar_asistencia(int(usuario_id), fecha)
        except Exception as e:
            logger.error(f"Error registering attendance: {e}")
            raise

    def eliminar_asistencia(self, usuario_id: int, fecha: Optional[date] = None) -> bool:
        """Delete attendance for a user on a specific date."""
        try:
            if fecha is None:
                fecha = self._today_local_date()

            self.db.execute(delete(Asistencia).where(Asistencia.usuario_id == int(usuario_id), Asistencia.fecha == fecha))
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
            start_date = self._today_local_date() - timedelta(days=days)
            result = self.db.execute(
                text("""
                    SELECT fecha::date, COUNT(*) as count
                    FROM asistencias
                    WHERE fecha >= :start_date
                    GROUP BY fecha::date
                    ORDER BY fecha::date
                """),
                {'start_date': start_date}
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
                start_date = self._today_local_date() - timedelta(days=days)
                result = self.db.execute(
                    text("""
                        SELECT EXTRACT(HOUR FROM hora_registro)::INT as hour, COUNT(*) as count
                        FROM asistencias
                        WHERE fecha >= :start_date
                        GROUP BY hour
                        ORDER BY hour
                    """),
                    {'start_date': start_date}
                )
            return [(int(row[0]), int(row[1])) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting hourly attendance: {e}")
            return []

    def obtener_asistencias_hoy_ids(self) -> List[int]:
        """Get list of user IDs who attended today."""
        try:
            hoy = self._today_local_date()
            result = self.db.execute(
                text("SELECT DISTINCT usuario_id FROM asistencias WHERE fecha = :fecha"),
                {'fecha': hoy}
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
                        SELECT a.id, a.usuario_id, a.fecha::date, a.hora_registro, u.nombre
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
                        SELECT a.id, a.usuario_id, a.fecha::date, a.hora_registro, u.nombre
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
                    start_date = self._today_local_date() - timedelta(days=30)
                    query = """
                        SELECT a.id, a.usuario_id, a.fecha::date, a.hora_registro, u.nombre
                        FROM asistencias a
                        JOIN usuarios u ON u.id = a.usuario_id
                        WHERE a.fecha >= :start_date AND (u.nombre ILIKE :q)
                        ORDER BY a.fecha DESC, a.hora_registro DESC
                        LIMIT :limit OFFSET :offset
                    """
                    params['start_date'] = start_date
                    params['q'] = f"%{q}%"
                else:
                    start_date = self._today_local_date() - timedelta(days=30)
                    query = """
                        SELECT a.id, a.usuario_id, a.fecha::date, a.hora_registro, u.nombre
                        FROM asistencias a
                        JOIN usuarios u ON u.id = a.usuario_id
                        WHERE a.fecha >= :start_date
                        ORDER BY a.fecha DESC, a.hora_registro DESC
                        LIMIT :limit OFFSET :offset
                    """
                    params['start_date'] = start_date
            
            result = self.db.execute(text(query), params)
            tz = self._get_app_timezone()
            return [
                {
                    'id': int(row[0]) if row[0] is not None else None,
                    'usuario_id': int(row[1]) if row[1] is not None else None,
                    'fecha': str(row[2]) if row[2] else None,
                    'hora': (
                        self._as_utc_naive(row[3]).replace(tzinfo=timezone.utc).astimezone(tz).time().isoformat(timespec='seconds')
                        if row[3] else None
                    ),
                    'usuario_nombre': row[4] or ''
                }
                for row in result.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting attendance details: {e}")
            return []

    def obtener_asistencias_detalle_paginadas(
        self,
        usuario_id: Optional[int] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        try:
            try:
                lim = max(1, min(int(limit or 50), 200))
            except Exception:
                lim = 50
            try:
                off = max(0, int(offset or 0))
            except Exception:
                off = 0

            params: Dict[str, Any] = {"limit": lim, "offset": off}
            where_parts: list[str] = []

            if usuario_id is not None:
                try:
                    params["usuario_id"] = int(usuario_id)
                    where_parts.append("a.usuario_id = :usuario_id")
                except Exception:
                    pass

            if start and end:
                params["start"] = start
                params["end"] = end
                where_parts.append("a.fecha BETWEEN :start AND :end")
            else:
                start_date = self._today_local_date() - timedelta(days=30)
                params["start_date"] = start_date
                where_parts.append("a.fecha >= :start_date")

            if q and str(q).strip():
                params["q"] = f"%{q}%"
                where_parts.append("(u.nombre ILIKE :q)")

            where_sql = " AND ".join(where_parts) if where_parts else "TRUE"

            count_query = f"""
                SELECT COUNT(*)
                FROM asistencias a
                JOIN usuarios u ON u.id = a.usuario_id
                WHERE {where_sql}
            """
            total = 0
            try:
                total = int(self.db.execute(text(count_query), params).scalar() or 0)
            except Exception:
                total = 0

            query = f"""
                SELECT a.id, a.usuario_id, a.fecha::date, a.hora_registro, u.nombre
                FROM asistencias a
                JOIN usuarios u ON u.id = a.usuario_id
                WHERE {where_sql}
                ORDER BY a.fecha DESC, a.hora_registro DESC
                LIMIT :limit OFFSET :offset
            """
            result = self.db.execute(text(query), params)
            tz = self._get_app_timezone()
            items = [
                {
                    'id': int(row[0]) if row[0] is not None else None,
                    'usuario_id': int(row[1]) if row[1] is not None else None,
                    'fecha': str(row[2]) if row[2] else None,
                    'hora': (
                        self._as_utc_naive(row[3]).replace(tzinfo=timezone.utc).astimezone(tz).time().isoformat(timespec='seconds')
                        if row[3] else None
                    ),
                    'usuario_nombre': row[4] or ''
                }
                for row in result.fetchall()
            ]
            return {"items": items, "total": total}
        except Exception as e:
            logger.error(f"Error getting paged attendance details: {e}")
            return {"items": [], "total": 0}

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
                    created_at TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_station_tokens_token ON checkin_station_tokens(token);
                CREATE INDEX IF NOT EXISTS idx_station_tokens_gym ON checkin_station_tokens(gym_id);
            """))
            try:
                self.db.execute(text("ALTER TABLE checkin_station_tokens ADD COLUMN IF NOT EXISTS created_at TIMESTAMP"))
            except Exception:
                pass
            try:
                self.db.execute(text("ALTER TABLE checkin_station_tokens ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP"))
            except Exception:
                pass
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

            now = self._now_utc_naive()
            min_interval_seconds = int(os.getenv("STATION_TOKEN_MIN_INTERVAL_SECONDS", "2") or 2)
            try:
                active = self.db.execute(
                    text(
                        """
                            SELECT token, expires_at, created_at
                            FROM checkin_station_tokens
                            WHERE gym_id = :gym_id AND used_by IS NULL AND expires_at > :now
                            ORDER BY created_at DESC NULLS LAST, id DESC
                            LIMIT 1
                        """
                    ),
                    {'gym_id': gym_id, 'now': now}
                ).fetchone()
            except Exception:
                active = None

            if active and min_interval_seconds > 0:
                created_at = self._as_utc_naive(active[2])
                if created_at and (now - created_at).total_seconds() < float(min_interval_seconds):
                    expires_at = self._as_utc_naive(active[1])
                    remaining = int((expires_at - now).total_seconds()) if expires_at else int(expires_seconds)
                    return {
                        'token': active[0],
                        'expires_at': expires_at.isoformat() if hasattr(expires_at, 'isoformat') else str(expires_at),
                        'expires_in': max(5, remaining)
                    }
            
            # Invalidate any existing active tokens for this gym
            self.db.execute(
                text("DELETE FROM checkin_station_tokens WHERE gym_id = :gym_id AND used_by IS NULL"),
                {'gym_id': gym_id}
            )
            
            token = secrets.token_urlsafe(16)
            expires_at = self._now_utc_naive() + timedelta(seconds=expires_seconds)
            created_at = self._now_utc_naive()
            
            self.db.execute(
                text("""
                    INSERT INTO checkin_station_tokens (gym_id, token, expires_at, created_at)
                    VALUES (:gym_id, :token, :expires_at, :created_at)
                """),
                {'gym_id': gym_id, 'token': token, 'expires_at': expires_at, 'created_at': created_at}
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
            now = self._now_utc_naive()
            
            # Look for active token
            result = self.db.execute(
                text("""
                    SELECT token, expires_at 
                    FROM checkin_station_tokens 
                    WHERE gym_id = :gym_id AND used_by IS NULL AND expires_at > :now
                    ORDER BY created_at DESC NULLS LAST, id DESC LIMIT 1
                """),
                {'gym_id': gym_id, 'now': now}
            )
            row = result.fetchone()
            
            if row:
                expires_at = self._as_utc_naive(row[1])
                if expires_at is None:
                    return self.crear_station_token(gym_id)
                remaining = int((expires_at - now).total_seconds())
                
                # Ensure we have a minimum positive value to avoid instant refresh loops
                if remaining < 5:
                    # Token about to expire, create new one
                    return self.crear_station_token(gym_id)
                
                return {
                    'token': row[0],
                    'expires_at': expires_at.isoformat() if hasattr(expires_at, 'isoformat') else str(expires_at),
                    'expires_in': max(5, remaining)  # Minimum 5 seconds to prevent rapid polling
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
            now = self._now_utc_naive()
            expires_at = self._as_utc_naive(expires_at)
            if expires_at and expires_at < now:
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

            is_active, reason = self.verificar_usuario_activo(int(usuario_id))
            if not is_active:
                return False, reason or "Usuario inactivo", None
            
            # Check if already attended today
            hoy = self._today_local_date()
            check = self.db.execute(
                text("""
                    SELECT 1 FROM asistencias 
                    WHERE usuario_id = :id AND fecha = :fecha LIMIT 1
                """),
                {'id': usuario_id, 'fecha': hoy}
            )
            if check.fetchone():
                return True, f"{nombre} - Ya registrado hoy", {
                    'nombre': nombre,
                    'dni': dni,
                    'already_checked': True
                }
            
            try:
                self._registrar_asistencia_si_no_existe(int(usuario_id), hoy)
            except ValueError:
                pass
            
            # Mark token as used
            used_at = self._now_utc_naive()
            self.db.execute(
                text("""
                    UPDATE checkin_station_tokens 
                    SET used_by = :user_id, used_at = :used_at 
                    WHERE id = :token_id
                """),
                {'user_id': usuario_id, 'token_id': token_id, 'used_at': used_at}
            )
            
            self.db.commit()
            hora_local = self._now_local().time().isoformat(timespec='seconds')
            
            return True, "Check-in exitoso", {
                'nombre': nombre,
                'dni': dni,
                'hora': hora_local,
                'already_checked': False
            }
        except Exception as e:
            logger.error(f"Error validating station scan: {e}")
            self.db.rollback()
            return False, str(e), None

    def obtener_station_checkins_recientes(self, gym_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent check-ins for the station display."""
        try:
            hoy = self._today_local_date()
            tz = self._get_app_timezone()
            result = self.db.execute(
                text("""
                    SELECT u.nombre, u.dni, a.hora_registro
                    FROM asistencias a
                    JOIN usuarios u ON u.id = a.usuario_id
                    WHERE a.fecha = :fecha
                    ORDER BY a.hora_registro DESC
                    LIMIT :limit
                """),
                {'limit': limit, 'fecha': hoy}
            )
            return [
                {
                    'nombre': row[0] or '',
                    'dni': row[1] or '',
                    'hora': (
                        self._as_utc_naive(row[2]).replace(tzinfo=timezone.utc).astimezone(tz).time().isoformat(timespec='seconds')
                        if row[2] else ''
                    )
                }
                for row in result.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting recent station check-ins: {e}")
            return []

    def obtener_station_stats(self, gym_id: int) -> Dict[str, int]:
        """Get today's check-in stats for station display."""
        try:
            hoy = self._today_local_date()
            result = self.db.execute(
                text("""
                    SELECT COUNT(*) FROM asistencias WHERE fecha = :fecha
                """),
                {'fecha': hoy}
            )
            total_hoy = result.scalar() or 0
            
            return {
                'total_hoy': total_hoy
            }
        except Exception as e:
            logger.error(f"Error getting station stats: {e}")
            return {'total_hoy': 0}

