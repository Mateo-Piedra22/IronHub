from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.dependencies import get_db_session, require_gestion_access, require_sucursal_selected
from src.security.session_claims import get_claims
from src.dependencies import get_audit_service
from src.services.audit_service import AuditService
from src.services.work_session_service import WorkSessionService

router = APIRouter()


@router.get("/api/my/work-session")
async def api_my_work_session_get(
    request: Request,
    _=Depends(require_gestion_access),
    db: Session = Depends(get_db_session),
):
    try:
        claims = get_claims(request)
        svc = WorkSessionService(db)
        data = svc.get_my_state(
            role=str(claims.get("role") or ""),
            user_id=claims.get("user_id"),
            session_profesor_id=request.session.get("gestion_profesor_id"),
        )
        return data
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.post("/api/my/work-session/start")
async def api_my_work_session_start(
    request: Request,
    sucursal_id: int = Depends(require_sucursal_selected),
    _=Depends(require_gestion_access),
    db: Session = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
):
    try:
        claims = get_claims(request)
        svc = WorkSessionService(db)
        data = svc.start_my_session(
            role=str(claims.get("role") or ""),
            user_id=claims.get("user_id"),
            session_profesor_id=request.session.get("gestion_profesor_id"),
            sucursal_id=int(sucursal_id) if sucursal_id else None,
        )
        try:
            if data and data.get("ok") and data.get("session_id"):
                table_name = "staff_sessions" if data.get("kind") == "staff" else "profesor_horas_trabajadas"
                audit.log_from_request(
                    request=request,
                    action=AuditService.ACTION_INSERT,
                    table_name=str(table_name),
                    record_id=int(data.get("session_id")),
                    old_values={},
                    new_values={
                        "kind": data.get("kind"),
                        "sucursal_id": data.get("sucursal_id"),
                        "started_at": data.get("started_at"),
                    },
                )
        except Exception:
            pass
        return data
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.post("/api/my/work-session/pause")
async def api_my_work_session_pause(
    request: Request,
    _=Depends(require_gestion_access),
    db: Session = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
):
    try:
        claims = get_claims(request)
        svc = WorkSessionService(db)
        data = svc.pause_my_session(
            role=str(claims.get("role") or ""),
            user_id=claims.get("user_id"),
            session_profesor_id=request.session.get("gestion_profesor_id"),
        )
        try:
            st = svc.get_my_state(
                role=str(claims.get("role") or ""),
                user_id=claims.get("user_id"),
                session_profesor_id=request.session.get("gestion_profesor_id"),
            )
            active = (st or {}).get("active") or {}
            if data and data.get("ok") and active.get("session_id"):
                audit.log_from_request(
                    request=request,
                    action=AuditService.ACTION_UPDATE,
                    table_name="work_session_pauses",
                    record_id=int(active.get("session_id")),
                    old_values={},
                    new_values={"kind": st.get("kind"), "event": "pause"},
                )
        except Exception:
            pass
        return data
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.post("/api/my/work-session/resume")
async def api_my_work_session_resume(
    request: Request,
    _=Depends(require_gestion_access),
    db: Session = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
):
    try:
        claims = get_claims(request)
        svc = WorkSessionService(db)
        data = svc.resume_my_session(
            role=str(claims.get("role") or ""),
            user_id=claims.get("user_id"),
            session_profesor_id=request.session.get("gestion_profesor_id"),
        )
        try:
            st = svc.get_my_state(
                role=str(claims.get("role") or ""),
                user_id=claims.get("user_id"),
                session_profesor_id=request.session.get("gestion_profesor_id"),
            )
            active = (st or {}).get("active") or {}
            if data and data.get("ok") and active.get("session_id"):
                audit.log_from_request(
                    request=request,
                    action=AuditService.ACTION_UPDATE,
                    table_name="work_session_pauses",
                    record_id=int(active.get("session_id")),
                    old_values={},
                    new_values={"kind": st.get("kind"), "event": "resume"},
                )
        except Exception:
            pass
        return data
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.post("/api/my/work-session/end")
async def api_my_work_session_end(
    request: Request,
    _=Depends(require_gestion_access),
    db: Session = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
):
    try:
        claims = get_claims(request)
        svc = WorkSessionService(db)
        st = svc.get_my_state(
            role=str(claims.get("role") or ""),
            user_id=claims.get("user_id"),
            session_profesor_id=request.session.get("gestion_profesor_id"),
        )
        active = (st or {}).get("active") or {}
        sid = active.get("session_id")
        kind = st.get("kind")
        data = svc.end_my_session(
            role=str(claims.get("role") or ""),
            user_id=claims.get("user_id"),
            session_profesor_id=request.session.get("gestion_profesor_id"),
        )
        try:
            if data and data.get("ok") and sid:
                table_name = "staff_sessions" if kind == "staff" else "profesor_horas_trabajadas"
                audit.log_from_request(
                    request=request,
                    action=AuditService.ACTION_UPDATE,
                    table_name=str(table_name),
                    record_id=int(sid),
                    old_values={},
                    new_values={"kind": kind, "event": "end", "minutos": data.get("minutos")},
                )
        except Exception:
            pass
        return data
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
