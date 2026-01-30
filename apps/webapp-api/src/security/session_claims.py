from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Request


OWNER_ROLES = {"dueño", "dueno", "owner", "admin", "administrador"}
PROFESOR_ROLES = {"profesor"}
STAFF_ROLES = {"empleado", "recepcionista", "staff"}
GESTION_ROLES = set().union(OWNER_ROLES, PROFESOR_ROLES, STAFF_ROLES)


def normalize_role(role: Any) -> str:
    try:
        return str(role or "").strip().lower()
    except Exception:
        return ""


def parse_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        iv = int(value)
        return iv
    except Exception:
        return None


def get_session_user_id(session: Dict[str, Any]) -> Optional[int]:
    uid = parse_int(session.get("user_id"))
    if uid:
        return uid
    uid = parse_int(session.get("gestion_profesor_user_id"))
    if uid:
        return uid
    return None


def get_sucursal_id(session: Dict[str, Any]) -> Optional[int]:
    sid = parse_int(session.get("sucursal_id"))
    if sid and sid > 0:
        return sid
    return None


def get_claims(request: Request) -> Dict[str, Any]:
    s = request.session
    role = normalize_role(s.get("role"))
    user_id = get_session_user_id(s)
    logged_in = bool(s.get("logged_in"))
    session_type = normalize_role(s.get("session_type") or ("gestion" if logged_in else "usuario" if user_id else ""))
    tenant = str(s.get("tenant") or "").strip() or None
    sucursal_id = get_sucursal_id(s)

    is_owner = role in OWNER_ROLES
    is_profesor = role in PROFESOR_ROLES
    is_staff = role in STAFF_ROLES
    is_gestion = (session_type == "gestion") or logged_in or (role in GESTION_ROLES)
    is_authenticated = bool(user_id) or logged_in

    return {
        "role": role,
        "user_id": user_id,
        "logged_in": logged_in,
        "session_type": session_type,
        "tenant": tenant,
        "sucursal_id": sucursal_id,
        "is_authenticated": is_authenticated,
        "is_gestion": is_gestion,
        "is_owner": is_owner,
        "is_profesor": is_profesor,
        "is_staff": is_staff,
    }


def set_session_claims(
    session: Dict[str, Any],
    *,
    tenant: Optional[str] = None,
    session_type: Optional[str] = None,
    role: Optional[str] = None,
    user_id: Optional[int] = None,
    logged_in: Optional[bool] = None,
    sucursal_id: Optional[int] = None,
) -> None:
    if tenant is not None:
        session["tenant"] = tenant
    if session_type is not None:
        session["session_type"] = normalize_role(session_type)
    if role is not None:
        session["role"] = normalize_role(role)
    if user_id is not None:
        session["user_id"] = int(user_id)
    if logged_in is not None:
        session["logged_in"] = bool(logged_in)
    if sucursal_id is not None:
        session["sucursal_id"] = int(sucursal_id)

