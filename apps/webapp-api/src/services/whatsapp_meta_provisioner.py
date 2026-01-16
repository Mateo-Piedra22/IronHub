from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Set, Tuple

import requests


def _api_version() -> str:
    return (os.getenv("META_GRAPH_API_VERSION") or os.getenv("WHATSAPP_API_VERSION") or "v19.0").strip()


def _template_language() -> str:
    return (os.getenv("WHATSAPP_TEMPLATE_LANGUAGE") or "es_AR").strip()


def standard_meta_templates(language_code: Optional[str] = None) -> List[Dict[str, Any]]:
    lang = (language_code or _template_language()).strip()

    def body(text: str, examples: List[str]) -> Dict[str, Any]:
        return {
            "type": "BODY",
            "text": text,
            "example": {"body_text": [examples]},
        }

    templates: List[Tuple[str, str, str, List[str]]] = [
        ("ih_welcome_v1", "UTILITY", "Hola {{1}}. ¡Bienvenido/a! Si necesitás ayuda, respondé a este mensaje.", ["Mateo"]),
        ("ih_payment_confirmed_v1", "UTILITY", "Hola {{1}}. Confirmamos tu pago de ${{2}} correspondiente a {{3}}. ¡Gracias!", ["Mateo", "25000", "01/2026"]),
        ("ih_membership_due_today_v1", "UTILITY", "Hola {{1}}. Recordatorio: tu cuota vence hoy ({{2}}). Si ya abonaste, ignorá este mensaje.", ["Mateo", "16/01"]),
        ("ih_membership_due_soon_v1", "UTILITY", "Hola {{1}}. Tu cuota vence el {{2}}. Si querés, respondé a este mensaje y te ayudamos a regularizar.", ["Mateo", "20/01"]),
        ("ih_membership_overdue_v1", "UTILITY", "Hola {{1}}. Tu cuota está vencida. Si ya abonaste, ignorá este mensaje. Si necesitás ayuda, respondé “AYUDA”.", ["Mateo"]),
        ("ih_membership_deactivated_v1", "UTILITY", "Hola {{1}}. Tu acceso está temporalmente suspendido. Motivo: {{2}}. Respondé a este mensaje si necesitás asistencia.", ["Mateo", "cuotas vencidas"]),
        ("ih_membership_reactivated_v1", "UTILITY", "Hola {{1}}. Tu acceso fue reactivado. ¡Gracias!", ["Mateo"]),
        ("ih_class_booking_confirmed_v1", "UTILITY", "Reserva confirmada: {{1}} el {{2}} a las {{3}}. Si no podés asistir, respondé “CANCELAR”.", ["Funcional", "16/01", "19:00"]),
        ("ih_class_booking_cancelled_v1", "UTILITY", "Tu reserva para {{1}} ({{2}} {{3}}) fue cancelada.", ["Funcional", "16/01", "19:00"]),
        ("ih_class_reminder_v1", "UTILITY", "Hola {{1}}. Recordatorio: {{2}} el {{3}} a las {{4}}.", ["Mateo", "Funcional", "16/01", "19:00"]),
        ("ih_waitlist_spot_available_v1", "UTILITY", "Hola {{1}}. Se liberó un cupo para {{2}} ({{3}} {{4}}). Respondé “SI” para tomarlo.", ["Mateo", "Funcional", "viernes", "19:00"]),
        ("ih_waitlist_confirmed_v1", "UTILITY", "Listo {{1}}. Te anotamos en {{2}} ({{3}} {{4}}).", ["Mateo", "Funcional", "viernes", "19:00"]),
        ("ih_schedule_change_v1", "UTILITY", "Aviso: hubo un cambio en {{1}}. Nuevo horario: {{2}} {{3}}.", ["Funcional", "viernes", "20:00"]),
        ("ih_auth_code_v1", "AUTHENTICATION", "Tu código de verificación es {{1}}. Vence en {{2}} minutos. No lo compartas con nadie.", ["928314", "10"]),
        ("ih_marketing_promo_v1", "MARKETING", "Hola {{1}}. Esta semana tenemos {{2}}. Si querés más info, respondé a este mensaje.", ["Mateo", "descuento del 10% en el plan trimestral"]),
        ("ih_marketing_new_class_v1", "MARKETING", "Nueva clase disponible: {{1}}. Primer horario: {{2}} {{3}}. ¿Querés que te reservemos un lugar?", ["Movilidad", "miércoles", "18:00"]),
    ]

    return [
        {
            "name": name,
            "language": lang,
            "category": category,
            "components": [body(body_text, examples)],
        }
        for name, category, body_text, examples in templates
    ]


def list_meta_templates(waba_id: str, access_token: str) -> Set[str]:
    url = f"https://graph.facebook.com/{_api_version()}/{waba_id}/message_templates"
    names: Set[str] = set()
    after: Optional[str] = None
    for _ in range(10):
        params = {"fields": "name,status", "limit": "200"}
        if after:
            params["after"] = after
        resp = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, params=params, timeout=15)
        data = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            raise RuntimeError(str(data.get("error") or data or f"HTTP {resp.status_code}"))
        for item in (data.get("data") or []):
            n = (item or {}).get("name")
            if n:
                names.add(str(n))
        paging = data.get("paging") or {}
        cursors = paging.get("cursors") or {}
        after = cursors.get("after")
        if not after:
            break
    return names


def create_meta_template(waba_id: str, access_token: str, template_payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"https://graph.facebook.com/{_api_version()}/{waba_id}/message_templates"
    resp = requests.post(url, headers={"Authorization": f"Bearer {access_token}"}, json=template_payload, timeout=25)
    data = resp.json() if resp.content else {}
    if resp.status_code >= 400:
        raise RuntimeError(str(data.get("error") or data or f"HTTP {resp.status_code}"))
    return data if isinstance(data, dict) else {}


def provision_standard_meta_templates(waba_id: str, access_token: str, language_code: Optional[str] = None) -> Dict[str, Any]:
    existing = list_meta_templates(waba_id, access_token)
    to_create = [t for t in standard_meta_templates(language_code) if (t.get("name") or "") not in existing]
    created: List[str] = []
    failed: List[Dict[str, str]] = []
    for t in to_create:
        name = str(t.get("name") or "")
        try:
            create_meta_template(waba_id, access_token, t)
            created.append(name)
        except Exception as e:
            failed.append({"name": name, "error": str(e)})
    return {"existing_count": len(existing), "created": created, "failed": failed}

