import logging
import os
import time
import re
import unicodedata
import secrets
import hashlib
import base64
import json
from typing import Any, Dict, List, Optional
import psycopg2
import psycopg2.extras
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

try:
    import requests
except ImportError:
    requests = None

# Local imports (self-contained in admin-api)
from src.database.raw_manager import RawPostgresManager
from src.secure_config import SecureConfig
from src.security_utils import SecurityUtils
from src.models.orm_models import Base, Usuario, Configuracion, MetodoPago, TipoCuota, ConceptoPago

logger = logging.getLogger(__name__)


class AdminService:
    def __init__(self, db_manager: RawPostgresManager):
        self.db = db_manager
        # Initialize admin infrastructure if needed
        try:
            self._ensure_admin_db_exists()
            self._ensure_schema()
            self._ensure_owner_user()
        except Exception as e:
            logger.error(f"Error initializing AdminService infra: {e}")

    def _env_flag(self, name: str, default: bool = False) -> bool:
        v = os.getenv(name)
        if v is None:
            return bool(default)
        try:
            s = str(v).strip().lower()
        except Exception:
            return bool(default)
        return s in ("1", "true", "t", "yes", "y", "on")

    def _ensure_admin_db_exists(self) -> None:
        """
        Verifica si la base de datos de administración existe y la crea si no.
        Se conecta a la base de datos 'postgres' (mantenimiento) para realizar esta operación.
        """
        target_db = self.db.params.get("database")
        if not target_db:
            return

        try:
            # Intentar conectar primero para ver si ya existe (es más rápido que crear conexión de mantenimiento siempre)
            with self.db.get_connection_context():
                return # Ya existe y conecta bien
        except Exception:
            # Si falla, asumimos que podría no existir y procedemos a intentar crearla
            pass

        try:
            # Configurar conexión a 'postgres' (maintenance db)
            maint_params = self.db.params.copy()
            maint_params["database"] = "postgres"
            
            # Extraer parámetros para psycopg2
            pg_params = {
                "host": maint_params.get("host"),
                "port": maint_params.get("port"),
                "dbname": "postgres",
                "user": maint_params.get("user"),
                "password": maint_params.get("password"),
                "sslmode": maint_params.get("sslmode", "require"),
                "connect_timeout": maint_params.get("connect_timeout", 10),
                "application_name": "gym_admin_bootstrap"
            }

            conn = psycopg2.connect(**pg_params)
            conn.autocommit = True
            try:
                cur = conn.cursor()
                # Verificar existencia de forma segura
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
                exists = cur.fetchone()
                if not exists:
                    logger.info(f"Base de datos {target_db} no encontrada. Creando...")
                    # CREATE DATABASE no admite parámetros, debemos sanitizar o confiar en el config
                    # Como es un nombre de DB interno, asumimos seguridad básica, pero idealmente validar caracteres.
                    safe_name = "".join(c for c in target_db if c.isalnum() or c in "_-")
                    if safe_name != target_db:
                        raise ValueError(f"Nombre de base de datos inválido: {target_db}")
                    
                    cur.execute(f"CREATE DATABASE {safe_name}")
                    logger.info(f"Base de datos {safe_name} creada exitosamente.")
                cur.close()
            finally:
                conn.close()
        except Exception as e:
            # Si falla aquí, es crítico (ej. credenciales mal, o no permiso para crear DB)
            logger.error(f"Error crítico asegurando existencia de DB Admin: {e}")
            # No relanzamos para permitir que _ensure_schema falle con su propio error si es conexión

    @staticmethod
    def resolve_admin_db_params() -> Dict[str, Any]:
        host = os.getenv("ADMIN_DB_HOST", "").strip()
        try:
            port = int(os.getenv("ADMIN_DB_PORT", "5432"))
        except Exception:
            port = 5432
        user = os.getenv("ADMIN_DB_USER", "").strip()
        password = os.getenv("ADMIN_DB_PASSWORD", "")
        sslmode = os.getenv("ADMIN_DB_SSLMODE", "require").strip()
        try:
            connect_timeout = int(os.getenv("ADMIN_DB_CONNECT_TIMEOUT", "4"))
        except Exception:
            connect_timeout = 4
        application_name = os.getenv("ADMIN_DB_APPLICATION_NAME", "gym_management_admin").strip()
        database = os.getenv("ADMIN_DB_NAME", "ironhub_admin").strip()

        try:
            h = host.lower()
            if ("neon.tech" in h) or ("neon" in h):
                if not sslmode or sslmode.lower() in ("disable", "prefer"):
                    sslmode = "require"
        except Exception:
            pass
        return {
            "host": host or "localhost",
            "port": port,
            "database": database or "ironhub_admin",
            "user": user or "postgres",
            "password": password,
            "sslmode": sslmode or "require",
            "connect_timeout": connect_timeout,
            "application_name": application_name or "gym_management_admin",
        }

    def _ensure_schema(self) -> None:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                try:
                    cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
                except Exception:
                    pass
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS gyms (id BIGSERIAL PRIMARY KEY, nombre TEXT NOT NULL, subdominio TEXT NOT NULL UNIQUE, db_name TEXT NOT NULL UNIQUE, b2_bucket_name TEXT, b2_bucket_id TEXT, whatsapp_phone_id TEXT, whatsapp_access_token TEXT, whatsapp_business_account_id TEXT, whatsapp_verify_token TEXT, whatsapp_app_secret TEXT, whatsapp_nonblocking BOOLEAN NOT NULL DEFAULT false, whatsapp_send_timeout_seconds NUMERIC(6,2) NULL, owner_phone TEXT, status TEXT NOT NULL DEFAULT 'active', hard_suspend BOOLEAN NOT NULL DEFAULT false, suspended_until TIMESTAMP WITHOUT TIME ZONE NULL, suspended_reason TEXT NULL, created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW())"
                )
                # Add missing columns if they don't exist
                columns = [
                    ("b2_key_id", "TEXT"),
                    ("b2_application_key", "TEXT"),
                    ("owner_password_hash", "TEXT"),
                    ("owner_phone", "TEXT"),
                    ("whatsapp_business_account_id", "TEXT"),
                    ("whatsapp_verify_token", "TEXT"),
                    ("whatsapp_app_secret", "TEXT"),
                    ("whatsapp_nonblocking", "BOOLEAN NOT NULL DEFAULT false"),
                    ("whatsapp_send_timeout_seconds", "NUMERIC(6,2) NULL")
                ]
                for col, dtype in columns:
                    try:
                        cur.execute(f"ALTER TABLE gyms ADD COLUMN IF NOT EXISTS {col} {dtype}")
                    except Exception:
                        pass
                
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS gym_payments (id BIGSERIAL PRIMARY KEY, gym_id BIGINT NOT NULL REFERENCES gyms(id) ON DELETE CASCADE, plan TEXT, amount NUMERIC(12,2), currency TEXT, paid_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(), valid_until TIMESTAMP WITHOUT TIME ZONE NULL, status TEXT, notes TEXT)"
                )
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS admin_users (id BIGSERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW())"
                )
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS admin_audit (id BIGSERIAL PRIMARY KEY, actor_username TEXT, action TEXT NOT NULL, gym_id BIGINT NULL, details TEXT NULL, created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW())"
                )
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS plans (id BIGSERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL, amount NUMERIC(12,2) NOT NULL, currency TEXT NOT NULL, period_days INTEGER NOT NULL, created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW())"
                )
                try:
                    cur.execute("ALTER TABLE plans ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT true")
                except Exception:
                    pass
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS gym_subscriptions (id BIGSERIAL PRIMARY KEY, gym_id BIGINT NOT NULL REFERENCES gyms(id) ON DELETE CASCADE, plan_id BIGINT NOT NULL REFERENCES plans(id) ON DELETE RESTRICT, start_date DATE NOT NULL, next_due_date DATE NOT NULL, status TEXT NOT NULL DEFAULT 'active', created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW())"
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS whatsapp_template_catalog (
                        id BIGSERIAL PRIMARY KEY,
                        template_name TEXT UNIQUE NOT NULL,
                        category TEXT NOT NULL DEFAULT 'UTILITY',
                        language TEXT NOT NULL DEFAULT 'es_AR',
                        body_text TEXT NOT NULL,
                        example_params JSONB,
                        active BOOLEAN NOT NULL DEFAULT TRUE,
                        version INTEGER NOT NULL DEFAULT 1,
                        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
                    )
                    """
                )
                try:
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_whatsapp_template_catalog_active ON whatsapp_template_catalog (active)")
                except Exception:
                    pass
                try:
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_gyms_subdominio_lower ON gyms (lower(subdominio))")
                except Exception:
                    pass
                try:
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_gyms_status ON gyms (status)")
                except Exception:
                    pass
                if self._env_flag("ADMIN_DB_ANALYZE_ON_BOOTSTRAP", True):
                    try:
                        cur.execute("ANALYZE gyms")
                    except Exception:
                        pass
                conn.commit()

                try:
                    cur.execute("SELECT COUNT(*) FROM whatsapp_template_catalog")
                    c = int((cur.fetchone() or [0])[0])
                    if c == 0:
                        defaults = self._default_whatsapp_template_catalog()
                        for t in defaults:
                            cur.execute(
                                "INSERT INTO whatsapp_template_catalog (template_name, category, language, body_text, example_params, active, version) VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (template_name) DO NOTHING",
                                (
                                    t.get("template_name"),
                                    t.get("category"),
                                    t.get("language"),
                                    t.get("body_text"),
                                    psycopg2.extras.Json(t.get("example_params")) if t.get("example_params") is not None else None,
                                    bool(t.get("active", True)),
                                    int(t.get("version", 1)),
                                ),
                            )
                        conn.commit()
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"Error ensuring schema: {e}")

    def _hash_password(self, password: str) -> str:
        salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
        return base64.b64encode(salt).decode("ascii") + ":" + base64.b64encode(dk).decode("ascii")

    def _verify_password(self, password: str, stored: str) -> bool:
        try:
            hs = str(stored or "").strip()
        except Exception:
            hs = stored
        if not hs:
            return False
        try:
            if hs.startswith("$2"):
                return SecurityUtils.verify_password(password, hs)
        except Exception:
            pass
        try:
            s, h = hs.split(":", 1)
            try:
                s = s.strip().strip('"').strip("'")
                h = h.strip().strip('"').strip("'")
            except Exception:
                pass
            salt = base64.b64decode(s.encode("ascii"))
            expected = base64.b64decode(h.encode("ascii"))
            dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
            return dk == expected
        except Exception:
            try:
                return SecurityUtils.verify_password(password, hs)
            except Exception:
                return False

    def _ensure_owner_user(self) -> None:
        try:
            pwd = os.getenv("ADMIN_INITIAL_PASSWORD", "").strip() or os.getenv("DEV_PASSWORD", "").strip()
            if not pwd:
                return
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute("SELECT id FROM admin_users WHERE username = %s", ("owner",))
                row = cur.fetchone()
                if not row:
                    ph = self._hash_password(pwd)
                    cur.execute("INSERT INTO admin_users (username, password_hash) VALUES (%s, %s)", ("owner", ph))
                    conn.commit()
                    try:
                        self.log_action("system", "bootstrap_admin_owner_user", None, None)
                    except Exception:
                        pass
        except Exception:
            pass

    def verificar_owner_password(self, password: str) -> bool:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute("SELECT password_hash FROM admin_users WHERE username = %s", ("owner",))
                row = cur.fetchone()
                if not row:
                    return False
                try:
                    stored = str(row[0] or "").strip()
                except Exception:
                    stored = row[0]
                return self._verify_password(password, stored)
        except Exception:
            return False

    def set_admin_owner_password(self, new_password: str) -> bool:
        try:
            if not (new_password or "").strip():
                return False
            ph = self._hash_password(str(new_password).strip())
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute("UPDATE admin_users SET password_hash = %s WHERE username = %s", (ph, "owner"))
                conn.commit()
            return True
        except Exception:
            return False

    # --- Gym Management Methods ---

    def listar_gimnasios(self) -> List[Dict[str, Any]]:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute("SELECT id, nombre, subdominio, db_name, owner_phone, status, hard_suspend, suspended_until, b2_bucket_name, b2_bucket_id, created_at FROM gyms ORDER BY id DESC")
                rows = cur.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error listing gyms: {e}")
            return []

    def listar_gimnasios_avanzado(self, page: int, page_size: int, q: Optional[str], status: Optional[str], order_by: Optional[str], order_dir: Optional[str]) -> Dict[str, Any]:
        try:
            p = max(int(page or 1), 1)
            ps = max(int(page_size or 20), 1)
            allowed_cols = {"id", "nombre", "subdominio", "status", "created_at"}
            ob = (order_by or "id").strip().lower()
            if ob not in allowed_cols:
                ob = "id"
            od = (order_dir or "desc").strip().upper()
            if od not in {"ASC", "DESC"}:
                od = "DESC"
            where_terms: List[str] = []
            params: List[Any] = []
            qv = str(q or "").strip().lower()
            if qv:
                where_terms.append("(LOWER(nombre) LIKE %s OR LOWER(subdominio) LIKE %s)")
                like = f"%{qv}%"
                params.extend([like, like])
            sv = str(status or "").strip().lower()
            if sv:
                where_terms.append("LOWER(status) = %s")
                params.append(sv)
            where_sql = (" WHERE " + " AND ".join(where_terms)) if where_terms else ""
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute(f"SELECT COUNT(*) FROM gyms{where_sql}", params)
                total_row = cur.fetchone()
                total = int(total_row[0]) if total_row else 0
            with self.db.get_connection_context() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(
                    f"SELECT id, nombre, subdominio, db_name, owner_phone, status, hard_suspend, suspended_until, b2_bucket_name, b2_bucket_id, whatsapp_phone_id, whatsapp_access_token, created_at FROM gyms{where_sql} ORDER BY {ob} {od} LIMIT %s OFFSET %s",
                    params + [ps, (p - 1) * ps]
                )
                rows = cur.fetchall()
            items: List[Dict[str, Any]] = []
            for r in rows:
                dct = dict(r)
                dct["wa_configured"] = bool((dct.get("whatsapp_phone_id") or "").strip()) and bool((dct.get("whatsapp_access_token") or "").strip())
                items.append(dct)
            return {"items": items, "total": total, "page": p, "page_size": ps}
        except Exception as e:
            logger.error(f"Error listing gyms advanced: {e}")
            return {"items": [], "total": 0, "page": 1, "page_size": int(page_size or 20)}

    def listar_gimnasios_con_resumen(self, page: int, page_size: int, q: Optional[str], status: Optional[str], order_by: Optional[str], order_dir: Optional[str]) -> Dict[str, Any]:
        try:
            p = max(int(page or 1), 1)
            ps = max(int(page_size or 20), 1)
            allowed_cols = {"id", "nombre", "subdominio", "status", "created_at", "next_due_date"}
            ob = (order_by or "id").strip().lower()
            if ob not in allowed_cols:
                ob = "id"
            od = (order_dir or "desc").strip().upper()
            if od not in {"ASC", "DESC"}:
                od = "DESC"
            where_terms: List[str] = []
            params: List[Any] = []
            qv = str(q or "").strip().lower()
            if qv:
                where_terms.append("(LOWER(g.nombre) LIKE %s OR LOWER(g.subdominio) LIKE %s)")
                like = f"%{qv}%"
                params.extend([like, like])
            sv = str(status or "").strip().lower()
            if sv:
                where_terms.append("LOWER(g.status) = %s")
                params.append(sv)
            where_sql = (" WHERE " + " AND ".join(where_terms)) if where_terms else ""
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute(f"SELECT COUNT(*) FROM gyms g{where_sql}", params)
                total_row = cur.fetchone()
                total = int(total_row[0]) if total_row else 0
            with self.db.get_connection_context() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                order_sql = f"ORDER BY gs.next_due_date {od} NULLS LAST" if ob == "next_due_date" else f"ORDER BY g.{ob} {od}"
                cur.execute(
                    f"""
                    SELECT g.id, g.nombre, g.subdominio, g.db_name, g.owner_phone, g.status, g.hard_suspend, g.suspended_until,
                           g.whatsapp_phone_id, g.whatsapp_access_token,
                           g.b2_bucket_name, g.b2_bucket_id, g.created_at,
                           gs.next_due_date, gs.status AS sub_status,
                           (SELECT amount FROM gym_payments WHERE gym_id = g.id ORDER BY paid_at DESC LIMIT 1) AS last_payment_amount,
                           (SELECT currency FROM gym_payments WHERE gym_id = g.id ORDER BY paid_at DESC LIMIT 1) AS last_payment_currency,
                           (SELECT paid_at FROM gym_payments WHERE gym_id = g.id ORDER BY paid_at DESC LIMIT 1) AS last_payment_at
                    FROM gyms g
                    LEFT JOIN gym_subscriptions gs ON gs.gym_id = g.id
                    {where_sql}
                    {order_sql}
                    LIMIT %s OFFSET %s
                    """,
                    params + [ps, (p - 1) * ps]
                )
                rows = cur.fetchall()
            items: List[Dict[str, Any]] = []
            for r in rows:
                dct = dict(r)
                dct["wa_configured"] = bool((dct.get("whatsapp_phone_id") or "").strip()) and bool((dct.get("whatsapp_access_token") or "").strip())
                items.append(dct)
            return {"items": items, "total": total, "page": p, "page_size": ps}
        except Exception as e:
            logger.error(f"Error listing gyms summary: {e}")
            return {"items": [], "total": 0, "page": 1, "page_size": int(page_size or 20)}

    def obtener_gimnasio(self, gym_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute("SELECT * FROM gyms WHERE id = %s", (int(gym_id),))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting gym {gym_id}: {e}")
            return None

    def set_estado_gimnasio(self, gym_id: int, status: str, hard_suspend: bool = False, suspended_until: Optional[str] = None, reason: Optional[str] = None) -> bool:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute("UPDATE gyms SET status = %s, hard_suspend = %s, suspended_until = %s, suspended_reason = %s WHERE id = %s", (status, bool(hard_suspend), suspended_until, reason, int(gym_id)))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error setting gym status {gym_id}: {e}")
            return False

    def registrar_pago(self, gym_id: int, plan: Optional[str], amount: Optional[float], currency: Optional[str], valid_until: Optional[str], status: Optional[str], notes: Optional[str]) -> bool:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO gym_payments (gym_id, plan, amount, currency, valid_until, status, notes) VALUES (%s, %s, %s, %s, %s, %s, %s)", (int(gym_id), plan, amount, currency, valid_until, status, notes))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error registering payment for gym {gym_id}: {e}")
            return False

    def listar_pagos(self, gym_id: int) -> List[Dict[str, Any]]:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute("SELECT id, plan, amount, currency, paid_at, valid_until, status, notes FROM gym_payments WHERE gym_id = %s ORDER BY paid_at DESC", (int(gym_id),))
                rows = cur.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error listing payments for gym {gym_id}: {e}")
            return []

    def listar_pagos_recientes(self, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            lim = max(int(limit or 10), 1)
            with self.db.get_connection_context() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(
                    "SELECT gp.id, gp.gym_id, g.nombre, g.subdominio, gp.plan, gp.amount, gp.currency, gp.paid_at, gp.valid_until, gp.status FROM gym_payments gp JOIN gyms g ON g.id = gp.gym_id ORDER BY gp.paid_at DESC LIMIT %s",
                    (lim,)
                )
                rows = cur.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error listing recent payments: {e}")
            return []

    def subdominio_disponible(self, subdominio: str) -> bool:
        try:
            s = str(subdominio or "").strip().lower()
            if not s:
                return False
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1 FROM gyms WHERE subdominio = %s", (s,))
                row = cur.fetchone()
                return not bool(row)
        except Exception:
            return False

    def actualizar_gimnasio(self, gym_id: int, nombre: Optional[str], subdominio: Optional[str]) -> Dict[str, Any]:
        try:
            gid = int(gym_id)
            nm = (nombre or "").strip()
            sd = (subdominio or "").strip().lower()
            sets: List[str] = []
            params: List[Any] = []
            if nm:
                sets.append("nombre = %s")
                params.append(nm)
            if sd:
                with self.db.get_connection_context() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT 1 FROM gyms WHERE subdominio = %s AND id <> %s", (sd, gid))
                    if cur.fetchone():
                        return {"ok": False, "error": "subdominio_in_use"}
                sets.append("subdominio = %s")
                params.append(sd)
            if not sets:
                return {"ok": False, "error": "no_fields"}
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                sql = f"UPDATE gyms SET {', '.join(sets)} WHERE id = %s"
                params.append(gid)
                cur.execute(sql, params)
                conn.commit()
            return {"ok": True}
        except Exception as e:
            logger.error(f"Error updating gym {gym_id}: {e}")
            return {"ok": False, "error": str(e)}

    def log_action(self, actor: Optional[str], action: str, gym_id: Optional[int], details: Optional[str]) -> bool:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO admin_audit (actor_username, action, gym_id, details) VALUES (%s, %s, %s, %s)",
                    (actor, action, gym_id, details)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error logging action: {e}")
            return False

    # --- Additional Methods from AdminDatabaseManager ---

    def _slugify(self, value: str) -> str:
        v = str(value or "").strip().lower()
        if not v:
            return ""
        nf = unicodedata.normalize("NFKD", v)
        ascii_v = nf.encode("ascii", "ignore").decode("ascii")
        ascii_v = re.sub(r"[^a-z0-9]+", "-", ascii_v)
        ascii_v = re.sub(r"-+", "-", ascii_v)
        ascii_v = ascii_v.strip("-")
        return ascii_v

    def _sanitize_db_name(self, db_name: str) -> str:
        """
        Sanitize a database name to prevent SQL injection.
        Only allows lowercase alphanumeric and underscores.
        PostgreSQL identifiers max 63 chars.
        """
        if not db_name:
            return ""
        # Only allow alphanumeric, underscore, hyphen
        sanitized = re.sub(r'[^a-z0-9_-]', '_', db_name.lower().strip())
        # Replace hyphen with underscore for DB names
        sanitized = sanitized.replace('-', '_')
        # Ensure it starts with a letter or underscore
        if sanitized and sanitized[0].isdigit():
            sanitized = '_' + sanitized
        # PostgreSQL max identifier length
        return sanitized[:63]

    def _validate_subdomain(self, subdomain: str) -> tuple:
        """
        Validate subdomain format.
        Returns (is_valid: bool, error_message: str)
        """
        if not subdomain:
            return False, "Subdomain cannot be empty"
        
        s = subdomain.strip().lower()
        
        if len(s) < 2:
            return False, "Subdomain too short (min 2 chars)"
        
        if len(s) > 63:
            return False, "Subdomain too long (max 63 chars)"
        
        # Check for dangerous characters
        dangerous = ["'", '"', ';', '--', '/*', '*/', '\\', '\x00']
        for char in dangerous:
            if char in s:
                return False, f"Invalid character in subdomain"
        
        # Must match subdomain pattern
        if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$', s):
            return False, "Subdomain must be alphanumeric with optional hyphens"
        
        # Reserved names
        reserved = ['admin', 'www', 'api', 'static', 'assets', 'test', 'staging']
        if s in reserved:
            return False, f"Subdomain '{s}' is reserved"
        
        return True, ""

    def sugerir_subdominio_unico(self, nombre_base: str) -> str:
        base = self._slugify(nombre_base)
        if not base:
            base = "gym"
        cur = base
        if self.subdominio_disponible(cur):
            return cur
        i = 1
        while i < 1000:
            cand = f"{base}-{i}"
            if self.subdominio_disponible(cand):
                return cand
            i += 1
        return f"{base}-{int(os.urandom(2).hex(), 16)}"

    def eliminar_gimnasio(self, gym_id: int) -> bool:
        try:
            db_name = None
            subdominio = None
            try:
                with self.db.get_connection_context() as conn:
                    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    cur.execute("SELECT db_name, subdominio FROM gyms WHERE id = %s", (int(gym_id),))
                    row = cur.fetchone()
                if row:
                    db_name = str(row.get("db_name") or "").strip()
                    subdominio = str(row.get("subdominio") or "").strip().lower()
            except Exception:
                db_name = None
            try:
                if subdominio:
                    self._b2_delete_prefix_for_sub(subdominio)
            except Exception:
                pass
            if db_name:
                try:
                    self._eliminar_db_postgres(db_name)
                except Exception:
                    pass
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM gyms WHERE id = %s", (int(gym_id),))
                conn.commit()
                return True
        except Exception:
            return False

    def is_gym_suspended(self, subdominio: str) -> bool:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute("SELECT status, hard_suspend, suspended_until FROM gyms WHERE subdominio = %s", (subdominio.strip().lower(),))
                row = cur.fetchone()
                if not row:
                    return False
                status, hard_s, until = row[0], row[1], row[2]
                if hard_s:
                    return True
                if str(status or "").lower() == "suspended":
                    if until is None:
                        return True
                    try:
                        from datetime import datetime
                        return datetime.utcnow() <= until
                    except Exception:
                        return True
                try:
                    cur.execute("SELECT valid_until FROM gym_payments gp JOIN gyms g ON gp.gym_id = g.id WHERE g.subdominio = %s ORDER BY gp.paid_at DESC LIMIT 1", (subdominio.strip().lower(),))
                    prow = cur.fetchone()
                    if not prow:
                        return False
                    vu = prow[0]
                    if vu is None:
                        return False
                    from datetime import datetime
                    return datetime.utcnow() > vu
                except Exception:
                    return False
        except Exception:
            return False

    def set_mantenimiento(self, gym_id: int, message: Optional[str]) -> bool:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute("UPDATE gyms SET status = %s, hard_suspend = false, suspended_until = NULL, suspended_reason = %s WHERE id = %s", ("maintenance", message, int(gym_id)))
                conn.commit()
                return True
        except Exception:
            return False

    def clear_mantenimiento(self, gym_id: int) -> bool:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute("UPDATE gyms SET status = %s, suspended_reason = NULL WHERE id = %s", ("active", int(gym_id)))
                conn.commit()
                return True
        except Exception:
            return False

    def schedule_mantenimiento(self, gym_id: int, until: Optional[str], message: Optional[str]) -> bool:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE gyms SET status = %s, hard_suspend = false, suspended_until = %s, suspended_reason = %s WHERE id = %s",
                    ("maintenance", until, message, int(gym_id)),
                )
                conn.commit()
                return True
        except Exception:
            return False

    def get_mantenimiento(self, subdominio: str) -> Optional[str]:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute("SELECT suspended_reason FROM gyms WHERE subdominio = %s AND status = 'maintenance'", (subdominio.strip().lower(),))
                row = cur.fetchone()
                return row[0] if row else None
        except Exception:
            return None

    def batch_set_maintenance(self, ids: List[int], message: Optional[str]) -> Dict[str, Any]:
        """Set maintenance mode for many gyms."""
        ok_count = 0
        fail_count = 0
        for gym_id in (ids or []):
            try:
                if self.set_mantenimiento(int(gym_id), message):
                    ok_count += 1
                else:
                    fail_count += 1
            except Exception:
                fail_count += 1
        return {"ok": True, "updated": ok_count, "failed": fail_count}

    def batch_schedule_maintenance(self, ids: List[int], until: Optional[str], message: Optional[str]) -> Dict[str, Any]:
        """Schedule maintenance mode for many gyms until a given datetime/date string."""
        ok_count = 0
        fail_count = 0
        for gym_id in (ids or []):
            try:
                if self.schedule_mantenimiento(int(gym_id), until, message):
                    ok_count += 1
                else:
                    fail_count += 1
            except Exception:
                fail_count += 1
        return {"ok": True, "updated": ok_count, "failed": fail_count}

    def batch_clear_maintenance(self, ids: List[int]) -> Dict[str, Any]:
        """Clear maintenance mode for many gyms."""
        ok_count = 0
        fail_count = 0
        for gym_id in (ids or []):
            try:
                if self.clear_mantenimiento(int(gym_id)):
                    ok_count += 1
                else:
                    fail_count += 1
            except Exception:
                fail_count += 1
        return {"ok": True, "updated": ok_count, "failed": fail_count}

    def batch_send_owner_message(self, ids: List[int], message: str) -> Dict[str, Any]:
        """Send a WhatsApp message to gym owners for many gyms."""
        sent = 0
        failed = 0
        msg = str(message or "").strip()
        if not msg:
            return {"ok": False, "error": "message_required", "sent": 0}
        for gym_id in (ids or []):
            try:
                if self._enviar_whatsapp_a_owner(int(gym_id), msg):
                    sent += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
        return {"ok": True, "sent": sent, "failed": failed}

    def batch_suspend(self, ids: List[int], reason: Optional[str] = None, until: Optional[str] = None, hard: bool = False) -> Dict[str, Any]:
        """Suspend many gyms by setting status='suspended'."""
        updated = 0
        failed = 0
        for gym_id in (ids or []):
            try:
                if self.set_estado_gimnasio(int(gym_id), "suspended", bool(hard), until, reason):
                    updated += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
        return {"ok": True, "updated": updated, "failed": failed}

    def batch_reactivate(self, ids: List[int]) -> Dict[str, Any]:
        """Reactivate many gyms by setting status='active' and clearing suspension fields."""
        updated = 0
        failed = 0
        for gym_id in (ids or []):
            try:
                if self.set_estado_gimnasio(int(gym_id), "active", False, None, None):
                    updated += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
        return {"ok": True, "updated": updated, "failed": failed}

    def batch_provision(self, ids: List[int]) -> Dict[str, Any]:
        """Re-provision tenant DB schema and push WhatsApp config for many gyms."""
        updated = 0
        failed = 0
        for gym_id in (ids or []):
            try:
                gym = self.obtener_gimnasio(int(gym_id))
                if not gym:
                    failed += 1
                    continue
                db_name = str(gym.get("db_name") or "").strip()
                if not db_name:
                    failed += 1
                    continue
                params = self.resolve_admin_db_params()
                params["database"] = db_name
                ok = self._bootstrap_tenant_db(params, owner_data={"phone": gym.get("owner_phone"), "gym_name": gym.get("nombre")})
                try:
                    self._push_whatsapp_to_gym_db(int(gym_id))
                except Exception:
                    pass
                if ok:
                    updated += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
        return {"ok": True, "provisioned": updated, "failed": failed}

    # --- Infrastructure & B2 Methods ---

    def _bootstrap_tenant_db(self, connection_params: Dict[str, Any], owner_data: Optional[Dict[str, Any]] = None) -> bool:
        try:
            # Construct URL for SQLAlchemy
            user = connection_params.get("user")
            password = connection_params.get("password")
            host = connection_params.get("host")
            port = connection_params.get("port")
            dbname = connection_params.get("database")
            
            url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
            if connection_params.get("sslmode"):
                url += f"?sslmode={connection_params.get('sslmode')}"
                
            engine = create_engine(url, pool_pre_ping=True)
            
            # 1. Create Schema
            tables = list(Base.metadata.tables.keys())
            logger.info(f"Bootstrapping tenant {dbname}. Tables to create: {tables}")
            
            # Ensure we are using the bound engine
            Base.metadata.create_all(bind=engine)
            
            # Verify creation
            try:
                from sqlalchemy import inspect
                insp = inspect(engine)
                created_tables = insp.get_table_names()
                logger.info(f"Tables actually created in {dbname}: {created_tables}")
                if not created_tables:
                    logger.error(f"CRITICAL: No tables created for {dbname} despite create_all execution.")
            except Exception as e:
                logger.error(f"Error verifying tables in {dbname}: {e}")

            # 1.5 Ensure critical constraints exist (create_all does not alter existing tables)
            try:
                with engine.connect() as conn:
                    conn.execute(text("""
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM pg_constraint WHERE conname = 'idx_pagos_usuario_mes_año'
                            ) THEN
                                EXECUTE format(
                                    'ALTER TABLE pagos ADD CONSTRAINT %I UNIQUE (usuario_id, mes, %I)',
                                    'idx_pagos_usuario_mes_año',
                                    'año'
                                );
                            END IF;

                            IF NOT EXISTS (
                                SELECT 1 FROM pg_constraint WHERE conname = 'asistencias_usuario_id_fecha_key'
                            ) THEN
                                EXECUTE 'ALTER TABLE asistencias ADD CONSTRAINT asistencias_usuario_id_fecha_key UNIQUE (usuario_id, fecha)';
                            END IF;
                        END $$;
                    """))

                    conn.execute(text("""
                        DO $$
                        BEGIN
                            IF EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name = 'ejercicios' AND column_name = 'variantes'
                            ) THEN
                                NULL;
                            ELSE
                                EXECUTE 'ALTER TABLE ejercicios ADD COLUMN variantes TEXT';
                            END IF;

                            IF EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name = 'usuarios' AND column_name = 'pin'
                            ) THEN
                                IF EXISTS (
                                    SELECT 1 FROM information_schema.columns
                                    WHERE table_name = 'usuarios' AND column_name = 'pin'
                                    AND data_type = 'character varying'
                                    AND (character_maximum_length IS NULL OR character_maximum_length < 100)
                                ) THEN
                                    EXECUTE 'ALTER TABLE usuarios ALTER COLUMN pin TYPE VARCHAR(100)';
                                END IF;
                                EXECUTE 'ALTER TABLE usuarios ALTER COLUMN pin SET DEFAULT ''123456''';
                            END IF;
                        END $$;
                    """))
                    conn.commit()
            except Exception as e:
                logger.warning(f"Could not ensure constraints in {dbname}: {e}")

            try:
                with engine.connect() as conn:
                    try:
                        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
                    except Exception:
                        pass
                    for stmt in (
                        "CREATE INDEX IF NOT EXISTS idx_usuarios_nombre_trgm ON usuarios USING gin (lower(nombre) gin_trgm_ops)",
                        "CREATE INDEX IF NOT EXISTS idx_rutinas_nombre_trgm ON rutinas USING gin (lower(nombre_rutina) gin_trgm_ops)",
                        "CREATE INDEX IF NOT EXISTS idx_ejercicios_nombre_trgm ON ejercicios USING gin (lower(nombre) gin_trgm_ops)",
                        "CREATE INDEX IF NOT EXISTS idx_rutina_ejercicios_rutina_dia_orden ON rutina_ejercicios (rutina_id, dia_semana, orden)",
                        "CREATE INDEX IF NOT EXISTS idx_comprobantes_pago_emitido_pago_fecha_desc ON comprobantes_pago (pago_id, fecha_creacion DESC) WHERE estado = 'emitido'",
                        "CREATE INDEX IF NOT EXISTS idx_pagos_metodo_fecha_desc ON pagos (metodo_pago_id, fecha_pago DESC)",
                    ):
                        try:
                            conn.execute(text(stmt))
                        except Exception:
                            pass
                    if self._env_flag("TENANT_DB_ANALYZE_ON_BOOTSTRAP", True):
                        for stmt in (
                            "ANALYZE usuarios",
                            "ANALYZE rutinas",
                            "ANALYZE ejercicios",
                            "ANALYZE pagos",
                            "ANALYZE comprobantes_pago",
                            "ANALYZE rutina_ejercicios",
                        ):
                            try:
                                conn.execute(text(stmt))
                            except Exception:
                                pass
                    conn.commit()
            except Exception as e:
                logger.warning(f"Could not ensure indexes in {dbname}: {e}")

            # 2. Create Owner User if provided
            if owner_data:
                Session = sessionmaker(bind=engine)
                session = Session()
                try:
                    # Check if owner exists
                    existing = session.query(Usuario).filter(Usuario.rol == 'owner').first()
                    if not existing:
                        # Default password/PIN for owner
                        owner = Usuario(
                            nombre="Dueño",
                            telefono=owner_data.get("phone") or "0000000000",
                            rol="owner",
                            pin="1234", # Default PIN
                            activo=True
                        )
                        session.add(owner)
                        
                        # Initialize some default config
                        cfg = Configuracion(
                            clave="gym_name",
                            valor=owner_data.get("gym_name") or "Mi Gimnasio",
                            tipo="string"
                        )
                        session.add(cfg)
                        
                        # Initialize default data
                        # Payment Methods
                        mp_efectivo = MetodoPago(nombre="Efectivo", icono="fa-money", color="#2ecc71", activo=True)
                        mp_transf = MetodoPago(nombre="Transferencia", icono="fa-bank", color="#3498db", activo=True)
                        session.add(mp_efectivo)
                        session.add(mp_transf)

                        # Quota Types
                        tc_mensual = TipoCuota(nombre="Mensual", precio=30.00, descripcion="Acceso mensual completo", duracion_dias=30, activo=True)
                        tc_diario = TipoCuota(nombre="Pase Diario", precio=5.00, descripcion="Acceso por un día", duracion_dias=1, activo=True)
                        session.add(tc_mensual)
                        session.add(tc_diario)

                        # Payment Concepts
                        cp_cuota = ConceptoPago(nombre="Cuota Mensual", tipo="fijo", precio_base=30.00, descripcion="Pago de cuota mensual", activo=True)
                        cp_matricula = ConceptoPago(nombre="Matrícula", tipo="fijo", precio_base=10.00, descripcion="Matrícula de inscripción", activo=True)
                        session.add(cp_cuota)
                        session.add(cp_matricula)
                        
                        session.commit()
                except Exception as e:
                    logger.error(f"Error seeding owner in {dbname}: {e}")
                    session.rollback()
                finally:
                    session.close()
            
            return True
        except Exception as e:
            logger.error(f"Error bootstrapping tenant {connection_params.get('database')}: {e}")
            return False

    def _crear_db_postgres(self, db_name: str, owner_data: Optional[Dict[str, Any]] = None) -> bool:
        try:
            name = str(db_name or "").strip()
            if not name:
                return False
            token = (os.getenv("NEON_API_TOKEN") or "").strip()
            if token and requests is not None:
                base = self.resolve_admin_db_params()
                host = str(base.get("host") or "").strip().lower()
                comp_host = host.replace("-pooler.", ".")
                api = "https://console.neon.tech/api/v2"
                headers = {"Accept": "application/json", "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                project_id = (os.getenv("NEON_PROJECT_ID") or "").strip()
                branch_id = (os.getenv("NEON_BRANCH_ID") or "").strip()
                
                # If project_id/branch_id not set, try to find them (simplified logic from original)
                if not project_id or not branch_id:
                    pr = requests.get(f"{api}/projects", headers=headers, timeout=10)
                    if pr.status_code == 200:
                        pjs = (pr.json() or {}).get("projects") or []
                        for pj in pjs:
                            pid = pj.get("id")
                            if not pid: continue
                            er = requests.get(f"{api}/projects/{pid}/endpoints", headers=headers, timeout=10)
                            if er.status_code == 200:
                                eps = (er.json() or {}).get("endpoints") or []
                                for ep in eps:
                                    h = str(ep.get("host") or "").strip().lower()
                                    hp = h.replace("-pooler.", ".")
                                    if h == host or hp == host or h == comp_host or hp == comp_host:
                                        project_id = pid
                                        branch_id = ep.get("branch_id")
                                        break
                            if project_id: break

                if project_id and branch_id:
                    # Check if DB exists
                    lr = requests.get(f"{api}/projects/{project_id}/branches/{branch_id}/databases", headers=headers, timeout=10)
                    if lr.status_code == 200:
                        dbs = (lr.json() or {}).get("databases") or []
                        for d in dbs:
                            if str(d.get("name") or "").strip().lower() == name.lower():
                                # Already exists, initialize
                                params = self.resolve_admin_db_params()
                                params["database"] = name
                                self._bootstrap_tenant_db(params, owner_data)
                                return True
                    
                    # Create DB
                    owner = "neondb_owner"
                    cr = requests.post(f"{api}/projects/{project_id}/branches/{branch_id}/databases", headers=headers, json={"database": {"name": name, "owner_name": owner}}, timeout=12)
                    if 200 <= cr.status_code < 300:
                        # Wait for DB to be ready
                        import time
                        time.sleep(2) # Initial wait
                        
                        params = self.resolve_admin_db_params()
                        params["database"] = name
                        
                        # Retry bootstrap a few times
                        for i in range(5):
                            if self._bootstrap_tenant_db(params, owner_data):
                                return True
                            time.sleep(2)
                        
                        return False
                    return False
                
            # Fallback to standard Postgres creation
            base = self.resolve_admin_db_params()
            host = base.get("host")
            port = int(base.get("port") or 5432)
            user = base.get("user")
            password = base.get("password")
            sslmode = base.get("sslmode")
            try:
                connect_timeout = int(base.get("connect_timeout") or 10)
            except Exception:
                connect_timeout = 10
            appname = (base.get("application_name") or "gym_admin_provisioner").strip()
            base_db = os.getenv("ADMIN_DB_BASE_NAME", "neondb").strip() or "neondb"
            
            def try_create(conn_db):
                conn = psycopg2.connect(host=host, port=port, dbname=conn_db, user=user, password=password, sslmode=sslmode, connect_timeout=connect_timeout, application_name=appname)
                try:
                    conn.autocommit = True
                    cur = conn.cursor()
                    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
                    exists = bool(cur.fetchone())
                    if not exists:
                        try:
                            cur.execute(f"CREATE DATABASE {name}")
                        except Exception:
                            pass
                    cur.close()
                    return True
                finally:
                    conn.close()

            created = False
            try:
                created = try_create(base_db)
            except Exception:
                # Fallback to 'postgres' if base_db (neondb) fails
                try:
                    created = try_create("postgres")
                except Exception:
                    created = False
            
            if not created:
                # Check if it exists anyway
                 try:
                    params = dict(base)
                    params["database"] = name
                    with RawPostgresManager(params).get_connection_context():
                        created = True
                 except Exception:
                    return False

            if created:
                params = dict(base)
                params["database"] = name
                self._bootstrap_tenant_db(params, owner_data)
                return True
            return False
        except Exception as e:
            logger.error(f"Error creating DB {db_name}: {e}")
            return False

    def _crear_db_postgres_con_reintentos(self, db_name: str, intentos: int = 3, espera: float = 2.0, owner_data: Optional[Dict[str, Any]] = None) -> tuple[bool, str]:
        ok = False
        last_err = ""
        for i in range(max(1, int(intentos))):
            try:
                ok = bool(self._crear_db_postgres(db_name, owner_data))
                if ok:
                    return True, ""
                last_err = "create_failed"
            except Exception as e:
                ok = False
                last_err = str(e)
            try:
                time.sleep(espera)
            except Exception:
                pass
        return False, last_err

    def _eliminar_db_postgres(self, db_name: str) -> bool:
        """
        Delete a PostgreSQL database safely.
        Uses proper sanitization to prevent SQL injection.
        """
        try:
            name = str(db_name or "").strip()
            if not name:
                return False
            
            # CRITICAL: Sanitize db_name to prevent SQL injection
            safe_name = self._sanitize_db_name(name)
            if not safe_name:
                logger.error(f"Invalid db_name for deletion: {name}")
                return False
            
            # Verify the sanitized name matches expected pattern
            if safe_name != name.lower().replace('-', '_'):
                logger.warning(f"Database name was sanitized from '{name}' to '{safe_name}'")
            
            token = (os.getenv("NEON_API_TOKEN") or "").strip()
            
            # Try Neon API first if available
            if token and requests is not None:
                try:
                    project_id = (os.getenv("NEON_PROJECT_ID") or "").strip()
                    branch_id = (os.getenv("NEON_BRANCH_ID") or "").strip()
                    
                    if project_id and branch_id:
                        api = "https://console.neon.tech/api/v2"
                        headers = {
                            "Accept": "application/json",
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json"
                        }
                        
                        # Delete via API
                        del_url = f"{api}/projects/{project_id}/branches/{branch_id}/databases/{safe_name}"
                        resp = requests.delete(del_url, headers=headers, timeout=15)
                        
                        if 200 <= resp.status_code < 300 or resp.status_code == 404:
                            logger.info(f"Deleted database '{safe_name}' via Neon API")
                            return True
                except Exception as e:
                    logger.warning(f"Neon API deletion failed, falling back to SQL: {e}")
            
            # Fallback to direct SQL
            base = self.resolve_admin_db_params()
            host = base.get("host")
            port = int(base.get("port") or 5432)
            user = base.get("user")
            password = base.get("password")
            sslmode = base.get("sslmode")
            connect_timeout = int(base.get("connect_timeout") or 10)
            application_name = (base.get("application_name") or "gym_admin_provisioner").strip()
            
            # Connect to maintenance DB to drop
            conn = psycopg2.connect(
                host=host, port=port, dbname="postgres",
                user=user, password=password, sslmode=sslmode,
                connect_timeout=connect_timeout, application_name=application_name
            )
            try:
                conn.autocommit = True
                cur = conn.cursor()
                
                # Terminate existing connections
                try:
                    cur.execute(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()",
                        (safe_name,)
                    )
                except Exception as e:
                    logger.debug(f"Could not terminate connections to {safe_name}: {e}")
                
                # Use psycopg2.sql for safe identifier quoting
                from psycopg2 import sql
                drop_query = sql.SQL("DROP DATABASE IF EXISTS {}").format(
                    sql.Identifier(safe_name)
                )
                
                try:
                    cur.execute(drop_query)
                    logger.info(f"Dropped database: {safe_name}")
                except Exception as e:
                    logger.error(f"Failed to drop database {safe_name}: {e}")
                    return False
                
                cur.close()
            finally:
                conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting database {db_name}: {e}")
            return False

    def _rename_db_postgres(self, old_name: str, new_name: str) -> bool:
        try:
            on = str(old_name or "").strip()
            nn = str(new_name or "").strip()
            if not on or not nn or on == nn:
                return False
            base = self.resolve_admin_db_params()
            host = base.get("host")
            port = int(base.get("port") or 5432)
            user = base.get("user")
            password = base.get("password")
            sslmode = base.get("sslmode")
            connect_timeout = int(base.get("connect_timeout") or 10)
            application_name = (base.get("application_name") or "gym_admin_renamer").strip()
            
            conn = psycopg2.connect(host=host, port=port, dbname="postgres", user=user, password=password, sslmode=sslmode, connect_timeout=connect_timeout, application_name=application_name)
            try:
                conn.autocommit = True
                cur = conn.cursor()
                try:
                    cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s", (on,))
                except Exception:
                    pass
                try:
                    cur.execute(f"ALTER DATABASE {on} RENAME TO {nn}")
                except Exception:
                    return False
                cur.close()
            finally:
                conn.close()
            return True
        except Exception:
            return False

    # --- B2 Methods (Simplified Wrapper) ---
    
    def _b2_authorize_master(self) -> Dict[str, Any]:
        try:
            acc = (os.getenv("B2_MASTER_KEY_ID") or "").strip()
            key = (os.getenv("B2_MASTER_APPLICATION_KEY") or "").strip()
            if not acc or not key: return {}
            r = requests.get("https://api.backblazeb2.com/b2api/v4/b2_authorize_account", auth=(acc, key), timeout=12)
            return r.json() if r.status_code == 200 else {}
        except Exception:
            return {}

    def _b2_api_url(self, auth: Dict[str, Any]) -> str:
        try:
            return str((auth or {}).get("apiUrl") or "").strip() or str((((auth or {}).get("apiInfo") or {}).get("storageApi") or {}).get("apiUrl") or "").strip()
        except Exception:
            return ""

    def _b2_ensure_bucket_env(self) -> Dict[str, Any]:
        # Simplification: just return what's in env or try to find it
        return {"bucket_name": (os.getenv("B2_BUCKET_NAME") or "").strip(), "bucket_id": (os.getenv("B2_BUCKET_ID") or "").strip()}

    def _b2_upload_placeholder(self, bucket_id: str, prefix: str) -> bool:
        # Placeholder
        return True

    def _b2_get_s3_client(self):
        try:
            import boto3
            from botocore.config import Config
            
            endpoint = os.getenv("B2_ENDPOINT_URL") # e.g. https://s3.us-east-005.backblazeb2.com or Cloudflare endpoint
            key_id = os.getenv("B2_KEY_ID") or os.getenv("B2_MASTER_KEY_ID")
            app_key = os.getenv("B2_APPLICATION_KEY") or os.getenv("B2_MASTER_APPLICATION_KEY")
            
            if not endpoint or not key_id or not app_key:
                return None
                
            # Try to infer region from endpoint if possible (B2 specific)
            region_name = None
            if "backblazeb2.com" in endpoint:
                # e.g. https://s3.us-east-005.backblazeb2.com -> us-east-005
                try:
                    parts = endpoint.replace("https://", "").replace("http://", "").split(".")
                    if len(parts) >= 2 and parts[0] == "s3":
                        region_name = parts[1]
                except Exception:
                    pass
            
            # Ensure endpoint has protocol
            if endpoint and not endpoint.startswith("http"):
                endpoint = f"https://{endpoint}"

            return boto3.client(
                's3',
                endpoint_url=endpoint,
                aws_access_key_id=key_id,
                aws_secret_access_key=app_key,
                config=Config(signature_version='s3v4'),
                region_name=region_name
            )
        except ImportError:
            logger.warning("boto3 not installed, cannot use S3/B2 storage")
            return None
        except Exception as e:
            logger.error(f"Error creating S3 client: {e}")
            return None

    def _b2_ensure_prefix_for_sub(self, subdominio: str) -> bool:
        try:
            s = str(subdominio or "").strip().lower()
            if not s: return False
            
            bucket = os.getenv("B2_BUCKET_NAME")
            if not bucket:
                logger.error("B2_BUCKET_NAME not set")
                return False
            
            s3 = self._b2_get_s3_client()
            if not s3:
                logger.error("Could not create S3 client")
                return False
            
            # Create a placeholder file to "create" the directory
            key = f"{s}-assets/.keep"
            s3.put_object(Bucket=bucket, Key=key, Body=b"")
            logger.info(f"Created B2 asset folder: {key}")
            return True
        except Exception as e:
            logger.error(f"Error ensuring B2 prefix for {subdominio}: {e}")
            return False

    def _b2_delete_prefix_for_sub(self, subdominio: str) -> bool:
        try:
            s = str(subdominio or "").strip().lower()
            if not s: return False
            
            bucket = os.getenv("B2_BUCKET_NAME")
            if not bucket: return False
            
            s3 = self._b2_get_s3_client()
            if not s3: return False
            
            prefix = f"{s}-assets/"
            
            # List and delete objects
            paginator = s3.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
            
            for page in pages:
                if 'Contents' in page:
                    objects = [{'Key': obj['Key']} for obj in page['Contents']]
                    if objects:
                        s3.delete_objects(Bucket=bucket, Delete={'Objects': objects})
            return True
        except Exception as e:
            logger.error(f"Error deleting B2 prefix for {subdominio}: {e}")
            return False

    def _b2_migrate_prefix_for_sub(self, old_sub: str, new_sub: str) -> bool:
        try:
            old_p = f"{old_sub}-assets/"
            new_p = f"{new_sub}-assets/"
            
            bucket = os.getenv("B2_BUCKET_NAME")
            if not bucket: return False
            
            s3 = self._b2_get_s3_client()
            if not s3: return False
            
            # Copy objects
            paginator = s3.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket, Prefix=old_p)
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        old_key = obj['Key']
                        new_key = old_key.replace(old_p, new_p, 1)
                        s3.copy_object(Bucket=bucket, CopySource={'Bucket': bucket, 'Key': old_key}, Key=new_key)
                        # Delete old
                        s3.delete_object(Bucket=bucket, Key=old_key)
            return True
        except Exception as e:
            logger.error(f"Error migrating B2 prefix: {e}")
            return False

    def upload_gym_asset(self, gym_id: int, file_content: bytes, filename: str, content_type: str = "application/octet-stream") -> Dict[str, Any]:
        """Upload a file to the gym's B2 assets folder and return the public URL."""
        try:
            # Get gym info
            gym = self.obtener_gimnasio(gym_id)
            if not gym:
                return {"ok": False, "error": "gym_not_found"}
            
            subdominio = gym.get("subdominio", "").strip().lower()
            if not subdominio:
                return {"ok": False, "error": "invalid_subdomain"}
            
            bucket = os.getenv("B2_BUCKET_NAME")
            if not bucket:
                return {"ok": False, "error": "B2_BUCKET_NAME not configured"}
            
            s3 = self._b2_get_s3_client()
            if not s3:
                return {"ok": False, "error": "S3 client not available"}
            
            # Ensure assets folder exists
            self._b2_ensure_prefix_for_sub(subdominio)
            
            # Sanitize filename
            safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
            timestamp = int(time.time())
            key = f"{subdominio}-assets/{timestamp}_{safe_filename}"
            
            # Upload
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=file_content,
                ContentType=content_type
            )
            
            # Build public URL (Cloudflare R2 or B2 public bucket)
            cdn_domain = os.getenv("CDN_CUSTOM_DOMAIN", "") or os.getenv("B2_CDN_DOMAIN", "")
            if cdn_domain:
                if not cdn_domain.startswith("http"):
                    cdn_domain = f"https://{cdn_domain}"
                public_url = f"{cdn_domain}/{key}"
            else:
                # Fallback to B2 native URL
                endpoint = os.getenv("B2_ENDPOINT_URL", "").strip()
                if endpoint:
                    public_url = f"{endpoint}/{bucket}/{key}"
                else:
                    public_url = f"https://{bucket}.s3.backblazeb2.com/{key}"
            
            logger.info(f"Uploaded asset for gym {gym_id}: {key}")
            return {"ok": True, "url": public_url, "key": key}
        except Exception as e:
            logger.error(f"Error uploading asset for gym {gym_id}: {e}")
            return {"ok": False, "error": str(e)}

    def save_gym_branding(self, gym_id: int, branding: Dict[str, Any]) -> Dict[str, Any]:
        """Save branding configuration for a gym (logo_url, colors, address, etc.)."""
        try:
            gym = self.obtener_gimnasio(gym_id)
            if not gym:
                return {"ok": False, "error": "gym_not_found"}
            
            subdominio = gym.get("subdominio", "").strip().lower()
            if not subdominio:
                return {"ok": False, "error": "invalid_subdomain"}
            
            # Get gym's tenant database
            db_name = gym.get("db_name")
            if not db_name:
                return {"ok": False, "error": "no_tenant_db"}
            
            # Save branding to configuracion table in tenant DB
            engine = self._get_tenant_engine(db_name)
            if not engine:
                return {"ok": False, "error": "could_not_connect_tenant"}
            
            Session = sessionmaker(bind=engine)
            session = Session()
            try:
                # Branding config keys
                config_keys = {
                    "logo_url": branding.get("logo_url", ""),
                    "nombre_publico": branding.get("nombre_publico", ""),
                    "direccion": branding.get("direccion", ""),
                    "color_primario": branding.get("color_primario", "#6366f1"),
                    "color_secundario": branding.get("color_secundario", "#22c55e"),
                    "color_fondo": branding.get("color_fondo", "#0a0a0a"),
                    "color_texto": branding.get("color_texto", "#ffffff"),
                }
                
                for key, value in config_keys.items():
                    # Upsert each config
                    existing = session.query(Configuracion).filter_by(clave=key).first()
                    if existing:
                        existing.valor = str(value)
                    else:
                        session.add(Configuracion(clave=key, valor=str(value)))
                
                session.commit()
                
                self.log_action("owner", "save_branding", gym_id, f"Updated branding for {subdominio}")
                return {"ok": True}
            finally:
                session.close()
                engine.dispose()
        except Exception as e:
            logger.error(f"Error saving branding for gym {gym_id}: {e}")
            return {"ok": False, "error": str(e)}

    def get_gym_branding(self, gym_id: int) -> Dict[str, Any]:
        """Get current branding configuration for a gym."""
        try:
            gym = self.obtener_gimnasio(gym_id)
            if not gym:
                return {}
            
            db_name = gym.get("db_name")
            if not db_name:
                return {}
            
            engine = self._get_tenant_engine(db_name)
            if not engine:
                return {}
            
            Session = sessionmaker(bind=engine)
            session = Session()
            try:
                branding = {}
                config_keys = ["logo_url", "nombre_publico", "direccion", "color_primario", 
                              "color_secundario", "color_fondo", "color_texto"]
                
                for key in config_keys:
                    config = session.query(Configuracion).filter_by(clave=key).first()
                    if config:
                        branding[key] = config.valor
                
                return branding
            finally:
                session.close()
                engine.dispose()
        except Exception as e:
            logger.error(f"Error getting branding for gym {gym_id}: {e}")
            return {}

    def get_gym_reminder_message(self, gym_id: int) -> Optional[str]:
        try:
            gym = self.obtener_gimnasio(gym_id)
            if not gym:
                return None
            db_name = gym.get("db_name")
            if not db_name:
                return None
            engine = self._get_tenant_engine(db_name)
            if not engine:
                return None
            Session = sessionmaker(bind=engine)
            session = Session()
            try:
                row = session.query(Configuracion).filter_by(clave="reminder_message").first()
                if not row:
                    return None
                return str(row.valor or "")
            finally:
                session.close()
                engine.dispose()
        except Exception:
            return None

    def set_gym_reminder_message(self, gym_id: int, message: Optional[str]) -> Dict[str, Any]:
        try:
            gym = self.obtener_gimnasio(gym_id)
            if not gym:
                return {"ok": False, "error": "gym_not_found"}
            db_name = gym.get("db_name")
            if not db_name:
                return {"ok": False, "error": "no_tenant_db"}
            engine = self._get_tenant_engine(db_name)
            if not engine:
                return {"ok": False, "error": "could_not_connect_tenant"}
            Session = sessionmaker(bind=engine)
            session = Session()
            try:
                msg = str(message or "")
                existing = session.query(Configuracion).filter_by(clave="reminder_message").first()
                if existing:
                    existing.valor = msg
                else:
                    session.add(Configuracion(clave="reminder_message", valor=msg))
                session.commit()
                return {"ok": True}
            finally:
                session.close()
                engine.dispose()
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _get_tenant_engine(self, db_name: str):
        """Get SQLAlchemy engine for a tenant database."""
        try:
            params = self.db.params.copy()
            params["database"] = db_name
            
            conn_str = f"postgresql://{params.get('user')}:{params.get('password')}@{params.get('host')}:{params.get('port')}/{db_name}?sslmode={params.get('sslmode', 'require')}"
            return create_engine(conn_str, pool_pre_ping=True)
        except Exception as e:
            logger.error(f"Error creating tenant engine for {db_name}: {e}")
            return None

    # --- Complex Business Logic ---

    def crear_gimnasio(self, nombre: str, subdominio: str, whatsapp_phone_id: str | None = None, whatsapp_access_token: str | None = None, owner_phone: str | None = None, whatsapp_business_account_id: str | None = None, whatsapp_verify_token: str | None = None, whatsapp_app_secret: str | None = None, whatsapp_nonblocking: bool | None = None, whatsapp_send_timeout_seconds: float | None = None, b2_bucket_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new gym with its own database.
        
        Security:
        - Validates subdomain format to prevent injection
        - Sanitizes database name
        - Logs all operations to audit table
        """
        try:
            self._ensure_schema()
        except Exception:
            pass
        
        # Validate subdomain
        sub = subdominio.strip().lower()
        is_valid, error = self._validate_subdomain(sub)
        if not is_valid:
            logger.warning(f"Invalid subdomain rejected: '{subdominio}' - {error}")
            return {"error": f"invalid_subdomain: {error}"}
        
        # Check if subdomain is available
        if not self.subdominio_disponible(sub):
            return {"error": "subdomain_already_exists"}
        
        # Validate nombre
        if not nombre or len(nombre.strip()) < 2:
            return {"error": "invalid_name: Name too short"}
        
        # Build DB name with sanitization
        suffix = os.getenv("TENANT_DB_SUFFIX", "_db")
        db_name = self._sanitize_db_name(f"{sub}{suffix}")
        if not db_name:
            return {"error": "invalid_db_name"}
        
        # Create DB
        owner_data = {"phone": owner_phone, "gym_name": nombre}
        created_db, err_msg = self._crear_db_postgres_con_reintentos(db_name, intentos=3, espera=2.0, owner_data=owner_data)
        if not created_db:
            # Log failed attempt
            try:
                self.log_action("system", "gym_creation_failed", None, f"subdomain={sub}, error={err_msg}")
            except Exception:
                pass
            return {"error": f"db_creation_failed: {err_msg}"}
            
        # Ensure B2 folder
        try:
             if not self._b2_ensure_prefix_for_sub(sub):
                 logger.error(f"B2 folder creation returned False for {sub}")
        except Exception as e:
             logger.error(f"B2 folder creation exception: {e}")

        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO gyms (nombre, subdominio, db_name, b2_bucket_name, b2_bucket_id, b2_key_id, b2_application_key, whatsapp_phone_id, whatsapp_access_token, whatsapp_business_account_id, whatsapp_verify_token, whatsapp_app_secret, whatsapp_nonblocking, whatsapp_send_timeout_seconds, owner_phone) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id", (nombre.strip(), sub, db_name, None, None, None, None, (whatsapp_phone_id or "").strip() or None, (whatsapp_access_token or "").strip() or None, (whatsapp_business_account_id or "").strip() or None, (whatsapp_verify_token or "").strip() or None, (whatsapp_app_secret or "").strip() or None, bool(whatsapp_nonblocking or False), whatsapp_send_timeout_seconds, (owner_phone or "").strip() or None))
                rid = cur.fetchone()[0]
                conn.commit()
                
                # Log successful creation
                try:
                    self.log_action("system", "gym_created", int(rid), f"subdomain={sub}, db_name={db_name}")
                except Exception:
                    pass
                
                try:
                    if (whatsapp_phone_id or whatsapp_access_token or whatsapp_business_account_id or whatsapp_verify_token or whatsapp_app_secret):
                        self._push_whatsapp_to_gym_db(int(rid))
                except Exception:
                    pass
                
                return {"id": int(rid), "nombre": nombre.strip(), "subdominio": sub, "db_name": db_name, "db_created": bool(created_db)}
        except Exception as e:
            logger.error(f"Error creating gym: {e}")
            # Log error
            try:
                self.log_action("system", "gym_creation_error", None, f"subdomain={sub}, error={str(e)}")
            except Exception:
                pass
            return {"error": str(e)}

    def renombrar_gimnasio_y_assets(self, gym_id: int, nombre: Optional[str], subdominio: Optional[str]) -> Dict[str, Any]:
        try:
            gid = int(gym_id)
            nm = (nombre or "").strip()
            sd = (subdominio or "").strip().lower()
            
            with self.db.get_connection_context() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute("SELECT subdominio, db_name FROM gyms WHERE id = %s", (gid,))
                row = cur.fetchone()
            if not row:
                return {"ok": False, "error": "gym_not_found"}
            
            old_sub = str((row or {}).get("subdominio") or "").strip().lower()
            old_db = str((row or {}).get("db_name") or "").strip()
            new_sub = sd or old_sub
            
            # If subdominio is changing, we need to handle renames
            if sd and sd != old_sub:
                # Migrate Assets (B2) - simplified
                try:
                    self._b2_migrate_prefix_for_sub(old_sub, new_sub)
                except Exception:
                    pass
                
                # Rename DB
                if old_db:
                    try:
                        suffix = os.getenv("TENANT_DB_SUFFIX", "_db")
                        new_db = f"{new_sub}{suffix}"
                        # Check if rename is needed and if old_db != new_db
                        if old_db != new_db:
                            if self._rename_db_postgres(old_db, new_db):
                                with self.db.get_connection_context() as conn:
                                    cur = conn.cursor()
                                    cur.execute("UPDATE gyms SET db_name = %s WHERE id = %s", (new_db, gid))
                                    conn.commit()
                    except Exception:
                        pass

            return self.actualizar_gimnasio(gid, nm, sd)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def eliminar_gimnasio(self, gym_id: int) -> bool:
        try:
            db_name = None
            subdominio = None
            try:
                with self.db.get_connection_context() as conn:
                    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    cur.execute("SELECT db_name, subdominio FROM gyms WHERE id = %s", (int(gym_id),))
                    row = cur.fetchone()
                if row:
                    db_name = str(row.get("db_name") or "").strip()
                    subdominio = str(row.get("subdominio") or "").strip().lower()
            except Exception:
                db_name = None
            
            # 1. Delete Assets (B2)
            try:
                if subdominio:
                    self._b2_delete_prefix_for_sub(subdominio)
            except Exception:
                pass
            
            # 2. Drop Database
            if db_name:
                try:
                    # Try Neon drop first if applicable, then standard Postgres drop
                    if not self._eliminar_db_postgres(db_name):
                        logger.warning(f"Could not drop database {db_name} for gym {gym_id}")
                except Exception:
                    pass
            
            # 3. Delete Record
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM gyms WHERE id = %s", (int(gym_id),))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error deleting gym {gym_id}: {e}")
            return False

    def set_gym_owner_phone(self, gym_id: int, owner_phone: Optional[str]) -> bool:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute("UPDATE gyms SET owner_phone = %s WHERE id = %s", ((owner_phone or "").strip() or None, int(gym_id)))
                conn.commit()
                return True
        except Exception:
            return False

    def set_gym_whatsapp_config(self, gym_id: int, phone_id: Optional[str], access_token: Optional[str], waba_id: Optional[str], verify_token: Optional[str], app_secret: Optional[str], nonblocking: Optional[bool], send_timeout_seconds: Optional[float]) -> bool:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                enc_at = SecureConfig.encrypt_waba_secret((access_token or '').strip()) if access_token and str(access_token).strip() else None
                enc_vt = SecureConfig.encrypt_waba_secret((verify_token or '').strip()) if verify_token and str(verify_token).strip() else None
                enc_as = SecureConfig.encrypt_waba_secret((app_secret or '').strip()) if app_secret and str(app_secret).strip() else None
                cur.execute(
                    "UPDATE gyms SET whatsapp_phone_id = %s, whatsapp_access_token = %s, whatsapp_business_account_id = %s, whatsapp_verify_token = %s, whatsapp_app_secret = %s, whatsapp_nonblocking = %s, whatsapp_send_timeout_seconds = %s WHERE id = %s",
                    (
                        (phone_id or "").strip() or None,
                        enc_at,
                        (waba_id or "").strip() or None,
                        enc_vt,
                        enc_as,
                        bool(nonblocking or False),
                        send_timeout_seconds,
                        int(gym_id),
                    ),
                )
                conn.commit()
            try:
                self._push_whatsapp_to_gym_db(int(gym_id))
            except Exception:
                pass
            return True
        except Exception:
            return False

    def clear_gym_whatsapp_config(self, gym_id: int) -> bool:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    UPDATE gyms
                    SET whatsapp_phone_id = NULL,
                        whatsapp_access_token = NULL,
                        whatsapp_business_account_id = NULL,
                        whatsapp_verify_token = NULL,
                        whatsapp_app_secret = NULL,
                        whatsapp_nonblocking = FALSE,
                        whatsapp_send_timeout_seconds = NULL
                    WHERE id = %s
                    """,
                    (int(gym_id),)
                )
                conn.commit()
            try:
                self._push_whatsapp_to_gym_db(int(gym_id))
            except Exception:
                pass
            return True
        except Exception:
            return False

    def _push_whatsapp_to_gym_db(self, gym_id: int) -> bool:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute("SELECT db_name, subdominio, whatsapp_phone_id, whatsapp_access_token, whatsapp_business_account_id, whatsapp_verify_token, whatsapp_app_secret, whatsapp_nonblocking, whatsapp_send_timeout_seconds FROM gyms WHERE id = %s", (int(gym_id),))
                row = cur.fetchone()
            if not row: return False
            
            db_name = str(row.get("db_name") or "").strip()
            subdominio = str(row.get("subdominio") or "").strip().lower()
            if not db_name: return False
            
            params = self.resolve_admin_db_params()
            params["database"] = db_name
            try:
                # Use a temporary connection for this push operation instead of full DatabaseManager
                # to avoid recursive initialization issues or context confusion
                
                # Decrypt secrets
                at_raw = str(row.get("whatsapp_access_token") or "")
                vt_raw = str(row.get("whatsapp_verify_token") or "")
                as_raw = str(row.get("whatsapp_app_secret") or "")
                
                at = SecureConfig.decrypt_waba_secret(at_raw) if at_raw else None
                vt = SecureConfig.decrypt_waba_secret(vt_raw) if vt_raw else ""
                asc = SecureConfig.decrypt_waba_secret(as_raw) if as_raw else ""
                
                # Direct psycopg2 update to tenant DB
                conn_params = params.copy()
                # Ensure psycopg2 compatible params
                pg_params = {
                    "host": conn_params.get("host"),
                    "port": conn_params.get("port"),
                    "dbname": conn_params.get("database"),
                    "user": conn_params.get("user"),
                    "password": conn_params.get("password"),
                    "sslmode": conn_params.get("sslmode"),
                    "connect_timeout": conn_params.get("connect_timeout"),
                    "application_name": "gym_admin_push_whatsapp"
                }
                
                with psycopg2.connect(**pg_params) as t_conn:
                    with t_conn.cursor() as t_cur:
                        # Update configuracion table (key-value store)
                        # NOTE: gym_config is a fixed-column table, configuracion is key-value
                        
                        # Helper to upsert config in configuracion table
                        def _upsert_config(k, v):
                            t_cur.execute(
                                "INSERT INTO configuracion (clave, valor) VALUES (%s, %s) ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor",
                                (k, v)
                            )
                        def _delete_config(k):
                            t_cur.execute("DELETE FROM configuracion WHERE clave = %s", (k,))

                        phone_id = str(row.get("whatsapp_phone_id") or "").strip()
                        waba_id = str(row.get("whatsapp_business_account_id") or "").strip()

                        if phone_id:
                            _upsert_config("WHATSAPP_PHONE_ID", phone_id)
                        else:
                            _delete_config("WHATSAPP_PHONE_ID")

                        if waba_id:
                            _upsert_config("WHATSAPP_BUSINESS_ACCOUNT_ID", waba_id)
                        else:
                            _delete_config("WHATSAPP_BUSINESS_ACCOUNT_ID")

                        if at:
                            _upsert_config("WHATSAPP_ACCESS_TOKEN", at)
                        else:
                            _delete_config("WHATSAPP_ACCESS_TOKEN")

                        if vt:
                            _upsert_config("WHATSAPP_VERIFY_TOKEN", vt)
                            _upsert_config("webhook_verify_token", vt)
                        else:
                            _delete_config("WHATSAPP_VERIFY_TOKEN")
                            _delete_config("webhook_verify_token")

                        if asc:
                            _upsert_config("WHATSAPP_APP_SECRET", asc)
                        else:
                            _delete_config("WHATSAPP_APP_SECRET")

                        try:
                            nb = bool(row.get("whatsapp_nonblocking") or False)
                            _upsert_config("NONBLOCKING_WHATSAPP_SEND", "1" if nb else "0")
                        except Exception:
                            pass
                        try:
                            st = row.get("whatsapp_send_timeout_seconds")
                            if st is None:
                                _delete_config("WHATSAPP_SEND_TIMEOUT_SECONDS")
                            else:
                                _upsert_config("WHATSAPP_SEND_TIMEOUT_SECONDS", str(st))
                        except Exception:
                            pass

                        t_cur.execute(
                            """
                            CREATE TABLE IF NOT EXISTS whatsapp_config (
                                id SERIAL PRIMARY KEY,
                                phone_id VARCHAR(50) NOT NULL,
                                waba_id VARCHAR(50) NOT NULL,
                                access_token TEXT,
                                active BOOLEAN DEFAULT TRUE,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )
                            """
                        )

                        if phone_id and waba_id and at:
                            t_cur.execute("UPDATE whatsapp_config SET active = FALSE")
                            t_cur.execute(
                                "INSERT INTO whatsapp_config (phone_id, waba_id, access_token, active) VALUES (%s, %s, %s, TRUE)",
                                (phone_id, waba_id, at)
                            )
                        else:
                            t_cur.execute("UPDATE whatsapp_config SET active = FALSE")
                            
                        # Push CDN/Logo URL config if available
                        try:
                            b2_bucket = os.getenv("B2_BUCKET_NAME")
                            cdn_domain = os.getenv("CDN_CUSTOM_DOMAIN")
                            if b2_bucket and cdn_domain and subdominio:
                                 logo_path = f"{subdominio}-assets/logo.png"
                                 logo_url = f"https://{cdn_domain}/file/{b2_bucket}/{logo_path}"
                                 _upsert_config("gym_logo_url", logo_url)
                        except Exception:
                            pass
                            
                    t_conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error pushing whatsapp config to tenant DB: {e}")
                return False
        except Exception:
            return False

    # --- Metrics & Audit ---

    def obtener_metricas_agregadas(self) -> Dict[str, Any]:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM gyms")
                total_gyms = int((cur.fetchone() or [0])[0])
                cur.execute("SELECT COUNT(*) FROM gyms WHERE status = 'active'")
                active_gyms = int((cur.fetchone() or [0])[0])
                cur.execute("SELECT COUNT(*) FROM gyms WHERE status = 'suspended'")
                suspended_gyms = int((cur.fetchone() or [0])[0])
                cur.execute("SELECT COUNT(*) FROM gyms WHERE status = 'maintenance'")
                maintenance_gyms = int((cur.fetchone() or [0])[0])
                cur.execute("SELECT COUNT(*) FROM gyms WHERE created_at >= (CURRENT_DATE - INTERVAL '7 days')")
                gyms_last_7 = int((cur.fetchone() or [0])[0])
                cur.execute("SELECT COUNT(*) FROM gyms WHERE created_at >= (CURRENT_DATE - INTERVAL '30 days')")
                gyms_last_30 = int((cur.fetchone() or [0])[0])
                cur.execute("SELECT COUNT(*) FROM gyms WHERE whatsapp_phone_id IS NOT NULL AND whatsapp_access_token IS NOT NULL")
                whatsapp_cfg = int((cur.fetchone() or [0])[0])
                
                storage_cfg = 0 # Simplified
                
                cur.execute("SELECT COUNT(*) FROM gym_subscriptions WHERE status = 'overdue'")
                overdue_subs = int((cur.fetchone() or [0])[0])
                cur.execute("SELECT COUNT(*) FROM gym_subscriptions WHERE status = 'active'")
                active_subs = int((cur.fetchone() or [0])[0])
                cur.execute("SELECT COALESCE(SUM(amount),0) FROM gym_payments WHERE paid_at >= (CURRENT_DATE - INTERVAL '30 days')")
                payments_30_sum = float((cur.fetchone() or [0.0])[0] or 0)
                
                cur.execute("SELECT created_at::date AS d, COUNT(*) AS c FROM gyms WHERE created_at >= (CURRENT_DATE - INTERVAL '30 days') GROUP BY d ORDER BY d ASC")
                series_rows = cur.fetchall()
                series_30 = [{"date": str(r[0]), "count": int(r[1])} for r in series_rows]
            return {
                "gyms": {"total": total_gyms, "active": active_gyms, "suspended": suspended_gyms, "maintenance": maintenance_gyms, "last_7": gyms_last_7, "last_30": gyms_last_30, "series_30": series_30},
                "whatsapp": {"configured": whatsapp_cfg},
                "storage": {"configured": storage_cfg},
                "subscriptions": {"active": active_subs, "overdue": overdue_subs},
                "payments": {"last_30_sum": payments_30_sum},
            }
        except Exception:
            return {"gyms": {"total": 0, "active": 0, "suspended": 0, "maintenance": 0, "last_7": 0, "last_30": 0, "series_30": []}, "whatsapp": {"configured": 0}, "storage": {"configured": 0}, "subscriptions": {"active": 0, "overdue": 0}, "payments": {"last_30_sum": 0.0}}

    def obtener_warnings_admin(self) -> List[str]:
        ws: List[str] = []
        try:
            m = self.obtener_metricas_agregadas()
            if int((m.get("subscriptions") or {}).get("overdue") or 0) > 0:
                ws.append("Hay suscripciones vencidas")
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM gyms WHERE owner_phone IS NULL OR TRIM(owner_phone) = ''")
                no_phone = int((cur.fetchone() or [0])[0])
                if no_phone > 0:
                    ws.append("Gimnasios sin teléfono del dueño")
                cur.execute("SELECT COUNT(*) FROM gyms WHERE whatsapp_phone_id IS NULL OR whatsapp_access_token IS NULL")
                no_wa = int((cur.fetchone() or [0])[0])
                if no_wa > 0:
                    ws.append("Gimnasios sin WhatsApp configurado")
                cur.execute("SELECT COUNT(*) FROM gyms WHERE status = 'suspended'")
                sus = int((cur.fetchone() or [0])[0])
                if sus > 0:
                    ws.append("Gimnasios suspendidos")
        except Exception:
            pass
        return ws

    def resumen_auditoria(self, last_days: int = 7) -> Dict[str, Any]:
        try:
            d = max(int(last_days or 7), 1)
            with self.db.get_connection_context() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(
                    "SELECT action, COUNT(*) AS c FROM admin_audit WHERE created_at >= (CURRENT_DATE - (%s || ' days')::interval) GROUP BY action ORDER BY c DESC",
                    (d,)
                )
                by_action = [dict(r) for r in cur.fetchall()]
                cur.execute(
                    "SELECT COALESCE(actor_username,'') AS actor_username, COUNT(*) AS c FROM admin_audit WHERE created_at >= (CURRENT_DATE - (%s || ' days')::interval) GROUP BY actor_username ORDER BY c DESC",
                    (d,)
                )
                by_actor = [dict(r) for r in cur.fetchall()]
            return {"by_action": by_action, "by_actor": by_actor, "days": d}
        except Exception:
            return {"by_action": [], "by_actor": [], "days": int(last_days or 7)}

    def listar_proximos_vencimientos(self, days: int) -> List[Dict[str, Any]]:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute("SELECT g.id as gym_id, g.nombre, g.subdominio, gs.next_due_date FROM gym_subscriptions gs JOIN gyms g ON g.id = gs.gym_id WHERE gs.status = 'active' AND gs.next_due_date <= (CURRENT_DATE + (%s || ' days')::interval) ORDER BY gs.next_due_date ASC", (int(days),))
                rows = cur.fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return []

    def obtener_auditoria_gym(self, gym_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(
                    "SELECT actor_username, action, details, created_at FROM admin_audit WHERE gym_id = %s ORDER BY created_at DESC LIMIT %s",
                    (int(gym_id), int(limit))
                )
                rows = cur.fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return []

    def listar_planes(self) -> List[Dict[str, Any]]:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute("SELECT id, name, amount, currency, period_days, active, created_at FROM plans ORDER BY amount ASC")
                rows = cur.fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return []

    def crear_plan(self, name: str, amount: float, currency: str, period_days: int) -> Dict[str, Any]:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO plans (name, amount, currency, period_days, active) VALUES (%s, %s, %s, %s, true) RETURNING id",
                    (name.strip(), float(amount), currency.upper(), int(period_days))
                )
                row = cur.fetchone()
                conn.commit()
                return {"ok": True, "id": row[0] if row else None}
        except Exception as e:
            logger.error(f"Error creating plan: {e}")
            return {"ok": False, "error": str(e)}

    def actualizar_plan(self, plan_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not updates:
                return {"ok": False, "error": "no_updates"}
            
            sets: List[str] = []
            params: List[Any] = []
            
            if "name" in updates:
                sets.append("name = %s")
                params.append(str(updates["name"]).strip())
            if "amount" in updates:
                sets.append("amount = %s")
                params.append(float(updates["amount"]))
            if "currency" in updates:
                sets.append("currency = %s")
                params.append(str(updates["currency"]).upper())
            if "period_days" in updates:
                sets.append("period_days = %s")
                params.append(int(updates["period_days"]))
            
            if not sets:
                return {"ok": False, "error": "no_valid_updates"}
            
            params.append(int(plan_id))
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute(f"UPDATE plans SET {', '.join(sets)} WHERE id = %s", params)
                conn.commit()
            return {"ok": True}
        except Exception as e:
            logger.error(f"Error updating plan {plan_id}: {e}")
            return {"ok": False, "error": str(e)}

    def toggle_plan(self, plan_id: int, active: bool) -> Dict[str, Any]:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute("UPDATE plans SET active = %s WHERE id = %s", (bool(active), int(plan_id)))
                conn.commit()
            return {"ok": True}
        except Exception as e:
            logger.error(f"Error toggling plan {plan_id}: {e}")
            return {"ok": False, "error": str(e)}

    def eliminar_plan(self, plan_id: int) -> Dict[str, Any]:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                # Check if plan is in use
                cur.execute("SELECT COUNT(*) FROM gym_subscriptions WHERE plan_id = %s", (int(plan_id),))
                count = cur.fetchone()[0]
                if count > 0:
                    return {"ok": False, "error": "plan_in_use", "count": count}
                
                cur.execute("DELETE FROM plans WHERE id = %s", (int(plan_id),))
                conn.commit()
            return {"ok": True}
        except Exception as e:
            logger.error(f"Error deleting plan {plan_id}: {e}")
            return {"ok": False, "error": str(e)}

    def enviar_recordatorios_vencimiento(self, days: int = 7) -> Dict[str, Any]:
        """Send reminder to gyms expiring in the next N days."""
        try:
            sent = 0
            upcoming = self.listar_proximos_vencimientos(days)
            
            for gym in upcoming:
                gym_id = gym.get("gym_id") or gym.get("id")
                if gym_id:
                    # Try to send WhatsApp reminder
                    try:
                        msg = f"Recordatorio: Su suscripción a IronHub vence el {gym.get('valid_until', 'pronto')}. Por favor renueve para evitar interrupciones."
                        self._enviar_whatsapp_a_owner(gym_id, msg)
                        sent += 1
                    except Exception:
                        pass
            
            return {"ok": True, "sent": sent, "total": len(upcoming)}
        except Exception as e:
            logger.error(f"Error sending reminders: {e}")
            return {"ok": False, "error": str(e), "sent": 0}

    def auto_suspender_vencidos(self, grace_days: int = 0) -> Dict[str, Any]:
        """Automatically suspend gyms that are past their due date by grace_days."""
        try:
            suspended = 0
            with self.db.get_connection_context() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                # Find gyms with expired subscriptions
                cur.execute("""
                    SELECT g.id, g.nombre, gs.next_due_date
                    FROM gyms g
                    JOIN gym_subscriptions gs ON gs.gym_id = g.id
                    WHERE g.status = 'active' 
                    AND gs.next_due_date < CURRENT_DATE - INTERVAL '%s days'
                """, (grace_days,))
                rows = cur.fetchall()
                
                for row in rows:
                    gym_id = row["id"]
                    try:
                        self.set_estado_gimnasio(
                            gym_id, 
                            "suspended", 
                            hard_suspend=False, 
                            reason=f"Subscription expired (auto-suspended after {grace_days} grace days)"
                        )
                        suspended += 1
                    except Exception:
                        pass
                
            return {"ok": True, "suspended": suspended}
        except Exception as e:
            logger.error(f"Error auto-suspending: {e}")
            return {"ok": False, "error": str(e), "suspended": 0}

    def _enviar_whatsapp_a_owner(self, gym_id: int, message: str) -> bool:
        """Send WhatsApp message to gym owner phone."""
        try:
            gym = self.obtener_gimnasio(gym_id)
            if not gym:
                return False
            
            owner_phone = gym.get("owner_phone", "").strip()
            if not owner_phone:
                return False
            
            # Get WhatsApp config
            phone_id = gym.get("whatsapp_phone_id", "").strip()
            access_token = gym.get("whatsapp_access_token", "").strip()
            
            if not phone_id or not access_token:
                return False
            
            if requests is None:
                return False
            
            url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
            payload = {
                "messaging_product": "whatsapp",
                "to": owner_phone.lstrip("+"),
                "type": "text",
                "text": {"body": message}
            }
            
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Error sending WhatsApp to owner of gym {gym_id}: {e}")
            return False

    def listar_templates(self) -> List[Dict[str, Any]]:
        return self.listar_whatsapp_template_catalog()

    def _default_whatsapp_template_catalog(self) -> List[Dict[str, Any]]:
        lang = (os.getenv("WHATSAPP_TEMPLATE_LANGUAGE") or "es_AR").strip()
        templates = [
            ("ih_welcome_v1", "UTILITY", f"Hola {{{{1}}}}. ¡Bienvenido/a! Si necesitás ayuda, respondé a este mensaje.", ["Mateo"]),
            ("ih_payment_confirmed_v1", "UTILITY", "Hola {{1}}. Confirmamos tu pago de ${{2}} correspondiente a {{3}}. ¡Gracias!", ["Mateo", "25000", "enero 2026"]),
            ("ih_membership_due_today_v1", "UTILITY", "Hola {{1}}. Recordatorio: tu cuota vence hoy ({{2}}). Si ya abonaste, ignorá este mensaje.", ["Mateo", "16 de enero"]),
            ("ih_membership_due_soon_v1", "UTILITY", "Hola {{1}}. Tu cuota vence el {{2}}. Si querés, respondé a este mensaje y te ayudamos a regularizar.", ["Mateo", "20 de enero"]),
            ("ih_membership_overdue_v1", "UTILITY", "Hola {{1}}. Tu cuota está vencida. Si ya abonaste, ignorá este mensaje. Si necesitás ayuda, respondé “AYUDA”.", ["Mateo"]),
            ("ih_membership_deactivated_v1", "UTILITY", "Hola {{1}}. Tu acceso está temporalmente suspendido. Motivo: {{2}}. Respondé a este mensaje si necesitás asistencia.", ["Mateo", "cuotas vencidas"]),
            ("ih_membership_reactivated_v1", "UTILITY", "Hola {{1}}. Tu acceso fue reactivado. ¡Gracias!", ["Mateo"]),
            ("ih_class_booking_confirmed_v1", "UTILITY", "Confirmación de reserva: clase {{1}} el {{2}} a las {{3}} hs.", ["Funcional", "16 de enero", "19:00"]),
            ("ih_class_booking_cancelled_v1", "UTILITY", "Tu reserva fue cancelada para la clase {{1}}. Si necesitás ayuda, respondé a este mensaje.", ["Funcional"]),
            ("ih_class_reminder_v1", "UTILITY", "Hola {{1}}. Te recordamos que tenés la clase de {{2}} programada para el día {{3}} a las {{4}} hs. Si no podés asistir, respondé a este mensaje para ayudarte.", ["Mateo", "Funcional", "viernes", "19:00"]),
            ("ih_waitlist_spot_available_v1", "UTILITY", "Hola {{1}}. Se liberó un cupo para {{2}} el {{3}} a las {{4}} hs. Respondé “SI” para tomarlo.", ["Mateo", "Funcional", "viernes", "19:00"]),
            ("ih_waitlist_confirmed_v1", "UTILITY", "Listo {{1}}. Te confirmamos tu lugar en la clase de {{2}} para el día {{3}} a las {{4}} hs. Si necesitás cambiarlo, respondé a este mensaje.", ["Mateo", "Funcional", "viernes", "19:00"]),
            ("ih_schedule_change_v1", "UTILITY", "Aviso: hubo un cambio en {{1}}. Nuevo horario: {{2}} a las {{3}} hs. Gracias.", ["Funcional", "viernes", "20:00"]),
            ("ih_auth_code_v1", "AUTHENTICATION", "Tu código de verificación es {{1}}. Vence en {{2}} minutos. No lo compartas con nadie.", ["928314", "10"]),
            ("ih_marketing_promo_v1", "MARKETING", "Hola {{1}}. Esta semana tenemos {{2}}. Si querés más info, respondé a este mensaje.", ["Mateo", "descuento del 10% en el plan trimestral"]),
            ("ih_marketing_new_class_v1", "MARKETING", "Nueva clase disponible: {{1}}. Primer horario: {{2}} {{3}}. ¿Querés que te reservemos un lugar?", ["Movilidad", "miércoles", "18:00"]),
        ]
        return [
            {
                "template_name": name,
                "category": category,
                "language": lang,
                "body_text": body,
                "example_params": examples,
                "active": False if name == "ih_auth_code_v1" else True,
                "version": 1,
            }
            for name, category, body, examples in templates
        ]

    def listar_whatsapp_template_catalog(self, active_only: bool = False) -> List[Dict[str, Any]]:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                if active_only:
                    cur.execute(
                        "SELECT template_name, category, language, body_text, example_params, active, version, created_at, updated_at FROM whatsapp_template_catalog WHERE active = TRUE ORDER BY template_name ASC"
                    )
                else:
                    cur.execute(
                        "SELECT template_name, category, language, body_text, example_params, active, version, created_at, updated_at FROM whatsapp_template_catalog ORDER BY template_name ASC"
                    )
                rows = cur.fetchall() or []
            out = []
            for r in rows:
                out.append(
                    {
                        "template_name": str(r.get("template_name") or ""),
                        "category": str(r.get("category") or "UTILITY"),
                        "language": str(r.get("language") or "es_AR"),
                        "body_text": str(r.get("body_text") or ""),
                        "example_params": r.get("example_params"),
                        "active": bool(r.get("active") is True),
                        "version": int(r.get("version") or 1),
                        "created_at": str(r.get("created_at") or ""),
                        "updated_at": str(r.get("updated_at") or ""),
                    }
                )
            return out
        except Exception:
            return []

    def _ensure_whatsapp_template_bindings_table(self, conn) -> None:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS whatsapp_template_bindings (
                binding_key VARCHAR(120) PRIMARY KEY,
                template_name VARCHAR(255) NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def _default_whatsapp_bindings(self) -> Dict[str, str]:
        return {
            "welcome": "ih_welcome_v1",
            "payment": "ih_payment_confirmed_v1",
            "membership_due_today": "ih_membership_due_today_v1",
            "membership_due_soon": "ih_membership_due_soon_v1",
            "overdue": "ih_membership_overdue_v1",
            "deactivation": "ih_membership_deactivated_v1",
            "membership_reactivated": "ih_membership_reactivated_v1",
            "class_booking_confirmed": "ih_class_booking_confirmed_v1",
            "class_booking_cancelled": "ih_class_booking_cancelled_v1",
            "class_reminder": "ih_class_reminder_v1",
            "waitlist": "ih_waitlist_spot_available_v1",
            "waitlist_confirmed": "ih_waitlist_confirmed_v1",
            "schedule_change": "ih_schedule_change_v1",
            "marketing_promo": "ih_marketing_promo_v1",
            "marketing_new_class": "ih_marketing_new_class_v1",
        }

    def list_whatsapp_template_bindings(self) -> Dict[str, str]:
        try:
            with self.db.get_connection_context() as conn:
                self._ensure_whatsapp_template_bindings_table(conn)
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute("SELECT binding_key, template_name FROM whatsapp_template_bindings ORDER BY binding_key ASC")
                rows = cur.fetchall() or []
                conn.commit()
            out: Dict[str, str] = {}
            for r in rows:
                out[str(r.get("binding_key") or "")] = str(r.get("template_name") or "")
            defaults = self._default_whatsapp_bindings()
            merged = {**defaults, **{k: v for k, v in out.items() if k}}
            missing = [k for k in defaults.keys() if k not in out]
            if missing:
                try:
                    self.sync_whatsapp_template_bindings_defaults(overwrite=False)
                except Exception:
                    pass
            return merged
        except Exception:
            return self._default_whatsapp_bindings()

    def upsert_whatsapp_template_binding(self, binding_key: str, template_name: str) -> Dict[str, Any]:
        k = str(binding_key or "").strip()
        t = str(template_name or "").strip()
        if not k or not t:
            return {"ok": False, "error": "binding_key_and_template_required"}
        try:
            with self.db.get_connection_context() as conn:
                self._ensure_whatsapp_template_bindings_table(conn)
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO whatsapp_template_bindings (binding_key, template_name, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (binding_key) DO UPDATE SET
                        template_name = EXCLUDED.template_name,
                        updated_at = NOW()
                    """,
                    (k, t),
                )
                conn.commit()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def sync_whatsapp_template_bindings_defaults(self, overwrite: bool = True) -> Dict[str, Any]:
        defaults = self._default_whatsapp_bindings()
        updated = 0
        created = 0
        failed: List[Dict[str, Any]] = []
        try:
            with self.db.get_connection_context() as conn:
                self._ensure_whatsapp_template_bindings_table(conn)
                cur = conn.cursor()
                for k, v in defaults.items():
                    if not overwrite:
                        cur.execute("SELECT 1 FROM whatsapp_template_bindings WHERE binding_key = %s LIMIT 1", (k,))
                        if cur.fetchone():
                            continue
                    cur.execute(
                        """
                        INSERT INTO whatsapp_template_bindings (binding_key, template_name, updated_at)
                        VALUES (%s, %s, NOW())
                        ON CONFLICT (binding_key) DO UPDATE SET
                            template_name = EXCLUDED.template_name,
                            updated_at = NOW()
                        """,
                        (k, v),
                    )
                    if cur.rowcount == 1:
                        created += 1
                    else:
                        updated += 1
                conn.commit()
            return {"ok": True, "overwrite": overwrite, "created": created, "updated": updated, "failed": failed}
        except Exception as e:
            return {"ok": False, "error": str(e), "created": created, "updated": updated, "failed": failed}

    def bump_whatsapp_template_version(self, template_name: str) -> Dict[str, Any]:
        name = str(template_name or "").strip()
        if not name:
            return {"ok": False, "error": "template_name_required"}
        try:
            m = re.match(r"^(?P<base>.+)_v(?P<v>\d+)$", name)
            if not m:
                return {"ok": False, "error": "template_name_must_end_with__vN"}
            base = m.group("base")
            v = int(m.group("v"))
            new_v = v + 1
            new_name = f"{base}_v{new_v}"

            with self.db.get_connection_context() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(
                    "SELECT template_name, category, language, body_text, example_params, active, version FROM whatsapp_template_catalog WHERE template_name = %s LIMIT 1",
                    (name,),
                )
                row = cur.fetchone()
                if not row:
                    return {"ok": False, "error": "template_not_found_in_catalog"}
                cur.execute("SELECT 1 FROM whatsapp_template_catalog WHERE template_name = %s LIMIT 1", (new_name,))
                if cur.fetchone():
                    return {"ok": False, "error": "target_version_already_exists", "new_template_name": new_name}

                cur.execute(
                    """
                    INSERT INTO whatsapp_template_catalog (template_name, category, language, body_text, example_params, active, version, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,NOW())
                    """,
                    (
                        new_name,
                        str(row.get("category") or "UTILITY"),
                        str(row.get("language") or "es_AR"),
                        str(row.get("body_text") or ""),
                        row.get("example_params"),
                        bool(row.get("active") is True),
                        int(row.get("version") or new_v),
                    ),
                )

                conn.commit()

            return {"ok": True, "new_template_name": new_name}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def upsert_whatsapp_template_catalog(self, template_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        name = str(template_name or "").strip()
        if not name:
            return {"ok": False, "error": "template_name_required"}
        try:
            category = str((data or {}).get("category") or "UTILITY").strip().upper()
            if category not in ("UTILITY", "AUTHENTICATION", "MARKETING"):
                category = "UTILITY"
            language = str((data or {}).get("language") or "es_AR").strip()
            body_text = str((data or {}).get("body_text") or "").strip()
            if not body_text:
                return {"ok": False, "error": "body_text_required"}
            active = bool((data or {}).get("active", True))
            version = int((data or {}).get("version") or 1)
            examples = (data or {}).get("example_params")
            examples_json = psycopg2.extras.Json(examples) if examples is not None else None

            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO whatsapp_template_catalog (template_name, category, language, body_text, example_params, active, version, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,NOW())
                    ON CONFLICT (template_name) DO UPDATE SET
                        category = EXCLUDED.category,
                        language = EXCLUDED.language,
                        body_text = EXCLUDED.body_text,
                        example_params = EXCLUDED.example_params,
                        active = EXCLUDED.active,
                        version = EXCLUDED.version,
                        updated_at = NOW()
                    """,
                    (name, category, language, body_text, examples_json, active, version),
                )
                conn.commit()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def delete_whatsapp_template_catalog(self, template_name: str) -> Dict[str, Any]:
        name = str(template_name or "").strip()
        if not name:
            return {"ok": False, "error": "template_name_required"}
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM whatsapp_template_catalog WHERE template_name = %s", (name,))
                conn.commit()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def sync_whatsapp_template_defaults(self, overwrite: bool = True) -> Dict[str, Any]:
        defaults = self._default_whatsapp_template_catalog()
        if not defaults:
            return {"ok": False, "error": "no_defaults"}
        updated = 0
        created = 0
        failed: List[Dict[str, Any]] = []
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                for t in defaults:
                    name = str(t.get("template_name") or "").strip()
                    if not name:
                        continue
                    if not overwrite:
                        try:
                            cur.execute("SELECT 1 FROM whatsapp_template_catalog WHERE template_name = %s LIMIT 1", (name,))
                            if cur.fetchone():
                                continue
                        except Exception:
                            pass
                    try:
                        cur.execute(
                            """
                            INSERT INTO whatsapp_template_catalog (template_name, category, language, body_text, example_params, active, version, updated_at)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,NOW())
                            ON CONFLICT (template_name) DO UPDATE SET
                                category = EXCLUDED.category,
                                language = EXCLUDED.language,
                                body_text = EXCLUDED.body_text,
                                example_params = EXCLUDED.example_params,
                                active = EXCLUDED.active,
                                version = EXCLUDED.version,
                                updated_at = NOW()
                            """,
                            (
                                name,
                                str(t.get("category") or "UTILITY"),
                                str(t.get("language") or "es_AR"),
                                str(t.get("body_text") or ""),
                                psycopg2.extras.Json(t.get("example_params")) if t.get("example_params") is not None else None,
                                bool(t.get("active", True)),
                                int(t.get("version", 1)),
                            ),
                        )
                        if cur.rowcount == 1:
                            created += 1
                        else:
                            updated += 1
                    except Exception as e:
                        failed.append({"name": name, "error": str(e)})
                conn.commit()
            self.log_action("owner", "whatsapp_templates_catalog_sync", None, f"overwrite={overwrite} created={created} updated={updated} failed={len(failed)}")
            return {"ok": True, "overwrite": overwrite, "created": created, "updated": updated, "failed": failed}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def provision_whatsapp_templates_to_gym(self, gym_id: int) -> Dict[str, Any]:
        try:
            gid = int(gym_id)
        except Exception:
            return {"ok": False, "error": "invalid_gym_id"}

        if requests is None:
            return {"ok": False, "error": "requests_not_available"}

        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute("SELECT db_name FROM gyms WHERE id = %s", (gid,))
                row = cur.fetchone()
            if not row:
                return {"ok": False, "error": "gym_not_found"}
            db_name = str(row.get("db_name") or "").strip()
            if not db_name:
                return {"ok": False, "error": "gym_db_missing"}

            params = self.resolve_admin_db_params()
            pg_params = {
                "host": params.get("host"),
                "port": params.get("port"),
                "dbname": db_name,
                "user": params.get("user"),
                "password": params.get("password"),
                "sslmode": params.get("sslmode"),
                "connect_timeout": params.get("connect_timeout"),
                "application_name": "admin_provision_whatsapp_templates",
            }

            with psycopg2.connect(**pg_params) as t_conn:
                with t_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as t_cur:
                    t_cur.execute(
                        "SELECT phone_id, waba_id, access_token FROM whatsapp_config WHERE active = TRUE ORDER BY created_at DESC LIMIT 1"
                    )
                    cfg = t_cur.fetchone()
            if not cfg:
                return {"ok": False, "error": "tenant_whatsapp_not_configured"}

            waba_id = str(cfg.get("waba_id") or "").strip()
            token_raw = str(cfg.get("access_token") or "").strip()
            if token_raw:
                try:
                    SecureConfig.require_waba_encryption()
                except Exception:
                    pass
            token = SecureConfig.decrypt_waba_secret(token_raw) if token_raw else ""
            if token_raw.startswith("gAAAA") and not token:
                return {"ok": False, "error": "token_decrypt_failed: revisar WABA_ENCRYPTION_KEY y cryptography en admin-api"}
            if not token and (token_raw.startswith("EAA") or token_raw.startswith("EAAB") or token_raw.startswith("EAAJ")):
                token = token_raw
            if token and token.startswith("gAAAA"):
                return {"ok": False, "error": "token_encrypted_or_unreadable: revisar WABA_ENCRYPTION_KEY (admin-api debe poder desencriptar)"}

            if not waba_id or not token:
                return {"ok": False, "error": "tenant_whatsapp_missing_waba_or_token"}

            templates = self.listar_whatsapp_template_catalog(active_only=True)
            if not templates:
                templates = self._default_whatsapp_template_catalog()

            api_version = (os.getenv("META_GRAPH_API_VERSION") or os.getenv("WHATSAPP_API_VERSION") or "v19.0").strip()
            list_url = f"https://graph.facebook.com/{api_version}/{waba_id}/message_templates"
            headers = {"Authorization": f"Bearer {token}"}

            existing = set()
            after = None
            for _ in range(10):
                params_q = {"fields": "name,status", "limit": "200"}
                if after:
                    params_q["after"] = after
                resp = requests.get(list_url, headers=headers, params=params_q, timeout=20)
                data = resp.json() if resp.content else {}
                if resp.status_code >= 400:
                    return {"ok": False, "error": str((data or {}).get("error") or data or resp.text)}
                for item in (data.get("data") or []):
                    n = (item or {}).get("name")
                    if n:
                        existing.add(str(n))
                cursors = ((data.get("paging") or {}).get("cursors") or {})
                after = cursors.get("after")
                if not after:
                    break

            created = []
            failed = []
            create_url = list_url
            template_status_by_name: Dict[str, str] = {}
            after = None
            for _ in range(10):
                params_q = {"fields": "name,status", "limit": "200"}
                if after:
                    params_q["after"] = after
                resp = requests.get(list_url, headers=headers, params=params_q, timeout=20)
                data = resp.json() if resp.content else {}
                if resp.status_code >= 400:
                    break
                for item in (data.get("data") or []):
                    n = (item or {}).get("name")
                    st = (item or {}).get("status")
                    if n:
                        template_status_by_name[str(n)] = str(st or "")
                cursors = ((data.get("paging") or {}).get("cursors") or {})
                after = cursors.get("after")
                if not after:
                    break

            def _try_parse_meta_error(raw: Any) -> str:
                try:
                    if isinstance(raw, dict):
                        u = raw.get("error_user_title") or ""
                        m = raw.get("error_user_msg") or raw.get("message") or ""
                        if u or m:
                            return f"{u}: {m}".strip(": ").strip()
                        return str(raw)
                    if isinstance(raw, str):
                        try:
                            obj = json.loads(raw)
                            if isinstance(obj, dict):
                                return _try_parse_meta_error(obj)
                        except Exception:
                            return raw
                    return str(raw)
                except Exception:
                    return "Error"

            def _bump_template_name(n: str) -> str:
                s = str(n or "").strip()
                m = re.match(r"^(?P<base>.+)_v(?P<v>\d+)$", s)
                if m:
                    base = m.group("base")
                    v = int(m.group("v"))
                    return f"{base}_v{v + 1}"
                return f"{s}_v2"

            def _is_meta_name_locked(err: str) -> bool:
                e = str(err or "").lower()
                return (
                    "se está eliminando el idioma" in e
                    or "mientras se está eliminando el contenido" in e
                    or "vuelve a intentarlo dentro de 4 weeks" in e
                    or "no es posible añadir contenido nuevo" in e
                    or "no puedes cambiar la categoría" in e
                )

            created_bumped: List[Dict[str, Any]] = []
            for t in templates:
                name = str(t.get("template_name") or "").strip()
                if not name or name in existing:
                    continue
                body_text = str(t.get("body_text") or "").strip()
                lang = str(t.get("language") or "es_AR").strip()
                cat = str(t.get("category") or "UTILITY").strip().upper()
                if cat == "AUTHENTICATION" or name == "ih_auth_code_v1":
                    continue
                examples = t.get("example_params") or []
                payload = {
                    "name": name,
                    "language": lang,
                    "category": cat,
                    "components": [
                        {
                            "type": "BODY",
                            "text": body_text,
                            "example": {"body_text": [examples]} if isinstance(examples, list) and examples else None,
                        }
                    ],
                }
                if payload["components"][0]["example"] is None:
                    payload["components"][0].pop("example", None)
                try:
                    r2 = requests.post(create_url, headers={**headers, "Content-Type": "application/json"}, json=payload, timeout=30)
                    d2 = r2.json() if r2.content else {}
                    if r2.status_code >= 400:
                        err_obj = (d2 or {}).get("error") or d2 or r2.text
                        err_str = _try_parse_meta_error(err_obj)
                        if _is_meta_name_locked(err_str):
                            new_name = name
                            for _ in range(10):
                                new_name = _bump_template_name(new_name)
                                if new_name not in existing:
                                    break
                            bumped_payload = {**payload, "name": new_name}
                            r3 = requests.post(create_url, headers={**headers, "Content-Type": "application/json"}, json=bumped_payload, timeout=30)
                            d3 = r3.json() if r3.content else {}
                            if r3.status_code >= 400:
                                err_obj2 = (d3 or {}).get("error") or d3 or r3.text
                                failed.append({"name": name, "error": err_str, "raw": err_obj, "bumped_to": new_name, "bumped_error": _try_parse_meta_error(err_obj2)})
                            else:
                                created.append(new_name)
                                existing.add(new_name)
                                created_bumped.append({"from": name, "to": new_name, "reason": "meta_name_locked"})
                                try:
                                    with self.db.get_connection_context() as aconn:
                                        acur = aconn.cursor()
                                        acur.execute(
                                            """
                                            INSERT INTO whatsapp_template_catalog (template_name, category, language, body_text, example_params, active, version, updated_at)
                                            VALUES (%s,%s,%s,%s,%s,%s,%s,NOW())
                                            ON CONFLICT (template_name) DO NOTHING
                                            """,
                                            (
                                                new_name,
                                                cat,
                                                lang,
                                                body_text,
                                                psycopg2.extras.Json(examples) if examples is not None else None,
                                                True,
                                                int(t.get("version") or 1),
                                            ),
                                        )
                                        aconn.commit()
                                except Exception:
                                    pass
                        else:
                            failed.append({"name": name, "error": err_str, "raw": err_obj})
                    else:
                        created.append(name)
                        existing.add(name)
                except Exception as e:
                    failed.append({"name": name, "error": str(e)})

            skipped = []
            for t in templates:
                name = str(t.get("template_name") or "").strip()
                if not name:
                    continue
                st = template_status_by_name.get(name)
                if st:
                    skipped.append({"name": name, "status": st})

            try:
                bindings = self.list_whatsapp_template_bindings()
            except Exception:
                bindings = self._default_whatsapp_bindings()

            try:
                with psycopg2.connect(**pg_params) as t_conn2:
                    with t_conn2.cursor() as t_cur2:
                        alias_map: Dict[str, str] = {}
                        try:
                            t_cur2.execute("SELECT clave, valor FROM configuracion WHERE clave LIKE %s", ("wa_template_alias_%",))
                            for r in (t_cur2.fetchall() or []):
                                try:
                                    k0 = str((r or [None, None])[0] or "")
                                    v0 = str((r or [None, None])[1] or "")
                                except Exception:
                                    k0, v0 = "", ""
                                if k0.startswith("wa_template_alias_") and v0:
                                    alias_map[k0.replace("wa_template_alias_", "")] = v0
                        except Exception:
                            alias_map = {}

                        alias_written = 0
                        for m in created_bumped:
                            old_n = str(m.get("from") or "").strip()
                            new_n = str(m.get("to") or "").strip()
                            if not old_n or not new_n:
                                continue
                            alias_map[old_n] = new_n
                            try:
                                t_cur2.execute(
                                    """
                                    INSERT INTO configuracion (clave, valor, tipo, descripcion)
                                    VALUES (%s,%s,%s,%s)
                                    ON CONFLICT (clave) DO UPDATE SET
                                        valor = EXCLUDED.valor,
                                        tipo = EXCLUDED.tipo,
                                        descripcion = EXCLUDED.descripcion
                                    """,
                                    (f"wa_template_alias_{old_n}", new_n, "string", "Alias auto-generado por Meta (bump por bloqueo de nombre/idioma)"),
                                )
                                alias_written += 1
                            except Exception:
                                pass

                        def _resolve_alias(n: str) -> str:
                            cur = str(n or "").strip()
                            for _ in range(10):
                                nxt = str(alias_map.get(cur) or "").strip()
                                if not nxt or nxt == cur:
                                    break
                                cur = nxt
                            return cur

                        for k, tname in (bindings or {}).items():
                            key = f"wa_meta_template_{str(k).strip()}"
                            chosen = str(tname or "").strip()
                            if not chosen:
                                continue
                            st = str(template_status_by_name.get(chosen) or "")
                            if not st or st.upper() != "APPROVED":
                                alt = _resolve_alias(chosen)
                                if alt and alt != chosen:
                                    chosen = alt
                                    st = str(template_status_by_name.get(chosen) or "")
                            if not st or st.upper() != "APPROVED":
                                continue
                            t_cur2.execute(
                                """
                                INSERT INTO configuracion (clave, valor, tipo, descripcion)
                                VALUES (%s,%s,%s,%s)
                                ON CONFLICT (clave) DO UPDATE SET
                                    valor = EXCLUDED.valor,
                                    tipo = EXCLUDED.tipo,
                                    descripcion = EXCLUDED.descripcion
                                """,
                                (key, chosen, "string", "Nombre de template Meta activo para este evento"),
                            )
                        t_conn2.commit()
            except Exception:
                pass

            self.log_action("owner", "whatsapp_templates_provisioned", gid, f"created={len(created)} failed={len(failed)}")
            return {"ok": True, "existing_count": len(existing), "created": created, "created_bumped": created_bumped, "skipped": skipped, "failed": failed}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def whatsapp_health_check_for_gym(self, gym_id: int) -> Dict[str, Any]:
        try:
            gid = int(gym_id)
        except Exception:
            return {"ok": False, "error": "invalid_gym_id"}

        if requests is None:
            return {"ok": False, "error": "requests_not_available"}

        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute("SELECT db_name FROM gyms WHERE id = %s", (gid,))
                row = cur.fetchone()
            if not row:
                return {"ok": False, "error": "gym_not_found"}
            db_name = str(row.get("db_name") or "").strip()
            if not db_name:
                return {"ok": False, "error": "gym_db_missing"}

            params = self.resolve_admin_db_params()
            pg_params = {
                "host": params.get("host"),
                "port": params.get("port"),
                "dbname": db_name,
                "user": params.get("user"),
                "password": params.get("password"),
                "sslmode": params.get("sslmode"),
                "connect_timeout": params.get("connect_timeout"),
                "application_name": "admin_whatsapp_health_check",
            }

            with psycopg2.connect(**pg_params) as t_conn:
                with t_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as t_cur:
                    t_cur.execute(
                        "SELECT phone_id, waba_id, access_token FROM whatsapp_config WHERE active = TRUE ORDER BY created_at DESC LIMIT 1"
                    )
                    cfg = t_cur.fetchone()
                    t_cur.execute("SELECT valor FROM configuracion WHERE clave = %s LIMIT 1", ("WHATSAPP_SEND_TIMEOUT_SECONDS",))
                    r_to = t_cur.fetchone()
            if not cfg:
                return {"ok": False, "error": "tenant_whatsapp_not_configured"}

            phone_id = str(cfg.get("phone_id") or "").strip()
            waba_id = str(cfg.get("waba_id") or "").strip()
            token_raw = str(cfg.get("access_token") or "").strip()
            if token_raw:
                try:
                    SecureConfig.require_waba_encryption()
                except Exception:
                    pass
            token = SecureConfig.decrypt_waba_secret(token_raw) if token_raw else ""
            if token_raw.startswith("gAAAA") and not token:
                return {"ok": False, "error": "token_decrypt_failed: revisar WABA_ENCRYPTION_KEY y cryptography en admin-api"}
            if not token and (token_raw.startswith("EAA") or token_raw.startswith("EAAB") or token_raw.startswith("EAAJ")):
                token = token_raw
            if token and token.startswith("gAAAA"):
                return {"ok": False, "error": "token_encrypted_or_unreadable: revisar WABA_ENCRYPTION_KEY (admin-api debe poder desencriptar)"}

            if not phone_id or not waba_id:
                return {"ok": False, "error": "missing_phone_or_waba", "phone_id": phone_id, "waba_id": waba_id}
            if not token:
                return {"ok": False, "error": "missing_token", "phone_id": phone_id, "waba_id": waba_id}

            api_version = (os.getenv("META_GRAPH_API_VERSION") or os.getenv("WHATSAPP_API_VERSION") or "v19.0").strip()
            try:
                timeout = float((r_to or {}).get("valor") or 25.0) if r_to else 25.0
            except Exception:
                timeout = 25.0
            if timeout < 5:
                timeout = 5.0
            if timeout > 120:
                timeout = 120.0

            headers = {"Authorization": f"Bearer {token}"}
            errors: list[str] = []
            phone_info: Dict[str, Any] = {}
            templates = {"count": 0, "approved": 0, "pending": 0, "rejected": 0}

            try:
                r = requests.get(
                    f"https://graph.facebook.com/{api_version}/{phone_id}",
                    headers=headers,
                    params={"fields": "id,display_phone_number,verified_name,quality_rating,platform_type,code_verification_status"},
                    timeout=timeout,
                )
                data = r.json() if r.content else {}
                if r.status_code >= 400:
                    errors.append(str((data or {}).get("error") or data or f"HTTP {r.status_code}"))
                else:
                    phone_info = data if isinstance(data, dict) else {}
            except Exception as e:
                errors.append(str(e))

            try:
                r = requests.get(
                    f"https://graph.facebook.com/{api_version}/{waba_id}/message_templates",
                    headers=headers,
                    params={"fields": "name,status", "limit": "200"},
                    timeout=timeout,
                )
                data = r.json() if r.content else {}
                if r.status_code >= 400:
                    errors.append(str((data or {}).get("error") or data or f"HTTP {r.status_code}"))
                else:
                    items = data.get("data") or []
                    templates["count"] = int(len(items))
                    for it in items:
                        st = str((it or {}).get("status") or "").upper()
                        if st == "APPROVED":
                            templates["approved"] += 1
                        elif st in ("PENDING", "IN_APPEAL"):
                            templates["pending"] += 1
                        elif st == "REJECTED":
                            templates["rejected"] += 1
            except Exception as e:
                errors.append(str(e))

            app_id = (os.getenv("META_APP_ID") or os.getenv("FACEBOOK_APP_ID") or "").strip()
            subscribed = None
            if app_id:
                try:
                    r = requests.get(
                        f"https://graph.facebook.com/{api_version}/{waba_id}/subscribed_apps",
                        headers=headers,
                        timeout=timeout,
                    )
                    data = r.json() if r.content else {}
                    if r.status_code >= 400:
                        errors.append(str((data or {}).get("error") or data or f"HTTP {r.status_code}"))
                    else:
                        subscribed = any(str((x or {}).get("id") or "") == str(app_id) for x in (data.get("data") or []))
                except Exception as e:
                    errors.append(str(e))

            return {
                "ok": len(errors) == 0,
                "phone_id": phone_id,
                "waba_id": waba_id,
                "phone": phone_info,
                "templates": templates,
                "subscribed_apps": {"app_id": app_id or None, "subscribed": subscribed},
                "errors": errors,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_tenant_whatsapp_active_config_for_gym(self, gym_id: int) -> Dict[str, Any]:
        try:
            gid = int(gym_id)
        except Exception:
            return {"ok": False, "error": "invalid_gym_id"}

        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute("SELECT db_name FROM gyms WHERE id = %s", (gid,))
                row = cur.fetchone()
            if not row:
                return {"ok": False, "error": "gym_not_found"}
            db_name = str(row.get("db_name") or "").strip()
            if not db_name:
                return {"ok": False, "error": "gym_db_missing"}

            params = self.resolve_admin_db_params()
            pg_params = {
                "host": params.get("host"),
                "port": params.get("port"),
                "dbname": db_name,
                "user": params.get("user"),
                "password": params.get("password"),
                "sslmode": params.get("sslmode"),
                "connect_timeout": params.get("connect_timeout"),
                "application_name": "admin_get_tenant_whatsapp_config",
            }

            with psycopg2.connect(**pg_params) as t_conn:
                with t_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as t_cur:
                    t_cur.execute(
                        """
                        SELECT phone_id, waba_id, access_token, active, created_at
                        FROM whatsapp_config
                        WHERE active = TRUE
                        ORDER BY created_at DESC
                        LIMIT 1
                        """
                    )
                    cfg = t_cur.fetchone()
            if not cfg:
                return {"ok": True, "configured": False, "phone_id": "", "waba_id": "", "access_token_present": False}

            phone_id = str(cfg.get("phone_id") or "").strip()
            waba_id = str(cfg.get("waba_id") or "").strip()
            token_raw = str(cfg.get("access_token") or "").strip()
            access_token_present = bool(SecureConfig.decrypt_waba_secret(token_raw) or token_raw)
            configured = bool(phone_id and waba_id and access_token_present)

            return {
                "ok": True,
                "configured": configured,
                "phone_id": phone_id,
                "waba_id": waba_id,
                "access_token_present": bool(access_token_present),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _action_specs(self) -> Dict[str, Dict[str, Any]]:
        return {
            "welcome": {"required_params": 1, "default_enabled": True},
            "payment": {"required_params": 3, "default_enabled": True},
            "membership_due_today": {"required_params": 2, "default_enabled": True},
            "membership_due_soon": {"required_params": 2, "default_enabled": True},
            "overdue": {"required_params": 1, "default_enabled": True},
            "deactivation": {"required_params": 2, "default_enabled": True},
            "membership_reactivated": {"required_params": 1, "default_enabled": True},
            "class_booking_confirmed": {"required_params": 3, "default_enabled": True},
            "class_booking_cancelled": {"required_params": 1, "default_enabled": True},
            "class_reminder": {"required_params": 4, "default_enabled": True},
            "waitlist": {"required_params": 4, "default_enabled": True},
            "waitlist_confirmed": {"required_params": 4, "default_enabled": True},
            "schedule_change": {"required_params": 3, "default_enabled": True},
            "marketing_promo": {"required_params": 2, "default_enabled": False},
            "marketing_new_class": {"required_params": 3, "default_enabled": False},
        }

    def _count_meta_params(self, body_text: str) -> int:
        matches = re.findall(r"\{\{(\d+)\}\}", str(body_text or ""))
        nums = []
        for m in matches:
            try:
                nums.append(int(m))
            except Exception:
                pass
        return max(nums) if nums else 0

    def get_gym_whatsapp_actions(self, gym_id: int) -> Dict[str, Any]:
        try:
            gid = int(gym_id)
        except Exception:
            return {"ok": False, "error": "invalid_gym_id"}
        specs = self._action_specs()
        bindings = self.list_whatsapp_template_bindings()
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute("SELECT db_name FROM gyms WHERE id = %s", (gid,))
                row = cur.fetchone()
            if not row:
                return {"ok": False, "error": "gym_not_found"}
            db_name = str(row.get("db_name") or "").strip()
            if not db_name:
                return {"ok": False, "error": "gym_db_missing"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

        params = self.resolve_admin_db_params()
        pg_params = {
            "host": params.get("host"),
            "port": params.get("port"),
            "dbname": db_name,
            "user": params.get("user"),
            "password": params.get("password"),
            "sslmode": params.get("sslmode"),
            "connect_timeout": params.get("connect_timeout"),
            "application_name": "admin_get_tenant_whatsapp_actions",
        }
        current_enabled: Dict[str, Optional[str]] = {}
        current_tpl: Dict[str, Optional[str]] = {}
        try:
            with psycopg2.connect(**pg_params) as t_conn:
                with t_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as t_cur:
                    t_cur.execute("SELECT clave, valor FROM configuracion WHERE clave LIKE 'wa_action_enabled_%' OR clave LIKE 'wa_meta_template_%'")
                    rows = t_cur.fetchall() or []
            for r in rows:
                k = str(r.get("clave") or "")
                v = r.get("valor")
                if k.startswith("wa_action_enabled_"):
                    current_enabled[k.replace("wa_action_enabled_", "")] = v
                elif k.startswith("wa_meta_template_"):
                    current_tpl[k.replace("wa_meta_template_", "")] = v
        except Exception:
            pass

        items: List[Dict[str, Any]] = []
        for action_key, spec in specs.items():
            default_tpl = str(bindings.get(action_key) or self._default_whatsapp_bindings().get(action_key) or "")
            raw_enabled = current_enabled.get(action_key)
            if raw_enabled is None:
                enabled = bool(spec.get("default_enabled") is True)
            else:
                enabled = str(raw_enabled or "").strip().lower() in ("1", "true", "yes", "on")
            tpl = str((current_tpl.get(action_key) or default_tpl) or "").strip()
            items.append(
                {
                    "action_key": action_key,
                    "enabled": bool(enabled),
                    "template_name": tpl,
                    "required_params": int(spec.get("required_params") or 0),
                    "default_enabled": bool(spec.get("default_enabled") is True),
                    "default_template_name": default_tpl,
                }
            )
        return {"ok": True, "actions": items}

    def set_gym_whatsapp_action(self, gym_id: int, action_key: str, enabled: bool, template_name: str) -> Dict[str, Any]:
        try:
            gid = int(gym_id)
        except Exception:
            return {"ok": False, "error": "invalid_gym_id"}
        key = str(action_key or "").strip()
        specs = self._action_specs()
        if key not in specs:
            return {"ok": False, "error": "invalid_action_key"}
        tname = str(template_name or "").strip()
        if not tname:
            tname = str(self.list_whatsapp_template_bindings().get(key) or self._default_whatsapp_bindings().get(key) or "").strip()
        if not tname:
            return {"ok": False, "error": "template_name_required"}

        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(
                    "SELECT template_name, body_text, active FROM whatsapp_template_catalog WHERE template_name = %s LIMIT 1",
                    (tname,),
                )
                row = cur.fetchone()
                if not row or not bool(row.get("active") is True):
                    return {"ok": False, "error": "template_not_found_or_inactive"}
                required = int(specs[key].get("required_params") or 0)
                actual = self._count_meta_params(str(row.get("body_text") or ""))
                if required != actual:
                    return {"ok": False, "error": f"params_mismatch_required_{required}_got_{actual}"}
                cur.execute("SELECT db_name FROM gyms WHERE id = %s", (gid,))
                grow = cur.fetchone()
            if not grow:
                return {"ok": False, "error": "gym_not_found"}
            db_name = str(grow.get("db_name") or "").strip()
            if not db_name:
                return {"ok": False, "error": "gym_db_missing"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

        params = self.resolve_admin_db_params()
        pg_params = {
            "host": params.get("host"),
            "port": params.get("port"),
            "dbname": db_name,
            "user": params.get("user"),
            "password": params.get("password"),
            "sslmode": params.get("sslmode"),
            "connect_timeout": params.get("connect_timeout"),
            "application_name": "admin_set_tenant_whatsapp_action",
        }
        meta_status = None
        meta_list_ok = False
        try:
            with psycopg2.connect(**pg_params) as t_conn0:
                with t_conn0.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as t_cur0:
                    t_cur0.execute(
                        "SELECT phone_id, waba_id, access_token FROM whatsapp_config WHERE active = TRUE ORDER BY created_at DESC LIMIT 1"
                    )
                    cfg = t_cur0.fetchone() or {}
            waba_id = str((cfg or {}).get("waba_id") or "").strip()
            token_raw = str((cfg or {}).get("access_token") or "").strip()
            token = SecureConfig.decrypt_waba_secret(token_raw) if token_raw else ""
            if not token and (token_raw.startswith("EAA") or token_raw.startswith("EAAB") or token_raw.startswith("EAAJ")):
                token = token_raw
            if waba_id and token:
                api_v = (os.getenv("META_GRAPH_API_VERSION") or os.getenv("WHATSAPP_API_VERSION") or "v19.0").strip()
                url = f"https://graph.facebook.com/{api_v}/{waba_id}/message_templates"
                headers = {"Authorization": f"Bearer {token}"}
                after = None
                for _ in range(10):
                    q = {"fields": "name,status", "limit": "200"}
                    if after:
                        q["after"] = after
                    resp = requests.get(url, headers=headers, params=q, timeout=20)
                    data = resp.json() if resp.content else {}
                    if resp.status_code >= 400:
                        break
                    meta_list_ok = True
                    for item in (data.get("data") or []):
                        if str((item or {}).get("name") or "") == tname:
                            meta_status = str((item or {}).get("status") or "")
                            break
                    if meta_status:
                        break
                    cursors = ((data.get("paging") or {}).get("cursors") or {})
                    after = cursors.get("after")
                    if not after:
                        break
        except Exception:
            meta_status = None
        if meta_list_ok and not meta_status:
            return {"ok": False, "error": "template_not_found_in_meta"}
        if meta_status and meta_status.upper() != "APPROVED":
            return {"ok": False, "error": f"template_not_approved_in_meta:{meta_status}"}
        try:
            with psycopg2.connect(**pg_params) as t_conn:
                with t_conn.cursor() as t_cur:
                    t_cur.execute(
                        """
                        INSERT INTO configuracion (clave, valor, tipo, descripcion)
                        VALUES (%s,%s,%s,%s)
                        ON CONFLICT (clave) DO UPDATE SET
                            valor = EXCLUDED.valor,
                            tipo = EXCLUDED.tipo,
                            descripcion = EXCLUDED.descripcion
                        """,
                        (f"wa_action_enabled_{key}", "true" if enabled else "false", "bool", "Habilita envío WhatsApp para esta acción"),
                    )
                    t_cur.execute(
                        """
                        INSERT INTO configuracion (clave, valor, tipo, descripcion)
                        VALUES (%s,%s,%s,%s)
                        ON CONFLICT (clave) DO UPDATE SET
                            valor = EXCLUDED.valor,
                            tipo = EXCLUDED.tipo,
                            descripcion = EXCLUDED.descripcion
                        """,
                        (f"wa_meta_template_{key}", tname, "string", "Nombre de template Meta activo para esta acción"),
                    )
                t_conn.commit()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_gym_owner_password(self, gym_id: int, new_password: str) -> bool:
        """
        Set the owner password for a specific gym.
        Updates both:
        1. gym_config table in the tenant database (owner_password key)
        2. owner_password_hash in the admin gyms table for backup
        
        The password is hashed using bcrypt.
        """
        try:
            if not (new_password or "").strip():
                return False
            
            # Hash the password with bcrypt
            import bcrypt
            password_hash = bcrypt.hashpw(
                new_password.encode('utf-8'), 
                bcrypt.gensalt()
            ).decode('utf-8')
            
            # Get gym info including db_name
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute("SELECT db_name, subdominio FROM gyms WHERE id = %s", (int(gym_id),))
                row = cur.fetchone()
                
            if not row:
                logger.error(f"Gym {gym_id} not found")
                return False
                
            db_name = str(row[0] or "").strip()
            subdominio = str(row[1] or "").strip()
            
            if not db_name:
                logger.error(f"Gym {gym_id} has no db_name")
                return False

            # 1. Update the admin DB gyms table
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE gyms SET owner_password_hash = %s WHERE id = %s",
                    (password_hash, int(gym_id))
                )
                conn.commit()
                logger.info(f"Updated owner_password_hash in admin gyms table for gym {gym_id}")

            # 2. Update the tenant's gym_config table
            params = self.resolve_admin_db_params()
            params["database"] = db_name
            
            pg_params = {
                "host": params.get("host"),
                "port": params.get("port"),
                "dbname": params.get("database"),
                "user": params.get("user"),
                "password": params.get("password"),
                "sslmode": params.get("sslmode"),
                "connect_timeout": params.get("connect_timeout"),
                "application_name": "gym_admin_set_owner_password"
            }

            with psycopg2.connect(**pg_params) as t_conn:
                with t_conn.cursor() as t_cur:
                    # Try to update gym_config table (new schema)
                    try:
                        # Check if gym_config table exists
                        t_cur.execute("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_name = 'gym_config'
                            )
                        """)
                        gym_config_exists = t_cur.fetchone()[0]
                        
                        if gym_config_exists:
                            # Upsert into gym_config
                            t_cur.execute("""
                                INSERT INTO gym_config (clave, valor) 
                                VALUES ('owner_password', %s)
                                ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor
                            """, (password_hash,))
                            logger.info(f"Updated gym_config.owner_password for gym {gym_id}")
                    except Exception as e:
                        logger.warning(f"Could not update gym_config: {e}")
                    
                    # Also try configuracion table (legacy schema)
                    try:
                        t_cur.execute("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_name = 'configuracion'
                            )
                        """)
                        config_exists = t_cur.fetchone()[0]
                        
                        if config_exists:
                            t_cur.execute("""
                                INSERT INTO configuracion (clave, valor) 
                                VALUES ('owner_password', %s)
                                ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor
                            """, (password_hash,))
                            logger.info(f"Updated configuracion.owner_password for gym {gym_id}")
                    except Exception as e:
                        logger.warning(f"Could not update configuracion: {e}")
                        
                t_conn.commit()
            
            return True
        except Exception as e:
            logger.error(f"Error setting owner password for gym {gym_id}: {e}")
            return False


    def cambiar_password_owner(self, gym_id: int, new_password: str) -> bool:
        """
        Change owner password for a gym. This is an alias/older version of set_gym_owner_password.
        Uses bcrypt hashing and updates both admin DB and tenant DB.
        """
        # Delegate to the properly implemented method
        return self.set_gym_owner_password(gym_id, new_password)


    def listar_auditoria_avanzada(self, page: int, page_size: int, actor: Optional[str], action: Optional[str], gym_id: Optional[int], date_from: Optional[str], date_to: Optional[str]) -> Dict[str, Any]:
        try:
            p = max(int(page or 1), 1)
            ps = max(int(page_size or 20), 1)
            where_terms: List[str] = []
            params: List[Any] = []
            
            if actor:
                where_terms.append("actor_username ILIKE %s")
                params.append(f"%{actor}%")
            if action:
                where_terms.append("action ILIKE %s")
                params.append(f"%{action}%")
            if gym_id:
                where_terms.append("gym_id = %s")
                params.append(int(gym_id))
            if date_from:
                where_terms.append("created_at >= %s")
                params.append(date_from)
            if date_to:
                where_terms.append("created_at <= %s")
                # Add one day to include the end date fully if time is 00:00
                params.append(f"{date_to} 23:59:59")
                
            where_sql = (" WHERE " + " AND ".join(where_terms)) if where_terms else ""
            
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute(f"SELECT COUNT(*) FROM admin_audit{where_sql}", params)
                total_row = cur.fetchone()
                total = int(total_row[0]) if total_row else 0
                
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(
                    f"SELECT * FROM admin_audit{where_sql} ORDER BY created_at DESC LIMIT %s OFFSET %s",
                    params + [ps, (p - 1) * ps]
                )
                rows = cur.fetchall()
            return {"items": [dict(r) for r in rows], "total": total, "page": p, "page_size": ps}
        except Exception as e:
            logger.error(f"Error listing audit advanced: {e}")
            return {"items": [], "total": 0, "page": 1, "page_size": int(page_size or 20)}

    def resumen_suscripciones(self) -> Dict[str, Any]:
        try:
            with self.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute("SELECT status, COUNT(*) FROM gym_subscriptions GROUP BY status")
                rows = cur.fetchall()
                stats = {r[0]: r[1] for r in rows}
                
                # Also get total active value?
                # This might require joining with plans to get value
                cur.execute("SELECT COALESCE(SUM(p.amount), 0) FROM gym_subscriptions s JOIN plans p ON p.id = s.plan_id WHERE s.status = 'active'")
                monthly_rr = float(cur.fetchone()[0] or 0)
                
                return {"active": stats.get("active", 0), "total": sum(stats.values()), "stats": stats, "mrr": monthly_rr}
        except Exception:
            return {"active": 0, "total": 0, "stats": {}, "mrr": 0.0}
