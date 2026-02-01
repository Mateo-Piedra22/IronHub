from __future__ import annotations

from typing import List, Optional

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.security.session_claims import get_claims, OWNER_ROLES, STAFF_ROLES, PROFESOR_ROLES
from src.services.entitlements_service import EntitlementsService
from src.services.membership_service import MembershipService


class BranchAccessService:
    def __init__(self, db: Session):
        self.db = db

    def get_allowed_sucursal_ids(
        self, request: Request, *, include_inactive: bool = False
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
                self.db.execute(
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
            es = EntitlementsService(self.db)
            access = es.get_effective_branch_access(int(user_id))
            if access is not None:
                if access.all_sucursales:
                    denied = set(access.denied_sucursal_ids)
                    if not denied:
                        return None
                    rows = (
                        self.db.execute(
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

        ms = MembershipService(self.db)
        m = ms.get_active_membership(int(user_id))
        if not m:
            return None
        if bool(m.get("all_sucursales")):
            return None
        mid = m.get("id")
        if not mid:
            return []
        return ms.get_membership_sucursales(int(mid))

    def is_sucursal_allowed(self, request: Request, sucursal_id: int) -> bool:
        try:
            sid = int(sucursal_id)
        except Exception:
            return False
        if sid <= 0:
            return False
        allowed = self.get_allowed_sucursal_ids(request, include_inactive=False)
        if allowed is None:
            return True
        return sid in allowed
