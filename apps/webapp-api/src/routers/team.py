from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text

from src.dependencies import (
    get_profesor_service,
    get_staff_service,
    require_feature,
    require_owner,
    require_sucursal_selected,
)
from src.models.orm_models import Profesor, StaffPermission, StaffProfile, Usuario
from src.services.profesor_service import ProfesorService
from src.services.staff_service import StaffService

router = APIRouter(dependencies=[Depends(require_feature("usuarios"))])


@router.get("/api/team")
async def api_team_list(
    request: Request,
    _=Depends(require_owner),
    svc_staff: StaffService = Depends(get_staff_service),
    search: str = "",
    all: bool = Query(False),
    sucursal_id: Optional[int] = Query(None),
):
    try:
        term = str(search or "").strip().lower()
        staff_like_roles = [
            "profesor",
            "empleado",
            "recepcionista",
            "staff",
            "admin",
            "administrador",
        ]
        stmt = select(Usuario).where(Usuario.rol.in_(staff_like_roles)).order_by(Usuario.nombre.asc())
        if not all and sucursal_id is not None:
            try:
                sid = int(sucursal_id)
            except Exception:
                sid = None
            if sid is not None and sid > 0:
                stmt = stmt.where(
                    text(
                        "EXISTS (SELECT 1 FROM usuario_sucursales us WHERE us.usuario_id = usuarios.id AND us.sucursal_id = :sid)"
                    )
                ).params(sid=sid)
        if term:
            like = f"%{term}%"
            stmt = stmt.where(
                func.lower(Usuario.nombre).like(like)
                | func.lower(func.coalesce(Usuario.dni, "")).like(like)
            )

        users = list(svc_staff.db.scalars(stmt).all())
        if not users:
            return {"ok": True, "items": []}

        user_ids = [int(u.id) for u in users]
        staff_profiles = {
            int(p.usuario_id): p
            for p in svc_staff.db.scalars(
                select(StaffProfile).where(StaffProfile.usuario_id.in_(user_ids))
            ).all()
        }
        staff_perms = {
            int(p.usuario_id): p
            for p in svc_staff.db.scalars(
                select(StaffPermission).where(StaffPermission.usuario_id.in_(user_ids))
            ).all()
        }
        profesores = {
            int(p.usuario_id): p
            for p in svc_staff.db.scalars(
                select(Profesor).where(Profesor.usuario_id.in_(user_ids))
            ).all()
        }

        branches_rows = (
            svc_staff.db.execute(
                text(
                    """
                    SELECT usuario_id, ARRAY_AGG(sucursal_id ORDER BY sucursal_id) AS sucursales
                    FROM usuario_sucursales
                    WHERE usuario_id = ANY(:ids)
                    GROUP BY usuario_id
                    """
                ),
                {"ids": user_ids},
            )
            .mappings()
            .all()
        )
        branch_map: Dict[int, List[int]] = {}
        for r in branches_rows or []:
            try:
                uid = int(r.get("usuario_id"))
            except Exception:
                continue
            arr = r.get("sucursales") or []
            out_ids: List[int] = []
            for x in arr:
                try:
                    out_ids.append(int(x))
                except Exception:
                    pass
            branch_map[uid] = out_ids

        out: List[Dict[str, Any]] = []
        for u in users:
            uid = int(u.id)
            prof = profesores.get(uid)
            st = staff_profiles.get(uid)
            perm = staff_perms.get(uid)
            scopes_val: List[str] = []
            if perm is not None:
                try:
                    scopes_val = list(perm.scopes or [])
                except Exception:
                    scopes_val = []
            item = {
                "id": uid,
                "nombre": u.nombre or "",
                "dni": u.dni or "",
                "telefono": u.telefono or "",
                "rol": (u.rol or "").strip().lower(),
                "activo": bool(u.activo),
                "sucursales": branch_map.get(uid, []),
                "scopes": scopes_val,
                "staff": {
                    "tipo": (getattr(st, "tipo", None) or "").strip().lower() or None,
                    "estado": (getattr(st, "estado", None) or "").strip().lower() or None,
                }
                if st is not None
                else None,
                "profesor": {
                    "id": int(prof.id),
                    "tipo": (prof.tipo or "").strip() or None,
                    "estado": (prof.estado or "").strip().lower() or None,
                }
                if prof is not None
                else None,
            }
            if item["profesor"] is not None:
                item["kind"] = "profesor"
            elif item["staff"] is not None:
                item["kind"] = "staff"
            else:
                item["kind"] = "usuario"
            out.append(item)

        return {"ok": True, "items": out}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/team/promote")
async def api_team_promote(
    request: Request,
    sucursal_id: int = Depends(require_sucursal_selected),
    _=Depends(require_owner),
    svc_prof: ProfesorService = Depends(get_profesor_service),
    svc_staff: StaffService = Depends(get_staff_service),
):
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    try:
        usuario_id = int((payload or {}).get("usuario_id"))
    except Exception:
        usuario_id = 0
    kind = str((payload or {}).get("kind") or "").strip().lower()
    rol = str((payload or {}).get("rol") or "").strip().lower()

    if not usuario_id:
        raise HTTPException(status_code=400, detail="usuario_id requerido")
    if kind not in ("profesor", "staff"):
        raise HTTPException(status_code=400, detail="kind inválido")

    try:
        current = svc_staff.db.execute(
            text("SELECT rol FROM usuarios WHERE id = :id LIMIT 1"),
            {"id": int(usuario_id)},
        ).fetchone()
        rol_actual = str(current[0] or "").strip().lower() if current else ""
    except Exception:
        rol_actual = ""
    if rol_actual in ("dueño", "dueno", "owner"):
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        sid = int(sucursal_id)
    except Exception:
        sid = 0

    if kind == "staff":
        if not rol or rol in ("dueño", "dueno", "owner"):
            rol = "empleado"
        svc_staff.set_user_role(int(usuario_id), rol)
        svc_staff.set_user_active(int(usuario_id), True)
        if sid > 0:
            svc_staff.set_user_branches(int(usuario_id), [sid])
        svc_staff.upsert_staff_profile(int(usuario_id), tipo=rol, estado="activo")
        existing_perm = svc_staff.db.scalars(
            select(StaffPermission).where(StaffPermission.usuario_id == int(usuario_id))
        ).first()
        if existing_perm is None:
            svc_staff.set_scopes(int(usuario_id), [])
        svc_staff.db.commit()
        return {"ok": True, "usuario_id": int(usuario_id), "kind": "staff"}

    profesor_id = int(
        svc_prof.crear_perfil_profesor(int(usuario_id), payload or {}, sucursal_id=int(sid))
    )
    svc_staff.set_user_role(int(usuario_id), "profesor")
    if sid > 0:
        svc_staff.set_user_branches(int(usuario_id), [sid])
    svc_staff.upsert_staff_profile(int(usuario_id), tipo="profesor", estado="activo")
    existing_perm = svc_staff.db.scalars(
        select(StaffPermission).where(StaffPermission.usuario_id == int(usuario_id))
    ).first()
    if existing_perm is None:
        svc_staff.set_scopes(int(usuario_id), [])
    svc_staff.db.commit()
    return {"ok": True, "usuario_id": int(usuario_id), "kind": "profesor", "profesor_id": int(profesor_id)}
