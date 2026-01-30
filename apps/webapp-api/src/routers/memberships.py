import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.dependencies import get_db_session, require_owner
from src.services.membership_service import MembershipService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/gestion/usuarios/{usuario_id}/membership")
async def api_get_user_membership(
    request: Request,
    usuario_id: int,
    _=Depends(require_owner),
    db: Session = Depends(get_db_session),
):
    svc = MembershipService(db)
    m = svc.get_active_membership(int(usuario_id))
    if not m:
        return {"ok": True, "membership": None}
    sucursales: List[int] = []
    try:
        if not bool(m.get("all_sucursales")):
            sucursales = svc.get_membership_sucursales(int(m.get("id")))
    except Exception:
        sucursales = []
    return {"ok": True, "membership": m, "sucursales": sucursales}


@router.post("/api/gestion/usuarios/{usuario_id}/membership")
async def api_set_user_membership(
    request: Request,
    usuario_id: int,
    _=Depends(require_owner),
    db: Session = Depends(get_db_session),
):
    svc = MembershipService(db)
    try:
        data = await request.json()
    except Exception:
        data = {}

    plan_name = data.get("plan_name")
    all_sucursales = bool(data.get("all_sucursales") or False)
    sucursal_ids = data.get("sucursal_ids") or data.get("sucursales") or []

    start_date = data.get("start_date")
    end_date = data.get("end_date")
    sd: Optional[date] = None
    ed: Optional[date] = None
    try:
        if start_date:
            sd = date.fromisoformat(str(start_date))
    except Exception:
        sd = None
    try:
        if end_date:
            ed = date.fromisoformat(str(end_date))
    except Exception:
        ed = None

    res = svc.set_active_membership(
        int(usuario_id),
        plan_name=str(plan_name).strip() if plan_name is not None else None,
        start_date=sd,
        end_date=ed,
        all_sucursales=bool(all_sucursales),
        sucursal_ids=sucursal_ids if isinstance(sucursal_ids, list) else [],
    )
    if not res.get("ok"):
        return JSONResponse(res, status_code=400)
    return res
