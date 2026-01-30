"""
Auth Service - SQLAlchemy ORM Implementation

Provides authentication-related operations using SQLAlchemy ORM.
Replaces raw SQL usage in auth.py with proper ORM queries.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
import os
import base64
import hashlib
import hmac

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
import logging

from sqlalchemy.orm import Session
from sqlalchemy import select, text

from src.services.base import BaseService
from src.database.orm_models import Usuario

logger = logging.getLogger(__name__)


class AuthService(BaseService):
    """Service for authentication operations using SQLAlchemy."""

    def __init__(self, db: Session):
        super().__init__(db)

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

    # ========== User Lookup ==========

    def obtener_usuario_por_dni(self, dni: str) -> Optional[Usuario]:
        """Get user by DNI."""
        try:
            stmt = select(Usuario).where(Usuario.dni == dni)
            return self.db.execute(stmt).scalars().first()
        except Exception as e:
            logger.error(f"Error getting user by DNI: {e}")
            return None

    def obtener_usuario_por_id(self, usuario_id: int) -> Optional[Usuario]:
        """Get user by ID."""
        return self.db.get(Usuario, usuario_id)

    def obtener_usuario_por_telefono(self, telefono: str) -> Optional[Usuario]:
        """Get user by phone number (for checkin auth)."""
        try:
            stmt = select(Usuario).where(Usuario.telefono == telefono)
            return self.db.execute(stmt).scalars().first()
        except Exception as e:
            logger.error(f"Error getting user by telefono: {e}")
            return None

    # ========== PIN Operations ==========

    def _hash_pin(self, pin: str) -> str:
        p = str(pin or "").strip()
        if not p:
            return ""
        try:
            import bcrypt  # type: ignore

            return bcrypt.hashpw(p.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        except Exception:
            iters = 200_000
            salt = os.urandom(16)
            dk = hashlib.pbkdf2_hmac("sha256", p.encode("utf-8"), salt, iters)
            salt_b64 = base64.urlsafe_b64encode(salt).decode("utf-8").rstrip("=")
            dk_b64 = base64.urlsafe_b64encode(dk).decode("utf-8").rstrip("=")
            return f"pbkdf2$sha256${iters}${salt_b64}${dk_b64}"

    def _verify_pbkdf2(self, pin: str, stored: str) -> bool:
        try:
            parts = str(stored or "").split("$")
            if len(parts) != 5:
                return False
            _scheme, algo, iters_s, salt_b64, dk_b64 = parts
            if algo != "sha256":
                return False
            iters = int(iters_s)
            if iters < 50_000 or iters > 2_000_000:
                return False
            pad = "=" * ((4 - (len(salt_b64) % 4)) % 4)
            salt = base64.urlsafe_b64decode((salt_b64 + pad).encode("utf-8"))
            pad2 = "=" * ((4 - (len(dk_b64) % 4)) % 4)
            dk = base64.urlsafe_b64decode((dk_b64 + pad2).encode("utf-8"))
            calc = hashlib.pbkdf2_hmac("sha256", str(pin).encode("utf-8"), salt, iters)
            return hmac.compare_digest(calc, dk)
        except Exception:
            return False

    def verificar_pin(self, usuario_id: int, pin: str) -> Dict[str, Any]:
        """
        Verify PIN for a user.
        Returns dict with: valid (bool), activo (bool), usuario (dict or None).
        """
        user = self.db.get(Usuario, usuario_id)
        if not user:
            return {"valid": False, "activo": False, "usuario": None}

        stored_pin = str(user.pin or "").strip()
        is_valid = False
        if stored_pin and pin is not None:
            try:
                if stored_pin.startswith("$2"):
                    import bcrypt

                    is_valid = bool(
                        bcrypt.checkpw(
                            str(pin).encode("utf-8"), stored_pin.encode("utf-8")
                        )
                    )
                elif stored_pin.startswith("pbkdf2$"):
                    is_valid = self._verify_pbkdf2(str(pin), stored_pin)
                else:
                    is_valid = stored_pin == str(pin)
            except Exception:
                is_valid = False

        if is_valid and stored_pin and not (stored_pin.startswith("$2") or stored_pin.startswith("pbkdf2$")):
            try:
                user.pin = self._hash_pin(str(pin))
                self.db.commit()
            except Exception:
                try:
                    self.db.rollback()
                except Exception:
                    pass

        return {
            "valid": is_valid,
            "activo": bool(user.activo),
            "usuario": self._usuario_to_dict(user) if is_valid else None,
        }

    def actualizar_pin(self, usuario_id: int, new_pin: str) -> bool:
        """Update user PIN."""
        try:
            user = self.db.get(Usuario, usuario_id)
            if not user:
                return False
            pin_str = str(new_pin or "").strip()
            if pin_str and pin_str.startswith("$2"):
                user.pin = pin_str
            elif pin_str and pin_str.startswith("pbkdf2$"):
                user.pin = pin_str
            elif pin_str:
                user.pin = self._hash_pin(pin_str)
            else:
                user.pin = pin_str
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating PIN: {e}")
            self.db.rollback()
            return False

    # ========== Checkin Auth ==========

    def verificar_checkin(self, dni: str, telefono: str) -> Dict[str, Any]:
        """
        Verify checkin credentials (DNI + phone).
        Returns dict with: valid (bool), activo (bool), usuario (dict or None).
        """
        user = self.obtener_usuario_por_dni(dni)
        if not user:
            return {
                "valid": False,
                "activo": False,
                "usuario": None,
                "error": "DNI no encontrado",
            }

        stored_phone = str(user.telefono or "").strip()
        input_phone = telefono.strip()

        # Compare phone (flexible matching)
        is_valid = False
        if stored_phone and input_phone:
            # Normalize: remove spaces, dashes, etc.
            norm_stored = "".join(c for c in stored_phone if c.isdigit())
            norm_input = "".join(c for c in input_phone if c.isdigit())
            # Check if last 8 digits match (flexible)
            if len(norm_stored) >= 8 and len(norm_input) >= 8:
                is_valid = norm_stored[-8:] == norm_input[-8:]
            else:
                is_valid = norm_stored == norm_input

        if not is_valid:
            return {
                "valid": False,
                "activo": bool(user.activo),
                "usuario": None,
                "error": "Teléfono no coincide",
            }

        if not user.activo:
            return {
                "valid": False,
                "activo": False,
                "usuario": None,
                "error": "Usuario inactivo",
            }

        return {
            "valid": True,
            "activo": bool(user.activo),
            "usuario": self._usuario_to_dict(user),
            "error": None,
        }

    # ========== Professor Operations ==========

    def obtener_profesores_activos(self) -> List[Dict[str, Any]]:
        """Get list of active professors for login dropdown."""
        try:
            result = self.db.execute(
                text("""
                    SELECT p.id, u.id as usuario_id, u.nombre, u.activo
                    FROM profesores p
                    JOIN usuarios u ON p.usuario_id = u.id
                    WHERE u.activo = true
                    ORDER BY u.nombre
                """)
            )
            return [
                {"id": row[0], "usuario_id": row[1], "nombre": row[2], "activo": row[3]}
                for row in result.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting active professors: {e}")
            return []

    def verificar_profesor_pin(self, profesor_id: int, pin: str) -> Dict[str, Any]:
        """
        Verify professor PIN.
        Returns dict with: valid (bool), profesor (dict or None), usuario (dict or None).
        """
        try:
            result = self.db.execute(
                text("""
                    SELECT p.id, p.usuario_id, u.nombre, u.pin, u.activo
                    FROM profesores p
                    JOIN usuarios u ON p.usuario_id = u.id
                    WHERE p.id = :prof_id
                """),
                {"prof_id": profesor_id},
            )
            row = result.fetchone()
            if not row:
                return {"valid": False, "profesor": None, "usuario": None}

            stored_pin = str(row[3] or "").strip()
            is_valid = False
            if stored_pin and pin is not None:
                try:
                    if stored_pin.startswith("$2"):
                        import bcrypt

                        is_valid = bool(
                            bcrypt.checkpw(
                                str(pin).encode("utf-8"), stored_pin.encode("utf-8")
                            )
                        )
                    else:
                        is_valid = stored_pin == str(pin)
                except Exception:
                    is_valid = False
            is_active = bool(row[4])

            if not is_active:
                return {
                    "valid": False,
                    "profesor": None,
                    "usuario": None,
                    "error": "Profesor inactivo",
                }

            if not is_valid:
                return {
                    "valid": False,
                    "profesor": None,
                    "usuario": None,
                    "error": "PIN inválido",
                }

            return {
                "valid": True,
                "profesor": {"id": row[0], "usuario_id": row[1], "nombre": row[2]},
                "usuario": {"id": row[1], "nombre": row[2], "activo": is_active},
                "error": None,
            }
        except Exception as e:
            logger.error(f"Error verifying profesor PIN: {e}")
            return {"valid": False, "profesor": None, "usuario": None, "error": str(e)}

    def verificar_owner_password(self, password: str) -> bool:
        """
        Verify owner password with Auto-Healing synchronization.
        Checks Admin DB first (as authority) and syncs to Local DB if different.
        """
        import os
        from sqlalchemy import text

        local_hash = None
        admin_hash = None
        local_user_id = None

        # 1. Get Local Hash & ID (using service's session)
        try:
            result = self.db.execute(
                text(
                    "SELECT id, pin FROM usuarios WHERE rol IN ('dueno', 'owner', 'admin') AND activo = true ORDER BY id LIMIT 1"
                )
            )
            row = result.fetchone()
            if row:
                local_user_id = row[0]
                local_hash = str(row[1] or "").strip()
        except Exception as e:
            logger.error(f"Error reading local owner: {e}")

        # 2. Get Admin Hash
        try:
            from src.dependencies import get_admin_db, get_current_tenant

            tenant = get_current_tenant()
            if not tenant:
                tenant = os.getenv("DEFAULT_TENANT", "testingiron")

            if tenant:
                adm_gen = get_admin_db()
                if adm_gen:
                    session = next(adm_gen)
                    try:
                        result = session.execute(
                            text(
                                "SELECT owner_password_hash FROM gyms WHERE subdominio = :sub"
                            ),
                            {"sub": str(tenant).strip().lower()},
                        )
                        row = result.fetchone()
                        if row and row[0]:
                            admin_hash = str(row[0]).strip()
                    finally:
                        session.close()
        except Exception as e:
            # Log warning but don't crash, allow fallback
            logger.warning(f"Could not fetch admin hash: {e}")

        # 3. AUTO-HEALING: Sync Admin -> Local if different
        if admin_hash and local_user_id:
            if admin_hash != local_hash:
                try:
                    logger.info("Syncing Admin password hash to Local DB...")
                    self.db.execute(
                        text("UPDATE usuarios SET pin = :pin WHERE id = :id"),
                        {"pin": admin_hash, "id": local_user_id},
                    )
                    self.db.commit()
                    local_hash = admin_hash
                except Exception as e:
                    logger.error(f"Auto-healing failed: {e}")
                    self.db.rollback()

        # 4. Verification
        target_hash = admin_hash if admin_hash else local_hash
        env_pwd = (
            os.getenv("WEBAPP_OWNER_PASSWORD", "") or os.getenv("OWNER_PASSWORD", "")
        ).strip()

        candidates = []
        if target_hash:
            candidates.append(target_hash)
        if env_pwd:
            candidates.append(env_pwd)
        if not candidates:
            candidates.append("admin")  # Fallback

        import bcrypt

        for secret in candidates:
            try:
                # Bcrypt
                if secret.startswith("$2"):
                    if bcrypt.checkpw(password.encode("utf-8"), secret.encode("utf-8")):
                        return True
                # Plaintext
                elif secret == password:
                    return True
            except Exception:
                continue

        return False

    # ========== Session/Work Session ==========

    def registrar_inicio_sesion_profesor(
        self, profesor_id: int, usuario_id: int
    ) -> Optional[int]:
        """Register professor work session start."""
        try:
            inicio = self._now_utc_naive()
            result = self.db.execute(
                text("""
                    INSERT INTO sesiones_trabajo_profesor 
                    (profesor_id, usuario_id, inicio, activa)
                    VALUES (:prof_id, :user_id, :inicio, true)
                    RETURNING id
                """),
                {"prof_id": profesor_id, "user_id": usuario_id, "inicio": inicio},
            )
            row = result.fetchone()
            self.db.commit()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Error registering work session: {e}")
            self.db.rollback()
            return None

    def finalizar_sesion_profesor(self, sesion_id: int) -> bool:
        """End professor work session."""
        try:
            fin = self._now_utc_naive()
            self.db.execute(
                text("""
                    UPDATE sesiones_trabajo_profesor 
                    SET fin = :fin, activa = false
                    WHERE id = :id AND activa = true
                """),
                {"id": sesion_id, "fin": fin},
            )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error ending work session: {e}")
            self.db.rollback()
            return False

    # ========== Helpers ==========

    def _usuario_to_dict(self, user: Usuario) -> Dict[str, Any]:
        """Convert Usuario ORM object to dict."""
        return {
            "id": user.id,
            "nombre": user.nombre,
            "dni": user.dni,
            "telefono": user.telefono,
            "email": getattr(user, "email", None),
            "activo": user.activo,
            "tipo_cuota": user.tipo_cuota,
            "fecha_vencimiento": user.fecha_proximo_vencimiento.isoformat()
            if user.fecha_proximo_vencimiento
            else None,
            "notas": getattr(user, "notas", None),
        }
