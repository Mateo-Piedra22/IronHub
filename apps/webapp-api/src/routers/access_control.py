from __future__ import annotations

import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.dependencies import (
    get_claims,
    get_db_session,
    require_feature,
    require_gestion_access,
    require_user_auth,
    require_scope_gestion,
)
from src.services.attendance_service import AttendanceService
from src.access_config_schema import normalize_access_device_config
from src.rate_limit_store import incr_and_check


router = APIRouter()


def _utcnow() -> datetime:
    return datetime.utcnow().replace(microsecond=0)


def _sha256(s: str) -> str:
    return hashlib.sha256(str(s or "").encode("utf-8")).hexdigest()


def _mask_value(v: str) -> str:
    s = str(v or "").strip()
    if len(s) <= 4:
        return "*" * len(s)
    return ("*" * (len(s) - 4)) + s[-4:]


def _normalize_credential(v: str) -> str:
    s = str(v or "").strip().lower()
    s = "".join(ch for ch in s if ch.isalnum())
    return s


def _extract_device_token(request: Request) -> str:
    auth = str(request.headers.get("authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return ""

def _extract_event_nonce(request: Request) -> str:
    return str(request.headers.get("x-event-nonce") or "").strip()

def _is_nonce_valid(n: str) -> bool:
    s = str(n or "").strip()
    return 16 <= len(s) <= 128

def _digits_only(s: str) -> str:
    return "".join(ch for ch in str(s or "") if ch.isdigit())

def _insert_access_event(
    db: Session,
    *,
    sucursal_id: Optional[int],
    device_id: int,
    event_type: str,
    subject_usuario_id: Optional[int],
    credential_type: Optional[str],
    credential_hint: Optional[str],
    input_kind: str,
    input_value_masked: Optional[str],
    decision: str,
    reason: str,
    unlock: bool,
    unlock_ms: Optional[int],
    meta: Dict[str, Any],
    event_nonce_hash: Optional[str],
) -> None:
    db.execute(
        text(
            """
            INSERT INTO access_events(
                sucursal_id, device_id, event_type, subject_usuario_id, credential_type, credential_hint,
                input_kind, input_value_masked, decision, reason, unlock, unlock_ms, meta, event_nonce_hash, created_at
            )
            VALUES (
                :sid, :did, :etype, :uid, :ct, :chint,
                :ik, :ivm, :dec, :reason, :unlock, :ums, CAST(:meta AS JSONB), :nh, NOW()
            )
            """
        ),
        {
            "sid": sucursal_id,
            "did": int(device_id),
            "etype": str(event_type or "")[:50],
            "uid": subject_usuario_id,
            "ct": str(credential_type)[:30] if credential_type else None,
            "chint": str(credential_hint)[:80] if credential_hint else None,
            "ik": str(input_kind or "")[:50],
            "ivm": str(input_value_masked or "")[:200] if input_value_masked is not None else None,
            "dec": str(decision or "deny")[:20],
            "reason": str(reason or "")[:500],
            "unlock": bool(unlock),
            "ums": int(unlock_ms) if unlock_ms is not None else None,
            "meta": json.dumps(_sanitize_meta(meta), ensure_ascii=False),
            "nh": str(event_nonce_hash) if event_nonce_hash else None,
        },
    )

def _parse_iso_dt(s: str) -> Optional[datetime]:
    try:
        v = str(s or "").strip()
        if not v:
            return None
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except Exception:
        return None


def _cfg_without_runtime(cfg: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(cfg, dict):
        return {}
    out = dict(cfg)
    out.pop("runtime_status", None)
    return out


def _sanitize_meta(v: Any) -> Dict[str, Any]:
    if not isinstance(v, dict):
        return {}
    out: Dict[str, Any] = {}
    for k, val in v.items():
        ks = str(k or "").strip()
        if not ks or len(ks) > 50:
            continue
        if isinstance(val, (str, int, float, bool)) or val is None:
            if isinstance(val, str) and len(val) > 200:
                out[ks] = val[:200]
            else:
                out[ks] = val
        else:
            out[ks] = str(val)[:200]
        if len(out) >= 30:
            break
    return out


def _sanitize_command_result(v: Any) -> Dict[str, Any]:
    if not isinstance(v, dict):
        return {}
    out: Dict[str, Any] = {}
    for k, val in v.items():
        ks = str(k or "").strip()
        if not ks or len(ks) > 50:
            continue
        if isinstance(val, (str, int, float, bool)) or val is None:
            if isinstance(val, str) and len(val) > 500:
                out[ks] = val[:500]
            else:
                out[ks] = val
        else:
            out[ks] = str(val)[:500]
        if len(out) >= 40:
            break
    return out


def _client_ip(request: Request) -> str:
    try:
        trust_proxy = str(os.getenv("PROXY_HEADERS_ENABLED", "0")).strip().lower() in ("1", "true", "yes", "on")
        if trust_proxy:
            xff = request.headers.get("x-forwarded-for")
            if xff:
                try:
                    return xff.split(",")[0].strip()
                except Exception:
                    return xff.strip()
            xri = request.headers.get("x-real-ip")
            if xri:
                return xri.strip()
        c = getattr(request, "client", None)
        if c and getattr(c, "host", None):
            return c.host
        return "0.0.0.0"
    except Exception:
        return "0.0.0.0"

def _parse_hhmm(s: str) -> Optional[int]:
    try:
        parts = str(s or "").strip().split(":")
        if len(parts) != 2:
            return None
        h = int(parts[0])
        m = int(parts[1])
        if h < 0 or h > 23 or m < 0 or m > 59:
            return None
        return h * 60 + m
    except Exception:
        return None


def _local_now_from_config(cfg: Dict[str, Any]) -> datetime:
    tz_name = str(cfg.get("timezone") or "").strip()
    if not tz_name:
        tz_name = str(os.getenv("APP_TIMEZONE") or os.getenv("TIMEZONE") or os.getenv("TZ") or "").strip()
    if not tz_name:
        tz_name = "America/Argentina/Buenos_Aires"
    try:
        import zoneinfo

        tz = zoneinfo.ZoneInfo(tz_name)
        return datetime.now(timezone.utc).astimezone(tz).replace(tzinfo=None, microsecond=0)
    except Exception:
        return datetime.utcnow().replace(microsecond=0)


def _is_within_allowed_hours(cfg: Dict[str, Any]) -> bool:
    rules = cfg.get("allowed_hours")
    if not isinstance(rules, list) or not rules:
        return True
    now = _local_now_from_config(cfg)
    wd = int(now.isoweekday())
    minutes = int(now.hour) * 60 + int(now.minute)
    for r in rules:
        if not isinstance(r, dict):
            continue
        days = r.get("days")
        if isinstance(days, list) and days:
            try:
                if wd not in [int(x) for x in days if x is not None]:
                    continue
            except Exception:
                pass
        start = _parse_hhmm(r.get("start"))
        end = _parse_hhmm(r.get("end"))
        if start is None or end is None:
            continue
        if start <= end:
            if start <= minutes <= end:
                return True
        else:
            if minutes >= start or minutes <= end:
                return True
    return False


def _allowed_event_types(cfg: Dict[str, Any]) -> Optional[set[str]]:
    v = cfg.get("allowed_event_types")
    if v is None:
        return None
    if not isinstance(v, list):
        return set()
    out: set[str] = set()
    for x in v:
        s = str(x or "").strip().lower()
        if s:
            out.add(s)
    return out


def _deny_if_rate_limited(db: Session, device_id: int, cfg: Dict[str, Any]) -> Optional[str]:
    try:
        max_per_min = int(cfg.get("max_events_per_minute") or 0)
    except Exception:
        max_per_min = 0
    if max_per_min <= 0:
        return None
    window_seconds = 60
    try:
        window_seconds = int(cfg.get("rate_limit_window_seconds") or 60)
    except Exception:
        window_seconds = 60
    window_seconds = max(5, min(window_seconds, 300))
    try:
        c = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM access_events
                WHERE device_id = :did AND created_at >= (NOW() - (:win || ' seconds')::interval)
                """
            ),
            {"did": int(device_id), "win": int(window_seconds)},
        ).scalar()
        if c is not None and int(c) >= int(max_per_min):
            return "Rate limit"
    except Exception:
        return None
    return None


def _deny_if_anti_passback(db: Session, usuario_id: int, sid: Optional[int], cfg: Dict[str, Any]) -> Optional[str]:
    try:
        apb = int(cfg.get("anti_passback_seconds") or 0)
    except Exception:
        apb = 0
    if apb <= 0:
        return None
    apb = max(5, min(apb, 24 * 3600))
    try:
        row = db.execute(
            text(
                """
                SELECT created_at
                FROM access_events
                WHERE subject_usuario_id = :uid
                  AND decision = 'allow'
                  AND unlock = TRUE
                  AND (:sid IS NULL OR sucursal_id = :sid)
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"uid": int(usuario_id), "sid": int(sid) if sid is not None else None},
        ).fetchone()
        if not row or not row[0]:
            return None
        last = row[0]
        if isinstance(last, str):
            try:
                last_dt = datetime.fromisoformat(last)
            except Exception:
                return None
        else:
            last_dt = last
        if not isinstance(last_dt, datetime):
            return None
        if (datetime.utcnow() - last_dt).total_seconds() < float(apb):
            return "Anti-passback"
    except Exception:
        return None
    return None


def _require_device(request: Request, db: Session) -> Dict[str, Any]:
    device_public_id = str(request.headers.get("x-device-id") or "").strip()
    token = _extract_device_token(request)
    if not device_public_id or not token:
        raise HTTPException(status_code=401, detail="Device no autenticado")
    row = db.execute(
        text(
            """
            SELECT id, sucursal_id, enabled, token_hash, config
            FROM access_devices
            WHERE device_public_id = :pid
            LIMIT 1
            """
        ),
        {"pid": device_public_id},
    ).mappings().first()
    if not row or not row.get("enabled"):
        raise HTTPException(status_code=401, detail="Device inválido")
    if str(row.get("token_hash") or "") != _sha256(token):
        raise HTTPException(status_code=401, detail="Device inválido")
    try:
        db.execute(
            text("UPDATE access_devices SET last_seen_at = NOW(), updated_at = NOW() WHERE id = :id"),
            {"id": int(row["id"])},
        )
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
    return dict(row)


@router.get("/api/access/device/config", dependencies=[Depends(require_feature("accesos"))])
async def api_access_device_config(request: Request, db: Session = Depends(get_db_session)):
    device = _require_device(request, db)
    cfg = device.get("config") if isinstance(device.get("config"), dict) else {}
    return {"ok": True, "config": _cfg_without_runtime(cfg), "sucursal_id": device.get("sucursal_id")}


@router.post("/api/access/device/enrollment/clear", dependencies=[Depends(require_feature("accesos"))])
async def api_access_device_clear_enrollment(request: Request, db: Session = Depends(get_db_session)):
    device = _require_device(request, db)
    db.execute(
        text(
            """
            UPDATE access_devices
            SET config = jsonb_set((COALESCE(config, '{}'::jsonb) - 'enroll_mode'), '{runtime_status}', (:rt)::jsonb, TRUE), updated_at = NOW()
            WHERE id = :id
            """
        ),
        {"id": int(device["id"]), "rt": json.dumps({"updated_at": datetime.now(timezone.utc).isoformat(), "enroll_ready": False})},
    )
    db.commit()
    return {"ok": True}


@router.post("/api/access/device/status", dependencies=[Depends(require_feature("accesos"))])
async def api_access_device_status(request: Request, db: Session = Depends(get_db_session)):
    device = _require_device(request, db)
    payload = {}
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    cfg = device.get("config") if isinstance(device.get("config"), dict) else {}
    enroll = cfg.get("enroll_mode") if isinstance(cfg.get("enroll_mode"), dict) else {}
    exp = _parse_iso_dt(str(enroll.get("expires_at") or ""))
    if exp and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    enroll_active = bool(enroll.get("enabled")) and (not exp or exp >= datetime.now(timezone.utc))
    enroll_ready = bool((payload or {}).get("enroll_ready")) and enroll_active
    test = (payload or {}).get("test")
    test_out: Optional[Dict[str, Any]] = None
    if isinstance(test, dict):
        kind = str(test.get("kind") or "").strip().lower()[:40]
        ok = bool(test.get("ok"))
        detail = str(test.get("detail") or "").strip()[:160]
        if kind:
            test_out = {"kind": kind, "ok": ok, "detail": detail or None, "at": datetime.now(timezone.utc).isoformat()}
    runtime = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "enroll_ready": bool(enroll_ready),
        "enroll_usuario_id": int(enroll.get("usuario_id") or 0) if enroll_active else None,
        "enroll_credential_type": str(enroll.get("credential_type") or "") if enroll_active else None,
        "input_source": str((payload or {}).get("input_source") or "")[:32] or None,
        "input_protocol": str((payload or {}).get("input_protocol") or "")[:32] or None,
        "serial_port": str((payload or {}).get("serial_port") or "")[:32] or None,
        "last_test": test_out,
    }
    db.execute(
        text(
            """
            UPDATE access_devices
            SET config = jsonb_set(COALESCE(config, '{}'::jsonb), '{runtime_status}', (:rt)::jsonb, TRUE),
                last_seen_at = NOW(),
                updated_at = NOW()
            WHERE id = :id
            """
        ),
        {"id": int(device["id"]), "rt": json.dumps(runtime)},
    )
    db.commit()
    return {"ok": True, "runtime_status": runtime}


@router.get("/api/access/device/commands", dependencies=[Depends(require_feature("accesos"))])
async def api_access_device_commands(request: Request, db: Session = Depends(get_db_session)):
    device = _require_device(request, db)
    try:
        lim = int(request.query_params.get("limit") or 5)
    except Exception:
        lim = 5
    lim = max(1, min(lim, 20))
    try:
        rows = db.execute(
            text(
                """
                WITH picked AS (
                    SELECT id
                    FROM access_commands
                    WHERE device_id = :did
                      AND status = 'pending'
                      AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY id ASC
                    LIMIT :lim
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE access_commands
                SET status = 'claimed', claimed_at = NOW()
                WHERE id IN (SELECT id FROM picked)
                RETURNING id, command_type, payload, created_at
                """
            ),
            {"did": int(device["id"]), "lim": lim},
        ).mappings().all()
        try:
            db.commit()
        except Exception:
            db.rollback()
        items: List[Dict[str, Any]] = []
        for r in rows:
            items.append(
                {
                    "id": int(r.get("id") or 0),
                    "type": str(r.get("command_type") or ""),
                    "payload": r.get("payload") if isinstance(r.get("payload"), dict) else {},
                    "created_at": (r.get("created_at").isoformat() if hasattr(r.get("created_at"), "isoformat") else str(r.get("created_at") or "")),
                }
            )
        return {"ok": True, "items": items}
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return {"ok": True, "items": []}


@router.post("/api/access/device/commands/{command_id}/ack", dependencies=[Depends(require_feature("accesos"))])
async def api_access_device_command_ack(command_id: int, request: Request, db: Session = Depends(get_db_session)):
    device = _require_device(request, db)
    payload = {}
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    ok = bool((payload or {}).get("ok", True))
    result = _sanitize_command_result((payload or {}).get("result"))
    result["ok"] = bool(ok)
    row = db.execute(
        text("SELECT status FROM access_commands WHERE id = :id AND device_id = :did LIMIT 1"),
        {"id": int(command_id), "did": int(device["id"])},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Comando no encontrado")
    status = str(row.get("status") or "").strip().lower()
    if status == "acked":
        return {"ok": True, "idempotent": True}
    db.execute(
        text(
            """
            UPDATE access_commands
            SET status = 'acked', acked_at = NOW(), result = CAST(:res AS JSONB)
            WHERE id = :id AND device_id = :did
            """
        ),
        {"id": int(command_id), "did": int(device["id"]), "res": json.dumps(result, ensure_ascii=False)},
    )
    try:
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
    return {"ok": True}


@router.get(
    "/api/access/bootstrap",
    dependencies=[Depends(require_gestion_access), Depends(require_feature("accesos")), Depends(require_scope_gestion("accesos:read"))],
)
async def api_access_bootstrap(request: Request, db: Session = Depends(get_db_session)):
    claims = get_claims(request)
    return {"ok": True, "tenant": str(claims.get("tenant") or "").strip().lower()}


@router.get(
    "/api/access/devices",
    dependencies=[Depends(require_gestion_access), Depends(require_feature("accesos")), Depends(require_scope_gestion("accesos:read"))],
)
async def api_access_list_devices(db: Session = Depends(get_db_session)):
    rows = db.execute(
        text(
            """
            SELECT id, sucursal_id, name, enabled, device_public_id, config, last_seen_at, created_at, updated_at
            FROM access_devices
            ORDER BY id DESC
            """
        )
    ).mappings().all()
    return {"ok": True, "items": [dict(r) for r in rows]}


@router.get(
    "/api/access/devices/{device_id}/commands",
    dependencies=[Depends(require_gestion_access), Depends(require_feature("accesos")), Depends(require_scope_gestion("accesos:read"))],
)
async def api_access_list_device_commands(device_id: int, limit: int = 50, db: Session = Depends(get_db_session)):
    l = max(1, min(int(limit or 50), 200))
    rows = db.execute(
        text(
            """
            SELECT id, device_id, command_type, status, request_id, actor_usuario_id,
                   payload, result, created_at, claimed_at, acked_at, expires_at
            FROM access_commands
            WHERE device_id = :did
            ORDER BY id DESC
            LIMIT :lim
            """
        ),
        {"did": int(device_id), "lim": l},
    ).mappings().all()
    return {"ok": True, "items": [dict(r) for r in rows]}


@router.post(
    "/api/access/devices/{device_id}/commands/{command_id}/cancel",
    dependencies=[Depends(require_gestion_access), Depends(require_feature("accesos")), Depends(require_scope_gestion("accesos:write"))],
)
async def api_access_cancel_device_command(device_id: int, command_id: int, db: Session = Depends(get_db_session)):
    row = db.execute(
        text("SELECT status FROM access_commands WHERE id = :id AND device_id = :did LIMIT 1"),
        {"id": int(command_id), "did": int(device_id)},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Comando no encontrado")
    status = str(row.get("status") or "").strip().lower()
    if status in ("acked", "canceled", "cancelled"):
        return {"ok": True, "idempotent": True}
    db.execute(
        text(
            """
            UPDATE access_commands
            SET status = 'canceled', expires_at = NOW()
            WHERE id = :id AND device_id = :did
            """
        ),
        {"id": int(command_id), "did": int(device_id)},
    )
    try:
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="No se pudo cancelar")
    return {"ok": True}


@router.post(
    "/api/access/devices/{device_id}/enrollment",
    dependencies=[Depends(require_gestion_access), Depends(require_feature("accesos")), Depends(require_scope_gestion("accesos:write"))],
)
async def api_access_device_start_enrollment(device_id: int, request: Request, db: Session = Depends(get_db_session)):
    payload = {}
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    usuario_id = (payload or {}).get("usuario_id")
    credential_type = str((payload or {}).get("credential_type") or "fob").strip().lower()[:30]
    overwrite = bool((payload or {}).get("overwrite", True))
    try:
        expires_seconds = int((payload or {}).get("expires_seconds") or 90)
    except Exception:
        expires_seconds = 90
    expires_seconds = max(15, min(expires_seconds, 10 * 60))
    if not usuario_id:
        raise HTTPException(status_code=400, detail="usuario_id requerido")
    if credential_type not in ("fob", "card"):
        raise HTTPException(status_code=400, detail="Tipo inválido")

    row = db.execute(
        text("SELECT id, sucursal_id, enabled FROM access_devices WHERE id = :id LIMIT 1"),
        {"id": int(device_id)},
    ).mappings().first()
    if not row or not row.get("enabled"):
        raise HTTPException(status_code=404, detail="Device no encontrado")
    if row.get("sucursal_id") is None:
        raise HTTPException(status_code=400, detail="El device debe estar vinculado a una sucursal")

    expires_at = (_utcnow() + timedelta(seconds=expires_seconds)).replace(tzinfo=timezone.utc).isoformat()
    enroll = {"enabled": True, "usuario_id": int(usuario_id), "credential_type": credential_type, "overwrite": overwrite, "expires_at": expires_at}
    db.execute(
        text(
            """
            UPDATE access_devices
            SET config = jsonb_set(jsonb_set(COALESCE(config, '{}'::jsonb), '{enroll_mode}', (:enroll)::jsonb, TRUE), '{runtime_status}', (:rt)::jsonb, TRUE),
                updated_at = NOW()
            WHERE id = :id
            """
        ),
        {"id": int(device_id), "enroll": json.dumps(enroll), "rt": json.dumps({"updated_at": datetime.now(timezone.utc).isoformat(), "enroll_ready": False})},
    )
    db.commit()
    return {"ok": True, "enroll_mode": enroll}


@router.post(
    "/api/access/devices/{device_id}/enrollment/clear",
    dependencies=[Depends(require_gestion_access), Depends(require_feature("accesos")), Depends(require_scope_gestion("accesos:write"))],
)
async def api_access_device_clear_enrollment_gestion(device_id: int, db: Session = Depends(get_db_session)):
    db.execute(
        text(
            """
            UPDATE access_devices
            SET config = jsonb_set((COALESCE(config, '{}'::jsonb) - 'enroll_mode'), '{runtime_status}', (:rt)::jsonb, TRUE), updated_at = NOW()
            WHERE id = :id
            """
        ),
        {"id": int(device_id), "rt": json.dumps({"updated_at": datetime.now(timezone.utc).isoformat(), "enroll_ready": False})},
    )
    db.commit()
    return {"ok": True}


@router.post(
    "/api/access/devices",
    dependencies=[Depends(require_gestion_access), Depends(require_feature("accesos")), Depends(require_scope_gestion("accesos:write"))],
)
async def api_access_create_device(request: Request, db: Session = Depends(get_db_session)):
    payload = {}
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    name = str((payload or {}).get("name") or "").strip()[:120] or "Device"
    sucursal_id = (payload or {}).get("sucursal_id")
    try:
        sucursal_id = int(sucursal_id) if sucursal_id is not None else None
    except Exception:
        sucursal_id = None
    device_public_id = secrets.token_urlsafe(16)[:32]
    pairing_code = (secrets.token_urlsafe(8)[:10]).replace("-", "").replace("_", "")
    pairing_expires_at = _utcnow() + timedelta(minutes=30)
    config = (payload or {}).get("config")
    if not isinstance(config, dict):
        config = {}
    config = normalize_access_device_config(config)
    db.execute(
        text(
            """
            INSERT INTO access_devices(sucursal_id, name, enabled, device_public_id, token_hash, pairing_code_hash, pairing_expires_at, config, created_at, updated_at)
            VALUES (:sid, :name, TRUE, :pid, NULL, :pch, :pexp, CAST(:cfg AS JSONB), NOW(), NOW())
            """
        ),
        {
            "sid": sucursal_id,
            "name": name,
            "pid": device_public_id,
            "pch": _sha256(pairing_code),
            "pexp": pairing_expires_at,
            "cfg": json.dumps(config or {}, ensure_ascii=False),
        },
    )
    db.commit()
    row = db.execute(
        text("SELECT id FROM access_devices WHERE device_public_id = :pid LIMIT 1"),
        {"pid": device_public_id},
    ).mappings().first()
    return {
        "ok": True,
        "device": {"id": int(row["id"]) if row else None, "name": name, "sucursal_id": sucursal_id, "device_public_id": device_public_id},
        "pairing_code": pairing_code,
        "pairing_expires_at": pairing_expires_at.isoformat(),
    }


@router.post(
    "/api/access/devices/{device_id}/rotate-pairing",
    dependencies=[Depends(require_gestion_access), Depends(require_feature("accesos")), Depends(require_scope_gestion("accesos:write"))],
)
async def api_access_rotate_pairing(device_id: int, db: Session = Depends(get_db_session)):
    pairing_code = (secrets.token_urlsafe(8)[:10]).replace("-", "").replace("_", "")
    pairing_expires_at = _utcnow() + timedelta(minutes=30)
    db.execute(
        text(
            """
            UPDATE access_devices
            SET pairing_code_hash = :pch, pairing_expires_at = :pexp, updated_at = NOW()
            WHERE id = :id
            """
        ),
        {"pch": _sha256(pairing_code), "pexp": pairing_expires_at, "id": int(device_id)},
    )
    db.commit()
    return {"ok": True, "pairing_code": pairing_code, "pairing_expires_at": pairing_expires_at.isoformat()}


@router.post(
    "/api/access/devices/{device_id}/revoke-token",
    dependencies=[Depends(require_gestion_access), Depends(require_feature("accesos")), Depends(require_scope_gestion("accesos:write"))],
)
async def api_access_revoke_device_token(device_id: int, db: Session = Depends(get_db_session)):
    db.execute(
        text("UPDATE access_devices SET token_hash = NULL, updated_at = NOW() WHERE id = :id"),
        {"id": int(device_id)},
    )
    db.commit()
    return {"ok": True}


@router.patch(
    "/api/access/devices/{device_id}",
    dependencies=[Depends(require_gestion_access), Depends(require_feature("accesos")), Depends(require_scope_gestion("accesos:write"))],
)
async def api_access_update_device(request: Request, device_id: int, db: Session = Depends(get_db_session)):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    name = payload.get("name")
    enabled = payload.get("enabled")
    sucursal_id = payload.get("sucursal_id")
    config = payload.get("config")
    updates = []
    params: Dict[str, Any] = {"id": int(device_id)}
    if name is not None:
        updates.append("name = :name")
        params["name"] = str(name).strip()[:120] or "Device"
    if enabled is not None:
        updates.append("enabled = :enabled")
        params["enabled"] = bool(enabled)
    if sucursal_id is not None:
        try:
            sid = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sid = None
        updates.append("sucursal_id = :sid")
        params["sid"] = sid
    if config is not None:
        if not isinstance(config, dict):
            config = {}
        config = normalize_access_device_config(config)
        updates.append("config = CAST(:config AS JSONB)")
        params["config"] = json.dumps(config, ensure_ascii=False)
    if not updates:
        return {"ok": True}
    updates.append("updated_at = NOW()")
    db.execute(text(f"UPDATE access_devices SET {', '.join(updates)} WHERE id = :id"), params)
    db.commit()
    return {"ok": True}


@router.post(
    "/api/access/devices/{device_id}/remote-unlock",
    dependencies=[Depends(require_gestion_access), Depends(require_feature("accesos")), Depends(require_scope_gestion("accesos:write"))],
)
async def api_access_device_remote_unlock(device_id: int, request: Request, db: Session = Depends(get_db_session)):
    claims = get_claims(request)
    payload = {}
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    try:
        unlock_ms = int((payload or {}).get("unlock_ms") or 0)
    except Exception:
        unlock_ms = 0
    unlock_ms = max(0, min(unlock_ms, 15000))
    reason = str((payload or {}).get("reason") or "remote_unlock").strip()[:200] or "remote_unlock"
    request_id = str((payload or {}).get("request_id") or "").strip()[:80] or None
    if not request_id:
        request_id = secrets.token_urlsafe(18)[:40]

    row = db.execute(
        text("SELECT id, sucursal_id, enabled, device_public_id, config FROM access_devices WHERE id = :id LIMIT 1"),
        {"id": int(device_id)},
    ).mappings().first()
    if not row or not row.get("enabled"):
        raise HTTPException(status_code=404, detail="Device no encontrado")
    cfg = row.get("config") if isinstance(row.get("config"), dict) else {}
    if not bool(cfg.get("allow_remote_unlock")):
        raise HTTPException(status_code=400, detail="Remote unlock deshabilitado en el device")

    cmd_payload = {"unlock_ms": unlock_ms} if unlock_ms > 0 else {}
    try:
        inserted = db.execute(
            text(
                """
                INSERT INTO access_commands(device_id, command_type, payload, status, request_id, actor_usuario_id, expires_at, created_at)
                VALUES (:did, 'unlock', CAST(:p AS JSONB), 'pending', :rid, :actor, NOW() + INTERVAL '30 seconds', NOW())
                ON CONFLICT (device_id, request_id) DO UPDATE
                SET created_at = access_commands.created_at
                RETURNING id
                """
            ),
            {
                "did": int(row["id"]),
                "p": json.dumps(cmd_payload, ensure_ascii=False),
                "rid": str(request_id) if request_id else None,
                "actor": int(claims.get("user_id") or 0) if claims.get("user_id") else None,
            },
        ).fetchone()
        cmd_id = int(inserted[0]) if inserted and inserted[0] is not None else None
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="No se pudo encolar comando")

    meta = {"actor_user_id": claims.get("user_id"), "reason": reason, "command_id": cmd_id, "source": "gestion"}
    try:
        db.execute(
            text(
                """
                INSERT INTO access_events(
                    sucursal_id, device_id, event_type, subject_usuario_id, credential_type, credential_hint,
                    input_kind, input_value_masked, decision, reason, unlock, unlock_ms, meta, event_nonce_hash, created_at
                )
                VALUES (
                    :sid, :did, 'remote_unlock', NULL, NULL, NULL,
                    'remote', NULL, 'allow', :reason, TRUE, :ums, CAST(:meta AS JSONB), NULL, NOW()
                )
                """
            ),
            {
                "sid": int(row["sucursal_id"]) if row.get("sucursal_id") is not None else None,
                "did": int(row["id"]),
                "reason": reason[:500],
                "ums": unlock_ms if unlock_ms > 0 else None,
                "meta": json.dumps(_sanitize_meta(meta), ensure_ascii=False),
            },
        )
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        db.execute(
            text(
                """
                INSERT INTO access_events(sucursal_id, device_id, event_type, decision, reason, unlock, unlock_ms, meta, created_at)
                VALUES (:sid, :did, 'remote_unlock', 'allow', :reason, TRUE, :ums, CAST(:meta AS JSONB), NOW())
                """
            ),
            {
                "sid": int(row["sucursal_id"]) if row.get("sucursal_id") is not None else None,
                "did": int(row["id"]),
                "reason": reason[:500],
                "ums": unlock_ms if unlock_ms > 0 else None,
                "meta": json.dumps(_sanitize_meta(meta), ensure_ascii=False),
            },
        )

    db.commit()
    return {"ok": True, "command_id": cmd_id, "request_id": request_id}


@router.post("/api/access/devices/pair", dependencies=[Depends(require_feature("accesos"))])
async def api_access_pair_device(request: Request, db: Session = Depends(get_db_session)):
    payload = {}
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    tenant = str(request.headers.get("x-tenant") or "").strip().lower()[:80] or "tenant"
    ip = _client_ip(request)[:80]
    limited, _count = incr_and_check(f"pair:ip:{tenant}:{ip}", 60, 20)
    if limited:
        raise HTTPException(status_code=429, detail="Rate limit", headers={"Retry-After": "30"})
    device_public_id = str((payload or {}).get("device_id") or "").strip()
    pairing_code = str((payload or {}).get("pairing_code") or "").strip()
    if not device_public_id or not pairing_code:
        raise HTTPException(status_code=400, detail="Datos inválidos")
    limited_dev, _count2 = incr_and_check(f"pair:device:{tenant}:{device_public_id[:80]}", 60, 10)
    if limited_dev:
        raise HTTPException(status_code=429, detail="Rate limit", headers={"Retry-After": "30"})
    row = db.execute(
        text(
            """
            SELECT id, enabled, pairing_code_hash, pairing_expires_at, config
            FROM access_devices
            WHERE device_public_id = :pid
            LIMIT 1
            """
        ),
        {"pid": device_public_id},
    ).mappings().first()
    if not row or not row.get("enabled"):
        raise HTTPException(status_code=404, detail="Device no encontrado")
    exp = row.get("pairing_expires_at")
    if exp is not None:
        try:
            if isinstance(exp, str):
                exp_dt = datetime.fromisoformat(exp)
            else:
                exp_dt = exp
            if exp_dt and exp_dt < _utcnow():
                raise HTTPException(status_code=400, detail="Pairing vencido")
        except HTTPException:
            raise
        except Exception:
            pass
    if not secrets.compare_digest(str(row.get("pairing_code_hash") or ""), _sha256(pairing_code)):
        raise HTTPException(status_code=400, detail="Pairing inválido")
    token = secrets.token_urlsafe(32)
    db.execute(
        text(
            """
            UPDATE access_devices
            SET token_hash = :th, pairing_code_hash = NULL, pairing_expires_at = NULL, updated_at = NOW(), last_seen_at = NOW()
            WHERE id = :id
            """
        ),
        {"th": _sha256(token), "id": int(row["id"])},
    )
    db.commit()
    cfg = row.get("config") if isinstance(row.get("config"), dict) else {}
    return {"ok": True, "token": token, "device": {"id": int(row["id"]), "device_public_id": device_public_id, "config": cfg}}


@router.get(
    "/api/access/credentials",
    dependencies=[Depends(require_gestion_access), Depends(require_feature("accesos")), Depends(require_scope_gestion("accesos:read"))],
)
async def api_access_list_credentials(db: Session = Depends(get_db_session), usuario_id: Optional[int] = None):
    where = ""
    params: Dict[str, Any] = {}
    if usuario_id is not None:
        where = "WHERE usuario_id = :uid"
        params["uid"] = int(usuario_id)
    rows = db.execute(
        text(
            f"""
            SELECT id, usuario_id, credential_type, label, active, created_at, updated_at
            FROM access_credentials
            {where}
            ORDER BY id DESC
            """
        ),
        params,
    ).mappings().all()
    return {"ok": True, "items": [dict(r) for r in rows]}


@router.post(
    "/api/access/credentials",
    dependencies=[Depends(require_gestion_access), Depends(require_feature("accesos")), Depends(require_scope_gestion("accesos:write"))],
)
async def api_access_create_credential(request: Request, db: Session = Depends(get_db_session)):
    payload = {}
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    usuario_id = (payload or {}).get("usuario_id")
    credential_type = str((payload or {}).get("credential_type") or "fob").strip().lower()[:30]
    value = str((payload or {}).get("value") or "").strip()
    label = str((payload or {}).get("label") or "").strip()[:120] or None
    if not usuario_id or not value:
        raise HTTPException(status_code=400, detail="Datos inválidos")
    if credential_type not in ("fob", "card", "pin"):
        raise HTTPException(status_code=400, detail="Tipo inválido")
    norm = _normalize_credential(value)
    if not norm:
        raise HTTPException(status_code=400, detail="Credencial inválida")
    if not label:
        tail = norm[-4:] if len(norm) >= 4 else norm
        label = f"{credential_type.upper()} ••••{tail}"
    h = _sha256(f"{credential_type}:{norm}")
    try:
        db.execute(
            text(
                """
                INSERT INTO access_credentials(usuario_id, credential_type, credential_hash, label, active, created_at, updated_at)
                VALUES (:uid, :ct, :ch, :label, TRUE, NOW(), NOW())
                """
            ),
            {"uid": int(usuario_id), "ct": credential_type, "ch": h, "label": label},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Credencial ya usada")
    return {"ok": True}


@router.get("/api/usuario/credentials", dependencies=[Depends(require_user_auth), Depends(require_feature("accesos"))])
async def api_usuario_access_credentials(request: Request, db: Session = Depends(get_db_session)):
    claims = get_claims(request)
    try:
        uid = int(claims.user_id or 0)
    except Exception:
        uid = 0
    if not uid:
        raise HTTPException(status_code=401, detail="No autenticado")
    rows = db.execute(
        text(
            """
            SELECT id, usuario_id, credential_type, label, active, created_at, updated_at
            FROM access_credentials
            WHERE usuario_id = :uid
            ORDER BY id DESC
            """
        ),
        {"uid": int(uid)},
    ).mappings().all()
    return {"ok": True, "items": [dict(r) for r in rows]}


@router.delete(
    "/api/access/credentials/{credential_id}",
    dependencies=[Depends(require_gestion_access), Depends(require_feature("accesos")), Depends(require_scope_gestion("accesos:write"))],
)
async def api_access_delete_credential(credential_id: int, db: Session = Depends(get_db_session)):
    db.execute(text("UPDATE access_credentials SET active = FALSE, updated_at = NOW() WHERE id = :id"), {"id": int(credential_id)})
    db.commit()
    return {"ok": True}


@router.post("/api/access/events", dependencies=[Depends(require_feature("accesos"))])
async def api_access_event(request: Request, db: Session = Depends(get_db_session)):
    device = _require_device(request, db)
    event_nonce = _extract_event_nonce(request)
    if not _is_nonce_valid(event_nonce):
        raise HTTPException(status_code=400, detail="X-Event-Nonce requerido")
    event_nonce_hash = _sha256(event_nonce) if event_nonce else None
    if event_nonce_hash:
        prev = db.execute(
            text(
                """
                SELECT decision, reason, unlock, unlock_ms
                FROM access_events
                WHERE device_id = :did AND event_nonce_hash = :nh
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"did": int(device["id"]), "nh": str(event_nonce_hash)},
        ).mappings().first()
        if prev:
            return {
                "ok": True,
                "decision": str(prev.get("decision") or "deny"),
                "reason": str(prev.get("reason") or ""),
                "unlock": bool(prev.get("unlock")),
                "unlock_ms": int(prev.get("unlock_ms")) if prev.get("unlock_ms") is not None else None,
                "idempotent": True,
            }
    payload = {}
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    event_type = str((payload or {}).get("event_type") or "").strip().lower()
    value = str((payload or {}).get("value") or "").strip()
    if len(value) > 512:
        value = value[:512]
    meta = _sanitize_meta((payload or {}).get("meta"))
    if not event_type:
        raise HTTPException(status_code=400, detail="event_type requerido")

    sid = device.get("sucursal_id")
    try:
        sid = int(sid) if sid is not None else None
    except Exception:
        sid = None

    if sid is None:
        decision = "deny"
        reason = "Device no asociado a una sucursal"
        unlock = False
        unlock_ms = None
        try:
            _insert_access_event(
                db,
                sucursal_id=None,
                device_id=int(device["id"]),
                event_type=event_type,
                subject_usuario_id=None,
                credential_type=None,
                credential_hint=None,
                input_kind=event_type,
                input_value_masked=_mask_value(value),
                decision=decision,
                reason=reason,
                unlock=unlock,
                unlock_ms=unlock_ms,
                meta=meta,
                event_nonce_hash=event_nonce_hash,
            )
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
        return {"ok": True, "decision": decision, "reason": reason, "unlock": unlock, "unlock_ms": unlock_ms}

    decision = "deny"
    reason = "No autorizado"
    unlock = False
    unlock_ms = None
    subject_usuario_id = None
    input_kind = event_type
    input_value_masked = _mask_value(value)
    credential_type = None
    credential_hint = None

    dev_cfg = device.get("config") if isinstance(device.get("config"), dict) else {}
    allowed = _allowed_event_types(dev_cfg)
    if allowed is not None and event_type != "enroll_credential":
        if event_type not in allowed:
            decision = "deny"
            reason = "Tipo no habilitado"
            unlock = False
            unlock_ms = None
            try:
                _insert_access_event(
                    db,
                    sucursal_id=sid,
                    device_id=int(device["id"]),
                    event_type=event_type,
                    subject_usuario_id=None,
                    credential_type=None,
                    credential_hint=None,
                    input_kind=input_kind,
                    input_value_masked=input_value_masked,
                    decision=decision,
                    reason=reason,
                    unlock=unlock,
                    unlock_ms=unlock_ms,
                    meta=meta,
                    event_nonce_hash=event_nonce_hash,
                )
                db.commit()
            except Exception:
                try:
                    db.rollback()
                except Exception:
                    pass
            return {"ok": True, "decision": decision, "reason": reason, "unlock": unlock, "unlock_ms": unlock_ms}
    if not _is_within_allowed_hours(dev_cfg):
        decision = "deny"
        reason = "Fuera de horario"
        unlock = False
        unlock_ms = None
        try:
            _insert_access_event(
                db,
                sucursal_id=sid,
                device_id=int(device["id"]),
                event_type=event_type,
                subject_usuario_id=None,
                credential_type=None,
                credential_hint=None,
                input_kind=input_kind,
                input_value_masked=input_value_masked,
                decision=decision,
                reason=reason,
                unlock=unlock,
                unlock_ms=unlock_ms,
                meta=meta,
                event_nonce_hash=event_nonce_hash,
            )
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
        return {"ok": True, "decision": decision, "reason": reason, "unlock": unlock, "unlock_ms": unlock_ms}
    rl_reason = _deny_if_rate_limited(db, int(device["id"]), dev_cfg)
    if rl_reason:
        decision = "deny"
        reason = rl_reason
        unlock = False
        unlock_ms = None
        try:
            _insert_access_event(
                db,
                sucursal_id=sid,
                device_id=int(device["id"]),
                event_type=event_type,
                subject_usuario_id=None,
                credential_type=None,
                credential_hint=None,
                input_kind=input_kind,
                input_value_masked=input_value_masked,
                decision=decision,
                reason=reason,
                unlock=unlock,
                unlock_ms=unlock_ms,
                meta=meta,
                event_nonce_hash=event_nonce_hash,
            )
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
        return {"ok": True, "decision": decision, "reason": reason, "unlock": unlock, "unlock_ms": unlock_ms}
    allow_manual_unlock = bool(dev_cfg.get("allow_manual_unlock", True))
    default_unlock_ms = int(dev_cfg.get("unlock_ms") or 2500)
    default_unlock_ms = max(250, min(default_unlock_ms, 15000))

    attendance_service = AttendanceService(db)

    if event_type == "manual_unlock":
        if allow_manual_unlock:
            decision = "allow"
            reason = "Manual override"
            unlock = True
            unlock_ms = default_unlock_ms
        else:
            decision = "deny"
            reason = "Manual override deshabilitado"

    elif event_type == "dni":
        if bool(dev_cfg.get("dni_requires_pin")):
            decision = "deny"
            reason = "PIN requerido"
        else:
            dni = _digits_only(value)
            if not (7 <= len(dni) <= 9):
                decision = "deny"
                reason = "DNI inválido"
            else:
                try:
                    row = db.execute(text("SELECT id FROM usuarios WHERE dni = :dni LIMIT 1"), {"dni": dni}).fetchone()
                    uid = int(row[0]) if row and row[0] is not None else None
                    if not uid:
                        decision = "deny"
                        reason = "DNI no encontrado"
                    else:
                        subject_usuario_id = int(uid)
                        apb_reason = _deny_if_anti_passback(db, int(subject_usuario_id), sid, dev_cfg)
                        if apb_reason:
                            decision = "deny"
                            reason = apb_reason
                        else:
                            ok, msg = attendance_service.verificar_acceso_usuario_sucursal(int(subject_usuario_id), sid)
                            if not ok:
                                decision = "deny"
                                reason = str(msg or "")
                            else:
                                attendance_service.registrar_asistencia(int(subject_usuario_id), sucursal_id=sid)
                                decision = "allow"
                                reason = "OK"
                                unlock = True
                                unlock_ms = default_unlock_ms
                except Exception:
                    decision = "deny"
                    reason = "Error validando DNI"

    elif event_type == "dni_pin":
        dni_raw = str((payload or {}).get("dni") or "").strip()
        pin = str((payload or {}).get("pin") or "").strip()
        dni = _digits_only(dni_raw)
        if not (7 <= len(dni) <= 9) or not pin:
            decision = "deny"
            reason = "Datos inválidos"
        elif len(pin) < 3 or len(pin) > 8 or any((not ch.isdigit()) for ch in pin):
            decision = "deny"
            reason = "PIN inválido"
        else:
            try:
                row = db.execute(text("SELECT id FROM usuarios WHERE dni = :dni LIMIT 1"), {"dni": dni}).fetchone()
                uid = int(row[0]) if row and row[0] is not None else None
                if not uid:
                    decision = "deny"
                    reason = "DNI no encontrado"
                else:
                    subject_usuario_id = int(uid)
                    apb_reason = _deny_if_anti_passback(db, int(subject_usuario_id), sid, dev_cfg)
                    if apb_reason:
                        decision = "deny"
                        reason = apb_reason
                    else:
                        ok, msg = attendance_service.registrar_asistencia_por_dni_y_pin(dni, pin, sid)
                        decision = "allow" if ok else "deny"
                        reason = str(msg or "")
                        unlock = bool(ok)
                        unlock_ms = default_unlock_ms if ok else None
            except Exception:
                decision = "deny"
                reason = "Error validando DNI"

    elif event_type == "enroll_credential":
        enroll = dev_cfg.get("enroll_mode") if isinstance(dev_cfg.get("enroll_mode"), dict) else {}
        if device.get("sucursal_id") is None:
            decision = "deny"
            reason = "Device sin sucursal"
        elif not enroll or not bool(enroll.get("enabled")):
            decision = "deny"
            reason = "Enroll no activo"
        else:
            try:
                exp = _parse_iso_dt(str(enroll.get("expires_at") or ""))
                if exp and exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp and exp < datetime.now(timezone.utc):
                    decision = "deny"
                    reason = "Enroll vencido"
                else:
                    usuario_id = int((payload or {}).get("usuario_id") or 0)
                    credential_type = str((payload or {}).get("credential_type") or "").strip().lower()[:30]
                    overwrite = bool((payload or {}).get("overwrite", True))
                    if credential_type not in ("fob", "card"):
                        decision = "deny"
                        reason = "Tipo inválido"
                    elif usuario_id <= 0:
                        decision = "deny"
                        reason = "Usuario inválido"
                    elif int(enroll.get("usuario_id") or 0) != int(usuario_id) or str(enroll.get("credential_type") or "") != credential_type:
                        decision = "deny"
                        reason = "Enroll no coincide"
                    else:
                        norm = _normalize_credential(value)
                        if not norm:
                            decision = "deny"
                            reason = "Credencial inválida"
                        else:
                            h = _sha256(f"{credential_type}:{norm}")
                            if overwrite:
                                try:
                                    db.execute(
                                        text(
                                            """
                                            UPDATE access_credentials
                                            SET active = FALSE, updated_at = NOW()
                                            WHERE usuario_id = :uid AND credential_type = :ct
                                            """
                                        ),
                                        {"uid": int(usuario_id), "ct": credential_type},
                                    )
                                except Exception:
                                    pass
                            try:
                                tail = norm[-4:] if len(norm) >= 4 else norm
                                label = f"{credential_type.upper()} ••••{tail}"
                                db.execute(
                                    text(
                                        """
                                        INSERT INTO access_credentials(usuario_id, credential_type, credential_hash, label, active, created_at, updated_at)
                                        VALUES (:uid, :ct, :ch, :label, TRUE, NOW(), NOW())
                                        """
                                    ),
                                    {"uid": int(usuario_id), "ct": credential_type, "ch": h, "label": label},
                                )
                                db.execute(
                                    text(
                                        """
                                        UPDATE access_devices
                                        SET config = jsonb_set((COALESCE(config, '{}'::jsonb) - 'enroll_mode'), '{runtime_status}', (:rt)::jsonb, TRUE), updated_at = NOW()
                                        WHERE id = :id
                                        """
                                    ),
                                    {"id": int(device["id"]), "rt": json.dumps({"updated_at": datetime.now(timezone.utc).isoformat(), "enroll_ready": False})},
                                )
                                db.commit()
                                decision = "allow"
                                reason = "ENROLLED"
                                unlock = False
                                unlock_ms = None
                                subject_usuario_id = int(usuario_id)
                            except Exception:
                                try:
                                    db.rollback()
                                except Exception:
                                    pass
                                decision = "deny"
                                reason = "Credencial ya usada"
            except Exception:
                decision = "deny"
                reason = "Error enroll"

    elif event_type in ("credential", "fob", "card"):
        credential_type = "fob" if event_type in ("credential", "fob") else "card"
        norm = _normalize_credential(value)
        if not norm:
            decision = "deny"
            reason = "Credencial inválida"
        else:
            ch = _sha256(f"{credential_type}:{norm}")
            row = db.execute(
                text(
                    """
                    SELECT usuario_id
                    FROM access_credentials
                    WHERE credential_hash = :ch AND active = TRUE
                    LIMIT 1
                    """
                ),
                {"ch": ch},
            ).mappings().first()
            if not row:
                decision = "deny"
                reason = "Credencial no registrada"
            else:
                try:
                    subject_usuario_id = int(row["usuario_id"])
                except Exception:
                    subject_usuario_id = None
                if subject_usuario_id is None:
                    decision = "deny"
                    reason = "Usuario inválido"
                else:
                    apb_reason = _deny_if_anti_passback(db, int(subject_usuario_id), sid, dev_cfg)
                    if apb_reason:
                        decision = "deny"
                        reason = apb_reason
                    else:
                        ok, msg = attendance_service.verificar_acceso_usuario_sucursal(int(subject_usuario_id), sid)
                        decision = "allow" if ok else "deny"
                        reason = str(msg or "")
                        if ok:
                            try:
                                attendance_service.registrar_asistencia(int(subject_usuario_id), sucursal_id=sid)
                            except Exception:
                                pass
                            unlock = True
                            unlock_ms = default_unlock_ms

    elif event_type == "qr_token":
        token = value
        if not token:
            decision = "deny"
            reason = "Token vacío"
        else:
            try:
                st = attendance_service.obtener_estado_token(token)
                if not st.get("exists"):
                    decision = "deny"
                    reason = "Token no encontrado"
                elif st.get("expired"):
                    decision = "deny"
                    reason = "Token expirado"
                elif st.get("used"):
                    decision = "deny"
                    reason = "Token ya utilizado"
                else:
                    uid = st.get("usuario_id")
                    try:
                        subject_usuario_id = int(uid) if uid is not None else None
                    except Exception:
                        subject_usuario_id = None
                    if subject_usuario_id is None:
                        decision = "deny"
                        reason = "Token inválido"
                    else:
                        apb_reason = _deny_if_anti_passback(db, int(subject_usuario_id), sid, dev_cfg)
                        if apb_reason:
                            decision = "deny"
                            reason = apb_reason
                        else:
                            ok, msg = attendance_service.validar_token_y_registrar_sin_sesion(token, sid)
                            decision = "allow" if ok else "deny"
                            reason = str(msg or "")
                            unlock = bool(ok)
                            unlock_ms = default_unlock_ms if ok else None
            except Exception:
                decision = "deny"
                reason = "Error validando QR"
    else:
        decision = "deny"
        reason = "Tipo no soportado"

    try:
        db.execute(
            text(
                """
                INSERT INTO access_events(
                    sucursal_id, device_id, event_type, subject_usuario_id, credential_type, credential_hint,
                    input_kind, input_value_masked, decision, reason, unlock, unlock_ms, meta, event_nonce_hash, created_at
                )
                VALUES (
                    :sid, :did, :etype, :uid, :ct, :chint,
                    :ik, :ivm, :dec, :reason, :unlock, :ums, CAST(:meta AS JSONB), :nh, NOW()
                )
                """
            ),
            {
                "sid": sid,
                "did": int(device["id"]),
                "etype": event_type,
                "uid": subject_usuario_id,
                "ct": credential_type,
                "chint": credential_hint,
                "ik": input_kind,
                "ivm": input_value_masked,
                "dec": decision,
                "reason": reason[:500],
                "unlock": bool(unlock),
                "ums": int(unlock_ms) if unlock_ms is not None else None,
                "meta": json.dumps(meta, ensure_ascii=False),
                "nh": str(event_nonce_hash) if event_nonce_hash else None,
            },
        )
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass

    return {
        "ok": True,
        "decision": decision,
        "reason": reason,
        "unlock": bool(unlock),
        "unlock_ms": int(unlock_ms) if unlock_ms is not None else None,
    }


@router.get(
    "/api/access/events",
    dependencies=[Depends(require_gestion_access), Depends(require_feature("accesos")), Depends(require_scope_gestion("accesos:read"))],
)
async def api_access_list_events(
    db: Session = Depends(get_db_session),
    page: int = 1,
    limit: int = 50,
    sucursal_id: Optional[int] = None,
    device_id: Optional[int] = None,
):
    p = max(1, int(page or 1))
    l = max(1, min(int(limit or 50), 200))
    off = (p - 1) * l
    where_terms = []
    params: Dict[str, Any] = {"limit": l, "offset": off}
    if sucursal_id is not None:
        where_terms.append("e.sucursal_id = :sid")
        params["sid"] = int(sucursal_id)
    if device_id is not None:
        where_terms.append("e.device_id = :did")
        params["did"] = int(device_id)
    where_sql = ("WHERE " + " AND ".join(where_terms)) if where_terms else ""
    rows = db.execute(
        text(
            f"""
            SELECT
              e.id, e.created_at, e.event_type, e.decision, e.reason, e.unlock, e.unlock_ms,
              e.sucursal_id, e.device_id, e.subject_usuario_id, e.input_value_masked
            FROM access_events e
            {where_sql}
            ORDER BY e.created_at DESC, e.id DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()
    return {"ok": True, "items": [dict(r) for r in rows], "page": p, "limit": l}
