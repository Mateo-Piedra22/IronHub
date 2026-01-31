from typing import Optional, List, Dict, Any

from sqlalchemy import text

from src.services.entitlements_service import EntitlementsService
from src.services.membership_service import MembershipService


class EntitlementsPayloadService:
    def __init__(self, db):
        self.db = db

    def get_payload(self, usuario_id: int, sucursal_actual_id: Optional[int]) -> Dict[str, Any]:
        es = EntitlementsService(self.db)
        summary = es.get_summary(int(usuario_id), sucursal_actual_id)
        enabled = es.is_enabled() and summary is not None

        allowed_sucursales: List[Dict[str, Any]] = []
        try:
            rows = (
                self.db.execute(
                    text("SELECT id, nombre, activa FROM sucursales ORDER BY id ASC")
                )
                .mappings()
                .all()
            )
            all_items = [
                {
                    "id": int(r["id"]),
                    "nombre": str(r.get("nombre") or ""),
                    "activa": bool(r.get("activa")) if r.get("activa") is not None else True,
                }
                for r in (rows or [])
                if r and r.get("id") is not None
            ]

            if summary is None:
                role = None
                try:
                    row = (
                        self.db.execute(
                            text(
                                "SELECT LOWER(COALESCE(rol,'socio')) AS rol FROM usuarios WHERE id = :id LIMIT 1"
                            ),
                            {"id": int(usuario_id)},
                        )
                        .mappings()
                        .first()
                    )
                    role = str((row or {}).get("rol") or "socio").strip().lower()
                except Exception:
                    role = None

                if role in (
                    "owner",
                    "dueño",
                    "dueno",
                    "admin",
                    "administrador",
                    "profesor",
                    "staff",
                    "recepcionista",
                    "empleado",
                ):
                    allowed_sucursales = all_items
                else:
                    ms = MembershipService(self.db)
                    m = ms.get_active_membership(int(usuario_id))
                    if not m:
                        allowed_sucursales = all_items
                    elif bool(m.get("all_sucursales")):
                        allowed_sucursales = all_items
                    else:
                        mid = m.get("id")
                        allowed_ids = set(ms.get_membership_sucursales(int(mid)) if mid else [])
                        allowed_sucursales = [
                            s for s in all_items if int(s["id"]) in allowed_ids
                        ]
            elif summary.branch_access.all_sucursales:
                denied = set(summary.branch_access.denied_sucursal_ids)
                allowed_sucursales = [
                    s for s in all_items if int(s["id"]) not in denied
                ]
            else:
                allow = set(summary.branch_access.allowed_sucursal_ids)
                allowed_sucursales = [s for s in all_items if int(s["id"]) in allow]
        except Exception:
            allowed_sucursales = []

        allowed_tipo_clases: List[Dict[str, Any]] = []
        allowed_clases: List[Dict[str, Any]] = []
        if summary is not None and summary.class_allowlist_enabled:
            try:
                tc_ids = list(summary.allowed_tipo_clase_ids or [])
                if tc_ids:
                    rows = (
                        self.db.execute(
                            text(
                                "SELECT id, nombre, activo FROM tipos_clases ORDER BY id ASC"
                            )
                        )
                        .mappings()
                        .all()
                    )
                    allowed_tc = set(int(x) for x in tc_ids)
                    for r in rows or []:
                        if (
                            r
                            and r.get("id") is not None
                            and int(r["id"]) in allowed_tc
                        ):
                            allowed_tipo_clases.append(
                                {
                                    "id": int(r["id"]),
                                    "nombre": str(r.get("nombre") or ""),
                                    "activo": bool(r.get("activo"))
                                    if r.get("activo") is not None
                                    else True,
                                }
                            )
            except Exception:
                allowed_tipo_clases = []

            try:
                c_ids = list(summary.allowed_clase_ids or [])
                if c_ids:
                    rows = (
                        self.db.execute(
                            text(
                                "SELECT id, nombre, sucursal_id, activa FROM clases ORDER BY id ASC"
                            )
                        )
                        .mappings()
                        .all()
                    )
                    allowed_c = set(int(x) for x in c_ids)
                    for r in rows or []:
                        if (
                            r
                            and r.get("id") is not None
                            and int(r["id"]) in allowed_c
                        ):
                            allowed_clases.append(
                                {
                                    "id": int(r["id"]),
                                    "nombre": str(r.get("nombre") or ""),
                                    "sucursal_id": int(r.get("sucursal_id"))
                                    if r.get("sucursal_id") is not None
                                    else None,
                                    "activa": bool(r.get("activa"))
                                    if r.get("activa") is not None
                                    else True,
                                }
                            )
            except Exception:
                allowed_clases = []

        return {
            "enabled": bool(enabled),
            "sucursal_actual_id": sucursal_actual_id,
            "branch_access": None
            if summary is None
            else {
                "all_sucursales": bool(summary.branch_access.all_sucursales),
                "allowed_sucursal_ids": list(summary.branch_access.allowed_sucursal_ids),
                "denied_sucursal_ids": list(summary.branch_access.denied_sucursal_ids),
            },
            "allowed_sucursales": allowed_sucursales,
            "class_allowlist_enabled": bool(summary.class_allowlist_enabled)
            if summary is not None
            else False,
            "allowed_tipo_clases": allowed_tipo_clases,
            "allowed_clases": allowed_clases,
        }
