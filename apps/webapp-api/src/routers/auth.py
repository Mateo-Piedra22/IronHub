from pathlib import Path
import logging
from fastapi import APIRouter, Request, Depends, status, Form
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from src.dependencies import get_auth_service, get_attendance_service, ensure_tenant_context, require_user_auth
from src.services.auth_service import AuthService
from src.services.attendance_service import AttendanceService
from src.utils import (
    _resolve_theme_vars, _resolve_logo_url, 
    get_gym_name, _issue_usuario_jwt, _get_usuario_nombre,
    _verify_owner_password
)
from src.rate_limit import (
    is_rate_limited_login, register_login_attempt, clear_login_attempts
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Setup templates
templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

@router.get("/login")
async def public_login_page(request: Request, error: str = ""):
    """Login page - returns JSON for API. Frontend (Next.js) handles the UI."""
    if error:
        return JSONResponse({"ok": False, "error": error, "login_required": True}, status_code=401)
    return JSONResponse({
        "ok": False,
        "login_required": True,
        "gym_name": get_gym_name("Gimnasio"),
        "logo_url": _resolve_logo_url()
    }, status_code=401)

@router.post("/login")
async def public_login_post(request: Request):
    """Public login - supports both form and JSON requests."""
    content_type = request.headers.get("content-type", "")
    accept_header = request.headers.get("accept", "")
    is_json_request = content_type.startswith("application/json") or "application/json" in accept_header
    
    try:
        if content_type.startswith("application/json"):
            data = await request.json()
            password = str(data.get("password") or "").strip()
        else:
            form = await request.form()
            password = str(form.get("password") or "").strip()
    except Exception:
        password = ""
    
    def error_response(message: str):
        if is_json_request:
            return JSONResponse({"ok": False, "error": message}, status_code=401)
        return RedirectResponse(url=f"/login?error={message}", status_code=303)
    
    def success_response():
        if is_json_request:
            return JSONResponse({"ok": True, "redirect": "/dashboard", "role": "dueño"})
        return RedirectResponse(url="/dashboard", status_code=303)
        
    if not password:
        return error_response("Contraseña requerida")
        
    if _verify_owner_password(password):
        request.session.clear()
        request.session["logged_in"] = True
        request.session["role"] = "dueño"
        return success_response()
        
    return error_response("Credenciales inválidas")

@router.get("/usuario/login")
async def usuario_login_page(request: Request, error: str = ""):
    """Usuario login page - returns JSON for API. Frontend handles the UI."""
    if error:
        return JSONResponse({"ok": False, "error": error, "login_required": True}, status_code=401)
    return JSONResponse({
        "ok": False,
        "login_required": True,
        "gym_name": get_gym_name("Gimnasio"),
        "logo_url": _resolve_logo_url()
    }, status_code=401)

@router.post("/usuario/login")
async def usuario_login_post(
    request: Request,
    svc: AuthService = Depends(get_auth_service)
):
    """Usuario login endpoint with rate limiting using SQLAlchemy."""
    content_type = request.headers.get("content-type", "")
    accept_header = request.headers.get("accept", "")
    is_json_request = content_type.startswith("application/json") or "application/json" in accept_header
    
    try:
        if content_type.startswith("application/json"):
            data = await request.json()
            dni = str(data.get("dni") or "").strip()
            pin = str(data.get("pin") or "").strip()
        else:
            form = await request.form()
            dni = str(form.get("dni") or "").strip()
            pin = str(form.get("pin") or "").strip()
    except Exception:
        dni = ""
        pin = ""
    
    def error_response(message: str):
        if is_json_request:
            return JSONResponse({"ok": False, "error": message}, status_code=401)
        return RedirectResponse(url=f"/usuario/login?error={message}", status_code=303)
    
    def success_response(user_data: dict = None):
        if is_json_request:
            return JSONResponse({"ok": True, "redirect": "/usuario/panel", **(user_data or {})})
        return RedirectResponse(url="/usuario/panel", status_code=303)
        
    if not dni or not pin:
        return error_response("Ingrese DNI y PIN")

    # Rate limiting check (10 IP / 5 DNI per 5 minutes)
    if is_rate_limited_login(request, dni):
        return error_response("Demasiados intentos. Intente más tarde")

    # Register attempt before verification
    register_login_attempt(request, dni)

    # Get user by DNI using SQLAlchemy
    user = svc.obtener_usuario_por_dni(dni)
    if not user:
        return error_response("DNI no encontrado")

    # Verify PIN using AuthService
    pin_result = svc.verificar_pin(user.id, pin)
    
    if not pin_result['valid']:
        return error_response("PIN inválido")
    
    if not pin_result['activo']:
        return error_response("Usuario inactivo")

    # Success: clear rate limits
    clear_login_attempts(request, dni)

    # Setup session with all required variables
    try:
        request.session.clear()
    except Exception:
        pass
    
    request.session["user_id"] = int(user.id)
    request.session["role"] = "user"

    # Set usuario_nombre
    user_name = None
    try:
        if user.nombre:
            request.session["usuario_nombre"] = user.nombre
            user_name = user.nombre
    except Exception:
        pass

    # Issue JWT token
    jwt_token = None
    try:
        tok = _issue_usuario_jwt(int(user.id))
        if tok:
            request.session["usuario_jwt"] = tok
            jwt_token = tok
    except Exception:
        pass

    return success_response({
        "user_id": int(user.id),
        "user_name": user_name,
        "jwt": jwt_token
    })


@router.get("/logout")
@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

@router.get("/usuario/logout")
@router.post("/usuario/logout")
async def usuario_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/usuario/login", status_code=303)

@router.get("/dashboard/logout")
@router.post("/dashboard/logout")
async def dashboard_logout(request: Request):
    return await logout(request)

@router.get("/checkin/logout")
@router.post("/checkin/logout")
async def checkin_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/checkin", status_code=303)

@router.get("/gestion/login")
async def login_page(request: Request, error: str = ""):
    """
    Gestion login page. For API/JSON requests, returns JSON.
    For browser requests, returns a 404 since templates are not included.
    The frontend (Next.js) handles the login UI.
    """
    accept_header = request.headers.get("accept", "")
    
    # For JSON/API requests, return JSON response
    if "application/json" in accept_header or error:
        if error:
            return JSONResponse({"ok": False, "error": error, "login_required": True}, status_code=401)
        return JSONResponse({"ok": False, "login_required": True, "message": "Login required"}, status_code=401)
    
    # For browser requests without JSON accept header, redirect to frontend login
    # The frontend handles the actual login UI
    return JSONResponse({
        "ok": False,
        "login_required": True,
        "message": "Please use the frontend application for login"
    }, status_code=401)


@router.get("/gestion/logout")
@router.post("/gestion/logout")
async def gestion_logout(
    request: Request,
    svc: AuthService = Depends(get_auth_service)
):
    """
    Logout for gestion (professor/owner) panel using SQLAlchemy.
    Finalizes professor work session before clearing session.
    """
    # Finalize professor work session if exists
    try:
        sesion_id = request.session.get("gestion_sesion_trabajo_id")
        if sesion_id is not None:
            try:
                svc.finalizar_sesion_profesor(int(sesion_id))
            except Exception:
                pass
    except Exception:
        pass
    
    request.session.clear()
    return RedirectResponse(url="/gestion/login", status_code=303)

@router.post("/gestion/auth")
async def gestion_auth(
    request: Request,
    svc: AuthService = Depends(get_auth_service),
    tenant: str = Depends(ensure_tenant_context)
):
    """Gestion (professor/owner) authentication using SQLAlchemy."""
    try:
        content_type = request.headers.get("content-type", "")
        accept_header = request.headers.get("accept", "")
        is_json_request = content_type.startswith("application/json") or "application/json" in accept_header
        
        if content_type.startswith("application/json"):
            data = await request.json()
        else:
            data = await request.form()
    except Exception:
        data = {}
        is_json_request = True  # Assume JSON for error responses
    
    def error_response(message: str):
        if is_json_request:
            return JSONResponse({"ok": False, "error": message}, status_code=401)
        return RedirectResponse(url=f"/gestion/login?error={message}", status_code=303)
    
    def success_response(redirect_url: str, session_data: dict = None):
        if is_json_request:
            return JSONResponse({"ok": True, "redirect": redirect_url, **(session_data or {})})
        return RedirectResponse(url=redirect_url, status_code=303)
        
    usuario_id_raw = data.get("usuario_id")
    owner_password = str(data.get("owner_password", "")).strip()
    pin_raw = data.get("pin")

    # Owner login logic
    if isinstance(usuario_id_raw, str) and usuario_id_raw == "__OWNER__":
        if not owner_password:
            return error_response("Ingrese la contraseña")
        if svc.verificar_owner_password(owner_password):
            request.session.clear()
            request.session["logged_in"] = True
            request.session["role"] = "dueño"
            request.session["tenant"] = tenant
            return success_response("/gestion", {"role": "dueño"})
        return error_response("Credenciales inválidas")

    # Professor/User login logic
    try:
        usuario_id = int(usuario_id_raw) if usuario_id_raw is not None else None
    except Exception:
        usuario_id = None
        
    pin = str(pin_raw or "").strip()
    
    if not usuario_id or not pin:
        return error_response("Parámetros inválidos")
    
    # Verify PIN using AuthService
    pin_result = svc.verificar_pin(usuario_id, pin)
    if not pin_result['valid']:
        return error_response("PIN inválido")
    
    # Clear session
    try:
        request.session.clear()
    except Exception:
        pass
        
    # Get user info
    user = svc.obtener_usuario_por_id(usuario_id)
    user_role = getattr(user, 'rol', None) if user else None
    user_name = getattr(user, 'nombre', None) if user else None
    
    # Check for professor privileges
    profesores = svc.obtener_profesores_activos()
    profesor_id = None
    for p in profesores:
        if p.get('usuario_id') == usuario_id:
            profesor_id = p.get('id')
            break
        
    request.session["gestion_profesor_user_id"] = usuario_id
    request.session["tenant"] = tenant
    try:
        request.session["role"] = "profesor"
    except Exception:
        pass
        
    if profesor_id:
        request.session["gestion_profesor_id"] = int(profesor_id)
        # Start work session
        try:
            sesion_id = svc.registrar_inicio_sesion_profesor(int(profesor_id), usuario_id)
            if sesion_id:
                request.session["gestion_sesion_trabajo_id"] = sesion_id
        except Exception:
            pass
            
    return success_response("/gestion", {
        "role": "profesor",
        "user_id": usuario_id,
        "user_name": user_name,
        "profesor_id": profesor_id
    })


@router.post("/api/auth/logout")
async def api_auth_logout(request: Request):
    request.session.clear()
    return JSONResponse({"ok": True})


@router.post("/api/auth/login")
async def api_auth_login(
    request: Request,
    svc: AuthService = Depends(get_auth_service),
    tenant: str = Depends(ensure_tenant_context)
):
    """
    JSON API endpoint for general login (DNI + password/PIN).
    Returns user info and session for the Next.js SPA.
    """
    try:
        data = await request.json()
        dni = str(data.get("dni") or "").strip()
        password = str(data.get("password") or "").strip()  # could be PIN or owner password
    except Exception:
        return JSONResponse({"ok": False, "error": "Datos inválidos"}, status_code=400)
    
    if not dni and not password:
        return JSONResponse({"ok": False, "error": "Credenciales requeridas"}, status_code=400)
    
    # If no DNI, try owner login with just password
    if not dni and password:
        if svc.verificar_owner_password(password):
            request.session.clear()
            request.session["logged_in"] = True
            request.session["role"] = "owner"
            return JSONResponse({
                "ok": True,
                "user": {
                    "id": 0,
                    "nombre": "Dueño",
                    "rol": "owner",
                    "dni": None
                }
            })
        return JSONResponse({"ok": False, "error": "Credenciales inválidas"}, status_code=401)
    
    # Rate limiting check
    if is_rate_limited_login(request, dni):
        return JSONResponse({"ok": False, "error": "Demasiados intentos"}, status_code=429)
    
    # Register attempt before verification
    register_login_attempt(request, dni)
    
    # Get user by DNI using SQLAlchemy
    user = svc.obtener_usuario_por_dni(dni)
    if not user:
        return JSONResponse({"ok": False, "error": "Credenciales inválidas"}, status_code=401)
    
    # Verify PIN using AuthService
    pin_result = svc.verificar_pin(user.id, password)
    if not pin_result['valid']:
        return JSONResponse({"ok": False, "error": "Credenciales inválidas"}, status_code=401)
    
    if not user.activo:
        return JSONResponse({"ok": False, "error": "Usuario inactivo"}, status_code=403)
    
    # Success: clear rate limits
    clear_login_attempts(request, dni)
    
    # Set session
    request.session.clear()
    request.session["user_id"] = int(user.id)
    request.session["role"] = getattr(user, 'rol', None) or "user"
    request.session["usuario_nombre"] = user.nombre or ""
    
    # Issue JWT token
    jwt_token = None
    try:
        jwt_token = _issue_usuario_jwt(int(user.id))
        if jwt_token:
            request.session["usuario_jwt"] = jwt_token
    except Exception:
        pass
    
    return JSONResponse({
        "ok": True,
        "user": {
            "id": user.id,
            "nombre": user.nombre or "",
            "rol": getattr(user, 'rol', None) or "user",
            "dni": user.dni
        }
    })


@router.get("/api/auth/session")
async def api_auth_session(request: Request):
    """
    JSON API endpoint to check current session status.
    Returns authenticated status and user info if logged in.
    """
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    logged_in = request.session.get("logged_in", False)
    
    if user_id:
        nombre = request.session.get("usuario_nombre", "")
        return JSONResponse({
            "authenticated": True,
            "user": {
                "id": user_id,
                "nombre": nombre,
                "rol": role or "user",
                "dni": None  # Don't expose DNI in session check
            }
        })
    elif logged_in and role in ("owner", "dueño"):
        return JSONResponse({
            "authenticated": True,
            "user": {
                "id": 0,
                "nombre": "Dueño",
                "rol": "owner",
                "dni": None
            }
        })
    else:
        return JSONResponse({
            "authenticated": False,
            "user": None
        })

@router.post("/checkin/auth")
async def checkin_auth(request: Request):
    try:
        form = await request.form()
        password = str(form.get("password") or "").strip()
    except Exception:
        password = ""
    
    if _verify_owner_password(password):
        request.session["logged_in"] = True
        request.session["role"] = "dueño"
        return RedirectResponse(url="/checkin", status_code=303)
        
    return RedirectResponse(url="/login?error=Credenciales%20inv%C3%A1lidas", status_code=303)

@router.post("/api/usuario/change_pin")
async def api_usuario_change_pin(
    request: Request,
    svc: AuthService = Depends(get_auth_service)
):
    """
    PIN change endpoint supporting unauthenticated flow using SQLAlchemy.
    Accepts {dni, old_pin, new_pin} and verifies old_pin before updating.
    """
    try:
        data = await request.json()
        dni = str(data.get("dni") or "").strip()
        old_pin = str(data.get("old_pin") or "").strip()
        new_pin = str(data.get("new_pin") or "").strip()
    except Exception:
        return JSONResponse({"ok": False, "error": "Datos inválidos"}, status_code=400)
    
    if not dni or not old_pin or not new_pin:
        return JSONResponse({"ok": False, "error": "Parámetros inválidos"}, status_code=400)
        
    if len(new_pin) < 4:
        return JSONResponse({"ok": False, "error": "El PIN nuevo debe tener al menos 4 caracteres"}, status_code=400)
    
    # Rate limiting check (uses same limits as login)
    if is_rate_limited_login(request, dni):
        return JSONResponse({"ok": False, "error": "Demasiados intentos. Intente más tarde"}, status_code=429)
    
    # Register attempt
    register_login_attempt(request, dni)
    
    # Get user by DNI using SQLAlchemy
    user = svc.obtener_usuario_por_dni(dni)
    if not user:
        return JSONResponse({"ok": False, "error": "DNI no encontrado"}, status_code=400)
    
    # Verify old PIN using AuthService
    pin_result = svc.verificar_pin(user.id, old_pin)
    if not pin_result['valid']:
        return JSONResponse({"ok": False, "error": "PIN antiguo inválido"}, status_code=400)
    
    # Validation: new PIN must differ from old PIN
    if new_pin == old_pin:
        return JSONResponse({"ok": False, "error": "El PIN nuevo debe ser distinto al actual"}, status_code=400)
    
    # Update PIN using AuthService
    if svc.actualizar_pin(user.id, new_pin):
        # Clear rate limits on success
        clear_login_attempts(request, dni)
        return JSONResponse({"ok": True}, status_code=200)
    else:
        return JSONResponse({"ok": False, "error": "Error al actualizar PIN"}, status_code=500)


# ============================================
# JSON API Endpoints for Next.js SPA
# These endpoints return JSON instead of HTML redirects
# ============================================

@router.post("/api/usuario/login")
async def api_usuario_login(
    request: Request,
    svc: AuthService = Depends(get_auth_service)
):
    """
    JSON API endpoint for usuario login (DNI + PIN) using SQLAlchemy.
    Returns user info, payment status, and JWT token for the SPA.
    """
    try:
        data = await request.json()
        dni = str(data.get("dni") or "").strip()
        pin = str(data.get("pin") or "").strip()
    except Exception:
        return JSONResponse({"success": False, "message": "Datos inválidos"}, status_code=400)
    
    if not dni:
        return JSONResponse({"success": False, "message": "DNI requerido"})
    
    # Rate limiting check
    if is_rate_limited_login(request, dni):
        return JSONResponse({"success": False, "message": "Demasiados intentos. Intente más tarde"}, status_code=429)
    
    # Register attempt before verification
    register_login_attempt(request, dni)
    
    # Get user by DNI using SQLAlchemy
    user = svc.obtener_usuario_por_dni(dni)
    if not user:
        return JSONResponse({"success": False, "message": "DNI no encontrado o incorrecto"})
    
    # PIN OPTIONAL as per simplified flow
    # Only verify PIN if explicitly provided and non-empty
    if pin:
        pin_result = svc.verificar_pin(user.id, pin)
        if not pin_result['valid']:
            return JSONResponse({"success": False, "message": "PIN incorrecto"})
    
    if not user.activo:
        return JSONResponse({
            "success": False, 
            "message": "Usuario inactivo or membresía vencida",
            "activo": False
        })
    
    # Success: clear rate limits
    clear_login_attempts(request, dni)
    
    # Set session with all required variables
    request.session.clear()
    request.session["user_id"] = int(user.id)
    request.session["role"] = "user"
    
    # Set usuario_nombre
    nombre = user.nombre or ""
    if nombre:
        request.session["usuario_nombre"] = nombre
    
    # Issue JWT token
    jwt_token = None
    try:
        jwt_token = _issue_usuario_jwt(int(user.id))
        if jwt_token:
            request.session["usuario_jwt"] = jwt_token
    except Exception:
        pass
    
    # Calculate days remaining if applicable
    dias_restantes = None
    if user.fecha_proximo_vencimiento:
        from datetime import datetime, date
        try:
            venc = user.fecha_proximo_vencimiento
            if isinstance(venc, datetime):
                venc = venc.date()
            dias_restantes = (venc - date.today()).days
        except Exception:
            pass
    
    return JSONResponse({
        "success": True,
        "user_id": user.id,
        "nombre": nombre,
        "activo": True,
        "exento": bool(getattr(user, 'exento', False)),
        "cuotas_vencidas": getattr(user, 'cuotas_vencidas', 0) or 0,
        "dias_restantes": dias_restantes,
        "fecha_proximo_vencimiento": str(user.fecha_proximo_vencimiento or ""),
        "token": jwt_token  # JWT for client-side use
    })


@router.post("/api/checkin/auth")
async def api_checkin_auth(
    request: Request,
    svc: AuthService = Depends(get_auth_service)
):
    """
    JSON API endpoint for check-in authentication (DNI only).
    Used for kiosk/self-service check-in flows.
    """
    try:
        data = await request.json()
        dni = str(data.get("dni") or "").strip()
        telefono = str(data.get("telefono") or "").strip()  # Optional now
    except Exception:
        return JSONResponse({"success": False, "message": "Datos inválidos"}, status_code=400)
    
    if not dni:
        return JSONResponse({"success": False, "message": "DNI requerido"})
    
    # First try with phone if provided
    if telefono:
        result = svc.verificar_checkin(dni, telefono)
    else:
        # DNI-only verification: just find user and check active status
        user = svc.obtener_usuario_por_dni(dni)
        if not user:
            result = {'valid': False, 'error': 'Usuario no encontrado'}
        elif not user.activo:
            result = {'valid': False, 'error': 'Usuario inactivo', 'activo': False}
        else:
            # Build user info dict for response
            result = {
                'valid': True,
                'usuario': {
                    'id': user.id,
                    'nombre': user.nombre,
                    'exento': getattr(user, 'exento', False),
                    'cuotas_vencidas': getattr(user, 'cuotas_vencidas', 0),
                    'fecha_vencimiento': getattr(user, 'fecha_proximo_vencimiento', None)
                }
            }
    
    if not result['valid']:
        error_msg = result.get('error', 'Verificación fallida')
        return JSONResponse({
            "success": False, 
            "message": error_msg,
            "activo": result.get('activo', False)
        })
    
    user_data = result.get('usuario', {})
    user_id = user_data.get('id')
    
    # Set session for subsequent requests (QR scan)
    request.session.clear()
    if user_id:
        request.session["user_id"] = int(user_id)
        request.session["role"] = "checkin"
        request.session["checkin_auth"] = True
    
    # Issue JWT token
    jwt_token = None
    try:
        if user_id:
            jwt_token = _issue_usuario_jwt(int(user_id))
            if jwt_token:
                request.session["usuario_jwt"] = jwt_token
    except Exception:
        pass

    # Calculate days remaining
    dias_restantes = None
    fecha_vencimiento = user_data.get('fecha_vencimiento')
    if fecha_vencimiento:
        from datetime import datetime, date
        try:
            if isinstance(fecha_vencimiento, str):
                venc = datetime.fromisoformat(fecha_vencimiento).date()
            elif isinstance(fecha_vencimiento, datetime):
                venc = fecha_vencimiento.date()
            else:
                venc = fecha_vencimiento
            dias_restantes = (venc - date.today()).days
        except Exception:
            pass
    
    return JSONResponse({
        "success": True,
        "usuario_id": user_id,
        "activo": True,
        "exento": bool(user_data.get('exento', False)),
        "cuotas_vencidas": user_data.get('cuotas_vencidas', 0) or 0,
        "dias_restantes": dias_restantes,
        "fecha_proximo_vencimiento": str(fecha_vencimiento or ""),
        "token": jwt_token
    })


@router.post("/api/checkin/qr")
async def api_checkin_qr(
    request: Request,
    svc: AttendanceService = Depends(get_attendance_service)
):
    """
    Validate station QR scan and register attendance.
    Requires authenticated user via session/cookie.
    """
    try:
        # Check session
        user_id = request.session.get("user_id")
        if not user_id:
            return JSONResponse({"ok": False, "mensaje": "Sesión no válida. Ingrese DNI nuevamente."}, status_code=401)

        data = await request.json()
        token = str(data.get("token") or "").strip()
        
        if not token:
             return JSONResponse({"ok": False, "mensaje": "Token QR requerido"}, status_code=400)
             
        # Validate and Check-in
        success, message, user_data = svc.validar_station_scan(token, user_id)
        
        if success:
             return JSONResponse({
                 "ok": True, 
                 "mensaje": message, 
                 "usuario": {
                     "nombre": user_data.get("nombre"),
                     "dni": user_data.get("dni")
                 }
             })
        else:
             return JSONResponse({"ok": False, "mensaje": message}, status_code=400)
             
    except Exception:
        logger.exception("Error en checkin QR")
        return JSONResponse({"ok": False, "mensaje": "Error de servidor"}, status_code=500)

