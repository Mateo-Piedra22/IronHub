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
import json

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

from sqlalchemy.orm import Session
from sqlalchemy import select, delete, text

from src.services.base import BaseService
from src.database.repositories.attendance_repository import AttendanceRepository
from src.database.orm_models import Usuario, Asistencia, Configuracion, Sucursal

logger = logging.getLogger(__name__)

ATTENDANCE_ALLOW_MULTIPLE_KEY = "attendance_allow_multiple_per_day"


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

    def _registrar_asistencia_si_no_existe(
        self, usuario_id: int, fecha: date, sucursal_id: Optional[int] = None
    ) -> Optional[int]:
        return self.repo.registrar_asistencia_comun(
            usuario_id,
            fecha,
            allow_multiple=self._allow_multiple_attendances_per_day(),
            sucursal_id=int(sucursal_id) if sucursal_id is not None else None,
        )

    def _get_default_sucursal_id(self) -> Optional[int]:
        try:
            sid = self.db.scalar(select(Sucursal.id).order_by(Sucursal.id.asc()).limit(1))
            return int(sid) if sid is not None else None
        except Exception:
            return None

    def _allow_multiple_attendances_per_day(self) -> bool:
        try:
            row = self.db.scalar(
                select(Configuracion.valor)
                .where(Configuracion.clave == ATTENDANCE_ALLOW_MULTIPLE_KEY)
                .limit(1)
            )
            if row is None:
                return False
            s = str(row)
            try:
                import json as _json

                v = _json.loads(s)
                return bool(v)
            except Exception:
                return s.strip().lower() in ("1", "true", "yes", "y", "on")
        except Exception:
            return False

    def idempotency_get_response(
        self, key: str, request_hash: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        k = str(key or "").strip()
        if not k:
            return None
        params: Dict[str, Any] = {"k": k}
        where = "key = :k AND (expires_at IS NULL OR expires_at > NOW())"
        if request_hash:
            where += " AND request_hash = :rh"
            params["rh"] = str(request_hash)
        row = self.db.execute(
            text(
                f"""
                SELECT response_status, response_body, expires_at
                FROM checkin_idempotency
                WHERE {where}
                LIMIT 1
                """
            ),
            params,
        ).fetchone()
        if not row:
            return None
        status_code = row[0]
        body = row[1]
        if status_code is None or body is None:
            return {"pending": True}
        try:
            parsed = body if isinstance(body, dict) else json.loads(body)
        except Exception:
            parsed = {"ok": False, "mensaje": "Respuesta inválida (idempotency)"}
        return {"pending": False, "status_code": int(status_code), "body": parsed}

    def idempotency_reserve(
        self,
        key: str,
        *,
        usuario_id: Optional[int],
        route: str,
        request_hash: Optional[str] = None,
        ttl_seconds: int = 60,
    ) -> bool:
        k = str(key or "").strip()
        if not k:
            return False
        try:
            self.db.execute(
                text(
                    """
                    INSERT INTO checkin_idempotency(key, expires_at, usuario_id, route, request_hash, response_status, response_body)
                    VALUES (:k, NOW() + (:ttl * INTERVAL '1 second'), :uid, :route, :rh, NULL, NULL)
                    ON CONFLICT (key) DO NOTHING
                    """
                ),
                {
                    "k": k,
                    "ttl": int(ttl_seconds),
                    "uid": int(usuario_id) if usuario_id is not None else None,
                    "route": str(route or ""),
                    "rh": str(request_hash) if request_hash else None,
                },
            )
            self.db.commit()
            return True
        except Exception:
            try:
                self.db.rollback()
            except Exception:
                pass
            return False

    def idempotency_store_response(
        self, key: str, *, status_code: int, body: Dict[str, Any]
    ) -> None:
        k = str(key or "").strip()
        if not k:
            return
        try:
            payload = json.dumps(body or {}, ensure_ascii=False)
            self.db.execute(
                text(
                    """
                    UPDATE checkin_idempotency
                    SET response_status = :s, response_body = CAST(:b AS JSONB)
                    WHERE key = :k
                    """
                ),
                {"k": k, "s": int(status_code), "b": payload},
            )
            self.db.commit()
        except Exception:
            try:
                self.db.rollback()
            except Exception:
                pass
        except Exception:
            try:
                self.db.rollback()
            except Exception:
                pass

    def _count_asistencias_usuario_fecha(self, usuario_id: int, fecha: date) -> int:
        try:
            return int(
                self.db.execute(
                    text(
                        "SELECT COUNT(*) FROM asistencias WHERE usuario_id = :uid AND fecha = :f"
                    ),
                    {"uid": int(usuario_id), "f": fecha},
                ).scalar()
                or 0
            )
        except Exception:
            return 0

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
                {"id": usuario_id},
            )
            row = result.fetchone()
            if not row:
                return False, "Usuario no encontrado"

            activo = bool(row[0]) if row[0] is not None else True
            rol = (row[1] or "socio").lower()
            cuotas_vencidas = int(row[2] or 0)

            # Exempt roles
            if rol in ("profesor", "owner", "dueño", "dueno"):
                return True, ""

            if not activo:
                if cuotas_vencidas >= 3:
                    return False, "Desactivado por falta de pagos"
                return False, "Desactivado por administración"

            return True, ""
        except Exception as e:
            logger.error(f"Error checking user active status: {e}")
            return False, "No se pudo validar estado del usuario"

    def verificar_acceso_usuario_sucursal(
        self, usuario_id: int, sucursal_id: Optional[int]
    ) -> Tuple[bool, str]:
        sid = None
        try:
            sid = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sid = None
        if not sid:
            sid = self._get_default_sucursal_id()
        if not sid:
            return False, "Sucursal no encontrada"
        try:
            try:
                from src.services.entitlements_service import EntitlementsService

                ok_opt, reason = EntitlementsService(self.db).check_branch_access(
                    int(usuario_id), int(sid)
                )
                if ok_opt is not None:
                    return bool(ok_opt), str(reason or "")
            except Exception:
                pass
            from src.services.membership_service import MembershipService

            ok_opt, reason = MembershipService(self.db).check_access(
                int(usuario_id), int(sid)
            )
            if ok_opt is None:
                return self.verificar_usuario_activo(int(usuario_id))
            return bool(ok_opt), str(reason or "")
        except Exception:
            return self.verificar_usuario_activo(int(usuario_id))

    # ========== Token Management ==========

    def crear_checkin_token(
        self,
        usuario_id: int,
        expires_minutes: int = 5,
        sucursal_id: Optional[int] = None,
    ) -> str:
        """Create a check-in token for a user."""
        try:
            token = secrets.token_urlsafe(24)[:64]
            sid = (
                int(sucursal_id)
                if sucursal_id is not None
                else self._get_default_sucursal_id()
            )
            self.repo.crear_checkin_token(
                usuario_id,
                token,
                expires_minutes,
                sucursal_id=int(sid) if sid is not None else None,
            )
            return token
        except Exception as e:
            logger.error(f"Error creating check-in token: {e}")
            raise

    def obtener_estado_token(self, token: str) -> Dict[str, Any]:
        """Get token status: exists, used, expired."""
        try:
            cp = self.repo.obtener_checkin_por_token(token)
            if not cp:
                return {"exists": False, "used": False, "expired": True}

            usuario_id = cp.get("usuario_id")
            used_flag = bool(cp.get("used"))
            expires_at = self._as_utc_naive(cp.get("expires_at"))
            now = self._now_utc_naive()
            expired = bool(expires_at and expires_at < now)

            attended_today = False
            if usuario_id:
                hoy = self._today_local_date()
                sid = cp.get("sucursal_id")
                try:
                    sid = int(sid) if sid is not None else None
                except Exception:
                    sid = None
                attended_today = (
                    self.db.scalar(
                        select(Asistencia.id)
                        .where(
                            Asistencia.usuario_id == int(usuario_id),
                            Asistencia.fecha == hoy,
                            Asistencia.sucursal_id
                            == (int(sid) if sid is not None else None),
                        )
                        .limit(1)
                    )
                    is not None
                )

            allow_multiple = self._allow_multiple_attendances_per_day()
            used = used_flag or (attended_today and (not allow_multiple))
            return {
                "exists": True,
                "used": used,
                "expired": expired,
                "usuario_id": usuario_id,
                "sucursal_id": cp.get("sucursal_id"),
            }
        except Exception as e:
            logger.error(f"Error getting token status: {e}")
            return {"exists": False, "used": False, "expired": True, "error": str(e)}

    def marcar_token_usado(self, token: str) -> bool:
        """Mark a token as used."""
        try:
            self.repo.marcar_checkin_usado(token)
            return True
        except Exception as e:
            logger.error(f"Error marking token used: {e}")
            return False

    def validar_token_y_registrar(
        self, token: str, usuario_id: int, sucursal_id: Optional[int] = None
    ) -> Tuple[bool, str]:
        """Validate token and register attendance."""
        try:
            status = self.obtener_estado_token(token)

            if not status.get("exists"):
                return False, "Token no encontrado"

            if status.get("expired"):
                return False, "Token expirado"

            if status.get("used"):
                return False, "Token ya utilizado o asistencia ya registrada hoy"

            token_usuario_id = status.get("usuario_id")
            if not token_usuario_id:
                return False, "Token no asociado a usuario"
            if int(token_usuario_id) != int(usuario_id):
                return False, "Token no corresponde al usuario"

            sid = (
                int(sucursal_id)
                if sucursal_id is not None
                else self._get_default_sucursal_id()
            )
            is_active, reason = self.verificar_acceso_usuario_sucursal(
                int(usuario_id), sid
            )
            if not is_active:
                return False, reason or "Usuario inactivo"
            try:
                self.repo.registrar_asistencia(
                    int(usuario_id),
                    self._today_local_date(),
                    allow_multiple=self._allow_multiple_attendances_per_day(),
                    sucursal_id=int(sid) if sid is not None else None,
                )
            except ValueError:
                return False, "Token ya utilizado o asistencia ya registrada hoy"

            self.marcar_token_usado(token)
            if self._allow_multiple_attendances_per_day():
                n = self._count_asistencias_usuario_fecha(
                    int(usuario_id), self._today_local_date()
                )
                return True, f"Asistencia registrada ({n} hoy)"
            return True, "Asistencia registrada correctamente"
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return False, str(e)

    def validar_token_y_registrar_sin_sesion(
        self, token: str, sucursal_id: Optional[int] = None
    ) -> Tuple[bool, str]:
        """Validate token and register attendance without requiring session user_id.
        Gets user_id from the token itself."""
        try:
            status = self.obtener_estado_token(token)

            if not status.get("exists"):
                return False, "Token no encontrado"

            if status.get("expired"):
                return False, "Token expirado"

            if status.get("used"):
                return False, "Token ya utilizado"

            usuario_id = status.get("usuario_id")
            if not usuario_id:
                return False, "Token no asociado a usuario"

            is_active, reason = self.verificar_usuario_activo(int(usuario_id))
            if not is_active:
                return False, reason

            user = self.db.get(Usuario, int(usuario_id))
            nombre = (user.nombre or "") if user else ""

            sid = (
                int(sucursal_id)
                if sucursal_id is not None
                else self._get_default_sucursal_id()
            )
            is_active, reason = self.verificar_acceso_usuario_sucursal(
                int(usuario_id), sid
            )
            if not is_active:
                return False, reason or "Usuario inactivo"
            try:
                self.repo.registrar_asistencia(
                    int(usuario_id),
                    self._today_local_date(),
                    allow_multiple=self._allow_multiple_attendances_per_day(),
                    sucursal_id=int(sid) if sid is not None else None,
                )
            except ValueError:
                return False, "Token ya utilizado"

            self.marcar_token_usado(token)
            return True, nombre or "Asistencia registrada"
        except Exception as e:
            logger.error(f"Error validating token without session: {e}")
            return False, str(e)

    def registrar_asistencia_por_dni(
        self, dni: str, sucursal_id: Optional[int] = None
    ) -> Tuple[bool, str]:
        """Register attendance for a user by DNI lookup."""
        try:
            user = self.db.scalar(
                select(Usuario).where(Usuario.dni == str(dni)).limit(1)
            )
            if not user:
                return False, "DNI no encontrado"

            usuario_id = int(user.id)
            nombre = user.nombre or ""

            hoy = self._today_local_date()
            sid = (
                int(sucursal_id)
                if sucursal_id is not None
                else self._get_default_sucursal_id()
            )
            is_active, reason = self.verificar_acceso_usuario_sucursal(usuario_id, sid)
            if not is_active:
                return False, reason or "Usuario inactivo"
            allow_multiple = self._allow_multiple_attendances_per_day()
            if allow_multiple:
                try:
                    threshold = int(
                        os.getenv("CHECKIN_IDEMPOTENCY_WINDOW_SECONDS", "12") or 12
                    )
                except Exception:
                    threshold = 12
                if threshold > 0:
                    last = self.db.execute(
                        text(
                            "SELECT hora_registro FROM asistencias WHERE usuario_id = :id AND fecha = :fecha AND sucursal_id = :sid ORDER BY hora_registro DESC LIMIT 1"
                        ),
                        {
                            "id": usuario_id,
                            "fecha": hoy,
                            "sid": int(sid) if sid is not None else None,
                        },
                    ).fetchone()
                    if last and last[0]:
                        dt = self._as_utc_naive(last[0])
                        if dt and (self._now_utc_naive() - dt).total_seconds() < float(
                            threshold
                        ):
                            n = self._count_asistencias_usuario_fecha(
                                int(usuario_id), hoy
                            )
                            return True, f"{nombre} - Registrado ({n} hoy)"

            if not allow_multiple:
                if (
                    self.db.scalar(
                        select(Asistencia.id)
                        .where(
                            Asistencia.usuario_id == usuario_id,
                            Asistencia.fecha == hoy,
                            Asistencia.sucursal_id
                            == (int(sid) if sid is not None else None),
                        )
                        .limit(1)
                    )
                    is not None
                ):
                    return True, f"{nombre} - Ya registrado hoy"
            self.repo.registrar_asistencia(
                usuario_id,
                hoy,
                allow_multiple=allow_multiple,
                sucursal_id=int(sid) if sid is not None else None,
            )
            if allow_multiple:
                n = self._count_asistencias_usuario_fecha(int(usuario_id), hoy)
                return True, f"{nombre} - Registrado ({n} hoy)"
            return True, nombre
        except Exception as e:
            logger.error(f"Error registering attendance by DNI: {e}")
            return False, str(e)

    def registrar_asistencia_por_dni_y_pin(
        self, dni: str, pin: str, sucursal_id: Optional[int] = None
    ) -> Tuple[bool, str]:
        """Register attendance for a user by DNI + PIN verification (more secure)."""
        try:
            user = self.db.scalar(
                select(Usuario).where(Usuario.dni == str(dni)).limit(1)
            )
            if not user:
                return False, "DNI no encontrado"

            usuario_id = int(user.id)
            nombre = user.nombre or ""

            stored_pin = str(getattr(user, "pin", "") or "").strip()
            if not stored_pin:
                return False, "Usuario sin PIN configurado"

            pin_ok = False
            try:
                if stored_pin.startswith("$2"):
                    import bcrypt

                    pin_ok = bool(
                        bcrypt.checkpw(
                            str(pin).encode("utf-8"), stored_pin.encode("utf-8")
                        )
                    )
                else:
                    pin_ok = stored_pin == str(pin).strip()
            except Exception:
                pin_ok = False

            if not pin_ok:
                return False, "PIN incorrecto"

            hoy = self._today_local_date()
            sid = (
                int(sucursal_id)
                if sucursal_id is not None
                else self._get_default_sucursal_id()
            )
            is_active, reason = self.verificar_acceso_usuario_sucursal(usuario_id, sid)
            if not is_active:
                return False, reason or "Usuario inactivo"
            allow_multiple = self._allow_multiple_attendances_per_day()
            if allow_multiple:
                try:
                    threshold = int(
                        os.getenv("CHECKIN_IDEMPOTENCY_WINDOW_SECONDS", "12") or 12
                    )
                except Exception:
                    threshold = 12
                if threshold > 0:
                    last = self.db.execute(
                        text(
                            "SELECT hora_registro FROM asistencias WHERE usuario_id = :id AND fecha = :fecha AND sucursal_id = :sid ORDER BY hora_registro DESC LIMIT 1"
                        ),
                        {
                            "id": usuario_id,
                            "fecha": hoy,
                            "sid": int(sid) if sid is not None else None,
                        },
                    ).fetchone()
                    if last and last[0]:
                        dt = self._as_utc_naive(last[0])
                        if dt and (self._now_utc_naive() - dt).total_seconds() < float(
                            threshold
                        ):
                            n = self._count_asistencias_usuario_fecha(
                                int(usuario_id), hoy
                            )
                            return True, f"{nombre} - Registrado ({n} hoy)"

            if not allow_multiple:
                if (
                    self.db.scalar(
                        select(Asistencia.id)
                        .where(
                            Asistencia.usuario_id == usuario_id,
                            Asistencia.fecha == hoy,
                            Asistencia.sucursal_id
                            == (int(sid) if sid is not None else None),
                        )
                        .limit(1)
                    )
                    is not None
                ):
                    return True, f"{nombre} - Ya registrado hoy"
            self.repo.registrar_asistencia(
                usuario_id,
                hoy,
                allow_multiple=allow_multiple,
                sucursal_id=int(sid) if sid is not None else None,
            )
            if allow_multiple:
                n = self._count_asistencias_usuario_fecha(int(usuario_id), hoy)
                return True, f"{nombre} - Registrado ({n} hoy)"
            return True, nombre
        except Exception as e:
            logger.error(f"Error registering attendance by DNI+PIN: {e}")
            return False, str(e)

    # ========== Attendance Registration ==========

    def registrar_asistencia(
        self,
        usuario_id: int,
        fecha: Optional[date] = None,
        sucursal_id: Optional[int] = None,
    ) -> Optional[int]:
        """Register attendance for a user."""
        try:
            if fecha is None:
                fecha = self._today_local_date()

            is_active, reason = self.verificar_usuario_activo(int(usuario_id))
            if not is_active:
                raise PermissionError(reason or "Usuario inactivo")

            sid = (
                int(sucursal_id)
                if sucursal_id is not None
                else self._get_default_sucursal_id()
            )
            return self.repo.registrar_asistencia(
                int(usuario_id),
                fecha,
                allow_multiple=self._allow_multiple_attendances_per_day(),
                sucursal_id=int(sid) if sid is not None else None,
            )
        except Exception as e:
            logger.error(f"Error registering attendance: {e}")
            raise

    def eliminar_asistencia(
        self,
        usuario_id: Optional[int] = None,
        fecha: Optional[date] = None,
        asistencia_id: Optional[int] = None,
    ) -> bool:
        """Delete attendance for a user on a specific date."""
        try:
            if asistencia_id is not None:
                a = self.db.get(Asistencia, int(asistencia_id))
                uid = int(a.usuario_id) if a and a.usuario_id is not None else None
                f = a.fecha if a else None
                self.db.execute(
                    delete(Asistencia).where(Asistencia.id == int(asistencia_id))
                )
                if uid is not None and f is not None:
                    try:
                        remaining = int(
                            self.db.execute(
                                text(
                                    "SELECT COUNT(*) FROM asistencias WHERE usuario_id = :uid AND fecha = :f"
                                ),
                                {"uid": uid, "f": f},
                            ).scalar()
                            or 0
                        )
                        if remaining == 0:
                            self.db.execute(
                                text(
                                    "DELETE FROM asistencias_diarias WHERE usuario_id = :uid AND fecha = :f"
                                ),
                                {"uid": uid, "f": f},
                            )
                    except Exception:
                        pass
                self.db.commit()
                return True

            if usuario_id is None:
                raise ValueError("usuario_id requerido")
            if fecha is None:
                fecha = self._today_local_date()

            self.db.execute(
                delete(Asistencia).where(
                    Asistencia.usuario_id == int(usuario_id), Asistencia.fecha == fecha
                )
            )
            try:
                self.db.execute(
                    text(
                        "DELETE FROM asistencias_diarias WHERE usuario_id = :uid AND fecha = :f"
                    ),
                    {"uid": int(usuario_id), "f": fecha},
                )
            except Exception:
                pass
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
                {"start_date": start_date},
            )
            return [(str(row[0]), int(row[1])) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting daily attendance: {e}")
            return []

    def obtener_asistencias_por_rango(
        self, start: str, end: str
    ) -> List[Tuple[str, int]]:
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
                {"start": start, "end": end},
            )
            return [(str(row[0]), int(row[1])) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting attendance by range: {e}")
            return []

    def obtener_asistencias_por_hora(
        self, days: int = 30, start: Optional[str] = None, end: Optional[str] = None
    ) -> List[Tuple[int, int]]:
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
                    {"start": start, "end": end},
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
                    {"start_date": start_date},
                )
            return [(int(row[0]), int(row[1])) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting hourly attendance: {e}")
            return []

    def obtener_asistencias_hoy_ids(self, sucursal_id: Optional[int] = None) -> List[int]:
        """Get list of user IDs who attended today."""
        try:
            hoy = self._today_local_date()
            params = {"fecha": hoy}
            where = "fecha = :fecha"
            if sucursal_id is not None:
                try:
                    sid = int(sucursal_id)
                except Exception:
                    sid = None
                if sid is not None and sid > 0:
                    where += " AND sucursal_id = :sid"
                    params["sid"] = sid
            result = self.db.execute(
                text(
                    f"SELECT DISTINCT usuario_id FROM asistencias WHERE {where}"
                ),
                params,
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
        sucursal_id: Optional[int] = None,
        limit: int = 500,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get detailed attendance list with user names."""
        try:
            params = {"limit": limit, "offset": offset}
            sid = None
            try:
                sid = int(sucursal_id) if sucursal_id is not None else None
            except Exception:
                sid = None

            if start and end:
                if q:
                    query = """
                        SELECT a.id, a.usuario_id, a.fecha::date, a.hora_registro, u.nombre
                        FROM asistencias a
                        JOIN usuarios u ON u.id = a.usuario_id
                        WHERE a.fecha BETWEEN :start AND :end AND (u.nombre ILIKE :q) AND (:sid::INT IS NULL OR a.sucursal_id = :sid)
                        ORDER BY a.fecha DESC, a.hora_registro DESC
                        LIMIT :limit OFFSET :offset
                    """
                    params["start"] = start
                    params["end"] = end
                    params["q"] = f"%{q}%"
                else:
                    query = """
                        SELECT a.id, a.usuario_id, a.fecha::date, a.hora_registro, u.nombre
                        FROM asistencias a
                        JOIN usuarios u ON u.id = a.usuario_id
                        WHERE a.fecha BETWEEN :start AND :end AND (:sid::INT IS NULL OR a.sucursal_id = :sid)
                        ORDER BY a.fecha DESC, a.hora_registro DESC
                        LIMIT :limit OFFSET :offset
                    """
                    params["start"] = start
                    params["end"] = end
            else:
                if q:
                    start_date = self._today_local_date() - timedelta(days=30)
                    query = """
                        SELECT a.id, a.usuario_id, a.fecha::date, a.hora_registro, u.nombre
                        FROM asistencias a
                        JOIN usuarios u ON u.id = a.usuario_id
                        WHERE a.fecha >= :start_date AND (u.nombre ILIKE :q) AND (:sid::INT IS NULL OR a.sucursal_id = :sid)
                        ORDER BY a.fecha DESC, a.hora_registro DESC
                        LIMIT :limit OFFSET :offset
                    """
                    params["start_date"] = start_date
                    params["q"] = f"%{q}%"
                else:
                    start_date = self._today_local_date() - timedelta(days=30)
                    query = """
                        SELECT a.id, a.usuario_id, a.fecha::date, a.hora_registro, u.nombre
                        FROM asistencias a
                        JOIN usuarios u ON u.id = a.usuario_id
                        WHERE a.fecha >= :start_date AND (:sid::INT IS NULL OR a.sucursal_id = :sid)
                        ORDER BY a.fecha DESC, a.hora_registro DESC
                        LIMIT :limit OFFSET :offset
                    """
                    params["start_date"] = start_date
            params["sid"] = int(sid) if sid is not None else None

            result = self.db.execute(text(query), params)
            tz = self._get_app_timezone()
            return [
                {
                    "id": int(row[0]) if row[0] is not None else None,
                    "usuario_id": int(row[1]) if row[1] is not None else None,
                    "fecha": str(row[2]) if row[2] else None,
                    "hora": (
                        self._as_utc_naive(row[3])
                        .replace(tzinfo=timezone.utc)
                        .astimezone(tz)
                        .time()
                        .isoformat(timespec="seconds")
                        if row[3]
                        else None
                    ),
                    "usuario_nombre": row[4] or "",
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
        sucursal_id: Optional[int] = None,
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

            if sucursal_id is not None:
                try:
                    params["sucursal_id"] = int(sucursal_id)
                    where_parts.append("a.sucursal_id = :sucursal_id")
                except Exception:
                    pass

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
                where_parts.append("(u.nombre ILIKE :q OR u.dni ILIKE :q)")

            where_sql = " AND ".join(where_parts) if where_parts else "TRUE"

            count_query = f"""
                SELECT COUNT(*)
                FROM asistencias a
                JOIN usuarios u ON u.id = a.usuario_id
                LEFT JOIN sucursales s ON s.id = a.sucursal_id
                WHERE {where_sql}
            """
            total = 0
            try:
                total = int(self.db.execute(text(count_query), params).scalar() or 0)
            except Exception:
                total = 0

            query = f"""
                SELECT a.id, a.usuario_id, a.fecha::date, a.hora_registro, u.nombre, a.sucursal_id, s.nombre
                FROM asistencias a
                JOIN usuarios u ON u.id = a.usuario_id
                LEFT JOIN sucursales s ON s.id = a.sucursal_id
                WHERE {where_sql}
                ORDER BY a.fecha DESC, a.hora_registro DESC
                LIMIT :limit OFFSET :offset
            """
            result = self.db.execute(text(query), params)
            tz = self._get_app_timezone()
            items = [
                {
                    "id": int(row[0]) if row[0] is not None else None,
                    "usuario_id": int(row[1]) if row[1] is not None else None,
                    "fecha": str(row[2]) if row[2] else None,
                    "hora": (
                        self._as_utc_naive(row[3])
                        .replace(tzinfo=timezone.utc)
                        .astimezone(tz)
                        .time()
                        .isoformat(timespec="seconds")
                        if row[3]
                        else None
                    ),
                    "usuario_nombre": row[4] or "",
                    "sucursal_id": int(row[5]) if row[5] is not None else None,
                    "sucursal_nombre": str(row[6] or "") if row[6] is not None else None,
                }
                for row in result.fetchall()
            ]
            return {"items": items, "total": total}
        except Exception as e:
            logger.error(f"Error getting paged attendance details: {e}")
            return {"items": [], "total": 0}

    # ========== Station QR Check-in ==========

    def generar_station_key(self, sucursal_id: int) -> str:
        try:
            sid = int(sucursal_id)
        except Exception:
            sid = self._get_default_sucursal_id() or 0
        if not sid:
            return secrets.token_urlsafe(16)
        try:
            b = self.db.get(Sucursal, int(sid))
            if b is None:
                sid = self._get_default_sucursal_id() or 0
                b = self.db.get(Sucursal, int(sid)) if sid else None
            if b and b.station_key:
                return str(b.station_key)
            station_key = secrets.token_urlsafe(16)
            if b:
                b.station_key = station_key
            self.db.commit()
            return station_key
        except Exception as e:
            logger.error(f"Error generating station key: {e}")
            try:
                self.db.rollback()
            except Exception:
                pass
            return secrets.token_urlsafe(16)

    def validar_station_key(self, station_key: str) -> Optional[int]:
        try:
            k = str(station_key or "").strip()
        except Exception:
            k = ""
        if not k:
            return None
        try:
            sid = self.db.scalar(
                select(Sucursal.id)
                .where(Sucursal.station_key == k)
                .where(Sucursal.activa.is_(True))
                .limit(1)
            )
            return int(sid) if sid is not None else None
        except Exception as e:
            logger.error(f"Error validating station key: {e}")
            return None

    def crear_station_token(
        self, sucursal_id: int, expires_seconds: int = 300
    ) -> Dict[str, Any]:
        try:
            now = self._now_utc_naive()
            min_interval_seconds = int(
                os.getenv("STATION_TOKEN_MIN_INTERVAL_SECONDS", "2") or 2
            )
            self.db.execute(
                text("SELECT pg_advisory_xact_lock(:ns, :k)"),
                {"ns": 22001, "k": int(sucursal_id)},
            )
            try:
                active = self.db.execute(
                    text(
                        """
                            SELECT token, expires_at, created_at
                            FROM checkin_station_tokens
                            WHERE sucursal_id = :sid AND used_by IS NULL AND expires_at > :now
                            ORDER BY created_at DESC NULLS LAST, id DESC
                            LIMIT 1
                        """
                    ),
                    {"sid": int(sucursal_id), "now": now},
                ).fetchone()
            except Exception:
                active = None

            if active and min_interval_seconds > 0:
                created_at = self._as_utc_naive(active[2])
                if created_at and (now - created_at).total_seconds() < float(
                    min_interval_seconds
                ):
                    expires_at = self._as_utc_naive(active[1])
                    remaining = (
                        int((expires_at - now).total_seconds())
                        if expires_at
                        else int(expires_seconds)
                    )
                    return {
                        "token": active[0],
                        "expires_at": expires_at.isoformat()
                        if hasattr(expires_at, "isoformat")
                        else str(expires_at),
                        "expires_in": max(5, remaining),
                    }

            # Invalidate any existing active tokens for this gym
            self.db.execute(
                text(
                    "DELETE FROM checkin_station_tokens WHERE sucursal_id = :sid AND used_by IS NULL"
                ),
                {"sid": int(sucursal_id)},
            )
            self.db.execute(
                text(
                    "DELETE FROM checkin_station_tokens WHERE sucursal_id = :sid AND expires_at <= :now"
                ),
                {"sid": int(sucursal_id), "now": now},
            )

            token = secrets.token_urlsafe(16)
            expires_at = self._now_utc_naive() + timedelta(seconds=expires_seconds)
            created_at = self._now_utc_naive()
            gym_id = None
            try:
                from src.database.tenant_connection import get_current_tenant_gym_id

                gym_id = get_current_tenant_gym_id()
            except Exception:
                gym_id = None

            self.db.execute(
                text("""
                    INSERT INTO checkin_station_tokens (gym_id, sucursal_id, token, expires_at, created_at)
                    VALUES (:gym_id, :sid, :token, :expires_at, :created_at)
                """),
                {
                    "gym_id": int(gym_id) if gym_id is not None else 0,
                    "sid": int(sucursal_id),
                    "token": token,
                    "expires_at": expires_at,
                    "created_at": created_at,
                },
            )
            self.db.commit()

            return {
                "token": token,
                "expires_at": expires_at.isoformat(),
                "expires_in": expires_seconds,
            }
        except Exception as e:
            logger.error(f"Error creating station token: {e}")
            self.db.rollback()
            raise

    def obtener_station_token_activo(
        self, sucursal_id: int
    ) -> Optional[Dict[str, Any]]:
        try:
            now = self._now_utc_naive()

            # Look for active token
            result = self.db.execute(
                text("""
                    SELECT token, expires_at 
                    FROM checkin_station_tokens 
                    WHERE sucursal_id = :sid AND used_by IS NULL AND expires_at > :now
                    ORDER BY created_at DESC NULLS LAST, id DESC LIMIT 1
                """),
                {"sid": int(sucursal_id), "now": now},
            )
            row = result.fetchone()

            if row:
                expires_at = self._as_utc_naive(row[1])
                if expires_at is None:
                    return self.crear_station_token(sucursal_id)
                remaining = int((expires_at - now).total_seconds())

                # Ensure we have a minimum positive value to avoid instant refresh loops
                if remaining < 5:
                    # Token about to expire, create new one
                    return self.crear_station_token(sucursal_id)

                return {
                    "token": row[0],
                    "expires_at": expires_at.isoformat()
                    if hasattr(expires_at, "isoformat")
                    else str(expires_at),
                    "expires_in": max(
                        5, remaining
                    ),  # Minimum 5 seconds to prevent rapid polling
                }

            # No active token, create new one
            return self.crear_station_token(sucursal_id)
        except Exception as e:
            logger.error(f"Error getting active station token: {e}")
            return self.crear_station_token(sucursal_id)

    def validar_station_scan(
        self, token: str, usuario_id: int
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Validate a station token scan and register attendance.
        Returns (success, message, user_data).
        """
        try:
            # Check token exists and is valid
            result = self.db.execute(
                text("""
                    SELECT id, sucursal_id, expires_at, used_by 
                    FROM checkin_station_tokens 
                    WHERE token = :token LIMIT 1
                """),
                {"token": token},
            )
            row = result.fetchone()

            if not row:
                return False, "Código QR inválido", None

            token_id, sucursal_id, expires_at, used_by = row
            try:
                sucursal_id = (
                    int(sucursal_id)
                    if sucursal_id is not None
                    else self._get_default_sucursal_id()
                )
            except Exception:
                sucursal_id = self._get_default_sucursal_id()

            sucursal_nombre = None
            sucursal_codigo = None
            try:
                if sucursal_id is not None:
                    row_s = self.db.execute(
                        text(
                            "SELECT nombre, codigo FROM sucursales WHERE id = :id LIMIT 1"
                        ),
                        {"id": int(sucursal_id)},
                    ).fetchone()
                    if row_s:
                        sucursal_nombre = (
                            str(row_s[0] or "") if row_s[0] is not None else None
                        )
                        sucursal_codigo = (
                            str(row_s[1] or "") if row_s[1] is not None else None
                        )
            except Exception:
                sucursal_nombre = None
                sucursal_codigo = None

            branch_info = {
                "sucursal_id": int(sucursal_id) if sucursal_id is not None else None,
                "sucursal_nombre": sucursal_nombre,
                "sucursal_codigo": sucursal_codigo,
                "branch_id": int(sucursal_id) if sucursal_id is not None else None,
                "branch_name": sucursal_nombre,
                "branch_code": sucursal_codigo,
            }

            # Check expiration
            now = self._now_utc_naive()
            expires_at = self._as_utc_naive(expires_at)
            if expires_at and expires_at < now:
                return False, "Código QR expirado", None

            # Get user info
            user_result = self.db.execute(
                text("SELECT nombre, dni, activo FROM usuarios WHERE id = :id LIMIT 1"),
                {"id": usuario_id},
            )
            user_row = user_result.fetchone()

            if not user_row:
                return False, "Usuario no encontrado", None

            nombre, dni, activo = user_row

            if used_by:
                try:
                    if int(used_by) == int(usuario_id):
                        return (
                            True,
                            f"{nombre} - Ya registrado",
                            {
                                "nombre": nombre,
                                "dni": dni,
                                "already_checked": True,
                                **branch_info,
                            },
                        )
                except Exception:
                    pass
                return False, "Código QR ya utilizado", None

            is_active, reason = self.verificar_acceso_usuario_sucursal(
                int(usuario_id), sucursal_id
            )
            if not is_active:
                return False, reason or "Usuario inactivo", None

            # Check if already attended today
            hoy = self._today_local_date()
            allow_multiple = self._allow_multiple_attendances_per_day()
            if not allow_multiple:
                check = self.db.execute(
                    text("""
                        SELECT 1 FROM asistencias 
                        WHERE usuario_id = :id AND fecha = :fecha AND sucursal_id = :sid LIMIT 1
                    """),
                    {
                        "id": usuario_id,
                        "fecha": hoy,
                        "sid": int(sucursal_id) if sucursal_id is not None else None,
                    },
                )
                if check.fetchone():
                    return (
                        True,
                        f"{nombre} - Ya registrado hoy",
                        {
                            "nombre": nombre,
                            "dni": dni,
                            "already_checked": True,
                            **branch_info,
                        },
                    )

            used_at = self._now_utc_naive()
            claimed = self.db.execute(
                text(
                    """
                    UPDATE checkin_station_tokens
                    SET used_by = :user_id, used_at = :used_at
                    WHERE id = :token_id AND used_by IS NULL
                    RETURNING id
                    """
                ),
                {"user_id": int(usuario_id), "token_id": int(token_id), "used_at": used_at},
            ).fetchone()
            if not claimed:
                row2 = self.db.execute(
                    text(
                        """
                        SELECT used_by FROM checkin_station_tokens
                        WHERE id = :token_id LIMIT 1
                        """
                    ),
                    {"token_id": int(token_id)},
                ).fetchone()
                if row2 and row2[0] is not None:
                    try:
                        if int(row2[0]) == int(usuario_id):
                            return (
                                True,
                                f"{nombre} - Ya registrado",
                                {"nombre": nombre, "dni": dni, "already_checked": True},
                            )
                    except Exception:
                        pass
                return False, "Código QR ya utilizado", None

            try:
                self._registrar_asistencia_si_no_existe(
                    int(usuario_id),
                    hoy,
                    sucursal_id=int(sucursal_id) if sucursal_id is not None else None,
                )
            except ValueError:
                pass

            self.db.commit()
            hora_local = self._now_local().time().isoformat(timespec="seconds")

            if allow_multiple:
                n = self._count_asistencias_usuario_fecha(int(usuario_id), hoy)
                return (
                    True,
                    f"Check-in exitoso ({n} hoy)",
                    {
                        "nombre": nombre,
                        "dni": dni,
                        "hora": hora_local,
                        "already_checked": False,
                        **branch_info,
                    },
                )
            return (
                True,
                "Check-in exitoso",
                {
                    "nombre": nombre,
                    "dni": dni,
                    "hora": hora_local,
                    "already_checked": False,
                    **branch_info,
                },
            )
        except Exception as e:
            logger.error(f"Error validating station scan: {e}")
            self.db.rollback()
            return False, str(e), None

    def obtener_station_checkins_recientes(
        self, gym_id: int, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get recent check-ins for the station display."""
        try:
            hoy = self._today_local_date()
            tz = self._get_app_timezone()
            result = self.db.execute(
                text("""
                    SELECT u.nombre, u.dni, a.hora_registro
                    FROM asistencias a
                    JOIN usuarios u ON u.id = a.usuario_id
                    WHERE a.fecha = :fecha AND a.sucursal_id = :sid
                    ORDER BY a.hora_registro DESC
                    LIMIT :limit
                """),
                {"limit": limit, "fecha": hoy, "sid": int(gym_id)},
            )
            return [
                {
                    "nombre": row[0] or "",
                    "dni": row[1] or "",
                    "hora": (
                        self._as_utc_naive(row[2])
                        .replace(tzinfo=timezone.utc)
                        .astimezone(tz)
                        .time()
                        .isoformat(timespec="seconds")
                        if row[2]
                        else ""
                    ),
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
                    SELECT COUNT(*) FROM asistencias WHERE fecha = :fecha AND sucursal_id = :sid
                """),
                {"fecha": hoy, "sid": int(gym_id)},
            )
            total_hoy = result.scalar() or 0

            return {"total_hoy": total_hoy}
        except Exception as e:
            logger.error(f"Error getting station stats: {e}")
            return {"total_hoy": 0}
