import logging
import secrets
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text

from src.dependencies import (
    get_user_service,
    get_profesor_service,
    require_gestion_access,
    require_owner,
    get_auth_service,
    get_whatsapp_dispatch_service,
    get_audit_service,
    require_feature,
    require_sucursal_selected,
    require_sucursal_selected_optional,
    get_membership_service,
    require_scope,
)
from src.services import UserService, ProfesorService
from src.services.auth_service import AuthService
from src.services.whatsapp_dispatch_service import WhatsAppDispatchService
from src.services.audit_service import AuditService
from src.services.membership_service import MembershipService
from src.services.entitlements_payload_service import EntitlementsPayloadService

# Fallback for UsuarioEstado if not imported correctly or available
try:
    from src.models import UsuarioEstado
except ImportError:
    UsuarioEstado = None

router = APIRouter()
logger = logging.getLogger(__name__)

templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/api/usuario/entitlements")
async def api_usuario_entitlements(
    request: Request,
    _=Depends(require_sucursal_selected),
    user_service: UserService = Depends(get_user_service),
):
    session_user_id = request.session.get("user_id")
    if session_user_id is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        uid = int(session_user_id)
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized")
    sid = request.session.get("sucursal_id")
    try:
        sid_int = int(sid) if sid is not None else None
    except Exception:
        sid_int = None

    payload = EntitlementsPayloadService(user_service.db).get_payload(uid, sid_int)

    return {
        "ok": True,
        **payload,
    }


@router.get(
    "/api/gestion/usuarios/{usuario_id}/entitlements/summary",
    dependencies=[Depends(require_feature("usuarios")), Depends(require_scope("usuarios:read"))],
)
async def api_usuario_entitlements_summary_gestion(
    usuario_id: int,
    request: Request,
    user_service: UserService = Depends(get_user_service),
    sucursal_id: int = Depends(require_sucursal_selected),
    _=Depends(require_gestion_access),
):
    try:
        uid = int(usuario_id)
        sid = int(sucursal_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Parámetros inválidos")
    payload = EntitlementsPayloadService(user_service.db).get_payload(uid, sid)
    return {"ok": True, **payload}


@router.post("/api/usuarios/{usuario_id}/pin/reset")
async def api_usuario_pin_reset(
    usuario_id: int,
    request: Request,
    _=Depends(require_owner),
    auth: AuthService = Depends(get_auth_service),
    audit: AuditService = Depends(get_audit_service),
):
    try:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        pin_in = (payload or {}).get("pin")
        pin = str(pin_in or "").strip()
        if not pin:
            pin = str(100000 + secrets.randbelow(900000))
        if len(pin) < 4:
            raise HTTPException(status_code=400, detail="PIN inválido")
        ok = bool(auth.actualizar_pin(int(usuario_id), pin))
        if not ok:
            return JSONResponse({"ok": False, "error": "No se pudo actualizar"}, status_code=400)
        try:
            audit.log_from_request(
                request=request,
                action=AuditService.ACTION_UPDATE,
                table_name="usuarios",
                record_id=int(usuario_id),
                old_values={"pin_reset": False},
                new_values={"pin_reset": True},
            )
        except Exception:
            pass
        return {"ok": True, "usuario_id": int(usuario_id), "pin": pin}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.get("/usuario/panel")
async def usuario_panel(
    request: Request, user_service: UserService = Depends(get_user_service)
):
    """Usuario panel - returns JSON with user data. Frontend handles the UI."""
    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"ok": False, "login_required": True}, status_code=401)

    try:
        data = user_service.get_user_panel_data(int(user_id))
    except Exception as e:
        logger.error(f"Error fetching user panel data: {e}")
        data = None

    if not data or not data.get("usuario"):
        request.session.clear()
        return JSONResponse({"ok": False, "login_required": True}, status_code=401)

    u = data["usuario"]

    return JSONResponse(
        {
            "ok": True,
            "usuario": {
                "id": getattr(u, "id", None),
                "nombre": getattr(u, "nombre", None),
                "dni": getattr(u, "dni", None),
                "activo": bool(getattr(u, "activo", False)),
            },
            "dias_restantes": data.get("dias_restantes"),
            "ultimo_pago": str(getattr(u, "ultimo_pago", None))
            if getattr(u, "ultimo_pago", None)
            else None,
            "pagos": data.get("pagos", []),
            "rutinas": data.get("rutinas", []),
        }
    )


# --- API Usuarios ---


@router.get(
    "/api/usuarios",
    dependencies=[Depends(require_feature("usuarios")), Depends(require_scope("usuarios:read"))],
)
async def api_usuarios_list(
    q: Optional[str] = None,
    search: Optional[str] = None,
    activo: Optional[bool] = None,
    page: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    user_service: UserService = Depends(get_user_service),
    sucursal_id: int = Depends(require_sucursal_selected),
    _=Depends(require_gestion_access),
):
    try:
        q_effective = (
            search if (search is not None and str(search).strip() != "") else q
        )
        limit_effective = max(1, min(int(limit or 50), 100))
        offset_effective = int(offset or 0)
        if offset_effective <= 0 and page is not None:
            try:
                page_int = int(page)
                if page_int > 0:
                    offset_effective = (page_int - 1) * limit_effective
            except Exception:
                pass
        offset_effective = max(0, offset_effective)

        out = user_service.list_users_paged(
            q_effective,
            activo=activo,
            limit=limit_effective,
            offset=offset_effective,
            sucursal_id=int(sucursal_id),
        )
        return {
            "usuarios": out.get("items", []),
            "total": int(out.get("total") or 0),
            "limit": int(limit_effective),
            "offset": int(offset_effective),
        }
    except Exception as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.put(
    "/api/usuarios/{usuario_id}/pin",
    dependencies=[
        Depends(require_feature("usuarios")),
        Depends(require_feature("usuarios:pin")),
        Depends(require_scope("usuarios:write")),
    ],
)
async def api_usuario_pin_set(
    usuario_id: int,
    request: Request,
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access),
):
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    try:
        is_owner = bool(request.session.get("logged_in")) and str(
            request.session.get("role") or ""
        ).strip().lower() in ("dueño", "dueno", "owner")

        reset = bool(payload.get("reset"))
        new_pin = payload.get("pin") or payload.get("new_pin")

        if reset:
            import secrets

            new_pin = "".join([str(secrets.randbelow(10)) for _ in range(6)])

        if new_pin is None:
            raise HTTPException(status_code=400, detail="pin es requerido")

        user_service.set_user_pin(int(usuario_id), str(new_pin), is_owner=is_owner)
        return {"ok": True, "pin": str(new_pin) if reset else None}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.get("/api/usuarios/check-dni", dependencies=[Depends(require_feature("usuarios"))])
async def api_check_dni_unique(
    request: Request,
    dni: str,
    exclude_id: Optional[int] = None,
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access),
):
    """
    Check if a DNI is available (not already in use by another user).

    Args:
        dni: The DNI to check
        exclude_id: Optional user ID to exclude from the check (for updates)

    Returns:
        {"available": bool, "user_id": int | null} - Whether the DNI is available
    """
    try:
        if not dni or not dni.strip():
            return {"available": True, "user_id": None}

        existing_user = user_service.get_user_by_dni(dni.strip())

        if existing_user is None:
            return {"available": True, "user_id": None}

        # If we're excluding a specific user (editing), check if it's the same user
        if exclude_id is not None and existing_user.id == exclude_id:
            return {"available": True, "user_id": existing_user.id}

        return {
            "available": False,
            "user_id": existing_user.id,
            "user_name": existing_user.nombre,
        }
    except Exception as e:
        logger.error(f"Error checking DNI: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/usuarios/{usuario_id}", dependencies=[Depends(require_feature("usuarios"))])
async def api_usuario_get(
    usuario_id: int,
    request: Request,
    user_service: UserService = Depends(get_user_service),
    sucursal_id: Optional[int] = Depends(require_sucursal_selected_optional),
    ms: MembershipService = Depends(get_membership_service),
):
    try:
        # AuthZ:
        # - Gestion sessions can access any user.
        # - Member sessions can only access their own record.
        try:
            role = str(request.session.get("role") or "").strip().lower()
        except Exception:
            role = ""
        is_gestion = (
            bool(request.session.get("logged_in"))
            or bool(request.session.get("gestion_profesor_user_id"))
            or role
            in (
                "dueño",
                "dueno",
                "owner",
                "admin",
                "administrador",
                "profesor",
                "empleado",
                "recepcionista",
                "staff",
            )
        )
        if is_gestion and sucursal_id is None:
            raise HTTPException(status_code=428, detail="Sucursal requerida")
        session_user_id = request.session.get("user_id")
        if (not is_gestion) and (session_user_id is None):
            raise HTTPException(status_code=401, detail="Unauthorized")
        if (
            (not is_gestion)
            and (session_user_id is not None)
            and int(session_user_id) != int(usuario_id)
        ):
            raise HTTPException(status_code=403, detail="Forbidden")
        if not is_gestion and session_user_id is not None:
            if sucursal_id is not None:
                allowed, reason = ms.check_access(int(session_user_id), int(sucursal_id))
            else:
                allowed, reason = ms.check_access_any(int(session_user_id))
            if allowed is False:
                raise HTTPException(status_code=403, detail=reason or "Forbidden")

        u = user_service.get_user(usuario_id)
        if not u:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        pin_value = None

        dias_restantes = None
        try:
            fpv = getattr(u, "fecha_proximo_vencimiento", None)
            if fpv:
                # Prefer service helper if present
                try:
                    today = user_service._today_local_date()  # type: ignore
                except Exception:
                    today = datetime.now(timezone.utc).replace(tzinfo=None).date()
                try:
                    fpv_d = fpv.date() if hasattr(fpv, "date") else fpv
                except Exception:
                    fpv_d = fpv
                dias_restantes = (fpv_d - today).days
        except Exception:
            dias_restantes = None

        sucursal_registro_id = getattr(u, "sucursal_registro_id", None)
        sucursal_registro_nombre = None
        try:
            if sucursal_registro_id is not None:
                row = user_service.db.execute(
                    text(
                        "SELECT nombre FROM sucursales WHERE id = :id LIMIT 1"
                    ),
                    {"id": int(sucursal_registro_id)},
                ).fetchone()
                if row and row[0]:
                    sucursal_registro_nombre = str(row[0])
        except Exception:
            sucursal_registro_nombre = None

        return {
            "id": u.id,
            "nombre": u.nombre,
            "dni": u.dni,
            "telefono": u.telefono,
            "email": getattr(u, "email", None),
            "pin": pin_value,
            "rol": (
                "user"
                if str(getattr(u, "rol", "") or "").strip().lower()
                in ("socio", "usuario")
                else getattr(u, "rol", None)
            ),
            "activo": bool(u.activo),
            "tipo_cuota": u.tipo_cuota,
            "tipo_cuota_nombre": u.tipo_cuota,
            "tipo_cuota_id": (
                user_service.payment_repo.obtener_tipo_cuota_por_nombre(u.tipo_cuota).id
                if getattr(u, "tipo_cuota", None)
                and user_service.payment_repo.obtener_tipo_cuota_por_nombre(
                    u.tipo_cuota
                )
                else None
            ),
            "notas": u.notas,
            "fecha_registro": u.fecha_registro,
            "fecha_proximo_vencimiento": u.fecha_proximo_vencimiento,
            "dias_restantes": dias_restantes,
            "cuotas_vencidas": u.cuotas_vencidas,
            "exento": bool(getattr(u, "exento", False)),
            "ultimo_pago": u.ultimo_pago,
            "sucursal_registro_id": int(sucursal_registro_id)
            if sucursal_registro_id is not None
            else None,
            "sucursal_registro_nombre": sucursal_registro_nombre,
        }
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.post(
    "/api/usuarios",
    dependencies=[Depends(require_feature("usuarios")), Depends(require_feature("usuarios:create"))],
)
async def api_usuario_create(
    request: Request,
    background_tasks: BackgroundTasks,
    user_service: UserService = Depends(get_user_service),
    wa: WhatsAppDispatchService = Depends(get_whatsapp_dispatch_service),
    _=Depends(require_gestion_access),
    sucursal_id: int = Depends(require_sucursal_selected),
):
    payload = await request.json()
    try:
        is_owner = bool(request.session.get("logged_in")) and str(
            request.session.get("role") or ""
        ).strip().lower() in ("dueño", "dueno", "owner")

        # Prepare data
        data = {
            "nombre": ((payload.get("nombre") or "").strip()).upper(),
            "dni": str(payload.get("dni") or "").strip(),
            "telefono": str(payload.get("telefono") or "").strip(),
            "pin": payload.get("pin") if isinstance(payload, dict) else None,
            "rol": (payload.get("rol") or "socio").strip().lower(),
            "activo": bool(payload.get("activo", True)),
            "tipo_cuota": payload.get("tipo_cuota"),
            "tipo_cuota_id": payload.get("tipo_cuota_id"),
            "notas": payload.get("notas"),
            "fecha_registro": datetime.now(timezone.utc).replace(tzinfo=None),
            "cuotas_vencidas": 0,
            "ultimo_pago": None,
            "sucursal_registro_id": int(sucursal_id) if sucursal_id else None,
        }

        if not data["nombre"] or not data["dni"]:
            raise HTTPException(
                status_code=400, detail="'nombre' y 'dni' son obligatorios"
            )

        new_id = user_service.create_user(data, is_owner=is_owner)
        try:
            role_norm = str(data.get("rol") or "").strip().lower()
        except Exception:
            role_norm = ""
        if role_norm in ("profesor", "empleado", "recepcionista", "staff"):
            try:
                sid_int = int(sucursal_id) if sucursal_id else None
            except Exception:
                sid_int = None
            if sid_int is not None and sid_int > 0:
                try:
                    user_service.db.execute(
                        text(
                            "INSERT INTO usuario_sucursales (usuario_id, sucursal_id, created_at) VALUES (:uid, :sid, NOW()) ON CONFLICT DO NOTHING"
                        ),
                        {"uid": int(new_id), "sid": int(sid_int)},
                    )
                    user_service.db.commit()
                except Exception:
                    try:
                        user_service.db.rollback()
                    except Exception:
                        pass
        try:
            if background_tasks is not None:
                background_tasks.add_task(
                    wa.send_welcome, int(new_id), int(sucursal_id)
                )
            else:
                wa.send_welcome(int(new_id), int(sucursal_id))
        except Exception:
            pass
        return {"id": new_id}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.put(
    "/api/usuarios/{usuario_id}",
    dependencies=[Depends(require_feature("usuarios")), Depends(require_feature("usuarios:update"))],
)
async def api_usuario_update(
    usuario_id: int,
    request: Request,
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access),
):
    payload = await request.json()
    try:
        is_owner = bool(request.session.get("logged_in")) and str(
            request.session.get("role") or ""
        ).strip().lower() in ("dueño", "dueno", "owner")

        # Clean payload
        data = payload.copy()
        if "nombre" in data:
            data["nombre"] = ((data.get("nombre") or "").strip()).upper()
        if "dni" in data:
            data["dni"] = str(data.get("dni") or "").strip()
        if "rol" in data:
            data["rol"] = (data.get("rol") or "socio").strip().lower()

        # Pin logic handled in service or simple pass through
        # The complicated pin logic in original router was about preserving existing pin if not provided.
        # Service update_user should handle 'if key in data'

        user_service.update_user(usuario_id, data, modifier_id=None, is_owner=is_owner)

        final_id = (
            int(data.get("new_id")) if (data.get("new_id") and is_owner) else usuario_id
        )
        return {"ok": True, "id": final_id}

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        if "no encontrado" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.delete(
    "/api/usuarios/{usuario_id}",
    dependencies=[Depends(require_feature("usuarios")), Depends(require_feature("usuarios:delete"))],
)
async def api_usuario_delete(
    usuario_id: int,
    request: Request,
    user_service: UserService = Depends(get_user_service),
    audit_service: AuditService = Depends(get_audit_service),
    _=Depends(require_gestion_access),
):
    try:
        # Get user info before deletion for audit log
        user_before = user_service.get_user(usuario_id)
        old_values = None
        if user_before:
            old_values = {
                "id": user_before.id,
                "nombre": user_before.nombre,
                "dni": user_before.dni,
                "activo": user_before.activo,
            }

        user_service.delete_user(usuario_id)

        # Log the deletion
        audit_service.log_from_request(
            request=request,
            action=AuditService.ACTION_DELETE,
            table_name="usuarios",
            record_id=usuario_id,
            old_values=old_values,
        )

        return {"ok": True}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.post("/api/usuarios/{usuario_id}/toggle-activo", dependencies=[Depends(require_feature("usuarios"))])
async def api_usuario_toggle_activo(
    usuario_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    user_service: UserService = Depends(get_user_service),
    wa: WhatsAppDispatchService = Depends(get_whatsapp_dispatch_service),
    audit_service: AuditService = Depends(get_audit_service),
    _=Depends(require_gestion_access),
):
    """Toggle user active status"""
    try:
        # Get previous state for audit
        user_before = user_service.get_user(usuario_id)
        old_activo = user_before.activo if user_before else None

        is_owner = bool(request.session.get("logged_in")) and str(
            request.session.get("role") or ""
        ).strip().lower() in ("dueño", "dueno", "owner")
        result = user_service.toggle_activo(usuario_id, is_owner=is_owner)
        if result.get("error") == "not_found":
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # Audit log the toggle
        new_activo = result.get("activo")
        audit_service.log_from_request(
            request=request,
            action=AuditService.ACTION_USER_ACTIVATE
            if new_activo
            else AuditService.ACTION_USER_DEACTIVATE,
            table_name="usuarios",
            record_id=usuario_id,
            old_values={"activo": old_activo},
            new_values={"activo": new_activo},
        )

        try:
            active = bool(result.get("activo"))
            if not active:
                if background_tasks is not None:
                    background_tasks.add_task(
                        wa.send_deactivation, int(usuario_id), "Desactivación manual"
                    )
                else:
                    wa.send_deactivation(int(usuario_id), "Desactivación manual")
            else:
                if background_tasks is not None:
                    background_tasks.add_task(
                        wa.send_membership_reactivated,
                        int(usuario_id),
                        request.session.get("sucursal_id"),
                    )
                else:
                    wa.send_membership_reactivated(
                        int(usuario_id), request.session.get("sucursal_id")
                    )
        except Exception:
            pass
        return result
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.put("/api/usuarios/{usuario_id}/notas", dependencies=[Depends(require_feature("usuarios"))])
async def api_usuario_notas_update(
    usuario_id: int,
    request: Request,
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access),
):
    """Update user notes"""
    try:
        payload = await request.json()
        notas = payload.get("notas") or ""
        user_service.update_notas(usuario_id, notas)
        return {"ok": True}
    except Exception as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.get("/api/usuarios/{usuario_id}/qr", dependencies=[Depends(require_feature("usuarios"))])
async def api_usuario_qr(
    usuario_id: int,
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access),
):
    """Generate QR code URL and token for user check-in"""
    try:
        return user_service.generate_qr_token(usuario_id)
    except Exception as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.post("/api/usuarios/{usuario_id}/qr", dependencies=[Depends(require_feature("usuarios"))])
async def api_usuario_qr_post(
    usuario_id: int,
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access),
):
    """Generate QR code URL and token for user check-in (POST alias)."""
    try:
        return user_service.generate_qr_token(usuario_id)
    except Exception as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.get("/api/etiquetas/suggestions")
async def api_etiquetas_suggestions(
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access),
):
    """Get common tag suggestions based on existing tags"""
    try:
        return {"etiquetas": user_service.get_tag_suggestions()}
    except Exception:
        return {"etiquetas": []}


# --- API Etiquetas de usuario ---


@router.get("/api/usuarios/{usuario_id}/etiquetas", dependencies=[Depends(require_feature("usuarios"))])
async def api_usuario_etiquetas_get(
    usuario_id: int,
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access),
):
    try:
        items = user_service.get_user_tags(usuario_id)
        return {"etiquetas": items}
    except Exception as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.post("/api/usuarios/{usuario_id}/etiquetas", dependencies=[Depends(require_feature("usuarios"))])
async def api_usuario_etiquetas_add(
    usuario_id: int,
    request: Request,
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access),
):
    payload = await request.json()
    try:
        assigned_by = (
            int(request.session.get("user_id"))
            if request.session.get("user_id")
            else None
        )
        ok = user_service.add_user_tag(usuario_id, payload, assigned_by)
        return {"ok": ok}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.delete("/api/usuarios/{usuario_id}/etiquetas/{etiqueta_id}", dependencies=[Depends(require_feature("usuarios"))])
async def api_usuario_etiquetas_remove(
    usuario_id: int,
    etiqueta_id: int,
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access),
):
    try:
        ok = user_service.remove_user_tag(usuario_id, etiqueta_id)
        return {"ok": ok}
    except Exception as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


# --- API Estados de usuario ---


@router.get("/api/usuarios/{usuario_id}/estados", dependencies=[Depends(require_feature("usuarios"))])
async def api_usuario_estados_get(
    usuario_id: int,
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access),
):
    """Get user states (lesionado, vacaciones, etc.)"""
    try:
        if not user_service.get_user(usuario_id):
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        items = user_service.get_user_states(usuario_id, solo_activos=True)
        return {"estados": items}
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.get("/api/usuarios_morosidad_ids", dependencies=[Depends(require_feature("usuarios"))])
async def api_usuarios_morosidad_ids(
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access),
):
    """Get IDs of users with overdue payments"""
    try:
        return user_service.get_morose_user_ids()
    except Exception as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.post("/api/usuarios/{usuario_id}/estados", dependencies=[Depends(require_feature("usuarios"))])
async def api_usuario_estados_add(
    usuario_id: int,
    request: Request,
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access),
):
    """Add a new state to user"""
    try:
        if not user_service.get_user(usuario_id):
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        payload = await request.json()
        creado_por = request.session.get("user_id")
        estado_id = user_service.add_user_state(usuario_id, payload, creado_por)
        return {"ok": True, "id": estado_id}
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.put("/api/usuarios/{usuario_id}/estados/{estado_id}", dependencies=[Depends(require_feature("usuarios"))])
async def api_usuario_estados_update(
    usuario_id: int,
    estado_id: int,
    request: Request,
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access),
):
    """Update a user state"""
    try:
        payload = await request.json()
        ok = user_service.update_user_state(estado_id, payload)
        if not ok:
            raise HTTPException(status_code=404, detail="Estado no encontrado")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.delete("/api/usuarios/{usuario_id}/estados/{estado_id}", dependencies=[Depends(require_feature("usuarios"))])
async def api_usuario_estados_delete(
    usuario_id: int,
    estado_id: int,
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access),
):
    """Delete (soft) a user state"""
    try:
        ok = user_service.delete_user_state(estado_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Estado no encontrado")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.get("/api/estados/plantillas")
async def api_estados_plantillas(
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access),
):
    """Get predefined state templates"""
    try:
        items = user_service.get_state_templates()
        return {"items": items}
    except Exception as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.get("/api/estados/templates")
async def api_estados_templates(
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access),
):
    """Get predefined state templates (frontend-compatible alias)"""
    try:
        items = user_service.get_state_templates()
        return {"templates": items}
    except Exception as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


# --- API Profesores ---


@router.get("/api/profesores_basico")
async def api_profesores_basico(
    profesor_service: ProfesorService = Depends(get_profesor_service),
):
    try:
        return profesor_service.list_teachers_basic()
    except Exception:
        return []


@router.get("/api/legacy/profesores_detalle")
async def api_profesores_detalle(
    request: Request,
    profesor_service: ProfesorService = Depends(get_profesor_service),
    _=Depends(require_owner),
):
    start = request.query_params.get("start")
    end = request.query_params.get("end")

    start_date = None
    end_date = None
    try:
        if start:
            start_date = datetime.strptime(start, "%Y-%m-%d").date()
        if end:
            end_date = datetime.strptime(end, "%Y-%m-%d").date()
    except Exception:
        pass

    return profesor_service.get_teacher_details_list(start_date, end_date)


@router.get("/api/legacy/profesores/{profesor_id}")
async def api_profesor_get(
    profesor_id: int,
    profesor_service: ProfesorService = Depends(get_profesor_service),
    _=Depends(require_owner),
):
    try:
        data = profesor_service.obtener_profesor(profesor_id)
        if not data:
            msg = "not_found"
            return JSONResponse(
                {
                    "ok": False,
                    "mensaje": msg,
                    "error": msg,
                    "success": False,
                    "message": msg,
                },
                status_code=404,
            )
        return data
    except Exception as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.put("/api/legacy/profesores/{profesor_id}")
async def api_profesor_update(
    profesor_id: int,
    request: Request,
    profesor_service: ProfesorService = Depends(get_profesor_service),
    _=Depends(require_owner),
):
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    try:
        profesor_service.actualizar_profesor(profesor_id, payload)
        return {
            "ok": True,
            "mensaje": "OK",
            "success": True,
            "message": "OK",
            "updated": 1,
        }
    except Exception as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.get("/api/legacy/profesor_sesiones")
async def api_profesor_sesiones(
    request: Request,
    profesor_service: ProfesorService = Depends(get_profesor_service),
    _=Depends(require_owner),
):
    pid = request.query_params.get("profesor_id")
    if not pid:
        return []

    start = request.query_params.get("start")
    end = request.query_params.get("end")

    start_date = None
    end_date = None
    try:
        if start:
            start_date = datetime.strptime(start, "%Y-%m-%d").date()
        if end:
            end_date = datetime.strptime(end, "%Y-%m-%d").date()
    except Exception:
        pass

    try:
        sesiones = profesor_service.get_teacher_sessions(int(pid), start_date, end_date)

        # Formatting similar to original
        out = []
        for s in sesiones:
            # Format logic if needed or return as is
            out.append(s)
        return out
    except Exception:
        return []
