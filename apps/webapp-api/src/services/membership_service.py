from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session


class MembershipService:
    def __init__(self, db: Session):
        self.db = db

    def get_active_membership(self, usuario_id: int) -> Optional[Dict[str, Any]]:
        today = date.today()
        row = (
            self.db.execute(
                text(
                    """
                    SELECT id, usuario_id, plan_name, status, start_date, end_date, all_sucursales, created_at, updated_at
                    FROM memberships
                    WHERE usuario_id = :uid
                      AND status = 'active'
                      AND start_date <= :today
                      AND (end_date IS NULL OR end_date >= :today)
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ),
                {"uid": int(usuario_id), "today": today},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def get_membership_sucursales(self, membership_id: int) -> List[int]:
        rows = self.db.execute(
            text(
                "SELECT sucursal_id FROM membership_sucursales WHERE membership_id = :mid ORDER BY sucursal_id ASC"
            ),
            {"mid": int(membership_id)},
        ).fetchall()
        out: List[int] = []
        for r in rows or []:
            try:
                out.append(int(r[0]))
            except Exception:
                pass
        return out

    def check_access(
        self, usuario_id: int, sucursal_id: int
    ) -> Tuple[Optional[bool], str]:
        m = self.get_active_membership(int(usuario_id))
        if not m:
            return None, ""
        if bool(m.get("all_sucursales")):
            return True, ""
        mid = m.get("id")
        if not mid:
            return False, "Membresía inválida"
        allowed = (
            self.db.execute(
                text(
                    """
                    SELECT 1
                    FROM membership_sucursales
                    WHERE membership_id = :mid AND sucursal_id = :sid
                    LIMIT 1
                    """
                ),
                {"mid": int(mid), "sid": int(sucursal_id)},
            ).fetchone()
            is not None
        )
        if not allowed:
            return False, "Membresía no válida para esta sucursal"
        return True, ""

    def set_active_membership(
        self,
        usuario_id: int,
        *,
        plan_name: Optional[str],
        start_date: Optional[date],
        end_date: Optional[date],
        all_sucursales: bool,
        sucursal_ids: Optional[List[int]],
    ) -> Dict[str, Any]:
        uid = int(usuario_id)
        sd = start_date or date.today()
        try:
            self.db.execute(
                text(
                    "UPDATE memberships SET status = 'replaced', updated_at = NOW() WHERE usuario_id = :uid AND status = 'active'"
                ),
                {"uid": uid},
            )
        except Exception:
            pass

        row = self.db.execute(
            text(
                """
                    INSERT INTO memberships (usuario_id, plan_name, status, start_date, end_date, all_sucursales, created_at, updated_at)
                    VALUES (:uid, :plan, 'active', :sd, :ed, :all, NOW(), NOW())
                    RETURNING id
                    """
            ),
            {
                "uid": uid,
                "plan": plan_name,
                "sd": sd,
                "ed": end_date,
                "all": bool(all_sucursales),
            },
        ).fetchone()
        mid = int(row[0]) if row and row[0] is not None else None
        if not mid:
            self.db.rollback()
            return {"ok": False, "error": "create_failed"}

        try:
            if not bool(all_sucursales):
                ids = [
                    int(x)
                    for x in (sucursal_ids or [])
                    if str(x).strip().isdigit() or isinstance(x, int)
                ]
                ids = sorted(set(ids))
                for sid in ids:
                    self.db.execute(
                        text(
                            "INSERT INTO membership_sucursales (membership_id, sucursal_id, created_at) VALUES (:mid,:sid,NOW()) ON CONFLICT DO NOTHING"
                        ),
                        {"mid": int(mid), "sid": int(sid)},
                    )
        except Exception:
            self.db.rollback()
            return {"ok": False, "error": "branch_link_failed"}

        self.db.commit()
        m = self.get_active_membership(uid)
        if not m:
            return {"ok": True, "membership_id": int(mid)}
        return {
            "ok": True,
            "membership": m,
            "sucursales": (
                self.get_membership_sucursales(int(m.get("id")))
                if not bool(m.get("all_sucursales"))
                else []
            ),
        }
