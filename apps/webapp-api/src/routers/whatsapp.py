"""WhatsApp Router - WhatsApp messaging API (tenant-scoped)."""
import logging
import os
import json
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Request, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, select

from src.dependencies import (
    require_gestion_access, require_owner, 
    get_whatsapp_service, get_whatsapp_dispatch_service, get_whatsapp_settings_service, get_db_session
)
from src.services.whatsapp_service import WhatsAppService
from src.services.whatsapp_dispatch_service import WhatsAppDispatchService
from src.services.whatsapp_settings_service import WhatsAppSettingsService
from src.models.orm_models import Configuracion
from src.database.tenant_connection import validate_tenant_name, set_current_tenant, tenant_session_scope

router = APIRouter()
logger = logging.getLogger(__name__)


def _ensure_triggers_table(db: Session) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS whatsapp_triggers (
            id SERIAL PRIMARY KEY,
            trigger_key VARCHAR(80) UNIQUE NOT NULL,
            enabled BOOLEAN DEFAULT FALSE,
            template_name VARCHAR(255),
            cooldown_minutes INTEGER DEFAULT 1440,
            last_run_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    db.commit()


def _ensure_templates_table(db: Session) -> None:
    db.execute(text("""
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
    db.commit()


def _is_owner_role(role: str) -> bool:
    r = (role or "").lower()
    return r in ("dueño", "dueno", "owner", "admin", "administrador")


def _redact_whatsapp_state_for_role(request: Request, state: Dict[str, Any]) -> Dict[str, Any]:
    """Redact sensitive fields (like access_token) for non-owner roles."""
    try:
        role = str(request.session.get("role") or "")
        if _is_owner_role(role):
            return state

        cfg = state.get("config")
        if isinstance(cfg, dict) and "access_token" in cfg:
            cfg = dict(cfg)
            cfg["access_token"] = ""
            state = dict(state)
            state["config"] = cfg
        return state
    except Exception:
        return state


@router.get("/api/whatsapp/state")
async def api_whatsapp_state(
    request: Request,
    _=Depends(require_gestion_access),
    st: WhatsAppSettingsService = Depends(get_whatsapp_settings_service)
):
    try:
        state = st.get_state()
        available = bool(state.get('disponible'))
        config_valid = bool(state.get('configuracion_valida'))
        enabled = bool(state.get('habilitado') and config_valid)
        server_ok = bool(state.get('servidor_activo'))
        payload = {
            'available': available,
            'enabled': enabled,
            'server_ok': server_ok,
            'config_valid': config_valid,
        }
        return {"ok": True, "mensaje": "OK", "success": True, "message": "OK", **payload}
    except Exception as e:
        return JSONResponse(
            {"ok": False, "mensaje": str(e), "success": False, "message": str(e), "error": str(e)},
            status_code=500,
        )


@router.get("/api/whatsapp/stats")
async def api_whatsapp_stats(
    _=Depends(require_owner),
    st: WhatsAppSettingsService = Depends(get_whatsapp_settings_service)
):
    try:
        data = st.get_stats()
        if isinstance(data, dict) and "ok" not in data:
            ok_val = "error" not in data
            msg = "OK" if ok_val else str(data.get("error") or "Error")
            data = {"ok": ok_val, "mensaje": msg, "success": ok_val, "message": msg, **data}
        return data
    except Exception as e:
        return JSONResponse(
            {"ok": False, "mensaje": str(e), "success": False, "message": str(e), "error": str(e)},
            status_code=500,
        )


@router.get("/api/whatsapp/pendings")
async def api_whatsapp_pendings(
    request: Request,
    _=Depends(require_owner),
    svc: WhatsAppService = Depends(get_whatsapp_service)
):
    try:
        dias = int(request.query_params.get("dias") or 30)
        limite = int(request.query_params.get("limit") or 200)
    except:
        dias, limite = 30, 200
    return {"items": svc.obtener_mensajes_fallidos(dias, limite)}


# === Frontend-compatible alias endpoints ===

@router.get("/api/whatsapp/pendientes")
async def api_whatsapp_pendientes(
    request: Request,
    _=Depends(require_owner),
    svc: WhatsAppService = Depends(get_whatsapp_service)
):
    """Alias for /api/whatsapp/pendings - returns {mensajes: []}."""
    try:
        dias = int(request.query_params.get("dias") or 30)
        limite = int(request.query_params.get("limit") or 300)
    except Exception:
        dias, limite = 30, 300
    items = svc.obtener_resumen_mensajes(dias, limite)

    def map_tipo(t: str) -> str:
        s = (t or '').strip().lower()
        if s in ('bienvenida', 'welcome'):
            return 'welcome'
        if s in ('pago', 'payment', 'payment_confirmation'):
            return 'payment'
        if s in ('desactivacion', 'deactivation'):
            return 'deactivation'
        if s in ('overdue', 'recordatorio_vencida', 'payment_reminder'):
            return 'overdue'
        if s in ('class_reminder', 'recordatorio_clase'):
            return 'class_reminder'
        if s in ('waitlist', 'lista_espera'):
            return 'class_reminder'
        return s or 'welcome'

    def map_estado(st: str) -> str:
        s = (st or '').strip().lower()
        if s == 'failed':
            return 'failed'
        if s in ('sent', 'delivered', 'read'):
            return 'sent'
        if s == 'received':
            return 'sent'
        return 'pending'

    mensajes = []
    for m in items:
        mensajes.append({
            'id': m.get('id'),
            'usuario_id': m.get('user_id') or 0,
            'usuario_nombre': m.get('usuario_nombre') or '',
            'telefono': m.get('usuario_telefono') or m.get('phone_number') or '',
            'tipo': map_tipo(m.get('message_type') or ''),
            'estado': map_estado(m.get('status') or ''),
            'contenido': m.get('message_content') or '',
            'error_detail': None,
            'fecha_envio': m.get('sent_at'),
            'created_at': m.get('created_at'),
        })
    return {"mensajes": mensajes}


@router.get("/api/whatsapp/status")
async def api_whatsapp_status(
    request: Request,
    _=Depends(require_gestion_access),
    st: WhatsAppSettingsService = Depends(get_whatsapp_settings_service)
):
    """Alias for /api/whatsapp/state."""
    try:
        return await api_whatsapp_state(request, st=st)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/whatsapp/config")
async def api_whatsapp_config_get(
    _=Depends(require_owner),
    st: WhatsAppSettingsService = Depends(get_whatsapp_settings_service)
):
    """GET endpoint for WhatsApp config."""
    try:
        cfg = st.get_ui_config()
        return {"ok": True, "mensaje": "OK", "success": True, "message": "OK", **cfg}
    except Exception as e:
        return JSONResponse(
            {"ok": False, "mensaje": str(e), "success": False, "message": str(e), "error": str(e)},
            status_code=500,
        )


@router.put("/api/whatsapp/config")
async def api_whatsapp_config_put(
    request: Request,
    _=Depends(require_owner),
    st: WhatsAppSettingsService = Depends(get_whatsapp_settings_service)
):
    try:
        try:
            payload = await request.json()
        except Exception:
            payload = {}

        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Payload inválido")

        cfg_in: Dict[str, Any] = {}
        if 'phone_number_id' in payload:
            cfg_in['phone_number_id'] = payload.get('phone_number_id')
        if 'whatsapp_business_account_id' in payload:
            cfg_in['whatsapp_business_account_id'] = payload.get('whatsapp_business_account_id')
        if 'waba_id' in payload and 'whatsapp_business_account_id' not in payload:
            cfg_in['whatsapp_business_account_id'] = payload.get('waba_id')
        if 'access_token' in payload:
            cfg_in['access_token'] = payload.get('access_token')
        if 'enabled' in payload:
            cfg_in['enabled'] = bool(payload.get('enabled'))
        if 'webhook_enabled' in payload:
            cfg_in['webhook_enabled'] = bool(payload.get('webhook_enabled'))
        if 'webhook_verify_token' in payload:
            cfg_in['webhook_verify_token'] = str(payload.get('webhook_verify_token') or '')

        _ = st.upsert_manual_config(cfg_in)
        return await api_whatsapp_config_get(st=st)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            {"ok": False, "mensaje": str(e), "success": False, "message": str(e), "error": str(e)},
            status_code=500,
        )


@router.get("/api/whatsapp/embedded-signup/config")
async def api_whatsapp_embedded_signup_config(
    _=Depends(require_owner),
):
    app_id = (os.getenv("META_APP_ID") or os.getenv("FACEBOOK_APP_ID") or "").strip()
    config_id = (os.getenv("META_WA_EMBEDDED_SIGNUP_CONFIG_ID") or "").strip()
    api_version = (os.getenv("META_GRAPH_API_VERSION") or os.getenv("WHATSAPP_API_VERSION") or "v19.0").strip()
    if not app_id or not config_id:
        return JSONResponse(
            {"ok": False, "mensaje": "Falta configuración", "success": False, "message": "Falta configuración", "error": "Missing config"},
            status_code=503,
        )
    return {"ok": True, "mensaje": "OK", "success": True, "message": "OK", "app_id": app_id, "config_id": config_id, "api_version": api_version}


@router.get("/api/whatsapp/embedded-signup/readiness")
async def api_whatsapp_embedded_signup_readiness(
    _=Depends(require_owner),
):
    app_id = (os.getenv("META_APP_ID") or os.getenv("FACEBOOK_APP_ID") or "").strip()
    app_secret = (os.getenv("META_APP_SECRET") or os.getenv("FACEBOOK_APP_SECRET") or "").strip()
    config_id = (os.getenv("META_WA_EMBEDDED_SIGNUP_CONFIG_ID") or "").strip()
    api_version = (os.getenv("META_GRAPH_API_VERSION") or os.getenv("WHATSAPP_API_VERSION") or "v19.0").strip()
    redirect_uri = (os.getenv("META_OAUTH_REDIRECT_URI") or "").strip()
    enc_key = (os.getenv("WABA_ENCRYPTION_KEY") or "").strip()

    missing = []
    if not app_id:
        missing.append("META_APP_ID")
    if not app_secret:
        missing.append("META_APP_SECRET")
    if not config_id:
        missing.append("META_WA_EMBEDDED_SIGNUP_CONFIG_ID")
    if not enc_key:
        missing.append("WABA_ENCRYPTION_KEY")

    return {
        "ok": len(missing) == 0,
        "app_id_present": bool(app_id),
        "app_secret_present": bool(app_secret),
        "config_id_present": bool(config_id),
        "api_version": api_version,
        "redirect_uri": redirect_uri,
        "waba_encryption_key_present": bool(enc_key),
        "missing": missing,
        "recommended_urls": {
            "privacy_policy": "https://ironhub.motiona.xyz/privacy",
            "terms": "https://ironhub.motiona.xyz/terms",
            "data_deletion_instructions": "https://ironhub.motiona.xyz/data-deletion",
            "data_deletion_callback": "https://ironhub.motiona.xyz/api/meta/data-deletion",
        },
    }


@router.post("/api/whatsapp/embedded-signup/complete")
async def api_whatsapp_embedded_signup_complete(
    request: Request,
    _=Depends(require_owner),
    st: WhatsAppSettingsService = Depends(get_whatsapp_settings_service),
):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    code = str((payload or {}).get("code") or "").strip()
    waba_id = str((payload or {}).get("waba_id") or "").strip()
    phone_number_id = str((payload or {}).get("phone_number_id") or "").strip()
    if not code or not waba_id or not phone_number_id:
        raise HTTPException(status_code=400, detail="code/waba_id/phone_number_id requeridos")
    access_token = st.exchange_code_for_access_token(code)
    st.set_credentials_from_embedded_signup(waba_id=waba_id, phone_number_id=phone_number_id, access_token=access_token)
    provision = st.provision_meta_templates_for_current_config()
    health = st.meta_health_check()
    return {"ok": True, "mensaje": "OK", "success": True, "message": "OK", "provision": provision, "health": health}

@router.get("/api/whatsapp/onboarding/status")
async def api_whatsapp_onboarding_status(
    _=Depends(require_owner),
    st: WhatsAppSettingsService = Depends(get_whatsapp_settings_service),
    db: Session = Depends(get_db_session),
):
    health = st.meta_health_check()
    try:
        enabled_count = db.execute(text("SELECT COUNT(*) FROM configuracion WHERE clave LIKE 'wa_action_enabled_%'")).scalar() or 0
    except Exception:
        enabled_count = 0
    try:
        template_count = db.execute(text("SELECT COUNT(*) FROM configuracion WHERE clave LIKE 'wa_meta_template_%'")).scalar() or 0
    except Exception:
        template_count = 0
    return {
        "ok": True,
        "connected": bool(health.get("ok")),
        "health": health,
        "actions": {"enabled_keys": int(enabled_count), "template_keys": int(template_count)},
    }


@router.post("/api/whatsapp/onboarding/reconcile")
async def api_whatsapp_onboarding_reconcile(
    _=Depends(require_owner),
    st: WhatsAppSettingsService = Depends(get_whatsapp_settings_service),
):
    result = st.reconcile_onboarding()
    ok = bool(result.get("ok"))
    msg = "OK" if ok else str(result.get("error") or "Error")
    return {"ok": ok, "mensaje": msg, "success": ok, "message": msg, **result}


@router.get("/api/whatsapp/health")
async def api_whatsapp_health(
    _=Depends(require_owner),
    st: WhatsAppSettingsService = Depends(get_whatsapp_settings_service),
):
    data = st.meta_health_check()
    ok = bool(data.get("ok"))
    msg = "OK" if ok else str(data.get("error") or "Error")
    return {"ok": ok, "mensaje": msg, "success": ok, "message": msg, **data}


@router.post("/internal/cron/whatsapp/reconcile")
async def internal_cron_whatsapp_reconcile(
    request: Request,
):
    secret = (os.getenv("INTERNAL_CRON_SECRET") or "").strip()
    incoming = (request.headers.get("X-Internal-Cron-Secret") or "").strip()
    if not secret:
        return JSONResponse({"ok": False, "error": "INTERNAL_CRON_SECRET not configured"}, status_code=503)
    if incoming != secret:
        return JSONResponse({"ok": False, "error": "Unauthorized"}, status_code=401)

    try:
        limit = int(request.query_params.get("limit") or 10)
    except Exception:
        limit = 10
    if limit < 1:
        limit = 1
    if limit > 50:
        limit = 50

    try:
        cursor = int(request.query_params.get("cursor") or 0)
    except Exception:
        cursor = 0

    from src.database.raw_manager import RawPostgresManager
    from src.database.tenant_connection import tenant_session_scope, set_current_tenant

    admin_params = {
        "host": os.getenv("ADMIN_DB_HOST", os.getenv("DB_HOST", "localhost")),
        "port": int(os.getenv("ADMIN_DB_PORT", os.getenv("DB_PORT", 5432))),
        "database": os.getenv("ADMIN_DB_NAME", os.getenv("DB_NAME", "ironhub_admin")),
        "user": os.getenv("ADMIN_DB_USER", os.getenv("DB_USER", "postgres")),
        "password": os.getenv("ADMIN_DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
        "sslmode": os.getenv("ADMIN_DB_SSLMODE", os.getenv("DB_SSLMODE", "require")),
        "connect_timeout": int(os.getenv("ADMIN_DB_CONNECT_TIMEOUT", "10")),
        "application_name": "cron_whatsapp_reconcile",
    }

    gyms = []
    try:
        adm = RawPostgresManager(connection_params=admin_params)
        with adm.get_connection_context() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, subdominio FROM gyms WHERE id > %s ORDER BY id ASC LIMIT %s",
                (cursor, limit),
            )
            gyms = cur.fetchall() or []
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    results = []
    next_cursor = None
    for row in gyms:
        try:
            gid = int((row or [0, ""])[0] or 0)
            tenant = str((row or [0, ""])[1] or "").strip().lower()
            if not tenant:
                continue
            set_current_tenant(tenant)
            with tenant_session_scope(tenant) as tdb:
                st = WhatsAppSettingsService(tdb)
                r = st.reconcile_onboarding()
            results.append({"gym_id": gid, "tenant": tenant, "ok": bool(r.get("ok")), "error": r.get("error")})
            next_cursor = gid
        except Exception as e:
            results.append({"gym_id": int((row or [0, ""])[0] or 0), "tenant": str((row or [0, ""])[1] or ""), "ok": False, "error": str(e)})

    return {"ok": True, "processed": len(results), "results": results, "next_cursor": next_cursor}


@router.get("/api/whatsapp/templates")
async def api_whatsapp_templates_list(
    _=Depends(require_owner),
    db: Session = Depends(get_db_session),
):
    _ensure_templates_table(db)
    rows = db.execute(text("""
        SELECT template_name, body_text, active, created_at
        FROM whatsapp_templates
        ORDER BY template_name ASC
    """)).fetchall()
    return {"templates": [{"template_name": r[0], "body_text": r[1], "active": bool(r[2]), "created_at": str(r[3]) if r[3] else None} for r in rows]}


@router.put("/api/whatsapp/templates/{template_name}")
async def api_whatsapp_templates_upsert(
    template_name: str,
    request: Request,
    _=Depends(require_owner),
    db: Session = Depends(get_db_session),
):
    _ensure_templates_table(db)
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    body_text = str(payload.get("body_text") or "").strip()
    if not body_text:
        raise HTTPException(status_code=400, detail="body_text requerido")
    active = bool(payload.get("active", True))
    db.execute(
        text("""
            INSERT INTO whatsapp_templates (template_name, body_text, active)
            VALUES (:name, :body, :active)
            ON CONFLICT (template_name) DO UPDATE
            SET body_text = EXCLUDED.body_text,
                active = EXCLUDED.active
        """),
        {"name": template_name, "body": body_text, "active": active},
    )
    db.commit()
    return {"ok": True}


@router.delete("/api/whatsapp/templates/{template_name}")
async def api_whatsapp_templates_delete(
    template_name: str,
    _=Depends(require_owner),
    db: Session = Depends(get_db_session),
):
    _ensure_templates_table(db)
    r = db.execute(text("DELETE FROM whatsapp_templates WHERE template_name = :name"), {"name": template_name})
    db.commit()
    return {"ok": True, "deleted": int(r.rowcount or 0)}


@router.get("/api/whatsapp/triggers")
async def api_whatsapp_triggers_list(
    _=Depends(require_owner),
    db: Session = Depends(get_db_session),
):
    _ensure_triggers_table(db)
    rows = db.execute(text("""
        SELECT trigger_key, enabled, template_name, cooldown_minutes, last_run_at
        FROM whatsapp_triggers
        ORDER BY trigger_key ASC
    """)).fetchall()
    return {"triggers": [{
        "trigger_key": r[0],
        "enabled": bool(r[1]),
        "template_name": r[2],
        "cooldown_minutes": int(r[3] or 0),
        "last_run_at": str(r[4]) if r[4] else None,
    } for r in rows]}


@router.put("/api/whatsapp/triggers/{trigger_key}")
async def api_whatsapp_triggers_upsert(
    trigger_key: str,
    request: Request,
    _=Depends(require_owner),
    db: Session = Depends(get_db_session),
):
    _ensure_triggers_table(db)
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    enabled = bool(payload.get("enabled", False))
    template_name = payload.get("template_name")
    cooldown_minutes = payload.get("cooldown_minutes")
    try:
        cooldown_minutes = int(cooldown_minutes) if cooldown_minutes is not None else 1440
    except Exception:
        cooldown_minutes = 1440
    db.execute(
        text("""
            INSERT INTO whatsapp_triggers (trigger_key, enabled, template_name, cooldown_minutes)
            VALUES (:k, :en, :tpl, :cd)
            ON CONFLICT (trigger_key) DO UPDATE
            SET enabled = EXCLUDED.enabled,
                template_name = EXCLUDED.template_name,
                cooldown_minutes = EXCLUDED.cooldown_minutes
        """),
        {"k": trigger_key, "en": enabled, "tpl": template_name, "cd": cooldown_minutes},
    )
    db.commit()
    return {"ok": True}


@router.post("/api/whatsapp/automation/run")
async def api_whatsapp_automation_run(
    request: Request,
    _=Depends(require_owner),
    db: Session = Depends(get_db_session),
    wa: WhatsAppDispatchService = Depends(get_whatsapp_dispatch_service),
):
    _ensure_triggers_table(db)
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    trigger_keys = payload.get("trigger_keys")
    dry_run = bool(payload.get("dry_run", False))
    if trigger_keys and not isinstance(trigger_keys, list):
        trigger_keys = None

    triggers = db.execute(text("""
        SELECT trigger_key, enabled, cooldown_minutes
        FROM whatsapp_triggers
    """)).fetchall()
    trig_map = {r[0]: {"enabled": bool(r[1]), "cooldown_minutes": int(r[2] or 0)} for r in triggers}

    def _selected(k: str) -> bool:
        return (trigger_keys is None) or (k in set(str(x) for x in trigger_keys))

    sent = 0
    scanned = 0
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if _selected("overdue_daily") and trig_map.get("overdue_daily", {}).get("enabled"):
        cooldown = int(trig_map.get("overdue_daily", {}).get("cooldown_minutes") or 1440)
        since = now - timedelta(minutes=cooldown)
        users = db.execute(text("""
            SELECT id, telefono
            FROM usuarios
            WHERE activo = TRUE
              AND COALESCE(cuotas_vencidas, 0) > 0
              AND fecha_proximo_vencimiento IS NOT NULL
              AND fecha_proximo_vencimiento < CURRENT_DATE
              AND TRIM(COALESCE(telefono,'')) <> ''
        """)).fetchall()
        for uid, _tel in users:
            scanned += 1
            already = db.execute(text("""
                SELECT 1 FROM whatsapp_messages
                WHERE user_id = :uid
                  AND message_type = 'overdue'
                  AND sent_at >= :since
                LIMIT 1
            """), {"uid": int(uid), "since": since}).fetchone()
            if already:
                continue
            if dry_run:
                sent += 1
                continue
            if wa.send_overdue_reminder(int(uid)):
                sent += 1
        if not dry_run:
            db.execute(text("UPDATE whatsapp_triggers SET last_run_at = :now WHERE trigger_key = 'overdue_daily'"), {"now": now})
            db.commit()

    return {"ok": True, "scanned": scanned, "sent": sent, "dry_run": dry_run}


@router.post("/api/whatsapp/retry-all")
async def api_whatsapp_retry_all(
    _=Depends(require_owner),
    svc: WhatsAppService = Depends(get_whatsapp_service),
    wa: WhatsAppDispatchService = Depends(get_whatsapp_dispatch_service)
):
    """Retry all failed WhatsApp messages."""
    try:
        failed_messages = svc.obtener_mensajes_fallidos(30, 200)
        retried = 0
        for msg in failed_messages:
            uid = msg.get('usuario_id') or msg.get('user_id')
            mtype = (msg.get('message_type') or '').strip().lower()
            if uid:
                try:
                    ok = False
                    if mtype in ("welcome", "bienvenida"):
                        ok = wa.send_welcome(int(uid))
                    elif mtype in ("payment", "pago", "payment_confirmation"):
                        ok = wa.send_payment_confirmation(int(uid))
                    elif mtype in ("deactivation", "desactivacion"):
                        ok = wa.send_deactivation(int(uid), "Por decisión del administrador")
                    elif mtype in ("overdue", "recordatorio_vencida", "payment_reminder"):
                        ok = wa.send_overdue_reminder(int(uid))
                    elif mtype in ("class_reminder", "recordatorio_clase"):
                        ok = wa.send_class_reminder(int(uid), "", "", "")
                    elif mtype in ("membership_due_today", "due_today"):
                        ok = wa.send_membership_due_today(int(uid), "")
                    elif mtype in ("membership_due_soon", "due_soon"):
                        ok = wa.send_membership_due_soon(int(uid), "")
                    elif mtype in ("membership_reactivated", "reactivated"):
                        ok = wa.send_membership_reactivated(int(uid))
                    elif mtype in ("class_booking_confirmed", "booking_confirmed"):
                        ok = wa.send_class_booking_confirmed(int(uid), "", "", "")
                    elif mtype in ("class_booking_cancelled", "booking_cancelled"):
                        ok = wa.send_class_booking_cancelled(int(uid), "")
                    elif mtype in ("waitlist", "waitlist_spot_available"):
                        ok = wa.send_waitlist_promotion(int(uid), "", "", "")
                    elif mtype in ("waitlist_confirmed",):
                        ok = wa.send_waitlist_confirmed(int(uid), "", "", "")
                    elif mtype in ("schedule_change",):
                        ok = wa.send_schedule_change(int(uid), "", "", "")
                    elif mtype in ("marketing_promo",):
                        ok = wa.send_marketing_promo(int(uid), "")
                    elif mtype in ("marketing_new_class",):
                        ok = wa.send_marketing_new_class(int(uid), "", "", "")
                    else:
                        ok = wa.send_welcome(int(uid))
                    if ok:
                        retried += 1
                except:
                    pass
        return {"ok": True, "mensaje": "OK", "success": True, "message": "OK", "retried": retried}
    except Exception as e:
        return JSONResponse(
            {"ok": False, "mensaje": str(e), "success": False, "message": str(e), "error": str(e)},
            status_code=500,
        )


@router.post("/api/whatsapp/clear-failed")
async def api_whatsapp_clear_failed(
    request: Request,
    _=Depends(require_owner),
    svc: WhatsAppService = Depends(get_whatsapp_service)
):
    """Alias for /api/whatsapp/clear_failures - clears failed messages."""
    try:
        payload = await request.json()
    except:
        payload = {}
    dias = int(payload.get("days") or 30)
    result = svc.limpiar_fallidos(None, dias)
    cleared = result.get('deleted', 0) if isinstance(result, dict) else 0
    return {"ok": True, "mensaje": "OK", "success": True, "message": "OK", "cleared": cleared}


@router.post("/api/whatsapp/mensajes/{mensaje_id}/retry")
async def api_whatsapp_mensaje_retry(
    mensaje_id: int,
    _=Depends(require_owner),
    svc: WhatsAppService = Depends(get_whatsapp_service),
    wa: WhatsAppDispatchService = Depends(get_whatsapp_dispatch_service)
):
    """Retry a specific WhatsApp message by ID."""
    msg = svc.obtener_mensaje_por_id(mensaje_id)
    if not msg:
        return JSONResponse({"ok": False, "mensaje": "Mensaje no encontrado", "success": False, "message": "Mensaje no encontrado"}, status_code=404)
    uid = msg.get('user_id')
    if not uid:
        return JSONResponse({"ok": False, "mensaje": "Mensaje sin usuario asociado", "success": False, "message": "Mensaje sin usuario asociado"}, status_code=400)
    mtype = (msg.get('message_type') or '').strip().lower()
    ok = False
    if mtype in ("welcome", "bienvenida"):
        ok = wa.send_welcome(int(uid))
    elif mtype in ("payment", "pago", "payment_confirmation"):
        ok = wa.send_payment_confirmation(int(uid))
    elif mtype in ("deactivation", "desactivacion"):
        ok = wa.send_deactivation(int(uid), "Por decisión del administrador")
    elif mtype in ("overdue", "recordatorio_vencida", "payment_reminder"):
        ok = wa.send_overdue_reminder(int(uid))
    elif mtype in ("class_reminder", "recordatorio_clase"):
        ok = wa.send_class_reminder(int(uid), "", "", "")
    elif mtype in ("membership_due_today", "due_today"):
        ok = wa.send_membership_due_today(int(uid), "")
    elif mtype in ("membership_due_soon", "due_soon"):
        ok = wa.send_membership_due_soon(int(uid), "")
    elif mtype in ("membership_reactivated", "reactivated"):
        ok = wa.send_membership_reactivated(int(uid))
    elif mtype in ("class_booking_confirmed", "booking_confirmed"):
        ok = wa.send_class_booking_confirmed(int(uid), "", "", "")
    elif mtype in ("class_booking_cancelled", "booking_cancelled"):
        ok = wa.send_class_booking_cancelled(int(uid), "")
    elif mtype in ("waitlist", "waitlist_spot_available"):
        ok = wa.send_waitlist_promotion(int(uid), "", "", "")
    elif mtype in ("waitlist_confirmed",):
        ok = wa.send_waitlist_confirmed(int(uid), "", "", "")
    elif mtype in ("schedule_change",):
        ok = wa.send_schedule_change(int(uid), "", "", "")
    elif mtype in ("marketing_promo",):
        ok = wa.send_marketing_promo(int(uid), "")
    elif mtype in ("marketing_new_class",):
        ok = wa.send_marketing_new_class(int(uid), "", "", "")
    else:
        ok = wa.send_welcome(int(uid))
    return {"ok": bool(ok), "success": bool(ok), "mensaje": "OK" if ok else "Error", "message": "OK" if ok else "Error"}


@router.post("/api/whatsapp/retry")
async def api_whatsapp_retry(
    request: Request,
    _=Depends(require_owner),
    svc: WhatsAppService = Depends(get_whatsapp_service),
    wa: WhatsAppDispatchService = Depends(get_whatsapp_dispatch_service)
):
    try:
        payload = await request.json()
    except:
        payload = {}
    
    telefono = str(payload.get("telefono") or payload.get("phone") or "").strip()
    usuario_id = payload.get("usuario_id")
    
    uid = int(usuario_id) if usuario_id else None
    if not uid and telefono:
        uid = svc.obtener_usuario_id_por_telefono(telefono)
    if not uid:
        return JSONResponse(
            {"ok": False, "mensaje": "usuario_id no encontrado", "success": False, "message": "usuario_id no encontrado"},
            status_code=400,
        )
    
    last = svc.obtener_ultimo_fallido(telefono, uid)
    last_type = (last.get("message_type") or "").lower() if last else ""
    
    if last_type in ("welcome", "bienvenida"):
        ok = wa.send_welcome(uid)
        msg = "OK" if bool(ok) else "Error"
        return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg, "tipo": last_type or "welcome"}
    elif last_type in ("overdue", "recordatorio_vencida", "payment_reminder"):
        ok = wa.send_overdue_reminder(uid)
        msg = "OK" if bool(ok) else "Error"
        return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg, "tipo": last_type}
    elif last_type in ("payment", "pago", "payment_confirmation"):
        ok = wa.send_payment_confirmation(uid)
        msg = "OK" if bool(ok) else "Error"
        return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg, "tipo": last_type}
    elif last_type in ("deactivation", "desactivacion"):
        ok = wa.send_deactivation(uid, "Por decisión del administrador")
        msg = "OK" if bool(ok) else "Error"
        return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg, "tipo": last_type}
    elif last_type in ("class_reminder", "recordatorio_clase"):
        ok = wa.send_class_reminder(uid, "", "", "")
        msg = "OK" if bool(ok) else "Error"
        return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg, "tipo": last_type}
    else:
        ok = wa.send_welcome(uid)
        msg = "OK" if bool(ok) else "Error"
        return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg, "tipo": last_type or "welcome"}


@router.post("/api/whatsapp/clear_failures")
async def api_whatsapp_clear_failures(
    request: Request,
    _=Depends(require_owner),
    svc: WhatsAppService = Depends(get_whatsapp_service)
):
    try:
        payload = await request.json()
    except:
        payload = {}
    telefono = str(payload.get("telefono") or payload.get("phone") or "").strip() or None
    dias = int(payload.get("desde_dias") or payload.get("days") or 30)
    result = svc.limpiar_fallidos(telefono, dias)
    ok_val = bool(isinstance(result, dict) and ('error' not in result))
    msg = "OK" if ok_val else str((result or {}).get('error') if isinstance(result, dict) else 'Error')
    payload_out = {"ok": ok_val, "mensaje": msg, "success": ok_val, "message": msg}
    if isinstance(result, dict):
        payload_out.update(result)
    return payload_out


@router.post("/api/whatsapp/server/start")
async def api_whatsapp_server_start(_=Depends(require_owner)):
    try:
        return {"ok": False, "mensaje": "No soportado", "success": False, "message": "No soportado"}
    except Exception as e:
        return JSONResponse(
            {"ok": False, "mensaje": str(e), "success": False, "message": str(e), "error": str(e)},
            status_code=500,
        )


@router.post("/api/whatsapp/server/stop")
async def api_whatsapp_server_stop(_=Depends(require_owner)):
    try:
        return {"ok": False, "mensaje": "No soportado", "success": False, "message": "No soportado"}
    except Exception as e:
        return JSONResponse(
            {"ok": False, "mensaje": str(e), "success": False, "message": str(e), "error": str(e)},
            status_code=500,
        )


@router.post("/api/whatsapp/config")
async def api_whatsapp_config(request: Request, _=Depends(require_owner), st: WhatsAppSettingsService = Depends(get_whatsapp_settings_service)):
    try:
        data = await request.json() if request.headers.get("content-type", "").startswith("application/json") else await request.form()
    except:
        data = {}
    allowed = {"phone_number_id", "whatsapp_business_account_id", "access_token", "allowlist_numbers", "allowlist_enabled", "enable_webhook", "max_retries", "retry_delay_seconds"}
    cfg = {k: data.get(k) for k in allowed if k in data}
    _ = st.upsert_manual_config(cfg)
    return {"ok": True, "mensaje": "OK", "success": True, "message": "OK", "applied_keys": list(cfg.keys())}


@router.post("/api/usuarios/{usuario_id}/whatsapp/bienvenida")
async def api_usuario_whatsapp_bienvenida(usuario_id: int, _=Depends(require_gestion_access), wa: WhatsAppDispatchService = Depends(get_whatsapp_dispatch_service)):
    try:
        ok = wa.send_welcome(usuario_id)
        msg = "OK" if bool(ok) else "Error"
        return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg}
    except Exception as e:
        return JSONResponse(
            {"ok": False, "mensaje": str(e), "success": False, "message": str(e), "error": str(e)},
            status_code=500,
        )


@router.post("/api/usuarios/{usuario_id}/whatsapp/confirmacion_pago")
async def api_usuario_whatsapp_confirmacion_pago(usuario_id: int, request: Request, _=Depends(require_gestion_access), wa: WhatsAppDispatchService = Depends(get_whatsapp_dispatch_service)):
    try:
        payload = await request.json()
    except:
        payload = {}
    
    monto = payload.get("monto")
    mes = payload.get("mes") or payload.get("month")
    anio = payload.get("año") or payload.get("anio") or payload.get("year")
    try:
        monto_f = float(monto) if monto is not None else None
    except Exception:
        monto_f = None
    try:
        mes_i = int(mes) if mes is not None else None
    except Exception:
        mes_i = None
    try:
        anio_i = int(anio) if anio is not None else None
    except Exception:
        anio_i = None
    ok = wa.send_payment_confirmation(usuario_id, monto_f, mes_i, anio_i)
    msg = "OK" if bool(ok) else "Error"
    return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg}


@router.post("/api/usuarios/{usuario_id}/whatsapp/desactivacion")
async def api_usuario_whatsapp_desactivacion(usuario_id: int, request: Request, _=Depends(require_gestion_access), wa: WhatsAppDispatchService = Depends(get_whatsapp_dispatch_service)):
    try:
        payload = await request.json()
    except:
        payload = {}
    motivo = (payload.get("motivo") or "cuotas vencidas").strip()
    ok = wa.send_deactivation(usuario_id=usuario_id, motivo=motivo)
    msg = "OK" if bool(ok) else "Error"
    return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg}


@router.post("/api/usuarios/{usuario_id}/whatsapp/recordatorio_vencida")
async def api_usuario_whatsapp_recordatorio_vencida(usuario_id: int, _=Depends(require_gestion_access), wa: WhatsAppDispatchService = Depends(get_whatsapp_dispatch_service)):
    ok = wa.send_overdue_reminder(usuario_id)
    msg = "OK" if bool(ok) else "Error"
    return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg}


@router.post("/api/usuarios/{usuario_id}/whatsapp/force")
async def api_usuario_whatsapp_force(
    usuario_id: int,
    request: Request,
    _=Depends(require_owner),
    wa: WhatsAppDispatchService = Depends(get_whatsapp_dispatch_service)
):
    """Force send a WhatsApp message of a specific type to a user."""
    try:
        payload = await request.json()
    except:
        payload = {}
    
    tipo = (payload.get("tipo") or "").lower()
    
    ok = False
    if tipo in ("welcome", "bienvenida"):
        ok = wa.send_welcome(usuario_id)
    elif tipo in ("overdue", "vencida", "recordatorio"):
        ok = wa.send_overdue_reminder(usuario_id)
    elif tipo in ("deactivation", "desactivacion"):
        ok = wa.send_deactivation(usuario_id=usuario_id, motivo="Por decisión del administrador")
    elif tipo in ("payment", "pago"):
        ok = wa.send_payment_confirmation(usuario_id)
    elif tipo in ("class_reminder", "clase", "recordatorio_clase"):
        ok = wa.send_class_reminder(usuario_id, "", "", "")
    else:
        # Default to welcome
        ok = wa.send_welcome(usuario_id)

    msg = "OK" if bool(ok) else "Error"
    return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg}


@router.post("/api/usuarios/{usuario_id}/whatsapp/recordatorio_clase")
async def api_usuario_whatsapp_recordatorio_clase(usuario_id: int, request: Request, _=Depends(require_gestion_access), wa: WhatsAppDispatchService = Depends(get_whatsapp_dispatch_service)):
    try:
        payload = await request.json()
    except:
        payload = {}
    ok = wa.send_class_reminder(
        usuario_id,
        payload.get('tipo_clase') or payload.get('clase_nombre') or '',
        payload.get('fecha') or '',
        payload.get('hora') or ''
    )
    msg = "OK" if bool(ok) else "Error"
    return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg}


@router.get("/api/usuarios/{usuario_id}/whatsapp/ultimo")
async def api_usuario_whatsapp_ultimo(usuario_id: int, request: Request, _=Depends(require_owner), svc: WhatsAppService = Depends(get_whatsapp_service)):
    direccion = request.query_params.get("direccion")
    tipo = request.query_params.get("tipo")
    return {
        "ok": True,
        "mensaje": "OK",
        "success": True,
        "message": "OK",
        "item": svc.obtener_ultimo_mensaje(usuario_id, tipo, direccion if direccion in (None, "enviado", "recibido") else None),
    }


@router.get("/api/usuarios/{usuario_id}/whatsapp/historial")
async def api_usuario_whatsapp_historial(usuario_id: int, request: Request, _=Depends(require_gestion_access), svc: WhatsAppService = Depends(get_whatsapp_service)):
    tipo = request.query_params.get("tipo")
    limite = int(request.query_params.get("limit") or 50)
    items = svc.obtener_historial_usuario(usuario_id, tipo, limite)
    return {"mensajes": items, "items": items}


@router.delete("/api/usuarios/{usuario_id}/whatsapp/{message_pk}")
async def api_usuario_whatsapp_delete(usuario_id: int, message_pk: int, _=Depends(require_owner), svc: WhatsAppService = Depends(get_whatsapp_service)):
    old_item = svc.obtener_mensaje_por_pk(usuario_id, message_pk)
    ok = svc.eliminar_mensaje_por_pk(usuario_id, message_pk)
    if not ok:
        return JSONResponse(
            {"ok": False, "mensaje": "Mensaje no encontrado", "success": False, "message": "Mensaje no encontrado"},
            status_code=404,
        )
    return {"ok": True, "mensaje": "OK", "success": True, "message": "OK", "deleted": message_pk}


@router.delete("/api/usuarios/{usuario_id}/whatsapp/by-mid/{message_id}")
async def api_usuario_whatsapp_delete_by_mid(usuario_id: int, message_id: str, _=Depends(require_owner), svc: WhatsAppService = Depends(get_whatsapp_service)):
    ok = svc.eliminar_mensaje_por_mid(usuario_id, message_id)
    if not ok:
        return JSONResponse(
            {"ok": False, "mensaje": "Mensaje no encontrado", "success": False, "message": "Mensaje no encontrado"},
            status_code=404,
        )
    return {"ok": True, "mensaje": "OK", "success": True, "message": "OK", "deleted_mid": message_id}


# --- Webhooks ---

@router.get("/webhooks/whatsapp")
async def whatsapp_verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    expected = os.getenv("WHATSAPP_VERIFY_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Verify token not configured")
    if mode == "subscribe" and expected and token == expected and challenge:
        return Response(content=str(challenge), media_type="text/plain")
    raise HTTPException(status_code=403, detail="Invalid verify token")


@router.get("/webhooks/whatsapp/{tenant}")
async def whatsapp_verify_tenant(tenant: str, request: Request):
    ok, err = validate_tenant_name(str(tenant or ""))
    if not ok:
        raise HTTPException(status_code=404, detail=str(err or "Not found"))
    set_current_tenant(str(tenant).strip().lower())
    with tenant_session_scope(str(tenant).strip().lower()) as db:
        st = WhatsAppSettingsService(db)
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")
        expected = os.getenv("WHATSAPP_VERIFY_TOKEN", "") or st.get_webhook_verify_token()
        if mode == "subscribe" and expected and token == expected and challenge:
            return Response(content=str(challenge), media_type="text/plain")
    raise HTTPException(status_code=403, detail="Invalid verify token")


@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request, svc: WhatsAppService = Depends(get_whatsapp_service), db: Session = Depends(get_db_session)):
    def _admin_db_params() -> Dict[str, Any]:
        return {
            "host": os.getenv("ADMIN_DB_HOST", os.getenv("DB_HOST", "localhost")),
            "port": int(os.getenv("ADMIN_DB_PORT", os.getenv("DB_PORT", 5432))),
            "database": os.getenv("ADMIN_DB_NAME", os.getenv("DB_NAME", "ironhub_admin")),
            "user": os.getenv("ADMIN_DB_USER", os.getenv("DB_USER", "postgres")),
            "password": os.getenv("ADMIN_DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
            "sslmode": os.getenv("ADMIN_DB_SSLMODE", os.getenv("DB_SSLMODE", "require")),
            "connect_timeout": 10,
            "application_name": "webapp_api_whatsapp_webhook",
        }

    def _resolve_tenant_by_phone_number_id(phone_number_id: str) -> Optional[str]:
        from src.database.raw_manager import RawPostgresManager

        pid = str(phone_number_id or "").strip()
        if not pid:
            return None
        try:
            adm = RawPostgresManager(connection_params=_admin_db_params())
            with adm.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute("SELECT subdominio FROM gyms WHERE whatsapp_phone_id = %s LIMIT 1", (pid,))
                row = cur.fetchone()
            return str(row[0]).strip().lower() if row and row[0] else None
        except Exception:
            return None

    def _extract_phone_number_id(payload: Dict[str, Any]) -> Optional[str]:
        try:
            for entry in (payload or {}).get("entry") or []:
                for change in (entry or {}).get("changes") or []:
                    value = (change or {}).get("value") or {}
                    md = value.get("metadata") or {}
                    pid = (md or {}).get("phone_number_id")
                    if pid:
                        return str(pid)
                    for st0 in value.get("statuses") or []:
                        c = (st0 or {}).get("recipient_id") or (st0 or {}).get("conversation") or None
                        _ = c
            return None
        except Exception:
            return None

    def _verify_signature(raw: bytes, request: Request, app_secret: str, dev_mode: bool, allow_unsigned: bool) -> None:
        if not app_secret and not (dev_mode or allow_unsigned):
            raise HTTPException(status_code=503, detail="Webhook signature not configured")
        if not app_secret:
            return
        import hmac, hashlib

        sig = request.headers.get("X-Hub-Signature-256") or ""
        expected_hash = hmac.new(app_secret.encode(), raw, hashlib.sha256).hexdigest()
        incoming_hash = str(sig).strip()
        if incoming_hash.lower().startswith("sha256="):
            incoming_hash = incoming_hash.split("=", 1)[1]
        if not hmac.compare_digest(expected_hash, incoming_hash):
            raise HTTPException(status_code=403, detail="Invalid signature")

    def _process_payload(svc0: WhatsAppService, payload0: Dict[str, Any]) -> None:
        for entry in payload0.get("entry") or []:
            for change in entry.get("changes") or []:
                value = change.get("value") or {}
                for status in value.get("statuses") or []:
                    mid, stt = status.get("id"), status.get("status")
                    if mid and stt:
                        svc0.actualizar_estado_mensaje(mid, stt)
                for msg in value.get("messages") or []:
                    mid = msg.get("id")
                    mtype = msg.get("type")
                    wa_from = msg.get("from")
                    text = None
                    if mtype == "text":
                        text = (msg.get("text") or {}).get("body")
                    elif mtype == "button":
                        text = (msg.get("button") or {}).get("text")
                    elif mtype == "interactive":
                        ir = msg.get("interactive") or {}
                        text = (ir.get("button_reply") or {}).get("title") or (ir.get("list_reply") or {}).get("title")
                    elif mtype in ("image", "audio", "video", "document"):
                        text = f"[{mtype}]"
                    uid = svc0.obtener_usuario_id_por_telefono(wa_from) if wa_from else None
                    svc0.registrar_mensaje_entrante(uid, wa_from, text or "", mid)

    try:
        raw = await request.body()
        dev_mode = os.getenv("DEVELOPMENT_MODE", "").lower() in ("1", "true", "yes") or os.getenv("ENV", "").lower() in ("dev", "development")
        allow_unsigned = os.getenv("ALLOW_UNSIGNED_WHATSAPP_WEBHOOK", "").lower() in ("1", "true", "yes")
        app_secret = (os.getenv("WHATSAPP_APP_SECRET", "") or "").strip()
        _verify_signature(raw, request, app_secret, dev_mode, allow_unsigned)
        payload = json.loads(raw.decode())
        if not isinstance(payload, dict):
            return {"status": "ignored"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Bad Request")

    phone_number_id = _extract_phone_number_id(payload)
    tenant = _resolve_tenant_by_phone_number_id(phone_number_id or "")
    if tenant:
        ok, err = validate_tenant_name(str(tenant))
        if not ok:
            return {"status": "ignored", "reason": "invalid_tenant"}
        set_current_tenant(str(tenant))
        with tenant_session_scope(str(tenant)) as tdb:
            tsvc = WhatsAppService(tdb)
            _process_payload(tsvc, payload)
        return {"status": "ok"}

    _process_payload(svc, payload)
    return {"status": "ok", "routed": False}


@router.post("/webhooks/whatsapp/{tenant}")
async def whatsapp_webhook_tenant(tenant: str, request: Request):
    ok, err = validate_tenant_name(str(tenant or ""))
    if not ok:
        raise HTTPException(status_code=404, detail=str(err or "Not found"))
    t = str(tenant).strip().lower()
    set_current_tenant(t)
    with tenant_session_scope(t) as db:
        svc = WhatsAppService(db)
        try:
            raw = await request.body()
            dev_mode = os.getenv("DEVELOPMENT_MODE", "").lower() in ("1", "true", "yes") or os.getenv("ENV", "").lower() in ("dev", "development")
            allow_unsigned = os.getenv("ALLOW_UNSIGNED_WHATSAPP_WEBHOOK", "").lower() in ("1", "true", "yes")

            app_secret = os.getenv("WHATSAPP_APP_SECRET", "")
            if not app_secret:
                try:
                    row = db.execute(select(Configuracion.valor).where(Configuracion.clave == "WHATSAPP_APP_SECRET").limit(1)).first()
                    app_secret = (row[0] if row else "") or ""
                except Exception:
                    app_secret = ""
            if not app_secret and not (dev_mode or allow_unsigned):
                raise HTTPException(status_code=503, detail="Webhook signature not configured")

            if app_secret:
                import hmac, hashlib
                sig = request.headers.get("X-Hub-Signature-256") or ""
                expected_hash = hmac.new(app_secret.encode(), raw, hashlib.sha256).hexdigest()
                incoming_hash = str(sig).strip()
                if incoming_hash.lower().startswith("sha256="):
                    incoming_hash = incoming_hash.split("=", 1)[1]
                if not hmac.compare_digest(expected_hash, incoming_hash):
                    raise HTTPException(status_code=403, detail="Invalid signature")

            payload = json.loads(raw.decode())
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=400, detail="Bad Request")

        for entry in payload.get("entry") or []:
            for change in entry.get("changes") or []:
                value = change.get("value") or {}

                for status in value.get("statuses") or []:
                    mid, stt = status.get("id"), status.get("status")
                    if mid and stt:
                        svc.actualizar_estado_mensaje(mid, stt)

                for msg in value.get("messages") or []:
                    mid = msg.get("id")
                    mtype = msg.get("type")
                    wa_from = msg.get("from")

                    text = None
                    if mtype == "text":
                        text = (msg.get("text") or {}).get("body")
                    elif mtype == "button":
                        text = (msg.get("button") or {}).get("text")
                    elif mtype == "interactive":
                        ir = msg.get("interactive") or {}
                        text = (ir.get("button_reply") or {}).get("title") or (ir.get("list_reply") or {}).get("title")
                    elif mtype in ("image", "audio", "video", "document"):
                        text = f"[{mtype}]"

                    uid = svc.obtener_usuario_id_por_telefono(wa_from) if wa_from else None
                    svc.registrar_mensaje_entrante(uid, wa_from, text or "", mid)

        return {"status": "ok"}
