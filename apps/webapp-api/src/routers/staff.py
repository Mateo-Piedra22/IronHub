from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse

from src.dependencies import (
    get_staff_service,
    require_gestion_access,
    require_owner,
    require_sucursal_selected,
    require_feature,
    get_audit_service,
)
from src.security.session_claims import get_claims
from src.services.audit_service import AuditService
from src.services.staff_service import StaffService

router = APIRouter(dependencies=[Depends(require_feature("usuarios"))])


@router.get("/api/staff")
async def api_staff_list(
    request: Request,
    sucursal_id: int = Depends(require_sucursal_selected),
    _=Depends(require_owner),
    svc: StaffService = Depends(get_staff_service),
    search: str = "",
    all: bool = Query(False),
):
    try:
        return {
            "items": svc.list_staff(
                search=search, sucursal_id=int(sucursal_id), show_all=False
            )
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/api/staff/{usuario_id}")
async def api_staff_update(
    usuario_id: int,
    request: Request,
    _=Depends(require_owner),
    svc: StaffService = Depends(get_staff_service),
    audit: AuditService = Depends(get_audit_service),
):
    try:
        old_state = svc.get_staff_item(int(usuario_id))
        payload = await request.json()
        rol = payload.get("rol")
        activo = payload.get("activo")
        tipo = payload.get("tipo")
        estado = payload.get("estado")
        sucursales = payload.get("sucursales")
        scopes = payload.get("scopes")

        if rol is not None:
            svc.set_user_role(int(usuario_id), str(rol))
        if activo is not None:
            svc.set_user_active(int(usuario_id), bool(activo))
        if tipo is not None or estado is not None:
            svc.upsert_staff_profile(int(usuario_id), tipo=tipo, estado=estado)
        if isinstance(sucursales, list):
            svc.set_user_branches(int(usuario_id), sucursales)
        if isinstance(scopes, list):
            svc.set_scopes(int(usuario_id), scopes)

        svc.commit()
        new_state = svc.get_staff_item(int(usuario_id))
        try:
            audit.log_from_request(
                request=request,
                action=AuditService.ACTION_UPDATE,
                table_name="usuarios",
                record_id=int(usuario_id),
                old_values=old_state or {},
                new_values=new_state or {},
            )
        except Exception:
            pass
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        try:
            svc.db.rollback()
        except Exception:
            pass
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/staff/session/start")
async def api_staff_session_start(
    request: Request,
    sucursal_id: int = Depends(require_sucursal_selected),
    _=Depends(require_gestion_access),
    svc: StaffService = Depends(get_staff_service),
):
    claims = get_claims(request)
    user_id = claims.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        sess_id = svc.start_session(int(user_id), int(sucursal_id))
        svc.commit()
        return {"ok": True, "session_id": int(sess_id)}
    except Exception as e:
        try:
            svc.db.rollback()
        except Exception:
            pass
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/staff/session/end")
async def api_staff_session_end(
    request: Request,
    _=Depends(require_gestion_access),
    svc: StaffService = Depends(get_staff_service),
):
    claims = get_claims(request)
    user_id = claims.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        ok = bool(svc.end_session(int(user_id)))
        if ok:
            svc.commit()
        else:
            svc.db.rollback()
        return {"ok": ok}
    except Exception as e:
        try:
            svc.db.rollback()
        except Exception:
            pass
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/staff/{usuario_id}/sesiones")
async def api_staff_sessions_list(
    usuario_id: int,
    request: Request,
    _=Depends(require_owner),
    svc: StaffService = Depends(get_staff_service),
    desde: str = "",
    hasta: str = "",
    page: int = 1,
    limit: int = 50,
):
    try:
        d = str(desde or "").strip() or None
        h = str(hasta or "").strip() or None
        return svc.list_sessions(int(usuario_id), desde=d, hasta=h, page=page, limit=limit)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/staff/{usuario_id}/sesiones/activa")
async def api_staff_session_active(
    usuario_id: int,
    _=Depends(require_owner),
    svc: StaffService = Depends(get_staff_service),
):
    try:
        return {"sesion": svc.get_active_session(int(usuario_id))}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/staff/{usuario_id}/sesiones")
async def api_staff_session_create(
    usuario_id: int,
    request: Request,
    _=Depends(require_owner),
    svc: StaffService = Depends(get_staff_service),
    audit: AuditService = Depends(get_audit_service),
):
    try:
        payload = await request.json()
        inicio_raw = (payload or {}).get("hora_inicio") or (payload or {}).get("inicio")
        fin_raw = (payload or {}).get("hora_fin") or (payload or {}).get("fin")
        sid = (payload or {}).get("sucursal_id")
        notas = (payload or {}).get("notas")
        if not inicio_raw:
            raise HTTPException(status_code=400, detail="hora_inicio requerido")
        try:
            inicio = datetime.fromisoformat(str(inicio_raw))
        except Exception:
            raise HTTPException(status_code=400, detail="hora_inicio inválido")
        fin = None
        if fin_raw:
            try:
                fin = datetime.fromisoformat(str(fin_raw))
            except Exception:
                raise HTTPException(status_code=400, detail="hora_fin inválido")
        try:
            sucursal_id = int(sid) if sid is not None else None
        except Exception:
            sucursal_id = None
        sess_id = svc.create_session(
            int(usuario_id),
            sucursal_id=sucursal_id,
            hora_inicio=inicio,
            hora_fin=fin,
            notas=str(notas) if notas is not None else None,
        )
        svc.commit()
        try:
            audit.log_from_request(
                request=request,
                action=AuditService.ACTION_INSERT,
                table_name="staff_sessions",
                record_id=int(sess_id),
                old_values={},
                new_values={
                    "usuario_id": int(usuario_id),
                    "sucursal_id": sucursal_id,
                    "hora_inicio": str(inicio_raw or ""),
                    "hora_fin": str(fin_raw or ""),
                },
            )
        except Exception:
            pass
        return {"ok": True, "id": int(sess_id)}
    except HTTPException:
        raise
    except Exception as e:
        try:
            svc.db.rollback()
        except Exception:
            pass
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/api/staff/sesiones/{sesion_id}")
async def api_staff_session_update(
    sesion_id: int,
    request: Request,
    _=Depends(require_owner),
    svc: StaffService = Depends(get_staff_service),
    audit: AuditService = Depends(get_audit_service),
):
    try:
        payload = await request.json()
        inicio_raw = (payload or {}).get("hora_inicio") or (payload or {}).get("inicio")
        fin_raw = (payload or {}).get("hora_fin") or (payload or {}).get("fin")
        sid = (payload or {}).get("sucursal_id")
        notas = (payload or {}).get("notas")
        inicio = None
        if inicio_raw is not None:
            try:
                inicio = datetime.fromisoformat(str(inicio_raw))
            except Exception:
                raise HTTPException(status_code=400, detail="hora_inicio inválido")
        fin = None
        if fin_raw is not None:
            try:
                fin = datetime.fromisoformat(str(fin_raw)) if fin_raw else None
            except Exception:
                raise HTTPException(status_code=400, detail="hora_fin inválido")
        sucursal_id = None
        if sid is not None:
            try:
                sucursal_id = int(sid) if sid else None
            except Exception:
                sucursal_id = None
        ok = bool(
            svc.update_session(
                int(sesion_id),
                sucursal_id=sucursal_id,
                hora_inicio=inicio,
                hora_fin=fin,
                notas=str(notas) if notas is not None else None,
            )
        )
        if ok:
            svc.commit()
            try:
                audit.log_from_request(
                    request=request,
                    action=AuditService.ACTION_UPDATE,
                    table_name="staff_sessions",
                    record_id=int(sesion_id),
                    old_values={},
                    new_values={
                        "sucursal_id": sucursal_id,
                        "hora_inicio": str(inicio_raw or ""),
                        "hora_fin": str(fin_raw or ""),
                    },
                )
            except Exception:
                pass
            return {"ok": True}
        svc.db.rollback()
        return JSONResponse({"ok": False, "error": "No encontrado"}, status_code=404)
    except HTTPException:
        raise
    except Exception as e:
        try:
            svc.db.rollback()
        except Exception:
            pass
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/staff/sesiones/{sesion_id}")
async def api_staff_session_delete(
    sesion_id: int,
    request: Request,
    _=Depends(require_owner),
    svc: StaffService = Depends(get_staff_service),
    audit: AuditService = Depends(get_audit_service),
):
    try:
        ok = bool(svc.delete_session(int(sesion_id)))
        if ok:
            svc.commit()
            try:
                audit.log_from_request(
                    request=request,
                    action=AuditService.ACTION_DELETE,
                    table_name="staff_sessions",
                    record_id=int(sesion_id),
                    old_values={},
                    new_values={},
                )
            except Exception:
                pass
            return {"ok": True}
        svc.db.rollback()
        return JSONResponse({"ok": False, "error": "No encontrado"}, status_code=404)
    except Exception as e:
        try:
            svc.db.rollback()
        except Exception:
            pass
        return JSONResponse({"error": str(e)}, status_code=500)
