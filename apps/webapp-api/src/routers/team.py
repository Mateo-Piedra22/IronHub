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
from src.database.clase_profesor_schema import ensure_clase_profesor_schema
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
            st_estado = str(getattr(st, "estado", "") or "").strip().lower() if st is not None else ""
            staff_visible = st is not None and st_estado != "inactivo"
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
                    "estado": st_estado or None,
                }
                if staff_visible
                else None,
                "profesor": None,
            }
            if prof is not None:
                prof_estado = str(getattr(prof, "estado", "") or "").strip().lower() or "activo"
                if prof_estado != "inactivo":
                    item["profesor"] = {
                        "id": int(prof.id),
                        "tipo": (prof.tipo or "").strip() or None,
                        "estado": prof_estado,
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


@router.get("/api/team/impact")
async def api_team_impact(
    usuario_id: int,
    request: Request,
    _=Depends(require_owner),
    svc_staff: StaffService = Depends(get_staff_service),
):
    try:
        uid = int(usuario_id)
    except Exception:
        raise HTTPException(status_code=400, detail="usuario_id inválido")
    if uid <= 0:
        raise HTTPException(status_code=400, detail="usuario_id inválido")

    try:
        current = svc_staff.db.execute(
            text("SELECT rol FROM usuarios WHERE id = :id LIMIT 1"),
            {"id": int(uid)},
        ).fetchone()
        rol_actual = str(current[0] or "").strip().lower() if current else ""
    except Exception:
        rol_actual = ""
    if rol_actual in ("dueño", "dueno", "owner"):
        raise HTTPException(status_code=403, detail="Forbidden")

    prof = (
        svc_staff.db.scalars(
            select(Profesor).where(Profesor.usuario_id == int(uid)).limit(1)
        ).first()
    )
    st = (
        svc_staff.db.scalars(
            select(StaffProfile).where(StaffProfile.usuario_id == int(uid)).limit(1)
        ).first()
    )
    perm = (
        svc_staff.db.scalars(
            select(StaffPermission).where(StaffPermission.usuario_id == int(uid)).limit(1)
        ).first()
    )

    ensure_clase_profesor_schema(svc_staff.db)

    profesor_impact: Dict[str, Any] = {"exists": False}
    if prof is not None:
        pid = int(getattr(prof, "id", 0) or 0)
        profesor_impact = {
            "exists": True,
            "profesor_id": pid,
            "estado": str(getattr(prof, "estado", "") or "").strip().lower() or "activo",
            "tipo": str(getattr(prof, "tipo", "") or "").strip() or None,
            "clases_asignadas_activas": int(
                svc_staff.db.execute(
                    text(
                        "SELECT COUNT(*) FROM profesor_clase_asignaciones WHERE profesor_id = :pid AND activa = TRUE"
                    ),
                    {"pid": int(pid)},
                ).scalar()
                or 0
            ),
            "sesiones_activas": int(
                svc_staff.db.execute(
                    text(
                        "SELECT COUNT(*) FROM profesor_horas_trabajadas WHERE profesor_id = :pid AND hora_fin IS NULL"
                    ),
                    {"pid": int(pid)},
                ).scalar()
                or 0
            ),
            "horarios_count": int(
                svc_staff.db.execute(
                    text(
                        "SELECT COUNT(*) FROM horarios_profesores WHERE profesor_id = :pid"
                    ),
                    {"pid": int(pid)},
                ).scalar()
                or 0
            ),
        }

    staff_impact = {
        "has_staff_profile": st is not None,
        "staff_estado": (str(getattr(st, "estado", "") or "").strip().lower() or None)
        if st is not None
        else None,
        "staff_tipo": (str(getattr(st, "tipo", "") or "").strip().lower() or None)
        if st is not None
        else None,
        "has_permissions": perm is not None,
        "scopes_count": len(list(perm.scopes or [])) if perm is not None else 0,
        "sesiones_activas": int(
            svc_staff.db.execute(
                text(
                    "SELECT COUNT(*) FROM staff_sessions WHERE staff_id = :sid AND hora_fin IS NULL"
                ),
                {"sid": int(getattr(st, "id", 0) or 0)},
            ).scalar()
            or 0
        )
        if st is not None
        else 0,
        "sucursales_count": int(
            svc_staff.db.execute(
                text("SELECT COUNT(*) FROM usuario_sucursales WHERE usuario_id = :uid"),
                {"uid": int(uid)},
            ).scalar()
            or 0
        ),
    }

    return {"ok": True, "usuario_id": int(uid), "profesor": profesor_impact, "staff": staff_impact}


@router.post("/api/team/convert")
async def api_team_convert(
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
    target = str((payload or {}).get("target") or "").strip().lower()
    force = bool((payload or {}).get("force"))
    rol_staff = str((payload or {}).get("rol") or "").strip().lower()

    if not usuario_id:
        raise HTTPException(status_code=400, detail="usuario_id requerido")
    if target not in ("staff", "profesor", "usuario"):
        raise HTTPException(status_code=400, detail="target inválido")

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

    ensure_clase_profesor_schema(svc_staff.db)

    prof = (
        svc_staff.db.scalars(
            select(Profesor).where(Profesor.usuario_id == int(usuario_id)).limit(1)
        ).first()
    )
    pid = int(getattr(prof, "id", 0) or 0) if prof is not None else 0
    st = (
        svc_staff.db.scalars(
            select(StaffProfile).where(StaffProfile.usuario_id == int(usuario_id)).limit(1)
        ).first()
    )
    staff_profile_id = int(getattr(st, "id", 0) or 0) if st is not None else 0
    active_assignments = 0
    active_prof_sessions = 0
    if pid:
        active_assignments = int(
            svc_staff.db.execute(
                text(
                    "SELECT COUNT(*) FROM profesor_clase_asignaciones WHERE profesor_id = :pid AND activa = TRUE"
                ),
                {"pid": int(pid)},
            ).scalar()
            or 0
        )
        active_prof_sessions = int(
            svc_staff.db.execute(
                text(
                    "SELECT COUNT(*) FROM profesor_horas_trabajadas WHERE profesor_id = :pid AND hora_fin IS NULL"
                ),
                {"pid": int(pid)},
            ).scalar()
            or 0
        )

    active_staff_sessions = 0
    if staff_profile_id:
        active_staff_sessions = int(
            svc_staff.db.execute(
                text(
                    "SELECT COUNT(*) FROM staff_sessions WHERE staff_id = :sid AND hora_fin IS NULL"
                ),
                {"sid": int(staff_profile_id)},
            ).scalar()
            or 0
        )

    def block_if_profesor_has_load(kind_error: str) -> None:
        if not pid:
            return
        if active_prof_sessions > 0:
            raise HTTPException(
                status_code=409,
                detail={
                    "ok": False,
                    "error": kind_error,
                    "reason": "sesion_profesor_activa",
                    "profesor_id": int(pid),
                    "sesiones_activas": int(active_prof_sessions),
                },
            )
        if active_assignments > 0:
            raise HTTPException(
                status_code=409,
                detail={
                    "ok": False,
                    "error": kind_error,
                    "reason": "clases_asignadas_activas",
                    "profesor_id": int(pid),
                    "clases_asignadas_activas": int(active_assignments),
                },
            )

    def block_if_staff_has_session(kind_error: str) -> None:
        if not staff_profile_id:
            return
        if active_staff_sessions > 0:
            raise HTTPException(
                status_code=409,
                detail={
                    "ok": False,
                    "error": kind_error,
                    "reason": "sesion_staff_activa",
                    "staff_profile_id": int(staff_profile_id),
                    "sesiones_activas": int(active_staff_sessions),
                },
            )

    try:
        sid = int(sucursal_id)
    except Exception:
        sid = 0

    if target == "profesor":
        if staff_profile_id and not force:
            block_if_staff_has_session("no_se_puede_quitar_staff")
        if prof is None:
            svc_prof.crear_perfil_profesor(int(usuario_id), payload or {}, sucursal_id=int(sid) if sid > 0 else None)
        else:
            try:
                svc_staff.db.execute(
                    text("UPDATE profesores SET estado = 'activo' WHERE id = :pid"),
                    {"pid": int(pid)},
                )
            except Exception:
                pass
        svc_staff.set_user_role(int(usuario_id), "profesor")
        if sid > 0:
            svc_staff.set_user_branches(int(usuario_id), [sid])
        if st is not None:
            try:
                svc_staff.db.execute(
                    text(
                        "UPDATE staff_profiles SET estado = 'inactivo', tipo = 'empleado', fecha_actualizacion = NOW() WHERE usuario_id = :uid"
                    ),
                    {"uid": int(usuario_id)},
                )
            except Exception:
                pass
        try:
            svc_staff.set_scopes(int(usuario_id), [])
        except Exception:
            pass
        try:
            svc_staff.db.commit()
        except Exception:
            svc_staff.db.rollback()
            raise
        return {"ok": True, "usuario_id": int(usuario_id), "target": "profesor"}

    if target == "staff":
        if not rol_staff or rol_staff in ("dueño", "dueno", "owner", "profesor"):
            rol_staff = "empleado"

        if pid and not force:
            block_if_profesor_has_load("no_se_puede_quitar_profesor")

        svc_staff.set_user_role(int(usuario_id), rol_staff)
        svc_staff.upsert_staff_profile(int(usuario_id), tipo=rol_staff, estado="activo")
        if sid > 0:
            svc_staff.set_user_branches(int(usuario_id), [sid])
        existing_perm = svc_staff.db.scalars(
            select(StaffPermission).where(StaffPermission.usuario_id == int(usuario_id))
        ).first()
        if existing_perm is None:
            svc_staff.set_scopes(int(usuario_id), [])

        if pid:
            if force and active_assignments > 0:
                svc_staff.db.execute(
                    text(
                        "UPDATE profesor_clase_asignaciones SET activa = FALSE WHERE profesor_id = :pid AND activa = TRUE"
                    ),
                    {"pid": int(pid)},
                )
            svc_staff.db.execute(
                text("UPDATE profesores SET estado = 'inactivo' WHERE id = :pid"),
                {"pid": int(pid)},
            )

        try:
            svc_staff.db.commit()
        except Exception:
            svc_staff.db.rollback()
            raise
        return {"ok": True, "usuario_id": int(usuario_id), "target": "staff"}

    if staff_profile_id and not force:
        block_if_staff_has_session("no_se_puede_quitar_del_equipo")
    if pid and not force:
        block_if_profesor_has_load("no_se_puede_quitar_del_equipo")

    svc_staff.set_user_role(int(usuario_id), "socio")
    if st is not None:
        svc_staff.upsert_staff_profile(int(usuario_id), estado="inactivo")
    try:
        svc_staff.set_user_branches(int(usuario_id), [])
    except Exception:
        pass
    try:
        svc_staff.set_scopes(int(usuario_id), [])
    except Exception:
        pass
    if pid:
        if force and active_assignments > 0:
            svc_staff.db.execute(
                text(
                    "UPDATE profesor_clase_asignaciones SET activa = FALSE WHERE profesor_id = :pid AND activa = TRUE"
                ),
                {"pid": int(pid)},
            )
        svc_staff.db.execute(
            text("UPDATE profesores SET estado = 'inactivo' WHERE id = :pid"),
            {"pid": int(pid)},
        )
    try:
        svc_staff.db.commit()
    except Exception:
        svc_staff.db.rollback()
        raise
    return {"ok": True, "usuario_id": int(usuario_id), "target": "usuario"}


@router.post("/api/team/delete_profile")
async def api_team_delete_profile(
    request: Request,
    _=Depends(require_owner),
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
    force = bool((payload or {}).get("force"))

    if not usuario_id:
        raise HTTPException(status_code=400, detail="usuario_id requerido")
    if kind not in ("staff", "profesor"):
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

    ensure_clase_profesor_schema(svc_staff.db)

    prof = (
        svc_staff.db.scalars(
            select(Profesor).where(Profesor.usuario_id == int(usuario_id)).limit(1)
        ).first()
    )
    pid = int(getattr(prof, "id", 0) or 0) if prof is not None else 0
    st = (
        svc_staff.db.scalars(
            select(StaffProfile).where(StaffProfile.usuario_id == int(usuario_id)).limit(1)
        ).first()
    )
    staff_profile_id = int(getattr(st, "id", 0) or 0) if st is not None else 0

    active_assignments = 0
    active_prof_sessions = 0
    if pid:
        active_assignments = int(
            svc_staff.db.execute(
                text(
                    "SELECT COUNT(*) FROM profesor_clase_asignaciones WHERE profesor_id = :pid AND activa = TRUE"
                ),
                {"pid": int(pid)},
            ).scalar()
            or 0
        )
        active_prof_sessions = int(
            svc_staff.db.execute(
                text(
                    "SELECT COUNT(*) FROM profesor_horas_trabajadas WHERE profesor_id = :pid AND hora_fin IS NULL"
                ),
                {"pid": int(pid)},
            ).scalar()
            or 0
        )

    active_staff_sessions = 0
    if staff_profile_id:
        active_staff_sessions = int(
            svc_staff.db.execute(
                text(
                    "SELECT COUNT(*) FROM staff_sessions WHERE staff_id = :sid AND hora_fin IS NULL"
                ),
                {"sid": int(staff_profile_id)},
            ).scalar()
            or 0
        )

    if kind == "profesor":
        if not pid:
            return {
                "ok": True,
                "usuario_id": int(usuario_id),
                "kind": "profesor",
                "deleted": False,
            }
        if active_prof_sessions > 0:
            raise HTTPException(
                status_code=409,
                detail={
                    "ok": False,
                    "error": "no_se_puede_eliminar_profesor",
                    "reason": "sesion_profesor_activa",
                    "profesor_id": int(pid),
                    "sesiones_activas": int(active_prof_sessions),
                },
            )
        if active_assignments > 0 and not force:
            raise HTTPException(
                status_code=409,
                detail={
                    "ok": False,
                    "error": "no_se_puede_eliminar_profesor",
                    "reason": "clases_asignadas_activas",
                    "profesor_id": int(pid),
                    "clases_asignadas_activas": int(active_assignments),
                },
            )
        if force and active_assignments > 0:
            svc_staff.db.execute(
                text(
                    "UPDATE profesor_clase_asignaciones SET activa = FALSE WHERE profesor_id = :pid AND activa = TRUE"
                ),
                {"pid": int(pid)},
            )
        try:
            svc_staff.db.execute(
                text("DELETE FROM profesores WHERE id = :pid"),
                {"pid": int(pid)},
            )
        except Exception:
            svc_staff.db.execute(
                text("UPDATE profesores SET estado = 'inactivo' WHERE id = :pid"),
                {"pid": int(pid)},
            )

        if st is not None:
            st_estado = str(getattr(st, "estado", "") or "").strip().lower()
            if st_estado != "inactivo":
                rol_staff = str(getattr(st, "tipo", "") or "").strip().lower() or "empleado"
                if rol_staff in ("dueño", "dueno", "owner", "profesor"):
                    rol_staff = "empleado"
                svc_staff.set_user_role(int(usuario_id), rol_staff)
            else:
                svc_staff.set_user_role(int(usuario_id), "socio")
                try:
                    svc_staff.set_user_branches(int(usuario_id), [])
                except Exception:
                    pass
        else:
            svc_staff.set_user_role(int(usuario_id), "socio")
            try:
                svc_staff.set_user_branches(int(usuario_id), [])
            except Exception:
                pass

        try:
            svc_staff.db.commit()
        except Exception:
            svc_staff.db.rollback()
            raise
        return {"ok": True, "usuario_id": int(usuario_id), "kind": "profesor", "deleted": True}

    if staff_profile_id and active_staff_sessions > 0:
        raise HTTPException(
            status_code=409,
            detail={
                "ok": False,
                "error": "no_se_puede_eliminar_staff",
                "reason": "sesion_staff_activa",
                "staff_profile_id": int(staff_profile_id),
                "sesiones_activas": int(active_staff_sessions),
            },
        )
    if st is None:
        return {"ok": True, "usuario_id": int(usuario_id), "kind": "staff", "deleted": False}
    try:
        svc_staff.db.execute(
            text("DELETE FROM staff_permissions WHERE usuario_id = :uid"),
            {"uid": int(usuario_id)},
        )
    except Exception:
        pass
    try:
        svc_staff.db.execute(
            text("DELETE FROM staff_profiles WHERE usuario_id = :uid"),
            {"uid": int(usuario_id)},
        )
    except Exception:
        svc_staff.db.execute(
            text("UPDATE staff_profiles SET estado = 'inactivo' WHERE usuario_id = :uid"),
            {"uid": int(usuario_id)},
        )

    if pid:
        prof_estado = str(getattr(prof, "estado", "") or "").strip().lower() if prof is not None else ""
        if prof_estado and prof_estado != "inactivo":
            svc_staff.set_user_role(int(usuario_id), "profesor")
        else:
            svc_staff.set_user_role(int(usuario_id), "socio")
            try:
                svc_staff.set_user_branches(int(usuario_id), [])
            except Exception:
                pass
    else:
        svc_staff.set_user_role(int(usuario_id), "socio")
        try:
            svc_staff.set_user_branches(int(usuario_id), [])
        except Exception:
            pass

    try:
        svc_staff.db.commit()
    except Exception:
        svc_staff.db.rollback()
        raise
    return {"ok": True, "usuario_id": int(usuario_id), "kind": "staff", "deleted": True}


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
        try:
            svc_staff.db.execute(
                text("UPDATE profesores SET estado = 'inactivo' WHERE usuario_id = :uid"),
                {"uid": int(usuario_id)},
            )
        except Exception:
            pass
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
    try:
        svc_staff.db.execute(
            text(
                "UPDATE staff_profiles SET estado = 'inactivo', tipo = 'empleado', fecha_actualizacion = NOW() WHERE usuario_id = :uid"
            ),
            {"uid": int(usuario_id)},
        )
    except Exception:
        pass
    try:
        svc_staff.set_scopes(int(usuario_id), [])
    except Exception:
        pass
    svc_staff.db.commit()
    return {"ok": True, "usuario_id": int(usuario_id), "kind": "profesor", "profesor_id": int(profesor_id)}
