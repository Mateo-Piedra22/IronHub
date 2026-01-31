import logging
import re
import secrets
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.dependencies import get_db_session, require_owner
from src.security.session_claims import get_claims, OWNER_ROLES, STAFF_ROLES, PROFESOR_ROLES
from src.services.membership_service import MembershipService
from src.database.connection import AdminSessionLocal

logger = logging.getLogger(__name__)
router = APIRouter()


def _is_authenticated_any(request: Request) -> bool:
    if request.session.get("user_id"):
        return True
    if request.session.get("logged_in") and request.session.get("role"):
        return True
    if request.session.get("gestion_profesor_user_id") is not None:
        return True
    return False


def _get_allowed_sucursal_ids(
    request: Request, db: Session, *, include_inactive: bool = False
) -> Optional[List[int]]:
    claims = get_claims(request)
    role = str(claims.get("role") or "").strip().lower()
    user_id = claims.get("user_id")
    if role in OWNER_ROLES:
        return None
    if role in STAFF_ROLES or role in PROFESOR_ROLES:
        if not user_id:
            return []
        rows = (
            db.execute(
                text(
                    """
                    SELECT us.sucursal_id
                    FROM usuario_sucursales us
                    JOIN sucursales s ON s.id = us.sucursal_id
                    WHERE us.usuario_id = :uid
                    """
                    + ("" if include_inactive else " AND s.activa = TRUE")
                    + " ORDER BY us.sucursal_id ASC"
                ),
                {"uid": int(user_id)},
            )
            .fetchall()
        )
        out: List[int] = []
        for r in rows or []:
            try:
                out.append(int(r[0]))
            except Exception:
                pass
        return out
    if not user_id:
        return []
    try:
        from src.services.entitlements_service import EntitlementsService

        es = EntitlementsService(db)
        access = es.get_effective_branch_access(int(user_id))
        if access is not None:
            if access.all_sucursales:
                denied = set(access.denied_sucursal_ids)
                if not denied:
                    return None
                rows = (
                    db.execute(
                        text(
                            "SELECT id FROM sucursales"
                            + ("" if include_inactive else " WHERE activa = TRUE")
                            + " ORDER BY id ASC"
                        )
                    )
                    .fetchall()
                )
                out: List[int] = []
                for r in rows or []:
                    try:
                        sid = int(r[0])
                    except Exception:
                        continue
                    if sid in denied:
                        continue
                    out.append(sid)
                return out
            out = []
            for x in access.allowed_sucursal_ids:
                try:
                    out.append(int(x))
                except Exception:
                    pass
            return out
    except Exception:
        pass
    ms = MembershipService(db)
    m = ms.get_active_membership(int(user_id))
    if not m:
        return None
    if bool(m.get("all_sucursales")):
        return None
    mid = m.get("id")
    if not mid:
        return []
    return ms.get_membership_sucursales(int(mid))


@router.get("/api/sucursales")
async def api_list_sucursales(request: Request, db: Session = Depends(get_db_session)):
    if not _is_authenticated_any(request):
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    try:
        allowed = _get_allowed_sucursal_ids(request, db, include_inactive=False)
        rows = (
            db.execute(
                text(
                    """
                    SELECT id, nombre, codigo, direccion, timezone, activa
                    FROM sucursales
                    WHERE activa = TRUE
                    ORDER BY id ASC
                    """
                )
            )
            .mappings()
            .all()
        )
        items: List[Dict[str, Any]] = []
        for r in rows or []:
            if not r:
                continue
            if r.get("id") is None:
                continue
            try:
                rid = int(r.get("id"))
            except Exception:
                continue
            if allowed is not None and rid not in allowed:
                continue
            items.append(
                {
                    "id": rid,
                    "nombre": str(r.get("nombre") or ""),
                    "codigo": str(r.get("codigo") or ""),
                    "direccion": r.get("direccion"),
                    "timezone": r.get("timezone"),
                    "activa": bool(r.get("activa"))
                    if r.get("activa") is not None
                    else True,
                }
            )
        current_id = request.session.get("sucursal_id")
        try:
            current_id = int(current_id) if current_id is not None else None
        except Exception:
            current_id = None
        return {"ok": True, "items": items, "sucursal_actual_id": current_id}
    except Exception as e:
        logger.error(f"Error listing sucursales: {e}")
        return JSONResponse({"ok": False, "error": "server_error"}, status_code=500)


@router.post("/api/sucursales/seleccionar")
async def api_select_sucursal(request: Request, db: Session = Depends(get_db_session)):
    if not _is_authenticated_any(request):
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    try:
        data = await request.json()
    except Exception:
        data = {}
    sucursal_id = data.get("sucursal_id")
    if sucursal_id is None or str(sucursal_id).strip() in ("", "0", "null", "none"):
        try:
            request.session.pop("sucursal_id", None)
        except Exception:
            pass
        return {"ok": True, "sucursal_actual_id": None}
    try:
        sid = int(sucursal_id)
    except Exception:
        return JSONResponse(
            {"ok": False, "error": "sucursal_id_invalid"}, status_code=400
        )
    if sid <= 0:
        try:
            request.session.pop("sucursal_id", None)
        except Exception:
            pass
        return {"ok": True, "sucursal_actual_id": None}

    try:
        allowed = _get_allowed_sucursal_ids(request, db, include_inactive=False)
        if allowed is not None and int(sid) not in allowed:
            return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)
        row = (
            db.execute(
                text(
                    "SELECT id FROM sucursales WHERE id = :id AND activa = TRUE LIMIT 1"
                ),
                {"id": sid},
            )
            .mappings()
            .first()
        )
        if not row:
            return JSONResponse(
                {"ok": False, "error": "sucursal_not_found"}, status_code=404
            )
        request.session["sucursal_id"] = int(sid)
        return {"ok": True, "sucursal_actual_id": int(sid)}
    except Exception as e:
        logger.error(f"Error selecting sucursal: {e}")
        return JSONResponse({"ok": False, "error": "server_error"}, status_code=500)


@router.post("/api/sucursales")
async def api_create_sucursal(
    request: Request,
    _=Depends(require_owner),
    db: Session = Depends(get_db_session),
):
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    nombre = str((payload or {}).get("nombre") or "").strip()
    codigo = str((payload or {}).get("codigo") or "").strip().lower()
    direccion = str((payload or {}).get("direccion") or "").strip() or None
    timezone = str((payload or {}).get("timezone") or "").strip() or None

    if not nombre or not codigo:
        return JSONResponse(
            {"ok": False, "error": "nombre_y_codigo_requeridos"}, status_code=400
        )

    if not re.match(r"^[a-z0-9][a-z0-9_-]{1,62}$", codigo):
        return JSONResponse({"ok": False, "error": "codigo_invalido"}, status_code=400)

    station_key = secrets.token_urlsafe(16)
    try:
        row = (
            db.execute(
                text(
                    """
                    INSERT INTO sucursales (nombre, codigo, direccion, timezone, station_key, activa)
                    VALUES (:nombre, :codigo, :direccion, :timezone, :station_key, TRUE)
                    RETURNING id
                    """
                ),
                {
                    "nombre": nombre,
                    "codigo": codigo,
                    "direccion": direccion,
                    "timezone": timezone,
                    "station_key": station_key,
                },
            )
            .mappings()
            .first()
        )
        db.commit()
        new_id = int(row["id"]) if row and row.get("id") is not None else None
        if not new_id:
            return JSONResponse({"ok": False, "error": "create_failed"}, status_code=500)
        return {"ok": True, "id": int(new_id)}
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.put("/api/sucursales/{sucursal_id}")
async def api_update_sucursal(
    sucursal_id: int,
    request: Request,
    _=Depends(require_owner),
    db: Session = Depends(get_db_session),
):
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    nombre = (payload or {}).get("nombre")
    codigo = (payload or {}).get("codigo")
    direccion = (payload or {}).get("direccion")
    timezone = (payload or {}).get("timezone")
    activa = (payload or {}).get("activa")

    sets: list[str] = []
    params: dict[str, Any] = {"id": int(sucursal_id)}

    if nombre is not None:
        sets.append("nombre = :nombre")
        params["nombre"] = str(nombre).strip()
    if codigo is not None:
        cod = str(codigo).strip().lower()
        if not re.match(r"^[a-z0-9][a-z0-9_-]{1,62}$", cod):
            return JSONResponse({"ok": False, "error": "codigo_invalido"}, status_code=400)
        sets.append("codigo = :codigo")
        params["codigo"] = cod
    if direccion is not None:
        sets.append("direccion = :direccion")
        params["direccion"] = str(direccion).strip() or None
    if timezone is not None:
        sets.append("timezone = :timezone")
        params["timezone"] = str(timezone).strip() or None
    if activa is not None:
        sets.append("activa = :activa")
        params["activa"] = bool(activa)

    if not sets:
        return {"ok": True}

    try:
        row = (
            db.execute(
                text("SELECT id, activa FROM sucursales WHERE id = :id LIMIT 1"),
                {"id": int(sucursal_id)},
            )
            .mappings()
            .first()
        )
        if not row:
            return JSONResponse({"ok": False, "error": "sucursal_not_found"}, status_code=404)

        db.execute(
            text(f"UPDATE sucursales SET {', '.join(sets)} WHERE id = :id"),
            params,
        )

        if activa is not None and bool(activa) is False:
            try:
                db.execute(
                    text(
                        "UPDATE whatsapp_config SET active = FALSE WHERE sucursal_id = :id AND active = TRUE"
                    ),
                    {"id": int(sucursal_id)},
                )
            except Exception:
                pass
            try:
                if int(request.session.get("sucursal_id") or 0) == int(sucursal_id):
                    request.session.pop("sucursal_id", None)
            except Exception:
                pass

        db.commit()
        try:
            claims = get_claims(request)
            tenant = str(claims.get("tenant") or "").strip().lower()
            if tenant:
                row2 = (
                    db.execute(
                        text(
                            "SELECT id, nombre, codigo, direccion, timezone, activa, station_key FROM sucursales WHERE id = :id LIMIT 1"
                        ),
                        {"id": int(sucursal_id)},
                    )
                    .mappings()
                    .first()
                )
                if row2 and row2.get("id") is not None:
                    admin_db = AdminSessionLocal()
                    try:
                        gid = admin_db.execute(
                            text("SELECT id FROM gyms WHERE subdominio = :t LIMIT 1"),
                            {"t": tenant},
                        ).scalar()
                        if gid:
                            admin_db.execute(
                                text(
                                    """
                                    UPDATE branches
                                    SET name = :name,
                                        code = :code,
                                        address = :address,
                                        timezone = :timezone,
                                        status = :status,
                                        station_key = :station_key
                                    WHERE gym_id = :gym_id AND id = :id
                                    """
                                ),
                                {
                                    "gym_id": int(gid),
                                    "id": int(row2.get("id")),
                                    "name": str(row2.get("nombre") or "").strip() or "Sucursal",
                                    "code": str(row2.get("codigo") or "").strip() or "",
                                    "address": row2.get("direccion"),
                                    "timezone": row2.get("timezone"),
                                    "status": "active" if bool(row2.get("activa")) else "inactive",
                                    "station_key": row2.get("station_key"),
                                },
                            )
                            admin_db.commit()
                    except Exception:
                        try:
                            admin_db.rollback()
                        except Exception:
                            pass
                    finally:
                        try:
                            admin_db.close()
                        except Exception:
                            pass
        except Exception:
            pass
        return {"ok": True}
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.get("/api/sucursales/{sucursal_id}/station")
async def api_get_sucursal_station_key(
    sucursal_id: int,
    request: Request,
    _=Depends(require_owner),
    db: Session = Depends(get_db_session),
):
    try:
        sid = int(sucursal_id)
    except Exception:
        return JSONResponse({"ok": False, "error": "sucursal_id_invalid"}, status_code=400)
    row = (
        db.execute(
            text(
                "SELECT id, station_key, activa FROM sucursales WHERE id = :id LIMIT 1"
            ),
            {"id": sid},
        )
        .mappings()
        .first()
    )
    if not row:
        return JSONResponse({"ok": False, "error": "sucursal_not_found"}, status_code=404)
    if not bool(row.get("activa")):
        return JSONResponse({"ok": False, "error": "sucursal_inactiva"}, status_code=400)
    station_key = str(row.get("station_key") or "").strip()
    if not station_key:
        station_key = secrets.token_urlsafe(16)
        try:
            db.execute(
                text("UPDATE sucursales SET station_key = :k WHERE id = :id"),
                {"k": station_key, "id": sid},
            )
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            return JSONResponse(
                {"ok": False, "error": "No se pudo generar la station key"},
                status_code=500,
            )
    origin = request.headers.get("origin", "")
    if origin:
        station_url = f"{origin}/station/{station_key}"
    else:
        host = request.headers.get("host", "")
        protocol = (
            "https"
            if request.headers.get("x-forwarded-proto") == "https"
            else "http"
        )
        station_url = f"{protocol}://{host}/station/{station_key}"
    return {"ok": True, "sucursal_id": sid, "station_key": station_key, "station_url": station_url}


@router.post("/api/sucursales/{sucursal_id}/station/regenerate")
async def api_regenerate_sucursal_station_key(
    sucursal_id: int,
    request: Request,
    _=Depends(require_owner),
    db: Session = Depends(get_db_session),
):
    try:
        sid = int(sucursal_id)
    except Exception:
        return JSONResponse({"ok": False, "error": "sucursal_id_invalid"}, status_code=400)
    row = (
        db.execute(
            text("SELECT id, activa FROM sucursales WHERE id = :id LIMIT 1"),
            {"id": sid},
        )
        .mappings()
        .first()
    )
    if not row:
        return JSONResponse({"ok": False, "error": "sucursal_not_found"}, status_code=404)
    if not bool(row.get("activa")):
        return JSONResponse({"ok": False, "error": "sucursal_inactiva"}, status_code=400)
    new_key = secrets.token_urlsafe(16)
    try:
        db.execute(
            text("UPDATE sucursales SET station_key = :k WHERE id = :id"),
            {"k": new_key, "id": sid},
        )
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return JSONResponse({"ok": False, "error": "No se pudo regenerar la station key"}, status_code=500)
    origin = request.headers.get("origin", "")
    if origin:
        station_url = f"{origin}/station/{new_key}"
    else:
        host = request.headers.get("host", "")
        protocol = (
            "https"
            if request.headers.get("x-forwarded-proto") == "https"
            else "http"
        )
        station_url = f"{protocol}://{host}/station/{new_key}"
    return {"ok": True, "sucursal_id": sid, "station_key": new_key, "station_url": station_url}


@router.delete("/api/sucursales/{sucursal_id}")
async def api_delete_sucursal(
    sucursal_id: int,
    request: Request,
    _=Depends(require_owner),
    db: Session = Depends(get_db_session),
):
    try:
        db.execute(
            text("UPDATE sucursales SET activa = FALSE WHERE id = :id"),
            {"id": int(sucursal_id)},
        )
        try:
            db.execute(
                text(
                    "UPDATE whatsapp_config SET active = FALSE WHERE sucursal_id = :id AND active = TRUE"
                ),
                {"id": int(sucursal_id)},
            )
        except Exception:
            pass
        db.commit()
        try:
            if int(request.session.get("sucursal_id") or 0) == int(sucursal_id):
                request.session.pop("sucursal_id", None)
        except Exception:
            pass
        return {"ok": True}
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
