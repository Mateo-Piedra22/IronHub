"""
Profesores Router - Complete profesor management API
Includes: CRUD, sessions, horarios, config, resumen
"""
import logging
from datetime import datetime, timezone, date, timedelta
from typing import Optional, List, Dict, Any
from calendar import monthrange

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse

from src.dependencies import get_db, require_gestion_access, require_owner

router = APIRouter()
logger = logging.getLogger(__name__)


def _ensure_profesor_tables(conn) -> None:
    """Ensure all profesor-related tables exist"""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                -- Profesor horarios (availability schedules)
                CREATE TABLE IF NOT EXISTS profesor_horarios (
                    id SERIAL PRIMARY KEY,
                    profesor_id INTEGER NOT NULL,
                    dia VARCHAR(20) NOT NULL,
                    hora_inicio TIME NOT NULL,
                    hora_fin TIME NOT NULL,
                    disponible BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_profesor_horarios_pid ON profesor_horarios(profesor_id);
                
                -- Profesor config (salary, specialty, etc)
                CREATE TABLE IF NOT EXISTS profesor_config (
                    id SERIAL PRIMARY KEY,
                    profesor_id INTEGER NOT NULL UNIQUE,
                    usuario_vinculado_id INTEGER,
                    monto DECIMAL(10,2),
                    monto_tipo VARCHAR(20) DEFAULT 'mensual',
                    especialidad TEXT,
                    experiencia_anios INTEGER,
                    certificaciones TEXT,
                    notas TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_profesor_config_pid ON profesor_config(profesor_id);
            """)
    except Exception as e:
        logger.error(f"Error ensuring profesor tables: {e}")


# === Profesores CRUD ===

@router.get("/api/profesores")
async def api_profesores_list(_=Depends(require_gestion_access)):
    """List all profesores with basic info"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        return {"profesores": []}
    try:
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT id, nombre, email, telefono, activo, created_at
                FROM profesores
                ORDER BY nombre ASC
            """)
            rows = cur.fetchall() or []
            profesores = [dict(r) for r in rows]
            return {"profesores": profesores}
    except Exception as e:
        logger.exception("Error listing profesores")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/profesores")
async def api_profesores_create(request: Request, _=Depends(require_owner)):
    """Create a new profesor"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        payload = await request.json()
        nombre = (payload.get("nombre") or "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="Nombre requerido")
        
        email = (payload.get("email") or "").strip() or None
        telefono = (payload.get("telefono") or "").strip() or None
        
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                INSERT INTO profesores (nombre, email, telefono, activo)
                VALUES (%s, %s, %s, TRUE)
                RETURNING id, nombre, email, telefono, activo
            """, (nombre, email, telefono))
            row = cur.fetchone()
            conn.commit()
            return dict(row) if row else {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error creating profesor")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/profesores/{profesor_id}")
async def api_profesor_get(profesor_id: int, _=Depends(require_gestion_access)):
    """Get single profesor by ID"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT id, nombre, email, telefono, activo, created_at
                FROM profesores WHERE id = %s
            """, (profesor_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Profesor no encontrado")
            return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/api/profesores/{profesor_id}")
async def api_profesor_update(profesor_id: int, request: Request, _=Depends(require_owner)):
    """Update profesor details"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        payload = await request.json()
        sets = []
        vals = []
        
        if "nombre" in payload:
            sets.append("nombre = %s")
            vals.append((payload["nombre"] or "").strip())
        if "email" in payload:
            sets.append("email = %s")
            vals.append((payload["email"] or "").strip() or None)
        if "telefono" in payload:
            sets.append("telefono = %s")
            vals.append((payload["telefono"] or "").strip() or None)
        if "activo" in payload:
            sets.append("activo = %s")
            vals.append(bool(payload["activo"]))
            
        if not sets:
            return {"ok": True}
            
        vals.append(profesor_id)
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(f"UPDATE profesores SET {', '.join(sets)} WHERE id = %s RETURNING *", vals)
            row = cur.fetchone()
            conn.commit()
            return dict(row) if row else {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/profesores/{profesor_id}")
async def api_profesor_delete(profesor_id: int, _=Depends(require_owner)):
    """Delete a profesor"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        with db.get_connection_context() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM profesores WHERE id = %s", (profesor_id,))
            conn.commit()
            return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# === Sesiones ===

@router.get("/api/profesores/{profesor_id}/sesiones")
async def api_profesor_sesiones(
    profesor_id: int,
    request: Request,
    _=Depends(require_gestion_access)
):
    """Get professor sessions with optional date filter"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        return {"sesiones": []}
    try:
        desde = request.query_params.get("desde")
        hasta = request.query_params.get("hasta")
        
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            query = """
                SELECT id, profesor_id, inicio, fin, duracion_minutos, notas
                FROM sesiones
                WHERE profesor_id = %s
            """
            params: List[Any] = [profesor_id]
            
            if desde:
                query += " AND DATE(inicio) >= %s"
                params.append(desde)
            if hasta:
                query += " AND DATE(inicio) <= %s"
                params.append(hasta)
                
            query += " ORDER BY inicio DESC LIMIT 100"
            
            cur.execute(query, params)
            rows = cur.fetchall() or []
            sesiones = []
            for r in rows:
                s = dict(r)
                # Format dates for JSON
                if s.get("inicio"):
                    s["inicio"] = s["inicio"].isoformat() if hasattr(s["inicio"], "isoformat") else str(s["inicio"])
                if s.get("fin"):
                    s["fin"] = s["fin"].isoformat() if hasattr(s["fin"], "isoformat") else str(s["fin"])
                sesiones.append(s)
            return {"sesiones": sesiones}
    except Exception as e:
        logger.exception("Error getting sesiones")
        return {"sesiones": []}


@router.post("/api/profesores/{profesor_id}/sesiones/start")
async def api_profesor_sesion_start(profesor_id: int, _=Depends(require_gestion_access)):
    """Start a new session for profesor"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        now = datetime.now(timezone.utc)
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Check for active session
            cur.execute("""
                SELECT id FROM sesiones 
                WHERE profesor_id = %s AND fin IS NULL
                ORDER BY inicio DESC LIMIT 1
            """, (profesor_id,))
            active = cur.fetchone()
            if active:
                raise HTTPException(status_code=400, detail="Ya hay una sesión activa")
            
            cur.execute("""
                INSERT INTO sesiones (profesor_id, inicio)
                VALUES (%s, %s)
                RETURNING id, profesor_id, inicio, fin, duracion_minutos
            """, (profesor_id, now))
            row = cur.fetchone()
            conn.commit()
            
            result = dict(row) if row else {}
            if result.get("inicio"):
                result["inicio"] = result["inicio"].isoformat()
            return result
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/profesores/{profesor_id}/sesiones/{sesion_id}/end")
async def api_profesor_sesion_end(
    profesor_id: int, 
    sesion_id: int, 
    _=Depends(require_gestion_access)
):
    """End an active session"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        now = datetime.now(timezone.utc)
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Get session
            cur.execute("""
                SELECT id, inicio FROM sesiones 
                WHERE id = %s AND profesor_id = %s AND fin IS NULL
            """, (sesion_id, profesor_id))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Sesión no encontrada o ya finalizada")
            
            inicio = row["inicio"]
            duracion = int((now - inicio).total_seconds() / 60) if inicio else 0
            
            cur.execute("""
                UPDATE sesiones 
                SET fin = %s, duracion_minutos = %s
                WHERE id = %s
                RETURNING id, profesor_id, inicio, fin, duracion_minutos
            """, (now, duracion, sesion_id))
            updated = cur.fetchone()
            conn.commit()
            
            result = dict(updated) if updated else {}
            if result.get("inicio"):
                result["inicio"] = result["inicio"].isoformat()
            if result.get("fin"):
                result["fin"] = result["fin"].isoformat()
            return result
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/sesiones/{sesion_id}")
async def api_sesion_delete(sesion_id: int, _=Depends(require_owner)):
    """Delete a session"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        with db.get_connection_context() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM sesiones WHERE id = %s", (sesion_id,))
            conn.commit()
            return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# === Horarios (Availability) ===

@router.get("/api/profesores/{profesor_id}/horarios")
async def api_profesor_horarios_list(profesor_id: int, _=Depends(require_gestion_access)):
    """List profesor availability schedules"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        return {"horarios": []}
    try:
        with db.get_connection_context() as conn:
            _ensure_profesor_tables(conn)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT id, profesor_id, dia, 
                       TO_CHAR(hora_inicio, 'HH24:MI') as hora_inicio,
                       TO_CHAR(hora_fin, 'HH24:MI') as hora_fin,
                       disponible
                FROM profesor_horarios
                WHERE profesor_id = %s
                ORDER BY 
                    CASE dia 
                        WHEN 'lunes' THEN 1 
                        WHEN 'martes' THEN 2 
                        WHEN 'miércoles' THEN 3 
                        WHEN 'jueves' THEN 4 
                        WHEN 'viernes' THEN 5 
                        WHEN 'sábado' THEN 6 
                        WHEN 'domingo' THEN 7 
                    END,
                    hora_inicio ASC
            """, (profesor_id,))
            rows = cur.fetchall() or []
            return {"horarios": [dict(r) for r in rows]}
    except Exception as e:
        logger.exception("Error listing horarios")
        return {"horarios": []}


@router.post("/api/profesores/{profesor_id}/horarios")
async def api_profesor_horario_create(
    profesor_id: int, 
    request: Request, 
    _=Depends(require_gestion_access)
):
    """Create availability schedule"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        payload = await request.json()
        dia = (payload.get("dia") or "").strip().lower()
        hora_inicio = payload.get("hora_inicio")
        hora_fin = payload.get("hora_fin")
        disponible = payload.get("disponible", True)
        
        if not dia or not hora_inicio or not hora_fin:
            raise HTTPException(status_code=400, detail="dia, hora_inicio y hora_fin son requeridos")
        
        with db.get_connection_context() as conn:
            _ensure_profesor_tables(conn)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                INSERT INTO profesor_horarios (profesor_id, dia, hora_inicio, hora_fin, disponible)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, profesor_id, dia, 
                          TO_CHAR(hora_inicio, 'HH24:MI') as hora_inicio,
                          TO_CHAR(hora_fin, 'HH24:MI') as hora_fin,
                          disponible
            """, (profesor_id, dia, hora_inicio, hora_fin, disponible))
            row = cur.fetchone()
            conn.commit()
            return dict(row) if row else {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/api/profesores/{profesor_id}/horarios/{horario_id}")
async def api_profesor_horario_update(
    profesor_id: int,
    horario_id: int,
    request: Request,
    _=Depends(require_gestion_access)
):
    """Update availability schedule"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        payload = await request.json()
        sets = []
        vals = []
        
        if "dia" in payload:
            sets.append("dia = %s")
            vals.append((payload["dia"] or "").strip().lower())
        if "hora_inicio" in payload:
            sets.append("hora_inicio = %s")
            vals.append(payload["hora_inicio"])
        if "hora_fin" in payload:
            sets.append("hora_fin = %s")
            vals.append(payload["hora_fin"])
        if "disponible" in payload:
            sets.append("disponible = %s")
            vals.append(bool(payload["disponible"]))
        
        if not sets:
            return {"ok": True}
        
        vals.extend([horario_id, profesor_id])
        with db.get_connection_context() as conn:
            _ensure_profesor_tables(conn)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(f"""
                UPDATE profesor_horarios 
                SET {', '.join(sets)}
                WHERE id = %s AND profesor_id = %s
                RETURNING id, profesor_id, dia,
                          TO_CHAR(hora_inicio, 'HH24:MI') as hora_inicio,
                          TO_CHAR(hora_fin, 'HH24:MI') as hora_fin,
                          disponible
            """, vals)
            row = cur.fetchone()
            conn.commit()
            return dict(row) if row else {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/profesores/{profesor_id}/horarios/{horario_id}")
async def api_profesor_horario_delete(
    profesor_id: int,
    horario_id: int,
    _=Depends(require_gestion_access)
):
    """Delete availability schedule"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        with db.get_connection_context() as conn:
            _ensure_profesor_tables(conn)
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM profesor_horarios WHERE id = %s AND profesor_id = %s",
                (horario_id, profesor_id)
            )
            conn.commit()
            return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# === Config ===

@router.get("/api/profesores/{profesor_id}/config")
async def api_profesor_config_get(profesor_id: int, _=Depends(require_gestion_access)):
    """Get profesor configuration"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        with db.get_connection_context() as conn:
            _ensure_profesor_tables(conn)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT pc.*, u.nombre as usuario_vinculado_nombre
                FROM profesor_config pc
                LEFT JOIN usuarios u ON pc.usuario_vinculado_id = u.id
                WHERE pc.profesor_id = %s
            """, (profesor_id,))
            row = cur.fetchone()
            
            if not row:
                # Return default config
                return {
                    "id": None,
                    "profesor_id": profesor_id,
                    "usuario_vinculado_id": None,
                    "usuario_vinculado_nombre": None,
                    "monto": None,
                    "monto_tipo": "mensual",
                    "especialidad": None,
                    "experiencia_anios": None,
                    "certificaciones": None,
                    "notas": None
                }
            
            result = dict(row)
            if result.get("monto"):
                result["monto"] = float(result["monto"])
            return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/api/profesores/{profesor_id}/config")
async def api_profesor_config_update(
    profesor_id: int,
    request: Request,
    _=Depends(require_owner)
):
    """Update profesor configuration (upsert)"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        payload = await request.json()
        
        with db.get_connection_context() as conn:
            _ensure_profesor_tables(conn)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Upsert configuration
            cur.execute("""
                INSERT INTO profesor_config (
                    profesor_id, usuario_vinculado_id, monto, monto_tipo,
                    especialidad, experiencia_anios, certificaciones, notas
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (profesor_id) DO UPDATE SET
                    usuario_vinculado_id = COALESCE(EXCLUDED.usuario_vinculado_id, profesor_config.usuario_vinculado_id),
                    monto = COALESCE(EXCLUDED.monto, profesor_config.monto),
                    monto_tipo = COALESCE(EXCLUDED.monto_tipo, profesor_config.monto_tipo),
                    especialidad = COALESCE(EXCLUDED.especialidad, profesor_config.especialidad),
                    experiencia_anios = COALESCE(EXCLUDED.experiencia_anios, profesor_config.experiencia_anios),
                    certificaciones = COALESCE(EXCLUDED.certificaciones, profesor_config.certificaciones),
                    notas = COALESCE(EXCLUDED.notas, profesor_config.notas),
                    updated_at = NOW()
                RETURNING *
            """, (
                profesor_id,
                payload.get("usuario_vinculado_id"),
                payload.get("monto"),
                payload.get("monto_tipo") or "mensual",
                payload.get("especialidad"),
                payload.get("experiencia_anios"),
                payload.get("certificaciones"),
                payload.get("notas")
            ))
            row = cur.fetchone()
            conn.commit()
            
            result = dict(row) if row else {}
            if result.get("monto"):
                result["monto"] = float(result["monto"])
            return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# === Resumen ===

@router.get("/api/profesores/{profesor_id}/resumen/mensual")
async def api_profesor_resumen_mensual(
    profesor_id: int,
    request: Request,
    _=Depends(require_gestion_access)
):
    """Get monthly summary of hours worked"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        return {"horas_trabajadas": 0, "horas_proyectadas": 0, "horas_extra": 0, "horas_totales": 0}
    try:
        mes = request.query_params.get("mes")
        anio = request.query_params.get("anio")
        
        now = datetime.now()
        mes_int = int(mes) if mes else now.month
        anio_int = int(anio) if anio else now.year
        
        # Get first and last day of month
        _, last_day = monthrange(anio_int, mes_int)
        start_date = date(anio_int, mes_int, 1)
        end_date = date(anio_int, mes_int, last_day)
        
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Get total worked hours
            cur.execute("""
                SELECT COALESCE(SUM(duracion_minutos), 0) as total_minutos
                FROM sesiones
                WHERE profesor_id = %s 
                  AND DATE(inicio) >= %s 
                  AND DATE(inicio) <= %s
                  AND fin IS NOT NULL
            """, (profesor_id, start_date, end_date))
            row = cur.fetchone()
            total_minutos = int(row["total_minutos"]) if row else 0
            horas_trabajadas = round(total_minutos / 60, 1)
            
            # Get projected hours from availability
            _ensure_profesor_tables(conn)
            cur.execute("""
                SELECT dia, hora_inicio, hora_fin
                FROM profesor_horarios
                WHERE profesor_id = %s AND disponible = TRUE
            """, (profesor_id,))
            horarios = cur.fetchall() or []
            
            # Calculate weekly projected hours
            horas_semana = 0
            for h in horarios:
                try:
                    inicio = datetime.strptime(str(h["hora_inicio"]), "%H:%M:%S")
                    fin = datetime.strptime(str(h["hora_fin"]), "%H:%M:%S")
                    horas_semana += (fin - inicio).seconds / 3600
                except:
                    pass
            
            # Multiply by ~4.3 weeks per month
            horas_proyectadas = round(horas_semana * 4.3, 1)
            horas_extra = max(0, round(horas_trabajadas - horas_proyectadas, 1))
            
            return {
                "horas_trabajadas": horas_trabajadas,
                "horas_proyectadas": horas_proyectadas,
                "horas_extra": horas_extra,
                "horas_totales": horas_trabajadas
            }
    except Exception as e:
        logger.exception("Error calculating monthly summary")
        return {"horas_trabajadas": 0, "horas_proyectadas": 0, "horas_extra": 0, "horas_totales": 0}


@router.get("/api/profesores/{profesor_id}/resumen/semanal")
async def api_profesor_resumen_semanal(
    profesor_id: int,
    request: Request,
    _=Depends(require_gestion_access)
):
    """Get weekly summary of hours worked"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        return {"horas_trabajadas": 0, "horas_proyectadas": 0, "horas_extra": 0, "horas_totales": 0}
    try:
        fecha = request.query_params.get("fecha")
        
        if fecha:
            ref_date = datetime.strptime(fecha, "%Y-%m-%d").date()
        else:
            ref_date = date.today()
        
        # Get Monday of the week
        start_of_week = ref_date - timedelta(days=ref_date.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Get total worked hours this week
            cur.execute("""
                SELECT COALESCE(SUM(duracion_minutos), 0) as total_minutos
                FROM sesiones
                WHERE profesor_id = %s 
                  AND DATE(inicio) >= %s 
                  AND DATE(inicio) <= %s
                  AND fin IS NOT NULL
            """, (profesor_id, start_of_week, end_of_week))
            row = cur.fetchone()
            total_minutos = int(row["total_minutos"]) if row else 0
            horas_trabajadas = round(total_minutos / 60, 1)
            
            # Get projected hours from availability
            _ensure_profesor_tables(conn)
            cur.execute("""
                SELECT dia, hora_inicio, hora_fin
                FROM profesor_horarios
                WHERE profesor_id = %s AND disponible = TRUE
            """, (profesor_id,))
            horarios = cur.fetchall() or []
            
            horas_proyectadas = 0
            for h in horarios:
                try:
                    inicio = datetime.strptime(str(h["hora_inicio"]), "%H:%M:%S")
                    fin = datetime.strptime(str(h["hora_fin"]), "%H:%M:%S")
                    horas_proyectadas += (fin - inicio).seconds / 3600
                except:
                    pass
            
            horas_proyectadas = round(horas_proyectadas, 1)
            horas_extra = max(0, round(horas_trabajadas - horas_proyectadas, 1))
            
            return {
                "horas_trabajadas": horas_trabajadas,
                "horas_proyectadas": horas_proyectadas,
                "horas_extra": horas_extra,
                "horas_totales": horas_trabajadas
            }
    except Exception as e:
        logger.exception("Error calculating weekly summary")
        return {"horas_trabajadas": 0, "horas_proyectadas": 0, "horas_extra": 0, "horas_totales": 0}
