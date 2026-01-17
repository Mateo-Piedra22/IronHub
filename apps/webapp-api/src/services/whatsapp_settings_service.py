from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import logging
import os

import requests
from sqlalchemy import select, func, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.database.tenant_connection import get_current_tenant
from src.secure_config import SecureConfig
from src.services.base import BaseService
from src.database.orm_models import WhatsappConfig, WhatsappMessage, Configuracion
from src.services.whatsapp_meta_provisioner import provision_standard_meta_templates

logger = logging.getLogger(__name__)


class WhatsAppSettingsService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        try:
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS whatsapp_config (
                    id SERIAL PRIMARY KEY,
                    phone_id VARCHAR(50) NOT NULL,
                    waba_id VARCHAR(50) NOT NULL,
                    access_token TEXT,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS configuracion (
                    id SERIAL PRIMARY KEY,
                    clave VARCHAR(255) UNIQUE NOT NULL,
                    valor TEXT
                )
            """))
            self.db.commit()
        except Exception:
            try:
                self.db.rollback()
            except Exception:
                pass

    def _sync_tenant_whatsapp_to_admin_db(self, phone_id: str, waba_id: str) -> None:
        tenant = str(get_current_tenant() or "").strip().lower()
        if not tenant or not phone_id:
            return
        try:
            from src.database.raw_manager import RawPostgresManager

            admin_params = {
                "host": os.getenv("ADMIN_DB_HOST", os.getenv("DB_HOST", "localhost")),
                "port": int(os.getenv("ADMIN_DB_PORT", os.getenv("DB_PORT", 5432))),
                "database": os.getenv("ADMIN_DB_NAME", os.getenv("DB_NAME", "ironhub_admin")),
                "user": os.getenv("ADMIN_DB_USER", os.getenv("DB_USER", "postgres")),
                "password": os.getenv("ADMIN_DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
                "sslmode": os.getenv("ADMIN_DB_SSLMODE", os.getenv("DB_SSLMODE", "require")),
                "connect_timeout": 10,
                "application_name": "webapp_sync_whatsapp_to_admin",
            }
            adm = RawPostgresManager(connection_params=admin_params)
            with adm.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    UPDATE gyms
                    SET whatsapp_phone_id = %s,
                        whatsapp_business_account_id = %s
                    WHERE subdominio = %s
                    """,
                    (str(phone_id).strip(), str(waba_id or "").strip() or None, tenant),
                )
                conn.commit()
        except Exception:
            return

    def _now_utc_naive(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def _get_cfg_value(self, clave: str) -> Optional[str]:
        try:
            row = self.db.execute(select(Configuracion.valor).where(Configuracion.clave == clave).limit(1)).first()
            return row[0] if row else None
        except Exception:
            return None

    def _set_cfg_value(self, clave: str, valor: Any) -> None:
        try:
            val_str = "" if valor is None else str(valor)
        except Exception:
            val_str = ""
        stmt = insert(Configuracion).values(clave=clave, valor=val_str).on_conflict_do_update(
            index_elements=["clave"],
            set_={"valor": val_str},
        )
        self.db.execute(stmt)

    def _get_active_config_row(self) -> Optional[WhatsappConfig]:
        try:
            return (
                self.db.execute(
                    select(WhatsappConfig)
                    .where(WhatsappConfig.active == True)
                    .order_by(WhatsappConfig.created_at.desc())
                    .limit(1)
                )
                .scalars()
                .first()
            )
        except Exception:
            return None

    def _decrypt_token_best_effort(self, raw: str) -> str:
        s = str(raw or "")
        if not s:
            return ""
        dec = SecureConfig.decrypt_waba_secret(s)
        if dec:
            return dec
        if s.startswith("EAA") or s.startswith("EAAB") or s.startswith("EAAJ"):
            return s
        return ""

    def _timeout_seconds(self) -> float:
        v = (self._get_cfg_value("WHATSAPP_SEND_TIMEOUT_SECONDS") or os.getenv("WHATSAPP_SEND_TIMEOUT_SECONDS") or "").strip()
        try:
            f = float(v) if v else 25.0
        except Exception:
            f = 25.0
        if f < 5:
            return 5.0
        if f > 120:
            return 120.0
        return f

    def _api_version(self) -> str:
        return (os.getenv("META_GRAPH_API_VERSION") or os.getenv("WHATSAPP_API_VERSION") or "v19.0").strip()

    def get_ui_config(self) -> Dict[str, Any]:
        row = self._get_active_config_row()
        token_raw = getattr(row, "access_token", "") if row else ""
        enabled = str(self._get_cfg_value("enabled") or "").strip().lower() in ("1", "true", "yes", "on")
        webhook_enabled = str(self._get_cfg_value("webhook_enabled") or self._get_cfg_value("enable_webhook") or "").strip().lower() in ("1", "true", "yes", "on")
        return {
            "phone_number_id": getattr(row, "phone_id", "") if row else "",
            "whatsapp_business_account_id": getattr(row, "waba_id", "") if row else "",
            "access_token": "",
            "access_token_present": bool(token_raw),
            "webhook_verify_token": self._get_cfg_value("webhook_verify_token") or "",
            "enabled": bool(enabled),
            "webhook_enabled": bool(webhook_enabled),
        }

    def upsert_manual_config(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            return self.get_ui_config()

        try:
            phone_id = str(payload.get("phone_number_id") or payload.get("phone_id") or "").strip() or None
            waba_id = str(payload.get("whatsapp_business_account_id") or payload.get("waba_id") or "").strip() or None
            token_in = payload.get("access_token")
            token_raw = str(token_in or "").strip()
            if token_raw:
                SecureConfig.require_waba_encryption()
            token_enc = SecureConfig.encrypt_waba_secret(token_raw) if token_raw else None

            row = self._get_active_config_row()
            if row is None:
                row = WhatsappConfig(phone_id=phone_id or "", waba_id=waba_id or "", access_token=token_enc, active=True)
                self.db.add(row)
            else:
                if phone_id is not None:
                    row.phone_id = phone_id
                if waba_id is not None:
                    row.waba_id = waba_id
                if token_enc is not None:
                    row.access_token = token_enc

            if "enabled" in payload:
                self._set_cfg_value("enabled", "1" if bool(payload.get("enabled")) else "0")
            if "webhook_enabled" in payload:
                self._set_cfg_value("webhook_enabled", "1" if bool(payload.get("webhook_enabled")) else "0")
            if "webhook_verify_token" in payload:
                self._set_cfg_value("webhook_verify_token", str(payload.get("webhook_verify_token") or ""))
            if "allowlist_numbers" in payload:
                self._set_cfg_value("allowlist_numbers", str(payload.get("allowlist_numbers") or ""))
            if "allowlist_enabled" in payload:
                self._set_cfg_value("allowlist_enabled", "1" if bool(payload.get("allowlist_enabled")) else "0")
            if "wa_template_language" in payload:
                self._set_cfg_value("wa_template_language", str(payload.get("wa_template_language") or ""))

            self.db.commit()
            try:
                self._sync_tenant_whatsapp_to_admin_db(phone_id=str(phone_id or ""), waba_id=str(waba_id or ""))
            except Exception:
                pass
            return self.get_ui_config()
        except Exception as e:
            try:
                self.db.rollback()
            except Exception:
                pass
            logger.error(f"WhatsAppSettingsService.upsert_manual_config error: {e}")
            return self.get_ui_config()

    def get_state(self) -> Dict[str, Any]:
        row = self._get_active_config_row()
        token_raw = getattr(row, "access_token", "") if row else ""
        valid = bool(
            (getattr(row, "phone_id", "") or "").strip()
            and (getattr(row, "waba_id", "") or "").strip()
            and self._decrypt_token_best_effort(token_raw).strip()
        )
        return {
            "disponible": True,
            "habilitado": bool(valid),
            "servidor_activo": False,
            "configuracion_valida": bool(valid),
        }

    def get_stats(self) -> Dict[str, Any]:
        try:
            total = self.db.execute(select(func.count(WhatsappMessage.id))).scalar() or 0
            since_30 = self._now_utc_naive() - timedelta(days=30)
            ultimo_mes = (
                self.db.execute(select(func.count(WhatsappMessage.id)).where(WhatsappMessage.sent_at >= since_30)).scalar() or 0
            )
            by_type = dict(
                self.db.execute(
                    select(WhatsappMessage.message_type, func.count(WhatsappMessage.id)).group_by(WhatsappMessage.message_type)
                ).all()
            )
            by_status = dict(
                self.db.execute(
                    select(WhatsappMessage.status, func.count(WhatsappMessage.id)).group_by(WhatsappMessage.status)
                ).all()
            )
            return {"total": int(total), "ultimo_mes": int(ultimo_mes), "por_tipo": by_type, "por_estado": by_status}
        except Exception as e:
            return {"error": str(e)}

    def get_webhook_verify_token(self) -> str:
        return str(self._get_cfg_value("WHATSAPP_VERIFY_TOKEN") or self._get_cfg_value("webhook_verify_token") or "")

    def exchange_code_for_access_token(self, code: str, redirect_uri: Optional[str] = None) -> str:
        app_id = (os.getenv("META_APP_ID") or os.getenv("FACEBOOK_APP_ID") or "").strip()
        app_secret = (os.getenv("META_APP_SECRET") or os.getenv("FACEBOOK_APP_SECRET") or "").strip()
        if not app_id or not app_secret:
            raise RuntimeError("META_APP_ID/META_APP_SECRET no configurados")
        ruri = redirect_uri
        if ruri is None:
            ruri = os.getenv("META_OAUTH_REDIRECT_URI")
        if ruri is None:
            ruri = ""
        url = f"https://graph.facebook.com/{(os.getenv('META_GRAPH_API_VERSION') or 'v19.0').strip()}/oauth/access_token"
        resp = requests.get(url, params={"client_id": app_id, "client_secret": app_secret, "code": str(code), "redirect_uri": str(ruri)}, timeout=25)  # type: ignore[name-defined]
        data = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            raise RuntimeError(str(data.get("error") or data or f"HTTP {resp.status_code}"))
        token = str((data or {}).get("access_token") or "").strip()
        if not token:
            raise RuntimeError("No access_token devuelto por Meta")
        return token

    def set_credentials_from_embedded_signup(self, waba_id: str, phone_number_id: str, access_token: str) -> None:
        waba = str(waba_id or "").strip()
        phone_id = str(phone_number_id or "").strip()
        token_raw = str(access_token or "").strip()
        if not waba or not phone_id or not token_raw:
            raise RuntimeError("Credenciales incompletas")

        SecureConfig.require_waba_encryption()
        token_enc = SecureConfig.encrypt_waba_secret(token_raw)

        row = self._get_active_config_row()
        if row is None:
            row = WhatsappConfig(phone_id=phone_id, waba_id=waba, access_token=token_enc, active=True)
            self.db.add(row)
        else:
            row.phone_id = phone_id
            row.waba_id = waba
            row.access_token = token_enc
            row.active = True

        if not str(self._get_cfg_value("enabled") or "").strip():
            self._set_cfg_value("enabled", "1")
        self.db.commit()
        try:
            self._sync_tenant_whatsapp_to_admin_db(phone_id=phone_id, waba_id=waba)
        except Exception:
            pass

    def provision_meta_templates_for_current_config(self, language_code: Optional[str] = None) -> Dict[str, Any]:
        row = self._get_active_config_row()
        if not row:
            raise RuntimeError("WhatsApp no configurado")
        waba_id = str(getattr(row, "waba_id", "") or "").strip()
        token = self._decrypt_token_best_effort(str(getattr(row, "access_token", "") or ""))
        if not waba_id or not token:
            raise RuntimeError("Falta waba_id o access_token")
        lang = language_code or (self._get_cfg_value("wa_template_language") or os.getenv("WHATSAPP_TEMPLATE_LANGUAGE") or "es_AR")
        return provision_standard_meta_templates(waba_id=waba_id, access_token=token, language_code=str(lang))

    def meta_health_check(self) -> Dict[str, Any]:
        row = self._get_active_config_row()
        if not row:
            return {"ok": False, "error": "WhatsApp no configurado"}

        phone_id = str(getattr(row, "phone_id", "") or "").strip()
        waba_id = str(getattr(row, "waba_id", "") or "").strip()
        token = self._decrypt_token_best_effort(str(getattr(row, "access_token", "") or ""))
        if not phone_id or not waba_id:
            return {"ok": False, "error": "Falta phone_id o waba_id", "phone_id": phone_id, "waba_id": waba_id}
        if not token:
            return {"ok": False, "error": "Falta access_token válido", "phone_id": phone_id, "waba_id": waba_id}

        api_version = self._api_version()
        timeout = self._timeout_seconds()
        headers = {"Authorization": f"Bearer {token}"}
        errors: list[str] = []
        phone_info: Dict[str, Any] = {}
        templates: Dict[str, Any] = {"count": 0, "approved": 0, "pending": 0, "rejected": 0}
        subscribed_apps: Dict[str, Any] = {"subscribed": None, "app_id": (os.getenv("META_APP_ID") or os.getenv("FACEBOOK_APP_ID") or "").strip()}

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
                app_id = subscribed_apps.get("app_id") or ""
                if app_id:
                    subscribed_apps["subscribed"] = any(str((x or {}).get("id") or "") == str(app_id) for x in (data.get("data") or []))
                else:
                    subscribed_apps["subscribed"] = None
        except Exception as e:
            errors.append(str(e))

        return {
            "ok": len(errors) == 0,
            "phone_id": phone_id,
            "waba_id": waba_id,
            "phone": phone_info,
            "templates": templates,
            "subscribed_apps": subscribed_apps,
            "errors": errors,
        }
