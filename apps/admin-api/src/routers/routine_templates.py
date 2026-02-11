import os
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.services.admin_service import AdminService
from src.utils.raw_postgres import RawPostgresManager

router = APIRouter(prefix="/api", tags=["RoutineTemplates"])

_admin_service = None


def get_admin_service() -> AdminService:
    global _admin_service
    if _admin_service is not None:
        return _admin_service
    params = AdminService.resolve_admin_db_params()
    db = RawPostgresManager(connection_params=params)
    _admin_service = AdminService(db)
    return _admin_service


def require_admin(request: Request):
    try:
        if request.session.get("admin_logged_in"):
            return
    except Exception:
        pass
    secret = os.getenv("ADMIN_SECRET", "").strip()
    if secret and request.headers.get("x-admin-secret") == secret:
        return
    raise HTTPException(status_code=401, detail="Unauthorized")


class RoutineTemplateAssignCreate(BaseModel):
    template_id: int
    activa: bool = True
    prioridad: int = 0
    notas: Optional[str] = None


class RoutineTemplateAssignUpdate(BaseModel):
    activa: Optional[bool] = None
    prioridad: Optional[int] = None
    notas: Optional[str] = None


@router.get("/gyms/{gym_id}/routine-templates/catalog")
async def get_routine_templates_catalog(gym_id: int, request: Request):
    require_admin(request)
    adm = get_admin_service()
    out = adm.tenant_routine_templates_catalog(int(gym_id))
    code = 200 if out.get("ok") else 400
    return JSONResponse(out, status_code=code)


@router.get("/gyms/{gym_id}/routine-templates/assignments")
async def get_routine_templates_assignments(gym_id: int, request: Request):
    require_admin(request)
    adm = get_admin_service()
    out = adm.tenant_routine_template_assignments(int(gym_id))
    code = 200 if out.get("ok") else 400
    return JSONResponse(out, status_code=code)


@router.post("/gyms/{gym_id}/routine-templates/assign")
async def assign_routine_template(gym_id: int, payload: RoutineTemplateAssignCreate, request: Request):
    require_admin(request)
    adm = get_admin_service()
    out = adm.tenant_assign_routine_template(
        int(gym_id),
        int(payload.template_id),
        activa=bool(payload.activa),
        prioridad=int(payload.prioridad or 0),
        notas=payload.notas,
    )
    code = 200 if out.get("ok") else 400
    return JSONResponse(out, status_code=code)


@router.patch("/gyms/{gym_id}/routine-templates/assignments/{assignment_id}")
async def update_routine_template_assignment(
    gym_id: int, assignment_id: int, payload: RoutineTemplateAssignUpdate, request: Request
):
    require_admin(request)
    adm = get_admin_service()
    out = adm.tenant_update_routine_template_assignment(
        int(gym_id),
        int(assignment_id),
        activa=payload.activa,
        prioridad=payload.prioridad,
        notas=payload.notas,
    )
    code = 200 if out.get("ok") else 400
    return JSONResponse(out, status_code=code)


@router.delete("/gyms/{gym_id}/routine-templates/assignments/{assignment_id}")
async def delete_routine_template_assignment(gym_id: int, assignment_id: int, request: Request):
    require_admin(request)
    adm = get_admin_service()
    out = adm.tenant_delete_routine_template_assignment(int(gym_id), int(assignment_id))
    code = 200 if out.get("ok") else 400
    return JSONResponse(out, status_code=code)

