from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.dependencies import get_admin_db, get_claims, get_db_session, require_feature
from src.services.feature_flags_service import FeatureFlagsService


router = APIRouter()


def _now() -> datetime:
    return datetime.utcnow().replace(microsecond=0)


def _row_to_dict(r: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(r or {})
    for k in ("created_at", "updated_at", "published_at"):
        try:
            if out.get(k) is not None and hasattr(out[k], "isoformat"):
                out[k] = out[k].isoformat()
        except Exception:
            pass
    return out


def _parse_version_tuple(v: str) -> List[int]:
    s = str(v or "").strip().lower()
    if s.startswith("v"):
        s = s[1:]
    parts = []
    for seg in s.split("."):
        seg = seg.strip()
        if not seg:
            continue
        n = ""
        for ch in seg:
            if ch.isdigit():
                n += ch
            else:
                break
        try:
            parts.append(int(n) if n else 0)
        except Exception:
            parts.append(0)
    return parts


def _version_gte(v: str, min_v: str) -> bool:
    a = _parse_version_tuple(v)
    b = _parse_version_tuple(min_v)
    if not b:
        return True
    while len(a) < len(b):
        a.append(0)
    while len(b) < len(a):
        b.append(0)
    return a >= b


def _modules_enabled(modules: Dict[str, Any], required: Any) -> bool:
    if not isinstance(required, list) or not required:
        return True
    for m in required:
        k = str(m or "").strip()
        if not k:
            continue
        if not bool(modules.get(k)):
            return False
    return True


def _norm_tenant_list(x: Any) -> List[str]:
    if not isinstance(x, list):
        return []
    out: List[str] = []
    for it in x:
        s = str(it or "").strip().lower()
        if s:
            out.append(s)
    return out


def _sql_audience_where() -> str:
    return """
        (
          audience_roles IS NULL
          OR jsonb_typeof(audience_roles) <> 'array'
          OR jsonb_array_length(audience_roles) = 0
          OR audience_roles ? :role
        )
        AND
        (
          audience_tenants IS NULL
          OR jsonb_typeof(audience_tenants) <> 'object'
          OR (
            (
              jsonb_array_length(COALESCE(audience_tenants->'include','[]'::jsonb)) = 0
              OR COALESCE(audience_tenants->'include','[]'::jsonb) ? :tenant
            )
            AND NOT (COALESCE(audience_tenants->'exclude','[]'::jsonb) ? :tenant)
          )
        )
    """


@router.get("/api/changelogs/status", dependencies=[Depends(require_feature("novedades"))])
async def api_changelog_status(
    request: Request,
    db: Session = Depends(get_admin_db),
    tenant_db: Session = Depends(get_db_session),
):
    claims = get_claims(request)
    tenant = str(claims.get("tenant") or "").strip().lower()
    user_id = claims.get("user_id")
    role = str(claims.get("role") or "user").strip().lower() or "user"
    if not tenant or not user_id:
        return {"ok": True, "has_unread": False, "latest": None}

    modules: Dict[str, Any] = {}
    try:
        sid = claims.get("sucursal_id")
        modules = (FeatureFlagsService(tenant_db).get_flags(sucursal_id=sid) or {}).get("modules") or {}
        if not isinstance(modules, dict):
            modules = {}
    except Exception:
        modules = {}

    app_ver = str(request.headers.get("x-app-version") or "").strip()

    latest_row = db.execute(
        text(
            f"""
            SELECT id, published_at, pinned, min_app_version, audience_modules
            FROM changelogs
            WHERE is_published = TRUE AND published_at IS NOT NULL
              AND {_sql_audience_where()}
            ORDER BY pinned DESC, published_at DESC, id DESC
            LIMIT 25
            """
        ),
        {"tenant": tenant, "role": role},
    ).mappings().all()
    latest = None
    for r in latest_row:
        if not _modules_enabled(modules, r.get("audience_modules")):
            continue
        min_v = str(r.get("min_app_version") or "").strip()
        if min_v and app_ver and not _version_gte(app_ver, min_v):
            continue
        latest = r
        break
    if not latest:
        return {"ok": True, "has_unread": False, "latest": None}

    seen = db.execute(
        text(
            """
            SELECT last_seen_at, last_seen_changelog_id
            FROM changelog_reads
            WHERE tenant = :tenant AND user_id = :uid AND user_role = :role
            LIMIT 1
            """
        ),
        {"tenant": tenant, "uid": int(user_id), "role": role},
    ).mappings().first()

    has_unread = True
    try:
        if seen and seen.get("last_seen_at") and latest.get("published_at"):
            has_unread = bool(latest["published_at"] > seen["last_seen_at"])
        elif seen and seen.get("last_seen_changelog_id") and latest.get("id"):
            has_unread = int(latest["id"]) > int(seen["last_seen_changelog_id"])
    except Exception:
        has_unread = True

    return {
        "ok": True,
        "has_unread": bool(has_unread),
        "latest": {"id": int(latest["id"]), "published_at": latest["published_at"].isoformat() if hasattr(latest["published_at"], "isoformat") else None},
    }


@router.get("/api/changelogs", dependencies=[Depends(require_feature("novedades"))])
async def api_changelog_list(
    request: Request,
    db: Session = Depends(get_admin_db),
    tenant_db: Session = Depends(get_db_session),
    page: int = 1,
    limit: int = 20,
):
    claims = get_claims(request)
    tenant = str(claims.get("tenant") or "").strip().lower()
    role = str(claims.get("role") or "user").strip().lower() or "user"
    if not tenant:
        raise HTTPException(status_code=400, detail="Tenant inválido")
    modules: Dict[str, Any] = {}
    try:
        sid = claims.get("sucursal_id")
        modules = (FeatureFlagsService(tenant_db).get_flags(sucursal_id=sid) or {}).get("modules") or {}
        if not isinstance(modules, dict):
            modules = {}
    except Exception:
        modules = {}
    app_ver = str(request.headers.get("x-app-version") or "").strip()

    page_i = max(1, int(page or 1))
    limit_i = max(1, min(int(limit or 20), 50))
    offset_i = (page_i - 1) * limit_i
    rows_all = db.execute(
        text(
            f"""
            SELECT id, version, title, body_markdown, change_type, image_url, is_published, published_at,
                   pinned, min_app_version, audience_modules,
                   created_at, updated_at
            FROM changelogs
            WHERE is_published = TRUE
              AND {_sql_audience_where()}
            ORDER BY pinned DESC, published_at DESC NULLS LAST, id DESC
            LIMIT 500
            """
        ),
        {"tenant": tenant, "role": role},
    ).mappings().all()

    filtered: List[Dict[str, Any]] = []
    for r in rows_all:
        if not _modules_enabled(modules, r.get("audience_modules")):
            continue
        min_v = str(r.get("min_app_version") or "").strip()
        if min_v and app_ver and not _version_gte(app_ver, min_v):
            continue
        filtered.append(_row_to_dict(dict(r)))

    total = len(filtered)
    page_items = filtered[offset_i : offset_i + limit_i]
    return {"ok": True, "items": page_items, "total": int(total), "limit": int(limit_i), "offset": int(offset_i)}


@router.post("/api/changelogs/read", dependencies=[Depends(require_feature("novedades"))])
async def api_changelog_mark_read(request: Request, db: Session = Depends(get_admin_db)):
    claims = get_claims(request)
    tenant = str(claims.get("tenant") or "").strip().lower()
    user_id = claims.get("user_id")
    role = str(claims.get("role") or "user").strip().lower() or "user"
    if not tenant:
        raise HTTPException(status_code=401, detail="No autenticado")
    if not user_id:
        if bool(claims.get("is_owner")):
            user_id = 0
            role = "owner"
        else:
            raise HTTPException(status_code=401, detail="No autenticado")

    latest = db.execute(
        text(
            "SELECT id, published_at FROM changelogs WHERE is_published = TRUE AND published_at IS NOT NULL ORDER BY published_at DESC, id DESC LIMIT 1"
        )
    ).mappings().first()
    latest_id = int(latest["id"]) if latest and latest.get("id") else None

    now = _now()
    db.execute(
        text(
            """
            INSERT INTO changelog_reads(tenant, user_id, user_role, last_seen_at, last_seen_changelog_id)
            VALUES (:tenant, :uid, :role, :ts, :cid)
            ON CONFLICT (tenant, user_id, user_role) DO UPDATE SET
                last_seen_at = EXCLUDED.last_seen_at,
                last_seen_changelog_id = EXCLUDED.last_seen_changelog_id
            """
        ),
        {"tenant": tenant, "uid": int(user_id), "role": role, "ts": now, "cid": latest_id},
    )
    db.commit()
    return {"ok": True}
