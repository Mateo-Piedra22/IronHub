"""
Webapp API Dependencies
Self-contained FastAPI dependency injection for webapp-api
"""

import logging
import json
import os
import re
from typing import Optional, Generator, List

from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


_schema_guard_lock = None
_schema_guard_done = set()
try:
    import threading

    _schema_guard_lock = threading.RLock()
except Exception:
    _schema_guard_lock = None


def _ensure_ejercicios_columns(session: Session, tenant: Optional[str]) -> None:
    try:
        auto_guard = str(os.getenv("AUTO_SCHEMA_GUARD", "")).strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        dev_mode = str(os.getenv("DEVELOPMENT_MODE", "")).strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        if not auto_guard and not dev_mode:
            return
    except Exception:
        return
    try:
        key = str(tenant or "__default__")
        if _schema_guard_lock is not None:
            with _schema_guard_lock:
                if key in _schema_guard_done:
                    return
        else:
            if key in _schema_guard_done:
                return
        session.execute(
            text("""
                ALTER TABLE ejercicios
                    ADD COLUMN IF NOT EXISTS objetivo VARCHAR(100) DEFAULT 'general',
                    ADD COLUMN IF NOT EXISTS equipamiento VARCHAR(100),
                    ADD COLUMN IF NOT EXISTS variantes TEXT;
            """)
        )

        try:
            session.commit()
        except Exception:
            session.rollback()
    except Exception:
        try:
            session.rollback()
        except Exception:
            pass
    finally:
        try:
            if _schema_guard_lock is not None:
                with _schema_guard_lock:
                    _schema_guard_done.add(str(tenant or "__default__"))
            else:
                _schema_guard_done.add(str(tenant or "__default__"))
        except Exception:
            pass


def _ensure_multisucursal_schema(session: Session, tenant: Optional[str]) -> None:
    try:
        auto_guard = str(os.getenv("AUTO_SCHEMA_GUARD", "")).strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        dev_mode = str(os.getenv("DEVELOPMENT_MODE", "")).strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        if not auto_guard and not dev_mode:
            return
    except Exception:
        return

    key = f"multisucursal:{str(tenant or '__default__')}"
    try:
        if _schema_guard_lock is not None:
            with _schema_guard_lock:
                if key in _schema_guard_done:
                    return
        else:
            if key in _schema_guard_done:
                return

        session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS sucursales (
                    id SERIAL PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    codigo TEXT NOT NULL UNIQUE,
                    direccion TEXT NULL,
                    timezone TEXT NULL,
                    station_key VARCHAR(64) NULL,
                    activa BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_sucursales_activa ON sucursales(activa);
                """
            )
        )
        try:
            session.execute(
                text(
                    "ALTER TABLE sucursales ADD COLUMN IF NOT EXISTS station_key VARCHAR(64) NULL"
                )
            )
        except Exception:
            pass
        try:
            session.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_sucursales_station_key ON sucursales(station_key) WHERE station_key IS NOT NULL AND TRIM(station_key) <> ''"
                )
            )
        except Exception:
            pass

        session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS usuario_sucursales (
                    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                    sucursal_id INTEGER NOT NULL REFERENCES sucursales(id) ON DELETE CASCADE,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                    PRIMARY KEY (usuario_id, sucursal_id)
                );
                CREATE INDEX IF NOT EXISTS idx_usuario_sucursales_sucursal_id ON usuario_sucursales(sucursal_id);
                """
            )
        )

        session.execute(
            text(
                "ALTER TABLE asistencias ADD COLUMN IF NOT EXISTS sucursal_id INTEGER NULL"
            )
        )
        try:
            session.execute(
                text(
                    "DO $$ BEGIN "
                    "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_asistencias_sucursal_id') THEN "
                    "ALTER TABLE asistencias ADD CONSTRAINT fk_asistencias_sucursal_id FOREIGN KEY (sucursal_id) REFERENCES sucursales(id) ON DELETE SET NULL; "
                    "END IF; "
                    "END $$;"
                )
            )
        except Exception:
            pass
        session.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_asistencias_sucursal_fecha ON asistencias(sucursal_id, fecha)"
            )
        )

        session.execute(
            text(
                "ALTER TABLE checkin_pending ADD COLUMN IF NOT EXISTS sucursal_id INTEGER NULL"
            )
        )
        try:
            session.execute(
                text(
                    "DO $$ BEGIN "
                    "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_checkin_pending_sucursal_id') THEN "
                    "ALTER TABLE checkin_pending ADD CONSTRAINT fk_checkin_pending_sucursal_id FOREIGN KEY (sucursal_id) REFERENCES sucursales(id) ON DELETE SET NULL; "
                    "END IF; "
                    "END $$;"
                )
            )
        except Exception:
            pass
        session.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_checkin_pending_sucursal_expires ON checkin_pending(sucursal_id, expires_at)"
            )
        )

        session.execute(
            text(
                """
                INSERT INTO sucursales (nombre, codigo)
                SELECT 'Sucursal Principal', 'principal'
                WHERE NOT EXISTS (SELECT 1 FROM sucursales);
                """
            )
        )
        session.execute(
            text(
                """
                UPDATE asistencias
                SET sucursal_id = (SELECT id FROM sucursales ORDER BY id ASC LIMIT 1)
                WHERE sucursal_id IS NULL;
                """
            )
        )
        session.execute(
            text(
                """
                UPDATE checkin_pending
                SET sucursal_id = (SELECT id FROM sucursales ORDER BY id ASC LIMIT 1)
                WHERE sucursal_id IS NULL;
                """
            )
        )
        try:
            session.commit()
        except Exception:
            session.rollback()
    except Exception:
        try:
            session.rollback()
        except Exception:
            pass
    finally:
        try:
            if _schema_guard_lock is not None:
                with _schema_guard_lock:
                    _schema_guard_done.add(key)
            else:
                _schema_guard_done.add(key)
        except Exception:
            pass


def _ensure_staff_schema(session: Session, tenant: Optional[str]) -> None:
    try:
        auto_guard = str(os.getenv("AUTO_SCHEMA_GUARD", "")).strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        dev_mode = str(os.getenv("DEVELOPMENT_MODE", "")).strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        if not auto_guard and not dev_mode:
            return
    except Exception:
        return

    key = f"staff_schema:{str(tenant or '__default__')}"
    try:
        if _schema_guard_lock is not None:
            with _schema_guard_lock:
                if key in _schema_guard_done:
                    return
        else:
            if key in _schema_guard_done:
                return

        session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS staff_profiles (
                    id SERIAL PRIMARY KEY,
                    usuario_id INTEGER NOT NULL UNIQUE REFERENCES usuarios(id) ON DELETE CASCADE,
                    tipo VARCHAR(50) NOT NULL DEFAULT 'empleado',
                    estado VARCHAR(20) NOT NULL DEFAULT 'activo',
                    fecha_creacion TIMESTAMP DEFAULT NOW(),
                    fecha_actualizacion TIMESTAMP DEFAULT NOW()
                )
                """
            )
        )
        try:
            session.execute(
                text(
                    "DO $$ BEGIN "
                    "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'staff_profiles_estado_check') THEN "
                    "ALTER TABLE staff_profiles ADD CONSTRAINT staff_profiles_estado_check CHECK (estado IN ('activo','inactivo','vacaciones')); "
                    "END IF; "
                    "END $$;"
                )
            )
        except Exception:
            pass

        session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS staff_sessions (
                    id SERIAL PRIMARY KEY,
                    staff_id INTEGER NOT NULL REFERENCES staff_profiles(id) ON DELETE CASCADE,
                    sucursal_id INTEGER NULL REFERENCES sucursales(id) ON DELETE SET NULL,
                    fecha DATE NOT NULL,
                    hora_inicio TIMESTAMP NOT NULL,
                    hora_fin TIMESTAMP NULL,
                    minutos_totales INTEGER NULL,
                    notas TEXT NULL,
                    fecha_creacion TIMESTAMP DEFAULT NOW()
                )
                """
            )
        )
        try:
            session.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uniq_sesion_activa_por_staff "
                    "ON staff_sessions(staff_id) WHERE hora_fin IS NULL"
                )
            )
            session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_staff_sessions_staff_id ON staff_sessions(staff_id)"
                )
            )
            session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_staff_sessions_fecha ON staff_sessions(fecha)"
                )
            )
            session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_staff_sessions_sucursal_id ON staff_sessions(sucursal_id)"
                )
            )
        except Exception:
            pass

        try:
            session.execute(
                text(
                    "ALTER TABLE profesor_horas_trabajadas ADD COLUMN IF NOT EXISTS sucursal_id INTEGER NULL"
                )
            )
        except Exception:
            pass
        try:
            session.execute(
                text(
                    "DO $$ BEGIN "
                    "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_profesor_horas_trabajadas_sucursal_id') THEN "
                    "ALTER TABLE profesor_horas_trabajadas "
                    "ADD CONSTRAINT fk_profesor_horas_trabajadas_sucursal_id "
                    "FOREIGN KEY (sucursal_id) REFERENCES sucursales(id) ON DELETE SET NULL; "
                    "END IF; "
                    "END $$;"
                )
            )
        except Exception:
            pass
        try:
            session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_profesor_horas_trabajadas_sucursal_id ON profesor_horas_trabajadas(sucursal_id)"
                )
            )
        except Exception:
            pass

        session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS work_session_pauses (
                    id SERIAL PRIMARY KEY,
                    session_kind VARCHAR(20) NOT NULL,
                    session_id INTEGER NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    ended_at TIMESTAMP NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
                """
            )
        )
        try:
            session.execute(
                text(
                    "DO $$ BEGIN "
                    "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'work_session_pauses_kind_check') THEN "
                    "ALTER TABLE work_session_pauses "
                    "ADD CONSTRAINT work_session_pauses_kind_check CHECK (session_kind IN ('profesor','staff')); "
                    "END IF; "
                    "END $$;"
                )
            )
        except Exception:
            pass
        try:
            session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_work_session_pauses_session ON work_session_pauses(session_kind, session_id)"
                )
            )
            session.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uniq_work_session_pause_active "
                    "ON work_session_pauses(session_kind, session_id) WHERE ended_at IS NULL"
                )
            )
            session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_work_session_pauses_started_at ON work_session_pauses(started_at)"
                )
            )
        except Exception:
            pass

        session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS staff_permissions (
                    usuario_id INTEGER PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
                    scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """
            )
        )

        try:
            session.commit()
        except Exception:
            session.rollback()
    except Exception:
        try:
            session.rollback()
        except Exception:
            pass
    finally:
        try:
            if _schema_guard_lock is not None:
                with _schema_guard_lock:
                    _schema_guard_done.add(key)
            else:
                _schema_guard_done.add(key)
        except Exception:
            pass


def _ensure_whatsapp_multisucursal_schema(session: Session, tenant: Optional[str]) -> None:
    try:
        auto_guard = str(os.getenv("AUTO_SCHEMA_GUARD", "")).strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        dev_mode = str(os.getenv("DEVELOPMENT_MODE", "")).strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        if not auto_guard and not dev_mode:
            return
    except Exception:
        return

    key = f"wa_multisucursal:{str(tenant or '__default__')}"
    try:
        if _schema_guard_lock is not None:
            with _schema_guard_lock:
                if key in _schema_guard_done:
                    return
        else:
            if key in _schema_guard_done:
                return

        session.execute(text("ALTER TABLE whatsapp_config ADD COLUMN IF NOT EXISTS sucursal_id INTEGER NULL"))
        try:
            session.execute(
                text(
                    "DO $$ BEGIN "
                    "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_whatsapp_config_sucursal_id') THEN "
                    "ALTER TABLE whatsapp_config ADD CONSTRAINT fk_whatsapp_config_sucursal_id FOREIGN KEY (sucursal_id) REFERENCES sucursales(id) ON DELETE SET NULL; "
                    "END IF; "
                    "END $$;"
                )
            )
        except Exception:
            pass
        try:
            session.execute(text("CREATE INDEX IF NOT EXISTS idx_whatsapp_config_sucursal_id ON whatsapp_config(sucursal_id)"))
            session.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uniq_whatsapp_config_active_global "
                    "ON whatsapp_config ((1)) WHERE active = TRUE AND sucursal_id IS NULL"
                )
            )
            session.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uniq_whatsapp_config_active_by_branch "
                    "ON whatsapp_config (sucursal_id) WHERE active = TRUE AND sucursal_id IS NOT NULL"
                )
            )
        except Exception:
            pass

        session.execute(text("ALTER TABLE whatsapp_messages ADD COLUMN IF NOT EXISTS sucursal_id INTEGER NULL"))
        session.execute(text("ALTER TABLE whatsapp_messages ADD COLUMN IF NOT EXISTS event_key VARCHAR(150) NULL"))
        try:
            session.execute(
                text(
                    "DO $$ BEGIN "
                    "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_whatsapp_messages_sucursal_id') THEN "
                    "ALTER TABLE whatsapp_messages ADD CONSTRAINT fk_whatsapp_messages_sucursal_id FOREIGN KEY (sucursal_id) REFERENCES sucursales(id) ON DELETE SET NULL; "
                    "END IF; "
                    "END $$;"
                )
            )
        except Exception:
            pass
        try:
            session.execute(text("CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_sucursal_id ON whatsapp_messages(sucursal_id)"))
            session.execute(text("CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_event_key ON whatsapp_messages(event_key)"))
            session.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uniq_whatsapp_messages_event_key "
                    "ON whatsapp_messages(event_key) "
                    "WHERE event_key IS NOT NULL AND TRIM(event_key) <> ''"
                )
            )
        except Exception:
            pass

        try:
            session.commit()
        except Exception:
            session.rollback()
    except Exception:
        try:
            session.rollback()
        except Exception:
            pass
    finally:
        try:
            if _schema_guard_lock is not None:
                with _schema_guard_lock:
                    _schema_guard_done.add(key)
            else:
                _schema_guard_done.add(key)
        except Exception:
            pass


def _ensure_branch_scoped_resources_schema(session: Session, tenant: Optional[str]) -> None:
    try:
        auto_guard = str(os.getenv("AUTO_SCHEMA_GUARD", "")).strip().lower() in ("1", "true", "yes", "on")
        dev_mode = str(os.getenv("DEVELOPMENT_MODE", "")).strip().lower() in ("1", "true", "yes", "on")
        if not auto_guard and not dev_mode:
            return
    except Exception:
        return

    key = f"branch_resources:{str(tenant or '__default__')}"
    try:
        if _schema_guard_lock is not None:
            with _schema_guard_lock:
                if key in _schema_guard_done:
                    return
        else:
            if key in _schema_guard_done:
                return

        session.execute(text("ALTER TABLE ejercicios ADD COLUMN IF NOT EXISTS sucursal_id INTEGER NULL"))
        try:
            session.execute(
                text(
                    "DO $$ BEGIN "
                    "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_ejercicios_sucursal_id') THEN "
                    "ALTER TABLE ejercicios ADD CONSTRAINT fk_ejercicios_sucursal_id FOREIGN KEY (sucursal_id) REFERENCES sucursales(id) ON DELETE SET NULL; "
                    "END IF; "
                    "END $$;"
                )
            )
        except Exception:
            pass
        try:
            session.execute(text("CREATE INDEX IF NOT EXISTS idx_ejercicios_sucursal_id ON ejercicios(sucursal_id)"))
        except Exception:
            pass

        session.execute(text("ALTER TABLE rutinas ADD COLUMN IF NOT EXISTS sucursal_id INTEGER NULL"))
        try:
            session.execute(
                text(
                    "DO $$ BEGIN "
                    "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_rutinas_sucursal_id') THEN "
                    "ALTER TABLE rutinas ADD CONSTRAINT fk_rutinas_sucursal_id FOREIGN KEY (sucursal_id) REFERENCES sucursales(id) ON DELETE SET NULL; "
                    "END IF; "
                    "END $$;"
                )
            )
        except Exception:
            pass
        try:
            session.execute(text("CREATE INDEX IF NOT EXISTS idx_rutinas_sucursal_id ON rutinas(sucursal_id)"))
        except Exception:
            pass

        session.execute(text("ALTER TABLE clases ADD COLUMN IF NOT EXISTS sucursal_id INTEGER NULL"))
        try:
            session.execute(
                text(
                    "DO $$ BEGIN "
                    "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_clases_sucursal_id') THEN "
                    "ALTER TABLE clases ADD CONSTRAINT fk_clases_sucursal_id FOREIGN KEY (sucursal_id) REFERENCES sucursales(id) ON DELETE SET NULL; "
                    "END IF; "
                    "END $$;"
                )
            )
        except Exception:
            pass
        try:
            session.execute(text("CREATE INDEX IF NOT EXISTS idx_clases_sucursal_id ON clases(sucursal_id)"))
        except Exception:
            pass

        try:
            session.commit()
        except Exception:
            session.rollback()
    except Exception:
        try:
            session.rollback()
        except Exception:
            pass
    finally:
        try:
            if _schema_guard_lock is not None:
                with _schema_guard_lock:
                    _schema_guard_done.add(key)
            else:
                _schema_guard_done.add(key)
        except Exception:
            pass


def _ensure_membership_schema(session: Session, tenant: Optional[str]) -> None:
    try:
        auto_guard = str(os.getenv("AUTO_SCHEMA_GUARD", "")).strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        dev_mode = str(os.getenv("DEVELOPMENT_MODE", "")).strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        if not auto_guard and not dev_mode:
            return
    except Exception:
        return

    key = f"membership:{str(tenant or '__default__')}"
    try:
        if _schema_guard_lock is not None:
            with _schema_guard_lock:
                if key in _schema_guard_done:
                    return
        else:
            if key in _schema_guard_done:
                return

        session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS memberships (
                    id SERIAL PRIMARY KEY,
                    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                    plan_name TEXT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    start_date DATE NOT NULL DEFAULT CURRENT_DATE,
                    end_date DATE NULL,
                    all_sucursales BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_memberships_usuario_status ON memberships(usuario_id, status);
                CREATE INDEX IF NOT EXISTS idx_memberships_status_end_date ON memberships(status, end_date);
                """
            )
        )
        session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS membership_sucursales (
                    membership_id INTEGER NOT NULL REFERENCES memberships(id) ON DELETE CASCADE,
                    sucursal_id INTEGER NOT NULL REFERENCES sucursales(id) ON DELETE CASCADE,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                    PRIMARY KEY (membership_id, sucursal_id)
                );
                CREATE INDEX IF NOT EXISTS idx_membership_sucursales_sucursal_id ON membership_sucursales(sucursal_id);
                """
            )
        )
        try:
            session.commit()
        except Exception:
            session.rollback()
    except Exception:
        try:
            session.rollback()
        except Exception:
            pass
    finally:
        try:
            if _schema_guard_lock is not None:
                with _schema_guard_lock:
                    _schema_guard_done.add(key)
            else:
                _schema_guard_done.add(key)
        except Exception:
            pass


# Import tenant context functions from tenant_connection to avoid circular imports
def _ensure_feature_flags_schema(session: Session, tenant: Optional[str]) -> None:
    key = f"feature_flags:{str(tenant or '__default__')}"
    try:
        if _schema_guard_lock is not None:
            with _schema_guard_lock:
                if key in _schema_guard_done:
                    return
        else:
            if key in _schema_guard_done:
                return

        default_flags = {
            "modules": {
                "usuarios": True,
                "pagos": True,
                "profesores": True,
                "empleados": True,
                "rutinas": True,
                "ejercicios": True,
                "clases": True,
                "asistencias": True,
                "whatsapp": True,
                "configuracion": True,
                "reportes": True,
                "entitlements_v2": False,
            }
        }
        session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS feature_flags (
                    id SMALLINT PRIMARY KEY,
                    flags JSONB NOT NULL DEFAULT '{}'::jsonb,
                    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
                );
                """
            )
        )
        session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS feature_flags_overrides (
                    sucursal_id INTEGER PRIMARY KEY REFERENCES sucursales(id) ON DELETE CASCADE,
                    flags JSONB NOT NULL DEFAULT '{}'::jsonb,
                    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
                );
                """
            )
        )
        session.execute(
            text(
                "INSERT INTO feature_flags (id, flags) VALUES (1, :flags::jsonb) ON CONFLICT (id) DO NOTHING"
            ),
            {"flags": json.dumps(default_flags, ensure_ascii=False)},
        )
        try:
            session.commit()
        except Exception:
            session.rollback()
    except Exception:
        try:
            session.rollback()
        except Exception:
            pass
    finally:
        try:
            if _schema_guard_lock is not None:
                with _schema_guard_lock:
                    _schema_guard_done.add(key)
            else:
                _schema_guard_done.add(key)
        except Exception:
            pass


# tenant_connection has the canonical CURRENT_TENANT contextvar
from src.database import tenant_connection as _tenant_connection
from src.database.tenant_connection import (
    get_tenant_session_factory,
    set_current_tenant,
    get_current_tenant,
    validate_tenant_name,
)

CURRENT_TENANT = _tenant_connection.CURRENT_TENANT

# Import local services
from src.database.connection import SessionLocal, AdminSessionLocal
from src.services.user_service import UserService

from src.services.payment_service import PaymentService
from src.services.auth_service import AuthService
from src.services.gym_config_service import GymConfigService
from src.services.clase_service import ClaseService
from src.services.training_service import TrainingService
from src.services.attendance_service import AttendanceService
from src.services.feature_flags_service import FeatureFlagsService
from src.security.session_claims import get_claims, OWNER_ROLES, STAFF_ROLES, PROFESOR_ROLES
from src.services.membership_service import MembershipService
from src.services.inscripciones_service import InscripcionesService
from src.services.profesor_service import ProfesorService
from src.services.staff_service import StaffService
from src.services.whatsapp_service import WhatsAppService
from src.services.whatsapp_dispatch_service import WhatsAppDispatchService
from src.services.whatsapp_settings_service import WhatsAppSettingsService
from src.services.reports_service import ReportsService
from src.services.admin_service import AdminService
from src.services.audit_service import AuditService


async def ensure_tenant_context(request: Request) -> Optional[str]:
    """
    Dependency to extract and set tenant context from request.
    Useful for routers that don't go through main app middleware (if any).
    """
    host = request.headers.get("host", "")
    tenant = request.headers.get("x-tenant")

    # Try to extract from subdomain if not in header
    if not tenant and host:
        base_domain = os.getenv("TENANT_BASE_DOMAIN", "ironhub.motiona.xyz")
        # Remove port
        host_clean = host.split(":")[0]
        if host_clean.endswith(f".{base_domain}"):
            candidate = host_clean.replace(f".{base_domain}", "")
            # Avoid 'www', 'api', 'admin' if they are reserved (optional, but good practice)
            if candidate not in ("www", "api", "admin", "admin-api"):
                tenant = candidate

    if tenant:
        try:
            t = str(tenant).strip().lower()
        except Exception:
            t = ""

        try:
            ok, _err = validate_tenant_name(t)
        except Exception:
            ok = False

        if ok:
            set_current_tenant(t)
            return t
    return None


def _try_set_tenant_from_request(request: Request) -> Optional[str]:
    session_tenant: Optional[str] = None
    try:
        session_tenant = (
            str(request.session.get("tenant") or "").strip().lower() or None
        )
    except Exception:
        session_tenant = None

    query_tenant: Optional[str] = None
    try:
        query_tenant = (
            str(request.query_params.get("tenant") or "").strip().lower() or None
        )
    except Exception:
        query_tenant = None

    header_tenant: Optional[str] = None
    try:
        header_tenant = (
            str(request.headers.get("x-tenant") or "").strip().lower() or None
        )
    except Exception:
        header_tenant = None

    origin_tenant: Optional[str] = None
    try:
        origin = str(request.headers.get("origin") or request.headers.get("referer") or "").strip().lower()
    except Exception:
        origin = ""
    if origin:
        try:
            base = str(os.getenv("TENANT_BASE_DOMAIN", "ironhub.motiona.xyz") or "").strip().lower().lstrip(".")
            if base:
                m = re.search(rf"^https?://([a-z0-9-]+)\.{re.escape(base)}", origin)
                if m:
                    cand = str(m.group(1) or "").strip().lower()
                    if cand and cand not in ("www", "api", "admin", "admin-api"):
                        origin_tenant = cand
        except Exception:
            origin_tenant = None

    tenant: Optional[str] = None
    if session_tenant:
        if (
            query_tenant
            and query_tenant != session_tenant
            and request.url.path.startswith("/api/")
        ):
            raise HTTPException(status_code=403, detail="Tenant mismatch")
        if (
            header_tenant
            and header_tenant != session_tenant
            and request.url.path.startswith("/api/")
        ):
            raise HTTPException(status_code=403, detail="Tenant mismatch")
        if (
            origin_tenant
            and origin_tenant != session_tenant
            and request.url.path.startswith("/api/")
        ):
            raise HTTPException(status_code=403, detail="Tenant mismatch")
        tenant = session_tenant
    else:
        if (
            origin_tenant
            and header_tenant
            and header_tenant != origin_tenant
            and request.url.path.startswith("/api/")
        ):
            raise HTTPException(status_code=403, detail="Tenant mismatch")
        tenant = query_tenant or header_tenant or origin_tenant

    if not tenant:
        try:
            host = str(request.headers.get("host") or "").strip()
        except Exception:
            host = ""

        if host:
            base_domain = (
                os.getenv("TENANT_BASE_DOMAIN", "ironhub.motiona.xyz").strip().lower()
            )
            host_clean = host.split(":")[0].strip().lower()
            if base_domain and host_clean.endswith(f".{base_domain}"):
                candidate = host_clean.replace(f".{base_domain}", "").strip()
                if candidate and candidate not in ("www", "api", "admin", "admin-api"):
                    tenant = candidate

    if not tenant:
        return None

    try:
        ok, _err = validate_tenant_name(str(tenant))
    except Exception:
        ok = False

    if not ok:
        return None

    try:
        set_current_tenant(str(tenant).strip().lower())
    except Exception:
        return None
    return str(tenant).strip().lower()


def get_db_session(request: Request) -> Generator[Session, None, None]:
    """
    Get a database session for the current tenant.
    Uses CURRENT_TENANT context variable to determine which database to connect to.

    IMPORTANT: If tenant is set but cannot connect, raises an error instead of
    silently falling back to the wrong database.
    """
    if not get_current_tenant():
        _try_set_tenant_from_request(request)

    tenant = get_current_tenant()

    if tenant:
        # Use tenant-specific session
        try:
            factory = get_tenant_session_factory(tenant)
            if factory:
                session = factory()
                try:
                    yield session
                finally:
                    session.close()
                return
            else:
                # Factory returned None - tenant lookup failed
                logger.error(f"Tenant session factory returned None for '{tenant}'")
                raise HTTPException(
                    status_code=503,
                    detail=f"Database connection unavailable for tenant '{tenant}'",
                )
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logger.error(f"Failed to get tenant session for '{tenant}': {e}")
            # Check if this looks like a production environment without proper config
            db_host = os.getenv("DB_HOST", "localhost")
            if db_host == "localhost" and not os.getenv("DEVELOPMENT_MODE"):
                logger.critical(
                    "PRODUCTION CONFIG ERROR: DB_HOST is 'localhost' but DEVELOPMENT_MODE not set. "
                    "Ensure DB_HOST, DB_USER, DB_PASSWORD are configured for production."
                )
            raise HTTPException(
                status_code=503, detail=f"Database connection error: {str(e)}"
            )

    # No tenant context - use global database
    # Also validate that we're not accidentally using localhost in production
    db_host = os.getenv("DB_HOST", "localhost")
    if db_host == "localhost" and not os.getenv("DEVELOPMENT_MODE"):
        logger.warning(
            "No tenant context and DB_HOST is 'localhost'. "
            "This may indicate missing environment configuration."
        )

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_user_service(session: Session = Depends(get_db_session)) -> UserService:
    """Get UserService instance with current session."""
    return UserService(session)


# Aliases for backwards compatibility with routers
get_db = get_db_session


def get_rm():
    """Get RoutineTemplateManager instance for PDF/Excel generation."""
    try:
        from src.routine_manager import RoutineTemplateManager

        return RoutineTemplateManager()
    except Exception:
        return None


def get_payment_service(session: Session = Depends(get_db_session)) -> PaymentService:
    """Get PaymentService instance with current session."""
    return PaymentService(session)


def get_auth_service(session: Session = Depends(get_db_session)) -> AuthService:
    """Get AuthService instance with current session."""
    return AuthService(session)


def get_gym_config_service(
    session: Session = Depends(get_db_session),
) -> GymConfigService:
    """Get GymConfigService instance with current session."""
    return GymConfigService(session)


def get_clase_service(session: Session = Depends(get_db_session)) -> ClaseService:
    """Get ClaseService instance with current session."""
    return ClaseService(session)


def get_training_service(session: Session = Depends(get_db_session)) -> TrainingService:
    """Get TrainingService instance with current session."""
    return TrainingService(session)


def get_attendance_service(
    session: Session = Depends(get_db_session),
) -> AttendanceService:
    """Get AttendanceService instance with current session."""
    return AttendanceService(session)


def get_membership_service(
    session: Session = Depends(get_db_session),
) -> MembershipService:
    return MembershipService(session)


def get_inscripciones_service(
    session: Session = Depends(get_db_session),
) -> InscripcionesService:
    """Get InscripcionesService instance with current session."""
    return InscripcionesService(session)


def get_profesor_service(session: Session = Depends(get_db_session)) -> ProfesorService:
    """Get ProfesorService instance with current session."""
    return ProfesorService(session)


def get_staff_service(session: Session = Depends(get_db_session)) -> StaffService:
    return StaffService(session)


def get_whatsapp_service(session: Session = Depends(get_db_session)) -> WhatsAppService:
    """Get WhatsAppService instance with current session."""
    return WhatsAppService(session)


def get_whatsapp_dispatch_service(
    session: Session = Depends(get_db_session),
) -> WhatsAppDispatchService:
    return WhatsAppDispatchService(session)


def get_whatsapp_settings_service(
    session: Session = Depends(get_db_session),
) -> WhatsAppSettingsService:
    return WhatsAppSettingsService(session)


def get_reports_service(
    request: Request, session: Session = Depends(get_db_session)
) -> ReportsService:
    """Get ReportsService instance with current session."""
    svc = ReportsService(session)
    try:
        svc.sucursal_id = get_claims(request).get("sucursal_id")  # type: ignore[attr-defined]
    except Exception:
        pass
    return svc


def get_admin_service(session: Session = Depends(get_db_session)) -> AdminService:
    """Get AdminService instance with current session."""
    return AdminService(session)


def get_audit_service(session: Session = Depends(get_db_session)) -> AuditService:
    """Get AuditService instance for logging sensitive actions."""
    return AuditService(session)


# Alias for backwards compatibility with routers
def get_pm(session: Session = Depends(get_db_session)) -> PaymentService:
    """Get PaymentService - alias for payments router backward compatibility."""
    return PaymentService(session)


def get_admin_db() -> Generator[Session, None, None]:
    """
    Get admin database session (always uses global/admin database).
    Used by public router for tenant-independent operations.
    """
    session = AdminSessionLocal()
    try:
        yield session
    finally:
        session.close()


# --- Security Dependencies ---


def require_feature(feature_key: str):
    async def _dep(request: Request, session: Session = Depends(get_db_session)):
        try:
            if str(feature_key or "").strip().lower() == "whatsapp" and str(
                request.url.path or ""
            ).startswith("/webhooks/whatsapp"):
                return True
        except Exception:
            pass
        try:
            enabled = FeatureFlagsService(session).is_enabled(
                feature_key, sucursal_id=get_claims(request).get("sucursal_id")
            )
        except Exception:
            enabled = False
        if enabled:
            return True
        if request.url.path.startswith("/api/"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
            )
        return RedirectResponse(url="/gestion", status_code=303)

    return _dep


def require_scope(scope_key: str):
    async def _dep(request: Request, session: Session = Depends(get_db_session)) -> bool:
        claims = get_claims(request)
        role = str(claims.get("role") or "").strip().lower()
        if role in OWNER_ROLES:
            return True
        user_id = claims.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
            )
        if role not in STAFF_ROLES and role not in PROFESOR_ROLES:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        row = session.execute(
            text("SELECT scopes FROM staff_permissions WHERE usuario_id = :uid"),
            {"uid": int(user_id)},
        ).scalar()
        scopes: List[str] = []
        try:
            if row:
                scopes = list(row)
        except Exception:
            scopes = []

        key = str(scope_key or "").strip()
        if not key:
            return True
        if key in scopes:
            return True
        parts = key.split(":", 1)
        if len(parts) == 2:
            if f"{parts[0]}:*" in scopes:
                return True
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return _dep


def require_scope_gestion(scope_key: str):
    async def _dep(request: Request, session: Session = Depends(get_db_session)) -> bool:
        claims = get_claims(request)
        st = str(claims.get("session_type") or "").strip().lower()
        if st != "gestion":
            return True
        return await require_scope(scope_key)(request, session)

    return _dep


async def require_gestion_access(request: Request):
    """Require gestion (management) panel access - owner or profesor."""
    claims = get_claims(request)
    if claims.get("is_gestion") and claims.get("is_authenticated"):
        return True
    if request.url.path.startswith("/api/"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )
    return RedirectResponse(url="/gestion/login", status_code=303)


async def require_owner(request: Request):
    """Require owner/admin access."""
    claims = get_claims(request)
    if not bool(claims.get("is_authenticated")):
        logger.warning(
            f"AUTH FAILED: Not logged in. Session keys: {list(request.session.keys())}"
        )
        if request.url.path.startswith("/api/"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
            )
        return RedirectResponse(url="/gestion/login", status_code=303)

    role = str(claims.get("role") or "").strip().lower()
    if role not in OWNER_ROLES:
        logger.warning(f"AUTH FAILED: Invalid role {role}")
        if request.url.path.startswith("/api/"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden"
            )
        return RedirectResponse(url="/gestion", status_code=303)
    return True


async def require_admin(request: Request):
    """Alias for require_owner."""
    return await require_owner(request)


async def require_profesor(request: Request):
    """Require profesor or higher access."""
    claims = get_claims(request)
    role = str(claims.get("role") or "").strip().lower()
    if (not bool(claims.get("is_authenticated"))) or role not in (
        "profesor",
        "dueño",
        "dueno",
        "owner",
        "admin",
        "administrador",
    ):
        if request.url.path.startswith("/api/"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
            )
        return RedirectResponse(url="/gestion/login", status_code=303)
    return True


async def require_user_auth(request: Request):
    """Require user (member) authentication from usuario panel."""
    claims = get_claims(request)
    user_id = claims.get("user_id")
    if not user_id:
        if request.url.path.startswith("/api/"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
            )
        return RedirectResponse(url="/usuario/login", status_code=303)
    return user_id


async def require_sucursal_selected(
    request: Request, db: Session = Depends(get_db_session)
):
    claims = get_claims(request)
    sid = claims.get("sucursal_id")
    if sid:
        try:
            sid_int = int(sid)
        except Exception:
            sid_int = 0
        if sid_int > 0:
            try:
                row = (
                    db.execute(
                        text(
                            "SELECT id FROM sucursales WHERE id = :id AND activa = TRUE LIMIT 1"
                        ),
                        {"id": int(sid_int)},
                    )
                    .mappings()
                    .first()
                )
                if row:
                    return int(sid_int)
            except Exception:
                pass
        try:
            request.session.pop("sucursal_id", None)
        except Exception:
            pass
    if request.url.path.startswith("/api/"):
        raise HTTPException(
            status_code=428, detail="Sucursal requerida"
        )
    path = str(request.url.path or "")
    if path.startswith("/dashboard"):
        return RedirectResponse(url="/dashboard/seleccionar-sucursal", status_code=303)
    if path.startswith("/usuario"):
        return RedirectResponse(url="/usuario/seleccionar-sucursal", status_code=303)
    return RedirectResponse(url="/gestion/seleccionar-sucursal", status_code=303)


async def require_sucursal_selected_optional(
    request: Request, db: Session = Depends(get_db_session)
) -> Optional[int]:
    claims = get_claims(request)
    sid = claims.get("sucursal_id")
    if sid:
        try:
            sid_int = int(sid)
        except Exception:
            sid_int = 0
        if sid_int > 0:
            try:
                row = (
                    db.execute(
                        text(
                            "SELECT id FROM sucursales WHERE id = :id AND activa = TRUE LIMIT 1"
                        ),
                        {"id": int(sid_int)},
                    )
                    .mappings()
                    .first()
                )
                if row:
                    return int(sid_int)
            except Exception:
                pass
        try:
            request.session.pop("sucursal_id", None)
        except Exception:
            pass
    return None


async def get_current_active_user(
    request: Request, user_service: UserService = Depends(get_user_service)
):
    """
    Get current active user from session or raise 401.
    Used by gym router for member-specific actions.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user required",
        )

    user = user_service.get_user_by_id(user_id)
    if not user:
        # Invalid session data
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )

    return user
