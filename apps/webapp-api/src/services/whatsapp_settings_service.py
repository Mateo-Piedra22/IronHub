from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, List

import logging
import os

import requests
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.database.tenant_connection import get_current_tenant
from src.secure_config import SecureConfig
from src.services.base import BaseService
from src.database.orm_models import WhatsappConfig, WhatsappMessage, Configuracion, Sucursal
from src.services.whatsapp_meta_provisioner import provision_standard_meta_templates

logger = logging.getLogger(__name__)


class WhatsAppSettingsService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)

    def _sync_tenant_whatsapp_to_admin_db(self, phone_id: str, waba_id: str) -> None:
        tenant = str(get_current_tenant() or "").strip().lower()
        if not tenant or not phone_id:
            return
        try:
            from src.database.raw_manager import RawPostgresManager

            admin_params = {
                "host": os.getenv("ADMIN_DB_HOST", os.getenv("DB_HOST", "localhost")),
                "port": int(os.getenv("ADMIN_DB_PORT", os.getenv("DB_PORT", 5432))),
                "database": os.getenv(
                    "ADMIN_DB_NAME", os.getenv("DB_NAME", "ironhub_admin")
                ),
                "user": os.getenv("ADMIN_DB_USER", os.getenv("DB_USER", "postgres")),
                "password": os.getenv(
                    "ADMIN_DB_PASSWORD", os.getenv("DB_PASSWORD", "")
                ),
                "sslmode": os.getenv(
                    "ADMIN_DB_SSLMODE", os.getenv("DB_SSLMODE", "require")
                ),
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

    def _admin_db_params(self) -> Dict[str, Any]:
        return {
            "host": os.getenv("ADMIN_DB_HOST", os.getenv("DB_HOST", "localhost")),
            "port": int(os.getenv("ADMIN_DB_PORT", os.getenv("DB_PORT", 5432))),
            "database": os.getenv(
                "ADMIN_DB_NAME", os.getenv("DB_NAME", "ironhub_admin")
            ),
            "user": os.getenv("ADMIN_DB_USER", os.getenv("DB_USER", "postgres")),
            "password": os.getenv("ADMIN_DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
            "sslmode": os.getenv(
                "ADMIN_DB_SSLMODE", os.getenv("DB_SSLMODE", "require")
            ),
            "connect_timeout": int(os.getenv("ADMIN_DB_CONNECT_TIMEOUT", "10")),
            "application_name": "webapp_whatsapp_onboarding",
        }

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

    def _fetch_admin_bindings(self) -> Dict[str, str]:
        try:
            from src.database.raw_manager import RawPostgresManager

            adm = RawPostgresManager(connection_params=self._admin_db_params())
            with adm.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT binding_key, template_name
                    FROM whatsapp_template_bindings
                    ORDER BY binding_key ASC
                    """
                )
                rows = cur.fetchall() or []
            out: Dict[str, str] = {}
            for r in rows:
                try:
                    k = str((r or [None, None])[0] or "").strip()
                    v = str((r or [None, None])[1] or "").strip()
                except Exception:
                    k, v = "", ""
                if k:
                    out[k] = v
            defaults = self._default_whatsapp_bindings()
            return {**defaults, **{k: v for k, v in out.items() if k}}
        except Exception:
            return self._default_whatsapp_bindings()

    def _log_admin_onboarding_event(
        self,
        event_type: str,
        severity: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        tenant = str(get_current_tenant() or "").strip().lower()
        if not tenant:
            return
        try:
            from src.database.raw_manager import RawPostgresManager
            import psycopg2.extras

            adm = RawPostgresManager(connection_params=self._admin_db_params())
            with adm.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO whatsapp_onboarding_events (subdominio, event_type, severity, message, details)
                    VALUES (%s,%s,%s,%s,%s)
                    """,
                    (
                        tenant,
                        str(event_type or "event"),
                        str(severity or "info"),
                        str(message or ""),
                        psycopg2.extras.Json(details or {})
                        if details is not None
                        else None,
                    ),
                )
                conn.commit()
        except Exception:
            return

    def _list_meta_templates_status_map(
        self, waba_id: str, access_token: str
    ) -> Dict[str, str]:
        api_version = self._api_version()
        url = f"https://graph.facebook.com/{api_version}/{waba_id}/message_templates"
        headers = {"Authorization": f"Bearer {access_token}"}
        after: Optional[str] = None
        out: Dict[str, str] = {}
        for _ in range(10):
            params: Dict[str, str] = {"fields": "name,status", "limit": "200"}
            if after:
                params["after"] = after
            resp = requests.get(
                url, headers=headers, params=params, timeout=self._timeout_seconds()
            )
            data = resp.json() if resp.content else {}
            if resp.status_code >= 400:
                raise RuntimeError(
                    str((data or {}).get("error") or data or f"HTTP {resp.status_code}")
                )
            for item in data.get("data") or []:
                n = str((item or {}).get("name") or "").strip()
                st = str((item or {}).get("status") or "").strip()
                if n:
                    out[n] = st
            cursors = (data.get("paging") or {}).get("cursors") or {}
            after = cursors.get("after")
            if not after:
                break
        return out

    def ensure_waba_subscribed_apps(self) -> Dict[str, Any]:
        row = self._get_active_config_row()
        if not row:
            return {"ok": False, "error": "WhatsApp no configurado"}
        waba_id = str(getattr(row, "waba_id", "") or "").strip()
        token = self._decrypt_token_best_effort(
            str(getattr(row, "access_token", "") or "")
        )
        if not waba_id or not token:
            return {"ok": False, "error": "Falta waba_id o access_token"}
        api_version = self._api_version()
        app_id = (
            os.getenv("META_APP_ID") or os.getenv("FACEBOOK_APP_ID") or ""
        ).strip()
        if not app_id:
            return {"ok": False, "error": "META_APP_ID no configurado"}
        headers = {"Authorization": f"Bearer {token}"}
        list_url = f"https://graph.facebook.com/{api_version}/{waba_id}/subscribed_apps"
        resp = requests.get(list_url, headers=headers, timeout=self._timeout_seconds())
        data = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            return {
                "ok": False,
                "error": str(
                    (data or {}).get("error") or data or f"HTTP {resp.status_code}"
                ),
            }
        subscribed = any(
            str((x or {}).get("id") or "") == str(app_id)
            for x in (data.get("data") or [])
        )
        if subscribed:
            return {
                "ok": True,
                "subscribed": True,
                "waba_id": waba_id,
                "app_id": app_id,
            }
        post_url = list_url
        resp2 = requests.post(
            post_url, headers=headers, json={}, timeout=self._timeout_seconds()
        )
        data2 = resp2.json() if resp2.content else {}
        if resp2.status_code >= 400:
            return {
                "ok": False,
                "error": str(
                    (data2 or {}).get("error") or data2 or f"HTTP {resp2.status_code}"
                ),
            }
        resp3 = requests.get(list_url, headers=headers, timeout=self._timeout_seconds())
        data3 = resp3.json() if resp3.content else {}
        if resp3.status_code >= 400:
            return {
                "ok": False,
                "error": str(
                    (data3 or {}).get("error") or data3 or f"HTTP {resp3.status_code}"
                ),
            }
        subscribed2 = any(
            str((x or {}).get("id") or "") == str(app_id)
            for x in (data3.get("data") or [])
        )
        return {
            "ok": True,
            "subscribed": bool(subscribed2),
            "waba_id": waba_id,
            "app_id": app_id,
        }

    def reconcile_onboarding(self) -> Dict[str, Any]:
        try:
            row = self._get_active_config_row()
            if not row:
                self._log_admin_onboarding_event(
                    "reconcile", "warning", "WhatsApp no configurado"
                )
                return {"ok": False, "error": "WhatsApp no configurado"}

            phone_id = str(getattr(row, "phone_id", "") or "").strip()
            waba_id = str(getattr(row, "waba_id", "") or "").strip()
            token = self._decrypt_token_best_effort(
                str(getattr(row, "access_token", "") or "")
            )
            if not phone_id or not waba_id or not token:
                self._log_admin_onboarding_event(
                    "reconcile",
                    "warning",
                    "Credenciales incompletas",
                    {
                        "phone_id": bool(phone_id),
                        "waba_id": bool(waba_id),
                        "token": bool(token),
                    },
                )
                return {"ok": False, "error": "Credenciales incompletas"}

            subscribe_res = self.ensure_waba_subscribed_apps()

            provision_res: Dict[str, Any] = {}
            try:
                provision_res = self.provision_meta_templates_for_current_config()
            except Exception as e:
                provision_res = {"ok": False, "error": str(e)}

            tmpl_status = {}
            try:
                tmpl_status = self._list_meta_templates_status_map(
                    waba_id=waba_id, access_token=token
                )
            except Exception as e:
                tmpl_status = {"__error__": str(e)}

            approved = {
                n
                for n, st in (tmpl_status or {}).items()
                if n and str(st).upper() == "APPROVED"
            }

            bindings = self._fetch_admin_bindings()
            core_enabled_default = {
                "marketing_promo": False,
                "marketing_new_class": False,
            }

            for k in (bindings or {}).keys():
                key = str(k or "").strip()
                if not key:
                    continue
                enabled_key = f"wa_action_enabled_{key}"
                if self._get_cfg_value(enabled_key) is None:
                    self._set_cfg_value(
                        enabled_key, "1" if core_enabled_default.get(key, True) else "0"
                    )

            alias_map: Dict[str, str] = {}
            try:
                rows = self.db.execute(
                    select(Configuracion.clave, Configuracion.valor).where(
                        Configuracion.clave.like("wa_template_alias_%")
                    )
                ).all()
                for c, v in rows:
                    ck = str(c or "")
                    if ck.startswith("wa_template_alias_"):
                        alias_map[ck.replace("wa_template_alias_", "", 1)] = str(
                            v or ""
                        )
            except Exception:
                alias_map = {}

            def resolve_alias(name: str) -> str:
                cur = str(name or "").strip()
                for _ in range(10):
                    nxt = str(alias_map.get(cur) or "").strip()
                    if not nxt or nxt == cur:
                        break
                    cur = nxt
                return cur

            def split_version(n: str) -> tuple[str, Optional[int]]:
                import re

                s = str(n or "").strip()
                m = re.match(r"^(?P<base>.+)_v(?P<v>\d+)$", s)
                if not m:
                    return (s, None)
                try:
                    return (m.group("base"), int(m.group("v")))
                except Exception:
                    return (m.group("base"), None)

            approved_versions: Dict[str, List[int]] = {}
            for n in approved:
                base, v = split_version(n)
                if v:
                    approved_versions.setdefault(base, []).append(int(v))

            def best_approved(name: str) -> str:
                cur = resolve_alias(name)
                if cur in approved:
                    return cur
                base, _v = split_version(cur)
                if base in approved_versions and approved_versions[base]:
                    best_v = max(int(x) for x in approved_versions[base])
                    cand = f"{base}_v{best_v}"
                    if cand in approved:
                        return cand
                return cur

            updated_templates = 0
            for k, desired in (bindings or {}).items():
                key = str(k or "").strip()
                if not key:
                    continue
                dest_key = f"wa_meta_template_{key}"
                current = str(self._get_cfg_value(dest_key) or "").strip()
                candidate = best_approved(str(desired or ""))
                if not candidate or candidate not in approved:
                    continue
                if current and current in approved:
                    continue
                if not current or current != candidate:
                    self._set_cfg_value(dest_key, candidate)
                    updated_templates += 1

            self.db.commit()

            tpl_counts = {"count": 0, "approved": 0, "pending": 0, "rejected": 0}
            if isinstance(tmpl_status, dict) and "__error__" not in tmpl_status:
                tpl_counts["count"] = int(len(tmpl_status))
                for st in tmpl_status.values():
                    s = str(st or "").upper()
                    if s == "APPROVED":
                        tpl_counts["approved"] += 1
                    elif s in ("PENDING", "IN_APPEAL"):
                        tpl_counts["pending"] += 1
                    elif s == "REJECTED":
                        tpl_counts["rejected"] += 1

            ok = bool(subscribe_res.get("ok")) and not (
                isinstance(tmpl_status, dict) and "__error__" in tmpl_status
            )
            self._log_admin_onboarding_event(
                "reconcile",
                "info" if ok else "warning",
                "Reconciliación ejecutada",
                {
                    "subscribed": subscribe_res.get("subscribed"),
                    "templates": tpl_counts,
                    "updated_templates": updated_templates,
                    "provision_ok": bool(provision_res.get("ok", True)),
                },
            )
            return {
                "ok": True,
                "subscribed_apps": subscribe_res,
                "provision": provision_res,
                "templates": tpl_counts,
                "updated_templates": updated_templates,
            }
        except Exception as e:
            try:
                self.db.rollback()
            except Exception:
                pass
            try:
                self._log_admin_onboarding_event(
                    "reconcile", "error", "Error en reconciliación", {"error": str(e)}
                )
            except Exception:
                pass
            return {"ok": False, "error": str(e)}

    def _now_utc_naive(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def _get_cfg_value(self, clave: str) -> Optional[str]:
        try:
            row = self.db.execute(
                select(Configuracion.valor).where(Configuracion.clave == clave).limit(1)
            ).first()
            return row[0] if row else None
        except Exception:
            return None

    def _set_cfg_value(self, clave: str, valor: Any) -> None:
        try:
            val_str = "" if valor is None else str(valor)
        except Exception:
            val_str = ""
        stmt = (
            insert(Configuracion)
            .values(clave=clave, valor=val_str)
            .on_conflict_do_update(
                index_elements=["clave"],
                set_={"valor": val_str},
            )
        )
        self.db.execute(stmt)

    def _get_active_config_row(self, sucursal_id: Optional[int] = None) -> Optional[WhatsappConfig]:
        try:
            sid: Optional[int] = None
            try:
                sid = int(sucursal_id) if sucursal_id is not None else None
            except Exception:
                sid = None
            if sid is not None and sid > 0:
                row = (
                    self.db.execute(
                        select(WhatsappConfig)
                        .join(Sucursal, Sucursal.id == WhatsappConfig.sucursal_id)
                        .where(
                            WhatsappConfig.active == True,
                            WhatsappConfig.sucursal_id == int(sid),
                            Sucursal.activa == True,
                        )
                        .order_by(WhatsappConfig.created_at.desc())
                        .limit(1)
                    )
                    .scalars()
                    .first()
                )
                if row is not None:
                    return row
            return (
                self.db.execute(
                    select(WhatsappConfig)
                    .where(WhatsappConfig.active == True)
                    .where(WhatsappConfig.sucursal_id.is_(None))
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
        v = (
            self._get_cfg_value("WHATSAPP_SEND_TIMEOUT_SECONDS")
            or os.getenv("WHATSAPP_SEND_TIMEOUT_SECONDS")
            or ""
        ).strip()
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
        return (
            os.getenv("META_GRAPH_API_VERSION")
            or os.getenv("WHATSAPP_API_VERSION")
            or "v19.0"
        ).strip()

    def get_ui_config(self, sucursal_id: Optional[int] = None) -> Dict[str, Any]:
        row = self._get_active_config_row(sucursal_id=sucursal_id)
        token_raw = getattr(row, "access_token", "") if row else ""
        enabled = str(
            self._get_cfg_value("wa_enabled") or self._get_cfg_value("enabled") or ""
        ).strip().lower() in ("1", "true", "yes", "on")
        webhook_enabled = str(
            self._get_cfg_value("wa_webhook_enabled")
            or self._get_cfg_value("webhook_enabled")
            or self._get_cfg_value("enable_webhook")
            or ""
        ).strip().lower() in ("1", "true", "yes", "on")
        return {
            "phone_number_id": getattr(row, "phone_id", "") if row else "",
            "whatsapp_business_account_id": getattr(row, "waba_id", "") if row else "",
            "access_token": "",
            "access_token_present": bool(token_raw),
            "webhook_verify_token": self._get_cfg_value("webhook_verify_token") or "",
            "enabled": bool(enabled),
            "webhook_enabled": bool(webhook_enabled),
        }

    def upsert_manual_config(self, payload: Dict[str, Any], sucursal_id: Optional[int] = None) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            return self.get_ui_config(sucursal_id=sucursal_id)

        try:
            phone_id = (
                str(
                    payload.get("phone_number_id") or payload.get("phone_id") or ""
                ).strip()
                or None
            )
            waba_id = (
                str(
                    payload.get("whatsapp_business_account_id")
                    or payload.get("waba_id")
                    or ""
                ).strip()
                or None
            )
            token_in = payload.get("access_token")
            token_raw = str(token_in or "").strip()
            if token_raw:
                SecureConfig.require_waba_encryption()
            token_enc = (
                SecureConfig.encrypt_waba_secret(token_raw) if token_raw else None
            )

            sid: Optional[int] = None
            try:
                sid = int(sucursal_id) if sucursal_id is not None else None
            except Exception:
                sid = None

            row: Optional[WhatsappConfig] = None
            if sid is not None and sid > 0:
                try:
                    row = (
                        self.db.execute(
                            select(WhatsappConfig)
                            .where(
                                WhatsappConfig.active == True,
                                WhatsappConfig.sucursal_id == int(sid),
                            )
                            .order_by(WhatsappConfig.created_at.desc())
                            .limit(1)
                        )
                        .scalars()
                        .first()
                    )
                except Exception:
                    row = None
            if row is None and (sid is None or sid <= 0):
                row = self._get_active_config_row(sucursal_id=None)
            if row is None:
                row = WhatsappConfig(
                    phone_id=phone_id or "",
                    waba_id=waba_id or "",
                    access_token=token_enc,
                    active=True,
                    sucursal_id=int(sid) if (sid is not None and sid > 0) else None,
                )
                self.db.add(row)
            else:
                if phone_id is not None:
                    row.phone_id = phone_id
                if waba_id is not None:
                    row.waba_id = waba_id
                if token_enc is not None:
                    row.access_token = token_enc
                try:
                    row.sucursal_id = int(sid) if (sid is not None and sid > 0) else None
                except Exception:
                    row.sucursal_id = None

            if "enabled" in payload:
                val = "1" if bool(payload.get("enabled")) else "0"
                self._set_cfg_value("wa_enabled", val)
                self._set_cfg_value("enabled", val)
            if "webhook_enabled" in payload:
                val = "1" if bool(payload.get("webhook_enabled")) else "0"
                self._set_cfg_value("wa_webhook_enabled", val)
                self._set_cfg_value("webhook_enabled", val)
            if "webhook_verify_token" in payload:
                self._set_cfg_value(
                    "webhook_verify_token",
                    str(payload.get("webhook_verify_token") or ""),
                )
            if "allowlist_numbers" in payload:
                self._set_cfg_value(
                    "allowlist_numbers", str(payload.get("allowlist_numbers") or "")
                )
            if "allowlist_enabled" in payload:
                self._set_cfg_value(
                    "allowlist_enabled",
                    "1" if bool(payload.get("allowlist_enabled")) else "0",
                )
            if "wa_template_language" in payload:
                self._set_cfg_value(
                    "wa_template_language",
                    str(payload.get("wa_template_language") or ""),
                )

            self.db.commit()
            try:
                self._sync_tenant_whatsapp_to_admin_db(
                    phone_id=str(phone_id or ""), waba_id=str(waba_id or "")
                )
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
            total = (
                self.db.execute(select(func.count(WhatsappMessage.id))).scalar() or 0
            )
            since_30 = self._now_utc_naive() - timedelta(days=30)
            ultimo_mes = (
                self.db.execute(
                    select(func.count(WhatsappMessage.id)).where(
                        WhatsappMessage.sent_at >= since_30
                    )
                ).scalar()
                or 0
            )
            by_type = dict(
                self.db.execute(
                    select(
                        WhatsappMessage.message_type, func.count(WhatsappMessage.id)
                    ).group_by(WhatsappMessage.message_type)
                ).all()
            )
            by_status = dict(
                self.db.execute(
                    select(
                        WhatsappMessage.status, func.count(WhatsappMessage.id)
                    ).group_by(WhatsappMessage.status)
                ).all()
            )
            return {
                "total": int(total),
                "ultimo_mes": int(ultimo_mes),
                "por_tipo": by_type,
                "por_estado": by_status,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_webhook_verify_token(self) -> str:
        return str(
            self._get_cfg_value("WHATSAPP_VERIFY_TOKEN")
            or self._get_cfg_value("webhook_verify_token")
            or ""
        )

    def exchange_code_for_access_token(
        self, code: str, redirect_uri: Optional[str] = None
    ) -> str:
        app_id = (
            os.getenv("META_APP_ID") or os.getenv("FACEBOOK_APP_ID") or ""
        ).strip()
        app_secret = (
            os.getenv("META_APP_SECRET") or os.getenv("FACEBOOK_APP_SECRET") or ""
        ).strip()
        if not app_id or not app_secret:
            raise RuntimeError("META_APP_ID/META_APP_SECRET no configurados")
        ruri = redirect_uri
        if ruri is None:
            ruri = os.getenv("META_OAUTH_REDIRECT_URI")
        if ruri is None:
            ruri = ""
        url = f"https://graph.facebook.com/{(os.getenv('META_GRAPH_API_VERSION') or 'v19.0').strip()}/oauth/access_token"
        resp = requests.get(
            url,
            params={
                "client_id": app_id,
                "client_secret": app_secret,
                "code": str(code),
                "redirect_uri": str(ruri),
            },
            timeout=25,
        )  # type: ignore[name-defined]
        data = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            raise RuntimeError(
                str(data.get("error") or data or f"HTTP {resp.status_code}")
            )
        token = str((data or {}).get("access_token") or "").strip()
        if not token:
            raise RuntimeError("No access_token devuelto por Meta")
        return token

    def set_credentials_from_embedded_signup(
        self, waba_id: str, phone_number_id: str, access_token: str
    ) -> None:
        waba = str(waba_id or "").strip()
        phone_id = str(phone_number_id or "").strip()
        token_raw = str(access_token or "").strip()
        if not waba or not phone_id or not token_raw:
            raise RuntimeError("Credenciales incompletas")

        SecureConfig.require_waba_encryption()
        token_enc = SecureConfig.encrypt_waba_secret(token_raw)

        row = self._get_active_config_row()
        if row is None:
            row = WhatsappConfig(
                phone_id=phone_id, waba_id=waba, access_token=token_enc, active=True
            )
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

    def provision_meta_templates_for_current_config(
        self, language_code: Optional[str] = None
    ) -> Dict[str, Any]:
        row = self._get_active_config_row()
        if not row:
            raise RuntimeError("WhatsApp no configurado")
        waba_id = str(getattr(row, "waba_id", "") or "").strip()
        token = self._decrypt_token_best_effort(
            str(getattr(row, "access_token", "") or "")
        )
        if not waba_id or not token:
            raise RuntimeError("Falta waba_id o access_token")
        lang = language_code or (
            self._get_cfg_value("wa_template_language")
            or os.getenv("WHATSAPP_TEMPLATE_LANGUAGE")
            or "es_AR"
        )
        return provision_standard_meta_templates(
            waba_id=waba_id, access_token=token, language_code=str(lang)
        )

    def meta_health_check(self) -> Dict[str, Any]:
        row = self._get_active_config_row()
        if not row:
            return {"ok": False, "error": "WhatsApp no configurado"}

        phone_id = str(getattr(row, "phone_id", "") or "").strip()
        waba_id = str(getattr(row, "waba_id", "") or "").strip()
        token = self._decrypt_token_best_effort(
            str(getattr(row, "access_token", "") or "")
        )
        if not phone_id or not waba_id:
            return {
                "ok": False,
                "error": "Falta phone_id o waba_id",
                "phone_id": phone_id,
                "waba_id": waba_id,
            }
        if not token:
            return {
                "ok": False,
                "error": "Falta access_token válido",
                "phone_id": phone_id,
                "waba_id": waba_id,
            }

        api_version = self._api_version()
        timeout = self._timeout_seconds()
        headers = {"Authorization": f"Bearer {token}"}
        errors: list[str] = []
        phone_info: Dict[str, Any] = {}
        templates: Dict[str, Any] = {
            "count": 0,
            "approved": 0,
            "pending": 0,
            "rejected": 0,
        }
        subscribed_apps: Dict[str, Any] = {
            "subscribed": None,
            "app_id": (
                os.getenv("META_APP_ID") or os.getenv("FACEBOOK_APP_ID") or ""
            ).strip(),
        }

        try:
            r = requests.get(
                f"https://graph.facebook.com/{api_version}/{phone_id}",
                headers=headers,
                params={
                    "fields": "id,display_phone_number,verified_name,quality_rating,platform_type,code_verification_status"
                },
                timeout=timeout,
            )
            data = r.json() if r.content else {}
            if r.status_code >= 400:
                errors.append(
                    str((data or {}).get("error") or data or f"HTTP {r.status_code}")
                )
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
                errors.append(
                    str((data or {}).get("error") or data or f"HTTP {r.status_code}")
                )
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
                errors.append(
                    str((data or {}).get("error") or data or f"HTTP {r.status_code}")
                )
            else:
                app_id = subscribed_apps.get("app_id") or ""
                if app_id:
                    subscribed_apps["subscribed"] = any(
                        str((x or {}).get("id") or "") == str(app_id)
                        for x in (data.get("data") or [])
                    )
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
