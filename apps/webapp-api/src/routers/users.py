import logging
from datetime import datetime, timezone, date
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.dependencies import (
    get_user_service, get_profesor_service, 
    require_gestion_access, require_owner
)
from src.services import UserService, ProfesorService
from src.utils import _resolve_theme_vars, _resolve_logo_url, get_gym_name

# Fallback for UsuarioEstado if not imported correctly or available
try:
    from src.models import UsuarioEstado
except ImportError:
    UsuarioEstado = None

router = APIRouter()
logger = logging.getLogger(__name__)

templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

@router.get("/usuario/panel")
async def usuario_panel(
    request: Request,
    user_service: UserService = Depends(get_user_service)
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
        
    if not data or not data.get('usuario'):
        request.session.clear()
        return JSONResponse({"ok": False, "login_required": True}, status_code=401)

    u = data['usuario']
    
    return JSONResponse({
        "ok": True,
        "usuario": {
            "id": getattr(u, 'id', None),
            "nombre": getattr(u, 'nombre', None),
            "dni": getattr(u, 'dni', None),
            "activo": bool(getattr(u, 'activo', False)),
        },
        "dias_restantes": data.get('dias_restantes'),
        "ultimo_pago": str(getattr(u, 'ultimo_pago', None)) if getattr(u, 'ultimo_pago', None) else None,
        "pagos": data.get('pagos', []),
        "rutinas": data.get('rutinas', [])
    })


# --- API Usuarios ---

@router.get("/api/usuarios")
async def api_usuarios_list(
    q: Optional[str] = None, 
    limit: int = 50, 
    offset: int = 0, 
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access)
):
    try:
        items = user_service.list_users(q, limit, offset)
        return {"usuarios": items, "total": len(items)}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@router.get("/api/usuarios/{usuario_id}")
async def api_usuario_get(
    usuario_id: int, 
    request: Request, 
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access)
):
    try:
        u = user_service.get_user(usuario_id)
        if not u:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
            
        # Aplicar visibilidad de PIN: 
        # 1. DUEÑO/ADMIN: NUNCA mostrar el PIN/HASH (Seguridad Estricta)
        user_role = str(getattr(u, "rol", "")).strip().lower()
        if user_role in ("dueño", "dueno", "owner", "admin", "administrador"):
            pin_value = None # Ocultar totalmente el hash del dueño
            
        # 2. PROFESORES: Un profesor no debe ver el PIN de otro profesor
        elif user_role == "profesor":
            try:
                prof_uid = request.session.get("gestion_profesor_user_id")
                # Si soy un profesor viendo a otro (y no a mi mismo), ocultar
                if prof_uid and int(usuario_id) != int(prof_uid):
                     pin_value = None
            except Exception:
                pass
            
        return {
            "id": u.id,
            "nombre": u.nombre,
            "dni": u.dni,
            "telefono": u.telefono,
            "pin": pin_value,
            "rol": u.rol,
            "activo": bool(u.activo),
            "tipo_cuota": u.tipo_cuota,
            "notas": u.notas,
            "fecha_registro": u.fecha_registro,
            "fecha_proximo_vencimiento": u.fecha_proximo_vencimiento,
            "cuotas_vencidas": u.cuotas_vencidas,
            "ultimo_pago": u.ultimo_pago,
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@router.post("/api/usuarios")
async def api_usuario_create(
    request: Request, 
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access)
):
    payload = await request.json()
    try:
        # Prepare data
        data = {
            "nombre": ((payload.get("nombre") or "").strip()).upper(),
            "dni": str(payload.get("dni") or "").strip(),
            "telefono": str(payload.get("telefono") or "").strip() or None,
            "pin": payload.get("pin") if isinstance(payload, dict) else None,
            "rol": (payload.get("rol") or "socio").strip().lower(),
            "activo": bool(payload.get("activo", True)),
            "tipo_cuota": payload.get("tipo_cuota"),
            "notas": payload.get("notas"),
            "fecha_registro": datetime.now(timezone.utc).isoformat(),
            "cuotas_vencidas": 0,
            "ultimo_pago": None
        }
        
        if not data["nombre"] or not data["dni"]:
            raise HTTPException(status_code=400, detail="'nombre' y 'dni' son obligatorios")
            
        new_id = user_service.create_user(data)
        return {"id": new_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@router.put("/api/usuarios/{usuario_id}")
async def api_usuario_update(
    usuario_id: int, 
    request: Request, 
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access)
):
    payload = await request.json()
    try:
        is_owner = bool(request.session.get("logged_in")) and str(request.session.get("role") or "").strip().lower() == "dueño"
        
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
        
        new_id = user_service.update_user(usuario_id, data, modifier_id=None, is_owner=is_owner)
        
        final_id = int(data.get("new_id")) if (data.get("new_id") and is_owner) else usuario_id
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
        return JSONResponse({"error": str(e)}, status_code=500)

@router.delete("/api/usuarios/{usuario_id}")
async def api_usuario_delete(
    usuario_id: int, 
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access)
):
    try:
        user_service.delete_user(usuario_id)
        return {"ok": True}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/usuarios/{usuario_id}/toggle-activo")
async def api_usuario_toggle_activo(
    usuario_id: int,
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access)
):
    """Toggle user active status"""
    try:
        result = user_service.toggle_activo(usuario_id)
        if result.get('error') == 'not_found':
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return result
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/api/usuarios/{usuario_id}/notas")
async def api_usuario_notas_update(
    usuario_id: int,
    request: Request,
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access)
):
    """Update user notes"""
    try:
        payload = await request.json()
        notas = payload.get("notas") or ""
        user_service.update_notas(usuario_id, notas)
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/usuarios/{usuario_id}/qr")
async def api_usuario_qr(
    usuario_id: int,
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access)
):
    """Generate QR code URL and token for user check-in"""
    try:
        return user_service.generate_qr_token(usuario_id)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/etiquetas/suggestions")
async def api_etiquetas_suggestions(
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access)
):
    """Get common tag suggestions based on existing tags"""
    try:
        return {"etiquetas": user_service.get_tag_suggestions()}
    except Exception as e:
        return {"etiquetas": []}


# --- API Etiquetas de usuario ---

@router.get("/api/usuarios/{usuario_id}/etiquetas")
async def api_usuario_etiquetas_get(
    usuario_id: int, 
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access)
):
    try:
        items = user_service.get_user_tags(usuario_id)
        return {"etiquetas": items}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@router.post("/api/usuarios/{usuario_id}/etiquetas")
async def api_usuario_etiquetas_add(
    usuario_id: int, 
    request: Request, 
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access)
):
    payload = await request.json()
    try:
        assigned_by = int(request.session.get("user_id")) if request.session.get("user_id") else None
        ok = user_service.add_user_tag(usuario_id, payload, assigned_by)
        return {"ok": ok}
    except ValueError as e:
         raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@router.delete("/api/usuarios/{usuario_id}/etiquetas/{etiqueta_id}")
async def api_usuario_etiquetas_remove(
    usuario_id: int, 
    etiqueta_id: int, 
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access)
):
    try:
        ok = user_service.remove_user_tag(usuario_id, etiqueta_id)
        return {"ok": ok}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# --- API Estados de usuario ---

@router.get("/api/usuarios/{usuario_id}/estados")
async def api_usuario_estados_get(
    usuario_id: int, 
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access)
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
        return JSONResponse({"error": str(e)}, status_code=500)

@router.get("/api/usuarios_morosidad_ids")
async def api_usuarios_morosidad_ids(
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access)
):
    """Get IDs of users with overdue payments"""
    try:
        return user_service.get_morose_user_ids()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@router.post("/api/usuarios/{usuario_id}/estados")
async def api_usuario_estados_add(
    usuario_id: int, 
    request: Request, 
    user_service: UserService = Depends(get_user_service),
    _=Depends(require_gestion_access)
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
        return JSONResponse({"error": str(e)}, status_code=500)

@router.put("/api/usuarios/{usuario_id}/estados/{estado_id}")
async def api_usuario_estados_update(
    usuario_id: int, 
    estado_id: int, 
    request: Request, 
    user_service: UserService = Depends(get_user_service), 
    _=Depends(require_gestion_access)
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
        return JSONResponse({"error": str(e)}, status_code=500)

@router.delete("/api/usuarios/{usuario_id}/estados/{estado_id}")
async def api_usuario_estados_delete(
    usuario_id: int, 
    estado_id: int, 
    user_service: UserService = Depends(get_user_service), 
    _=Depends(require_gestion_access)
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
        return JSONResponse({"error": str(e)}, status_code=500)

@router.get("/api/estados/plantillas")
async def api_estados_plantillas(
    user_service: UserService = Depends(get_user_service), 
    _=Depends(require_gestion_access)
):
    """Get predefined state templates"""
    try:
        items = user_service.get_state_templates()
        return {"items": items}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/estados/templates")
async def api_estados_templates(
    user_service: UserService = Depends(get_user_service), 
    _=Depends(require_gestion_access)
):
    """Get predefined state templates (frontend-compatible alias)"""
    try:
        items = user_service.get_state_templates()
        return {"templates": items}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# --- API Profesores ---

@router.get("/api/profesores_basico")
async def api_profesores_basico(
    profesor_service: ProfesorService = Depends(get_profesor_service)
):
    try:
        return profesor_service.list_teachers_basic()
    except Exception:
        return []

@router.get("/api/profesores_detalle")
async def api_profesores_detalle(
    request: Request, 
    profesor_service: ProfesorService = Depends(get_profesor_service),
    _=Depends(require_owner)
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

@router.get("/api/profesores/{profesor_id}")
async def api_profesor_get(
    profesor_id: int, 
    profesor_service: ProfesorService = Depends(get_profesor_service),
    _=Depends(require_owner)
):
    try:
        data = profesor_service.obtener_profesor(profesor_id)
        if not data:
            return JSONResponse({"error": "not_found"}, status_code=404)
        return data
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@router.put("/api/profesores/{profesor_id}")
async def api_profesor_update(
    profesor_id: int, 
    request: Request, 
    profesor_service: ProfesorService = Depends(get_profesor_service),
    _=Depends(require_owner)
):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
        
    try:
        profesor_service.actualizar_profesor(profesor_id, payload)
        return {"success": True, "updated": 1}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@router.get("/api/profesor_sesiones")
async def api_profesor_sesiones(
    request: Request, 
    profesor_service: ProfesorService = Depends(get_profesor_service),
    _=Depends(require_owner)
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
