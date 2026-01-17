from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import logging
import os
import re
from typing import Any, Dict, Optional

import requests
from sqlalchemy import select, text, insert
from sqlalchemy.orm import Session

from src.database.orm_models import Usuario, Pago, WhatsappConfig, WhatsappMessage, WhatsappTemplate, Configuracion
from src.services.base import BaseService
from src.secure_config import SecureConfig

logger = logging.getLogger(__name__)


@dataclass
class WhatsAppSendResult:
    ok: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class WhatsAppDispatchService(BaseService):
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
                CREATE TABLE IF NOT EXISTS whatsapp_messages (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER,
                    message_type VARCHAR(50) NOT NULL,
                    template_name VARCHAR(255) NOT NULL,
                    phone_number VARCHAR(50) NOT NULL,
                    message_id VARCHAR(100) UNIQUE,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'sent',
                    message_content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            self.db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_user_id ON whatsapp_messages(user_id)
            """))
            self.db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_phone ON whatsapp_messages(phone_number)
            """))
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS whatsapp_templates (
                    id SERIAL PRIMARY KEY,
                    template_name VARCHAR(255) UNIQUE NOT NULL,
                    header_text VARCHAR(60),
                    body_text TEXT NOT NULL,
                    variables JSONB,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            self.db.commit()
        except Exception:
            try:
                self.db.rollback()
            except Exception:
                pass

    def _now_utc_naive(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def _normalize_phone(self, phone: str) -> str:
        return re.sub(r"\D+", "", str(phone or ""))

    def _get_cfg_value(self, clave: str) -> Optional[str]:
        try:
            row = self.db.execute(select(Configuracion.valor).where(Configuracion.clave == clave).limit(1)).first()
            return row[0] if row else None
        except Exception:
            return None

    def _is_enabled(self) -> bool:
        v = self._get_cfg_value("enabled")
        try:
            return str(v or "").strip().lower() in ("1", "true", "yes", "on")
        except Exception:
            return False

    def send_waitlist_confirmed(self, usuario_id: int, tipo_clase: str, dia: str, hora: str) -> bool:
        if not self._is_action_enabled("waitlist_confirmed", True):
            return True
        u = self.db.get(Usuario, int(usuario_id))
        if not u or not getattr(u, "telefono", None):
            return False
        vars = {
            "name": str(getattr(u, "nombre", "") or ""),
            "class": str(tipo_clase or "la clase"),
            "day": str(dia or ""),
            "time": str(hora or ""),
        }
        tpl = self._get_meta_template_binding("waitlist_confirmed", "ih_waitlist_confirmed_v1")
        r = self.send_template_positional(int(usuario_id), str(u.telefono), tpl, [vars["name"], vars["class"], vars["day"], vars["time"]], "waitlist_confirmed")
        if r.ok:
            return True
        return False

    def send_membership_due_today(self, usuario_id: int, fecha: str) -> bool:
        if not self._is_action_enabled("membership_due_today", True):
            return True
        u = self.db.get(Usuario, int(usuario_id))
        if not u or not getattr(u, "telefono", None):
            return False
        name = str(getattr(u, "nombre", "") or "")
        tpl = self._get_meta_template_binding("membership_due_today", "ih_membership_due_today_v1")
        r = self.send_template_positional(int(usuario_id), str(u.telefono), tpl, [name, str(fecha or "")], "membership_due_today")
        return bool(r.ok)

    def send_membership_due_soon(self, usuario_id: int, fecha: str) -> bool:
        if not self._is_action_enabled("membership_due_soon", True):
            return True
        u = self.db.get(Usuario, int(usuario_id))
        if not u or not getattr(u, "telefono", None):
            return False
        name = str(getattr(u, "nombre", "") or "")
        tpl = self._get_meta_template_binding("membership_due_soon", "ih_membership_due_soon_v1")
        r = self.send_template_positional(int(usuario_id), str(u.telefono), tpl, [name, str(fecha or "")], "membership_due_soon")
        return bool(r.ok)

    def send_membership_reactivated(self, usuario_id: int) -> bool:
        if not self._is_action_enabled("membership_reactivated", True):
            return True
        u = self.db.get(Usuario, int(usuario_id))
        if not u or not getattr(u, "telefono", None):
            return False
        name = str(getattr(u, "nombre", "") or "")
        tpl = self._get_meta_template_binding("membership_reactivated", "ih_membership_reactivated_v1")
        r = self.send_template_positional(int(usuario_id), str(u.telefono), tpl, [name], "membership_reactivated")
        return bool(r.ok)

    def send_class_booking_confirmed(self, usuario_id: int, tipo_clase: str, fecha: str, hora: str) -> bool:
        if not self._is_action_enabled("class_booking_confirmed", True):
            return True
        u = self.db.get(Usuario, int(usuario_id))
        if not u or not getattr(u, "telefono", None):
            return False
        tpl = self._get_meta_template_binding("class_booking_confirmed", "ih_class_booking_confirmed_v1")
        r = self.send_template_positional(int(usuario_id), str(u.telefono), tpl, [str(tipo_clase or "clase"), str(fecha or ""), str(hora or "")], "class_booking_confirmed")
        return bool(r.ok)

    def send_class_booking_cancelled(self, usuario_id: int, tipo_clase: str) -> bool:
        if not self._is_action_enabled("class_booking_cancelled", True):
            return True
        u = self.db.get(Usuario, int(usuario_id))
        if not u or not getattr(u, "telefono", None):
            return False
        tpl = self._get_meta_template_binding("class_booking_cancelled", "ih_class_booking_cancelled_v1")
        r = self.send_template_positional(int(usuario_id), str(u.telefono), tpl, [str(tipo_clase or "clase")], "class_booking_cancelled")
        return bool(r.ok)

    def send_schedule_change(self, usuario_id: int, tipo_clase: str, dia: str, hora: str) -> bool:
        if not self._is_action_enabled("schedule_change", True):
            return True
        u = self.db.get(Usuario, int(usuario_id))
        if not u or not getattr(u, "telefono", None):
            return False
        tpl = self._get_meta_template_binding("schedule_change", "ih_schedule_change_v1")
        r = self.send_template_positional(int(usuario_id), str(u.telefono), tpl, [str(tipo_clase or "clase"), str(dia or ""), str(hora or "")], "schedule_change")
        return bool(r.ok)

    def send_marketing_promo(self, usuario_id: int, promo: str) -> bool:
        if not self._is_action_enabled("marketing_promo", False):
            return True
        u = self.db.get(Usuario, int(usuario_id))
        if not u or not getattr(u, "telefono", None):
            return False
        name = str(getattr(u, "nombre", "") or "")
        tpl = self._get_meta_template_binding("marketing_promo", "ih_marketing_promo_v1")
        r = self.send_template_positional(int(usuario_id), str(u.telefono), tpl, [name, str(promo or "")], "marketing_promo")
        return bool(r.ok)

    def send_marketing_new_class(self, usuario_id: int, clase: str, dia: str, hora: str) -> bool:
        if not self._is_action_enabled("marketing_new_class", False):
            return True
        u = self.db.get(Usuario, int(usuario_id))
        if not u or not getattr(u, "telefono", None):
            return False
        tpl = self._get_meta_template_binding("marketing_new_class", "ih_marketing_new_class_v1")
        r = self.send_template_positional(int(usuario_id), str(u.telefono), tpl, [str(clase or "clase"), str(dia or ""), str(hora or "")], "marketing_new_class")
        return bool(r.ok)

    def _allowlist_ok(self, phone: str) -> bool:
        try:
            enabled = str(self._get_cfg_value("allowlist_enabled") or "").strip().lower() in ("1", "true", "yes", "on")
        except Exception:
            enabled = False
        if not enabled:
            return True
        raw = str(self._get_cfg_value("allowlist_numbers") or "").strip()
        allowed = [self._normalize_phone(x) for x in raw.split(",") if x.strip()]
        ph = self._normalize_phone(phone)
        if not ph:
            return False
        return ph in set(a for a in allowed if a)

    def _is_action_enabled(self, action_key: str, default_enabled: bool = True) -> bool:
        v = self._get_cfg_value(f"wa_action_enabled_{str(action_key or '').strip()}")
        if v is None:
            return bool(default_enabled)
        try:
            return str(v or "").strip().lower() in ("1", "true", "yes", "on")
        except Exception:
            return bool(default_enabled)

    def _get_active_whatsapp_config(self) -> Optional[WhatsappConfig]:
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

    def _get_language_code(self) -> str:
        v = self._get_cfg_value("wa_template_language") or os.getenv("WHATSAPP_TEMPLATE_LANGUAGE") or "es_AR"
        try:
            return str(v).strip() or "es_AR"
        except Exception:
            return "es_AR"

    def _get_meta_template_binding(self, binding_key: str, default_template: str) -> str:
        key = f"wa_meta_template_{str(binding_key or '').strip()}"
        v = self._get_cfg_value(key)
        try:
            vv = str(v or "").strip()
        except Exception:
            vv = ""
        return vv or str(default_template or "")

    def _graph_post(self, phone_id: str, access_token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        api_version = (os.getenv("WHATSAPP_API_VERSION") or "v19.0").strip()
        url = f"https://graph.facebook.com/{api_version}/{phone_id}/messages"
        try:
            timeout_seconds = float(os.getenv("WHATSAPP_SEND_TIMEOUT_SECONDS", "8.0") or 8.0)
        except Exception:
            timeout_seconds = 8.0
        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout_seconds,
        )
        try:
            data = resp.json() if resp.content else {}
        except Exception:
            data = {}
        if resp.status_code >= 400:
            raise RuntimeError(str(data.get("error") or data or f"HTTP {resp.status_code}"))
        return data if isinstance(data, dict) else {}

    def _log_outgoing(self, user_id: Optional[int], phone: str, message_type: str, body: str, status: str, message_id: Optional[str]) -> None:
        try:
            sent_at = self._now_utc_naive()
            row = WhatsappMessage(
                user_id=int(user_id) if user_id is not None else None,
                message_type=str(message_type or "custom"),
                template_name=str(message_type or "custom"),
                phone_number=self._normalize_phone(phone),
                message_id=message_id,
                sent_at=sent_at,
                status=str(status or ""),
                message_content=str(body or ""),
            )
            self.db.add(row)
            self.db.commit()
        except Exception:
            try:
                self.db.rollback()
            except Exception:
                pass

    def _safe_format(self, s: str, vars: Dict[str, Any]) -> str:
        class _Default(dict):
            def __missing__(self, key):
                return ""
        try:
            return str(s or "").format_map(_Default({k: "" if v is None else v for k, v in (vars or {}).items()}))
        except Exception:
            return str(s or "")

    def _render_template(self, template_name: str, vars: Dict[str, Any]) -> Optional[str]:
        try:
            tpl = (
                self.db.execute(
                    select(WhatsappTemplate)
                    .where(WhatsappTemplate.template_name == template_name, WhatsappTemplate.active == True)
                    .limit(1)
                )
                .scalars()
                .first()
            )
            if not tpl:
                return None
            return self._safe_format(getattr(tpl, "body_text", "") or "", vars)
        except Exception:
            return None

    def send_text(self, user_id: Optional[int], phone: str, body: str, message_type: str) -> WhatsAppSendResult:
        cfg = self._get_active_whatsapp_config()
        phone_id = str(getattr(cfg, "phone_id", "") or "").strip() if cfg else ""
        access_token = self._decrypt_token_best_effort(str(getattr(cfg, "access_token", "") or "")) if cfg else ""

        if not self._is_enabled():
            self._log_outgoing(user_id, phone, message_type, body, "failed", None)
            return WhatsAppSendResult(ok=False, error="disabled")
        if not phone_id or not access_token:
            self._log_outgoing(user_id, phone, message_type, body, "failed", None)
            return WhatsAppSendResult(ok=False, error="missing_config")
        if not self._allowlist_ok(phone):
            self._log_outgoing(user_id, phone, message_type, body, "failed", None)
            return WhatsAppSendResult(ok=False, error="allowlist_blocked")

        to = self._normalize_phone(phone)
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": str(body or "")},
        }
        try:
            res = self._graph_post(phone_id, access_token, payload)
            mid = None
            try:
                msgs = res.get("messages") or []
                if msgs and isinstance(msgs, list):
                    mid = (msgs[0] or {}).get("id")
            except Exception:
                mid = None
            self._log_outgoing(user_id, phone, message_type, body, "sent", mid)
            return WhatsAppSendResult(ok=True, message_id=mid)
        except Exception as e:
            self._log_outgoing(user_id, phone, message_type, body, "failed", None)
            logger.error(f"WhatsApp send failed: {e}")
            return WhatsAppSendResult(ok=False, error=str(e))

    def send_template_positional(self, user_id: Optional[int], phone: str, template_name: str, body_params: list[str], message_type: str) -> WhatsAppSendResult:
        cfg = self._get_active_whatsapp_config()
        phone_id = str(getattr(cfg, "phone_id", "") or "").strip() if cfg else ""
        access_token = self._decrypt_token_best_effort(str(getattr(cfg, "access_token", "") or "")) if cfg else ""

        if not self._is_enabled():
            self._log_outgoing(user_id, phone, message_type, f"[template:{template_name}] {body_params}", "failed", None)
            return WhatsAppSendResult(ok=False, error="disabled")
        if not phone_id or not access_token:
            self._log_outgoing(user_id, phone, message_type, f"[template:{template_name}] {body_params}", "failed", None)
            return WhatsAppSendResult(ok=False, error="missing_config")
        if not self._allowlist_ok(phone):
            self._log_outgoing(user_id, phone, message_type, f"[template:{template_name}] {body_params}", "failed", None)
            return WhatsAppSendResult(ok=False, error="allowlist_blocked")

        to = self._normalize_phone(phone)
        lang = self._get_language_code()
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": str(template_name),
                "language": {"code": str(lang)},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": str(p)} for p in (body_params or [])],
                    }
                ],
            },
        }
        try:
            res = self._graph_post(phone_id, access_token, payload)
            mid = None
            try:
                msgs = res.get("messages") or []
                if msgs and isinstance(msgs, list):
                    mid = (msgs[0] or {}).get("id")
            except Exception:
                mid = None
            self._log_outgoing(user_id, phone, message_type, f"[template:{template_name}] {body_params}", "sent", mid)
            return WhatsAppSendResult(ok=True, message_id=mid)
        except Exception as e:
            self._log_outgoing(user_id, phone, message_type, f"[template:{template_name}] {body_params}", "failed", None)
            return WhatsAppSendResult(ok=False, error=str(e))

    def send_welcome(self, usuario_id: int) -> bool:
        u = self.db.get(Usuario, int(usuario_id))
        if not self._is_action_enabled("welcome", True):
            return True
        if not u or not getattr(u, "telefono", None):
            return False
        name = str(getattr(u, "nombre", "") or "")
        tpl = self._get_meta_template_binding("welcome", "ih_welcome_v1")
        r = self.send_template_positional(int(usuario_id), str(u.telefono), tpl, [name], "welcome")
        if r.ok:
            return True
        body = self._render_template("welcome", {"name": name}) or f"Hola {name}! Bienvenido/a."
        return self.send_text(int(usuario_id), str(u.telefono), body, "welcome").ok

    def send_payment_confirmation(self, usuario_id: int, monto: Optional[float] = None, mes: Optional[int] = None, anio: Optional[int] = None) -> bool:
        u = self.db.get(Usuario, int(usuario_id))
        if not self._is_action_enabled("payment", True):
            return True
        if not u or not getattr(u, "telefono", None):
            return False
        if monto is None or mes is None or anio is None:
            p = (
                self.db.execute(
                    select(Pago)
                    .where(Pago.usuario_id == int(usuario_id))
                    .order_by(Pago.fecha_pago.desc())
                    .limit(1)
                )
                .scalars()
                .first()
            )
            if p:
                try:
                    monto = float(monto if monto is not None else (getattr(p, "monto", 0) or 0))
                except Exception:
                    monto = 0.0
                try:
                    mes = int(mes if mes is not None else (getattr(p, "mes", 0) or 0))
                except Exception:
                    mes = 0
                try:
                    anio = int(anio if anio is not None else (getattr(p, "año", 0) or 0))
                except Exception:
                    anio = 0
        if monto is None or mes is None or anio is None:
            return False
        vars = {
            "name": str(getattr(u, "nombre", "") or ""),
            "amount": f"{float(monto):.2f}",
            "period": f"{int(mes):02d}/{int(anio)}",
        }
        tpl = self._get_meta_template_binding("payment", "ih_payment_confirmed_v1")
        r = self.send_template_positional(int(usuario_id), str(u.telefono), tpl, [vars["name"], vars["amount"], vars["period"]], "payment")
        if r.ok:
            return True
        body = self._render_template("payment", vars) or f"Hola {vars['name']}! Confirmamos tu pago de ${vars['amount']} correspondiente a {vars['period']}. Gracias."
        return self.send_text(int(usuario_id), str(u.telefono), body, "payment").ok

    def send_overdue_reminder(self, usuario_id: int) -> bool:
        u = self.db.get(Usuario, int(usuario_id))
        if not self._is_action_enabled("overdue", True):
            return True
        if not u or not getattr(u, "telefono", None):
            return False
        vars = {"name": str(getattr(u, "nombre", "") or "")}
        tpl = self._get_meta_template_binding("overdue", "ih_membership_overdue_v1")
        r = self.send_template_positional(int(usuario_id), str(u.telefono), tpl, [vars["name"]], "overdue")
        if r.ok:
            return True
        body = self._render_template("overdue", vars) or f"Hola {vars['name']}. Te recordamos que tu cuota se encuentra vencida. Si ya abonaste, por favor ignora este mensaje."
        return self.send_text(int(usuario_id), str(u.telefono), body, "overdue").ok

    def send_deactivation(self, usuario_id: int, motivo: str) -> bool:
        u = self.db.get(Usuario, int(usuario_id))
        if not self._is_action_enabled("deactivation", True):
            return True
        if not u or not getattr(u, "telefono", None):
            return False
        vars = {"name": str(getattr(u, "nombre", "") or ""), "reason": str(motivo or "cuotas vencidas")}
        tpl = self._get_meta_template_binding("deactivation", "ih_membership_deactivated_v1")
        r = self.send_template_positional(int(usuario_id), str(u.telefono), tpl, [vars["name"], vars["reason"]], "deactivation")
        if r.ok:
            return True
        body = self._render_template("deactivation", vars) or f"Hola {vars['name']}. Tu acceso fue desactivado. Motivo: {vars['reason']}."
        return self.send_text(int(usuario_id), str(u.telefono), body, "deactivation").ok

    def send_class_reminder(self, usuario_id: int, tipo_clase: str, fecha: str, hora: str) -> bool:
        u = self.db.get(Usuario, int(usuario_id))
        if not self._is_action_enabled("class_reminder", True):
            return True
        if not u or not getattr(u, "telefono", None):
            return False
        vars = {
            "name": str(getattr(u, "nombre", "") or ""),
            "class": str(tipo_clase or "clase"),
            "date": str(fecha or ""),
            "time": str(hora or ""),
        }
        tpl = self._get_meta_template_binding("class_reminder", "ih_class_reminder_v1")
        r = self.send_template_positional(int(usuario_id), str(u.telefono), tpl, [vars["name"], vars["class"], vars["date"], vars["time"]], "class_reminder")
        if r.ok:
            return True
        body = self._render_template("class_reminder", vars) or f"Hola {vars['name']}! Recordatorio: {vars['class']} el {vars['date']} a las {vars['time']}."
        return self.send_text(int(usuario_id), str(u.telefono), body, "class_reminder").ok

    def send_waitlist_promotion(self, usuario_id: int, tipo_clase: str, dia: str, hora: str) -> bool:
        u = self.db.get(Usuario, int(usuario_id))
        if not self._is_action_enabled("waitlist", True):
            return True
        if not u or not getattr(u, "telefono", None):
            return False
        vars = {
            "name": str(getattr(u, "nombre", "") or ""),
            "class": str(tipo_clase or "la clase"),
            "day": str(dia or ""),
            "time": str(hora or ""),
        }
        tpl = self._get_meta_template_binding("waitlist", "ih_waitlist_spot_available_v1")
        r = self.send_template_positional(int(usuario_id), str(u.telefono), tpl, [vars["name"], vars["class"], vars["day"], vars["time"]], "waitlist")
        if r.ok:
            return True
        body = self._render_template("waitlist", vars) or f"Hola {vars['name']}! Se liberó un cupo para {vars['class']}. Día: {vars['day']} {vars['time']}."
        return self.send_text(int(usuario_id), str(u.telefono), body, "waitlist").ok
