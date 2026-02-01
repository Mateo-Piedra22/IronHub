from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.dependencies import get_admin_db, get_claims, require_feature, require_gestion_access
from src.services import b2_storage


router = APIRouter()


ALLOWED_STATUS = {"open", "in_progress", "waiting_client", "resolved", "closed"}
ALLOWED_PRIORITY = {"low", "medium", "high", "critical"}
ALLOWED_CATEGORY = {"bug", "feature", "billing", "general"}


def _norm(v: Any) -> str:
    return str(v or "").strip()


def _lower(v: Any) -> str:
    return _norm(v).lower()


def _now() -> datetime:
    return datetime.utcnow().replace(microsecond=0)


def _sla_seconds_for_priority(priority: str) -> int:
    p = str(priority or "").strip().lower()
    if p == "critical":
        return 2 * 60 * 60
    if p == "high":
        return 6 * 60 * 60
    if p == "medium":
        return 24 * 60 * 60
    if p == "low":
        return 72 * 60 * 60
    return 24 * 60 * 60


def _get_sla_seconds(db: Session, tenant: str, priority: str, kind: str) -> int:
    k = str(kind or "").strip().lower()
    if k not in ("first", "next"):
        k = "next"
    p = str(priority or "").strip().lower()
    try:
        row = db.execute(
            text("SELECT sla_seconds FROM support_tenant_settings WHERE tenant = :t LIMIT 1"),
            {"t": str(tenant or "").strip().lower()},
        ).mappings().first()
        sla = row.get("sla_seconds") if row else None
        if isinstance(sla, dict) and p in sla and isinstance(sla.get(p), dict):
            sec = int((sla.get(p) or {}).get(k) or 0)
            if sec > 0:
                return sec
    except Exception:
        pass
    return _sla_seconds_for_priority(p)


def _ticket_row_to_dict(r: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(r or {})
    for k in ("created_at", "updated_at", "last_message_at"):
        try:
            if out.get(k) is not None and hasattr(out[k], "isoformat"):
                out[k] = out[k].isoformat()
        except Exception:
            pass
    return out


def _message_row_to_dict(r: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(r or {})
    try:
        if out.get("created_at") is not None and hasattr(out["created_at"], "isoformat"):
            out["created_at"] = out["created_at"].isoformat()
    except Exception:
        pass
    return out


@router.post(
    "/api/support/attachments",
    dependencies=[Depends(require_gestion_access), Depends(require_feature("soporte"))],
)
async def api_support_upload_attachment(
    request: Request,
    file: UploadFile = File(...),
):
    claims = get_claims(request)
    tenant = str(claims.get("tenant") or "").strip().lower()
    if not tenant:
        raise HTTPException(status_code=400, detail="Tenant inválido")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Archivo vacío")
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Archivo demasiado grande (max 5MB)")
    content_type = str(file.content_type or "application/octet-stream")
    ok, url_or_err, key = b2_storage.upload_file(
        content,
        str(file.filename or "file"),
        tenant,
        folder="support",
        content_type=content_type,
    )
    if not ok:
        raise HTTPException(status_code=500, detail=url_or_err or "No se pudo subir")
    return {
        "ok": True,
        "attachment": {
            "url": url_or_err,
            "key": key,
            "filename": str(file.filename or ""),
            "content_type": content_type,
            "size_bytes": int(len(content)),
        },
    }


@router.post(
    "/api/support/tickets",
    dependencies=[Depends(require_gestion_access), Depends(require_feature("soporte"))],
)
async def api_support_create_ticket(request: Request, db: Session = Depends(get_admin_db)):
    claims = get_claims(request)
    tenant = str(claims.get("tenant") or "").strip().lower()
    if not tenant:
        raise HTTPException(status_code=400, detail="Tenant inválido")

    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    subject = _norm(payload.get("subject"))[:180]
    if not subject:
        raise HTTPException(status_code=400, detail="Asunto requerido")

    category = _lower(payload.get("category")) or "general"
    if category not in ALLOWED_CATEGORY:
        category = "general"

    priority = _lower(payload.get("priority")) or "medium"
    if priority not in ALLOWED_PRIORITY:
        priority = "medium"

    content = _norm(payload.get("message"))[:8000]
    if not content:
        raise HTTPException(status_code=400, detail="Mensaje requerido")

    attachments = payload.get("attachments")
    if attachments is None:
        attachments = []
    if not isinstance(attachments, list):
        attachments = []
    if len(attachments) > 10:
        raise HTTPException(status_code=400, detail="Demasiados adjuntos")

    origin_url = _norm(payload.get("origin_url"))[:500] or None
    user_agent = _norm(payload.get("user_agent"))[:500] or _norm(request.headers.get("user-agent"))[:500] or None
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}

    user_id = claims.get("user_id")
    role = str(claims.get("role") or "")
    sucursal_id = claims.get("sucursal_id")
    gym_id = None
    try:
        gym_id = db.execute(
            text("SELECT id FROM gyms WHERE LOWER(subdominio) = :t LIMIT 1"),
            {"t": tenant},
        ).scalar()
    except Exception:
        gym_id = None

    now = _now()
    ticket_id = db.execute(
        text(
            """
            INSERT INTO support_tickets(
                gym_id, tenant, user_id, user_role, sucursal_id,
                subject, category, priority, status,
                origin_url, user_agent, meta,
                last_message_at, last_message_sender, unread_by_admin, unread_by_client,
                created_at, updated_at
            )
            VALUES (
                :gym_id, :tenant, :user_id, :role, :sucursal_id,
                :subject, :category, :priority, 'open',
                :origin_url, :user_agent, CAST(:meta AS JSONB),
                :last_message_at, 'client', TRUE, FALSE,
                :created_at, :updated_at
            )
            RETURNING id
            """
        ),
        {
            "gym_id": int(gym_id) if gym_id is not None else None,
            "tenant": tenant,
            "user_id": int(user_id) if user_id is not None else None,
            "role": role,
            "sucursal_id": int(sucursal_id) if sucursal_id is not None else None,
            "subject": subject,
            "category": category,
            "priority": priority,
            "origin_url": origin_url,
            "user_agent": user_agent,
            "meta": json.dumps(meta or {}, ensure_ascii=False),
            "last_message_at": now,
            "created_at": now,
            "updated_at": now,
        },
    ).scalar()
    if not ticket_id:
        db.rollback()
        raise HTTPException(status_code=500, detail="No se pudo crear ticket")

    try:
        sec = _get_sla_seconds(db, tenant, priority, "first")
        due = now + timedelta(seconds=int(sec))
        db.execute(
            text(
                """
                UPDATE support_tickets
                SET
                  first_response_due_at = COALESCE(first_response_due_at, :due),
                  next_response_due_at = :due,
                  updated_at = :ts
                WHERE id = :id
                """
            ),
            {"id": int(ticket_id), "due": due, "ts": now},
        )
    except Exception:
        pass

    db.execute(
        text(
            """
            INSERT INTO support_ticket_messages(ticket_id, sender_type, sender_id, content, attachments, read_by_recipient, created_at)
            VALUES (:ticket_id, 'client', :sender_id, :content, CAST(:attachments AS JSONB), FALSE, :created_at)
            """
        ),
        {
            "ticket_id": int(ticket_id),
            "sender_id": int(user_id) if user_id is not None else None,
            "content": content,
            "attachments": json.dumps(attachments or [], ensure_ascii=False),
            "created_at": now,
        },
    )
    db.commit()
    return {"ok": True, "ticket_id": int(ticket_id)}


@router.get(
    "/api/support/tickets",
    dependencies=[Depends(require_gestion_access), Depends(require_feature("soporte"))],
)
async def api_support_list_tickets(
    request: Request,
    db: Session = Depends(get_admin_db),
    status: str = "",
    page: int = 1,
    limit: int = 30,
):
    claims = get_claims(request)
    tenant = str(claims.get("tenant") or "").strip().lower()
    if not tenant:
        raise HTTPException(status_code=400, detail="Tenant inválido")
    role = str(claims.get("role") or "")
    is_owner = bool(claims.get("is_owner"))
    user_id = claims.get("user_id")

    st = _lower(status)
    if st and st not in ALLOWED_STATUS:
        st = ""

    page_i = max(1, int(page or 1))
    limit_i = max(1, min(int(limit or 30), 100))
    offset_i = (page_i - 1) * limit_i

    where = ["LOWER(tenant) = :tenant"]
    params: Dict[str, Any] = {"tenant": tenant, "limit": int(limit_i), "offset": int(offset_i)}
    if st:
        where.append("status = :status")
        params["status"] = st
    if not is_owner:
        where.append("user_id = :uid")
        params["uid"] = int(user_id or 0)

    where_sql = " AND ".join(where)
    total = db.execute(
        text(f"SELECT COUNT(*) FROM support_tickets WHERE {where_sql}"),
        params,
    ).scalar() or 0
    rows = db.execute(
        text(
            f"""
            SELECT
              id, gym_id, tenant, user_id, user_role, sucursal_id,
              subject, category, priority, status,
              origin_url, user_agent,
              last_message_at, last_message_sender,
              unread_by_admin, unread_by_client,
              created_at, updated_at
            FROM support_tickets
            WHERE {where_sql}
            ORDER BY last_message_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()
    return {
        "ok": True,
        "items": [_ticket_row_to_dict(dict(r)) for r in rows],
        "total": int(total),
        "limit": int(limit_i),
        "offset": int(offset_i),
        "viewer": {"role": role, "is_owner": bool(is_owner)},
    }


@router.get(
    "/api/support/tickets/{ticket_id}",
    dependencies=[Depends(require_gestion_access), Depends(require_feature("soporte"))],
)
async def api_support_get_ticket(
    ticket_id: int,
    request: Request,
    db: Session = Depends(get_admin_db),
):
    claims = get_claims(request)
    tenant = str(claims.get("tenant") or "").strip().lower()
    if not tenant:
        raise HTTPException(status_code=400, detail="Tenant inválido")
    is_owner = bool(claims.get("is_owner"))
    user_id = claims.get("user_id")

    t = db.execute(
        text(
            """
            SELECT
              id, gym_id, tenant, user_id, user_role, sucursal_id,
              subject, category, priority, status,
              origin_url, user_agent,
              last_message_at, last_message_sender,
              unread_by_admin, unread_by_client,
              created_at, updated_at
            FROM support_tickets
            WHERE id = :id AND LOWER(tenant) = :tenant
            LIMIT 1
            """
        ),
        {"id": int(ticket_id), "tenant": tenant},
    ).mappings().first()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    if (not is_owner) and int(t.get("user_id") or 0) != int(user_id or 0):
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    msgs = db.execute(
        text(
            """
            SELECT id, ticket_id, sender_type, sender_id, content, attachments, read_by_recipient, created_at
            FROM support_ticket_messages
            WHERE ticket_id = :id AND sender_type <> 'internal'
            ORDER BY created_at ASC, id ASC
            """
        ),
        {"id": int(ticket_id)},
    ).mappings().all()

    db.execute(
        text(
            """
            UPDATE support_tickets
            SET unread_by_client = FALSE, updated_at = NOW()
            WHERE id = :id
            """
        ),
        {"id": int(ticket_id)},
    )
    try:
        db.execute(
            text("UPDATE support_tickets SET last_client_read_at = NOW() WHERE id = :id"),
            {"id": int(ticket_id)},
        )
    except Exception:
        pass
    db.commit()

    return {
        "ok": True,
        "ticket": _ticket_row_to_dict(dict(t)),
        "messages": [_message_row_to_dict(dict(m)) for m in msgs],
    }


@router.post(
    "/api/support/tickets/{ticket_id}/reply",
    dependencies=[Depends(require_gestion_access), Depends(require_feature("soporte"))],
)
async def api_support_reply(
    ticket_id: int,
    request: Request,
    db: Session = Depends(get_admin_db),
):
    claims = get_claims(request)
    tenant = str(claims.get("tenant") or "").strip().lower()
    if not tenant:
        raise HTTPException(status_code=400, detail="Tenant inválido")
    is_owner = bool(claims.get("is_owner"))
    user_id = claims.get("user_id")

    t = db.execute(
        text("SELECT id, user_id, priority FROM support_tickets WHERE id = :id AND LOWER(tenant) = :tenant LIMIT 1"),
        {"id": int(ticket_id), "tenant": tenant},
    ).mappings().first()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    if (not is_owner) and int(t.get("user_id") or 0) != int(user_id or 0):
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    content = _norm(payload.get("message"))[:8000]
    if not content:
        raise HTTPException(status_code=400, detail="Mensaje requerido")
    attachments = payload.get("attachments")
    if attachments is None:
        attachments = []
    if not isinstance(attachments, list):
        attachments = []
    if len(attachments) > 10:
        raise HTTPException(status_code=400, detail="Demasiados adjuntos")

    now = _now()
    db.execute(
        text(
            """
            INSERT INTO support_ticket_messages(ticket_id, sender_type, sender_id, content, attachments, read_by_recipient, created_at)
            VALUES (:ticket_id, 'client', :sender_id, :content, CAST(:attachments AS JSONB), FALSE, :created_at)
            """
        ),
        {
            "ticket_id": int(ticket_id),
            "sender_id": int(user_id) if user_id is not None else None,
            "content": content,
            "attachments": json.dumps(attachments or [], ensure_ascii=False),
            "created_at": now,
        },
    )
    try:
        sec = _get_sla_seconds(db, tenant, str(t.get("priority") or "medium"), "next")
        due = now + timedelta(seconds=int(sec))
        db.execute(
            text(
                """
                UPDATE support_tickets
                SET
                  last_message_at = :ts,
                  last_message_sender = 'client',
                  unread_by_admin = TRUE,
                  unread_by_client = FALSE,
                  next_response_due_at = :due,
                  updated_at = :ts,
                  status = CASE
                    WHEN status IN ('resolved', 'closed') THEN status
                    WHEN status = 'waiting_client' THEN 'in_progress'
                    ELSE status
                  END
                WHERE id = :id
                """
            ),
            {"id": int(ticket_id), "ts": now, "due": due},
        )
    except Exception:
        db.execute(
            text(
                """
                UPDATE support_tickets
                SET
                  last_message_at = :ts,
                  last_message_sender = 'client',
                  unread_by_admin = TRUE,
                  unread_by_client = FALSE,
                  updated_at = :ts,
                  status = CASE
                    WHEN status IN ('resolved', 'closed') THEN status
                    WHEN status = 'waiting_client' THEN 'in_progress'
                    ELSE status
                  END
                WHERE id = :id
                """
            ),
            {"id": int(ticket_id), "ts": now},
        )
    db.commit()
    return {"ok": True}
