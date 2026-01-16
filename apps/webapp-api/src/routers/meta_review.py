import os
import re
from typing import Any, Dict

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from src.dependencies import require_owner, get_whatsapp_settings_service
from src.services.whatsapp_settings_service import WhatsAppSettingsService

router = APIRouter()


def _api_version() -> str:
    return (os.getenv("META_GRAPH_API_VERSION") or os.getenv("WHATSAPP_API_VERSION") or "v19.0").strip()

def _normalize_e164_digits(phone: str) -> str:
    s = re.sub(r"[^\d]", "", str(phone or ""))
    return s


@router.post("/api/meta-review/whatsapp/send-text")
async def meta_review_send_text(
    request: Request,
    _=Depends(require_owner),
    st: WhatsAppSettingsService = Depends(get_whatsapp_settings_service),
):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    to = str((payload or {}).get("to") or "").strip()
    body = str((payload or {}).get("body") or "").strip()
    if not to or not body:
        raise HTTPException(status_code=400, detail="to y body requeridos")
    to = _normalize_e164_digits(to)
    if not to:
        raise HTTPException(status_code=400, detail="to inválido")

    row = st._get_active_config_row()
    if not row:
        raise HTTPException(status_code=400, detail="WhatsApp no configurado")

    phone_id = str(getattr(row, "phone_id", "") or "").strip()
    token = st._decrypt_token_best_effort(str(getattr(row, "access_token", "") or ""))
    if not phone_id or not token:
        raise HTTPException(status_code=400, detail="Falta phone_id o access_token")

    url = f"https://graph.facebook.com/{_api_version()}/{phone_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=st._timeout_seconds())
        out = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            return JSONResponse({"ok": False, "error": out.get("error") or out or f"HTTP {resp.status_code}"}, status_code=400)
        return {"ok": True, "result": out}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.post("/api/meta-review/whatsapp/send-template")
async def meta_review_send_template(
    request: Request,
    _=Depends(require_owner),
    st: WhatsAppSettingsService = Depends(get_whatsapp_settings_service),
):
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    to = str((payload or {}).get("to") or "").strip()
    template_name = str((payload or {}).get("template_name") or "").strip()
    language = str((payload or {}).get("language") or os.getenv("WHATSAPP_TEMPLATE_LANGUAGE") or "es_AR").strip()
    params = (payload or {}).get("params") or []

    if not to or not template_name:
        raise HTTPException(status_code=400, detail="to y template_name requeridos")
    to = _normalize_e164_digits(to)
    if not to:
        raise HTTPException(status_code=400, detail="to inválido")

    row = st._get_active_config_row()
    if not row:
        raise HTTPException(status_code=400, detail="WhatsApp no configurado")

    phone_id = str(getattr(row, "phone_id", "") or "").strip()
    token = st._decrypt_token_best_effort(str(getattr(row, "access_token", "") or ""))
    if not phone_id or not token:
        raise HTTPException(status_code=400, detail="Falta phone_id o access_token")

    if not isinstance(params, list):
        params = []
    body_params = []
    for p in params:
        s = str(p or "").strip()
        if s:
            body_params.append({"type": "text", "text": s})

    url = f"https://graph.facebook.com/{_api_version()}/{phone_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language},
            "components": [{"type": "body", "parameters": body_params}] if body_params else [],
        },
    }
    if not data["template"]["components"]:
        data["template"].pop("components", None)

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=st._timeout_seconds())
        out = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            return JSONResponse({"ok": False, "error": out.get("error") or out or f"HTTP {resp.status_code}"}, status_code=400)
        return {"ok": True, "result": out}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.post("/api/meta-review/whatsapp/create-template")
async def meta_review_create_template(
    request: Request,
    _=Depends(require_owner),
    st: WhatsAppSettingsService = Depends(get_whatsapp_settings_service),
):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    name = str((payload or {}).get("name") or "").strip()
    body_text = str((payload or {}).get("body_text") or "").strip()
    category = str((payload or {}).get("category") or "UTILITY").strip().upper()
    language = str((payload or {}).get("language") or os.getenv("WHATSAPP_TEMPLATE_LANGUAGE") or "es_AR").strip()
    examples = (payload or {}).get("examples") or []

    if not name or not body_text:
        raise HTTPException(status_code=400, detail="name y body_text requeridos")
    if category not in ("UTILITY", "AUTHENTICATION", "MARKETING"):
        category = "UTILITY"

    row = st._get_active_config_row()
    if not row:
        raise HTTPException(status_code=400, detail="WhatsApp no configurado")

    waba_id = str(getattr(row, "waba_id", "") or "").strip()
    token = st._decrypt_token_best_effort(str(getattr(row, "access_token", "") or ""))
    if not waba_id or not token:
        raise HTTPException(status_code=400, detail="Falta waba_id o access_token")

    url = f"https://graph.facebook.com/{_api_version()}/{waba_id}/message_templates"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data: Dict[str, Any] = {
        "name": name,
        "language": language,
        "category": category,
        "components": [{"type": "BODY", "text": body_text}],
    }
    if isinstance(examples, list) and examples:
        data["components"][0]["example"] = {"body_text": [examples]}
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=st._timeout_seconds())
        out = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            return JSONResponse({"ok": False, "error": out.get("error") or out or f"HTTP {resp.status_code}"}, status_code=400)
        return {"ok": True, "result": out}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.get("/api/meta-review/whatsapp/health")
async def meta_review_health(
    _=Depends(require_owner),
    st: WhatsAppSettingsService = Depends(get_whatsapp_settings_service),
):
    data = st.meta_health_check()
    ok = bool(data.get("ok"))
    msg = "OK" if ok else str(data.get("error") or "Error")
    return {"ok": ok, "mensaje": msg, "success": ok, "message": msg, **data}
