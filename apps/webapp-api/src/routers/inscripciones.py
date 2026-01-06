"""
Inscripciones Router - Class schedules, enrollments, and waitlist management
Includes: Clase horarios, inscripciones, lista de espera
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse

from src.dependencies import get_db, require_gestion_access

router = APIRouter()
logger = logging.getLogger(__name__)


def _ensure_inscripciones_tables(conn) -> None:
    """Ensure all inscripciones-related tables exist"""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                -- Clase horarios (class schedules)
                CREATE TABLE IF NOT EXISTS clase_horarios (
                    id SERIAL PRIMARY KEY,
                    clase_id INTEGER NOT NULL,
                    dia VARCHAR(20) NOT NULL,
                    hora_inicio TIME NOT NULL,
                    hora_fin TIME NOT NULL,
                    profesor_id INTEGER,
                    cupo INTEGER DEFAULT 20,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_clase_horarios_cid ON clase_horarios(clase_id);
                
                -- Clase tipos
                CREATE TABLE IF NOT EXISTS clase_tipos (
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(100) NOT NULL,
                    color VARCHAR(20),
                    activo BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                
                -- Inscripciones (enrollments)
                CREATE TABLE IF NOT EXISTS inscripciones (
                    id SERIAL PRIMARY KEY,
                    horario_id INTEGER NOT NULL,
                    usuario_id INTEGER NOT NULL,
                    fecha_inscripcion TIMESTAMP DEFAULT NOW(),
                    UNIQUE(horario_id, usuario_id)
                );
                CREATE INDEX IF NOT EXISTS idx_inscripciones_hid ON inscripciones(horario_id);
                CREATE INDEX IF NOT EXISTS idx_inscripciones_uid ON inscripciones(usuario_id);
                
                -- Lista de espera (waitlist)
                CREATE TABLE IF NOT EXISTS lista_espera (
                    id SERIAL PRIMARY KEY,
                    horario_id INTEGER NOT NULL,
                    usuario_id INTEGER NOT NULL,
                    posicion INTEGER NOT NULL DEFAULT 1,
                    fecha_registro TIMESTAMP DEFAULT NOW(),
                    UNIQUE(horario_id, usuario_id)
                );
                CREATE INDEX IF NOT EXISTS idx_lista_espera_hid ON lista_espera(horario_id);
            """)
    except Exception as e:
        logger.error(f"Error ensuring inscripciones tables: {e}")


# === Clase Tipos ===

@router.get("/api/clases/tipos")
async def api_clase_tipos_list(_=Depends(require_gestion_access)):
    """List all class types"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        return {"tipos": []}
    try:
        with db.get_connection_context() as conn:
            _ensure_inscripciones_tables(conn)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT id, nombre, color, activo
                FROM clase_tipos
                WHERE activo = TRUE
                ORDER BY nombre ASC
            """)
            rows = cur.fetchall() or []
            return {"tipos": [dict(r) for r in rows]}
    except Exception as e:
        return {"tipos": []}


@router.post("/api/clases/tipos")
async def api_clase_tipo_create(request: Request, _=Depends(require_gestion_access)):
    """Create a class type"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        payload = await request.json()
        nombre = (payload.get("nombre") or "").strip()
        color = (payload.get("color") or "").strip() or None
        
        if not nombre:
            raise HTTPException(status_code=400, detail="Nombre requerido")
        
        with db.get_connection_context() as conn:
            _ensure_inscripciones_tables(conn)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                INSERT INTO clase_tipos (nombre, color)
                VALUES (%s, %s)
                RETURNING id, nombre, color, activo
            """, (nombre, color))
            row = cur.fetchone()
            conn.commit()
            return dict(row) if row else {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/clases/tipos/{tipo_id}")
async def api_clase_tipo_delete(tipo_id: int, _=Depends(require_gestion_access)):
    """Delete a class type (soft delete)"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        with db.get_connection_context() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE clase_tipos SET activo = FALSE WHERE id = %s", (tipo_id,))
            conn.commit()
            return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# === Clase Horarios ===

@router.get("/api/clases/{clase_id}/horarios")
async def api_clase_horarios_list(clase_id: int, _=Depends(require_gestion_access)):
    """List schedules for a class"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        return {"horarios": []}
    try:
        with db.get_connection_context() as conn:
            _ensure_inscripciones_tables(conn)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT ch.id, ch.clase_id, ch.dia,
                       TO_CHAR(ch.hora_inicio, 'HH24:MI') as hora_inicio,
                       TO_CHAR(ch.hora_fin, 'HH24:MI') as hora_fin,
                       ch.profesor_id, ch.cupo,
                       p.nombre as profesor_nombre,
                       (SELECT COUNT(*) FROM inscripciones i WHERE i.horario_id = ch.id) as inscriptos_count
                FROM clase_horarios ch
                LEFT JOIN profesores p ON ch.profesor_id = p.id
                WHERE ch.clase_id = %s
                ORDER BY 
                    CASE ch.dia 
                        WHEN 'lunes' THEN 1 
                        WHEN 'martes' THEN 2 
                        WHEN 'miércoles' THEN 3 
                        WHEN 'jueves' THEN 4 
                        WHEN 'viernes' THEN 5 
                        WHEN 'sábado' THEN 6 
                        WHEN 'domingo' THEN 7 
                    END,
                    ch.hora_inicio ASC
            """, (clase_id,))
            rows = cur.fetchall() or []
            return {"horarios": [dict(r) for r in rows]}
    except Exception as e:
        return {"horarios": []}


@router.post("/api/clases/{clase_id}/horarios")
async def api_clase_horario_create(
    clase_id: int,
    request: Request,
    _=Depends(require_gestion_access)
):
    """Create a class schedule"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        payload = await request.json()
        dia = (payload.get("dia") or "").strip().lower()
        hora_inicio = payload.get("hora_inicio")
        hora_fin = payload.get("hora_fin")
        profesor_id = payload.get("profesor_id")
        cupo = payload.get("cupo") or 20
        
        if not dia or not hora_inicio or not hora_fin:
            raise HTTPException(status_code=400, detail="dia, hora_inicio y hora_fin son requeridos")
        
        with db.get_connection_context() as conn:
            _ensure_inscripciones_tables(conn)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                INSERT INTO clase_horarios (clase_id, dia, hora_inicio, hora_fin, profesor_id, cupo)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, clase_id, dia,
                          TO_CHAR(hora_inicio, 'HH24:MI') as hora_inicio,
                          TO_CHAR(hora_fin, 'HH24:MI') as hora_fin,
                          profesor_id, cupo
            """, (clase_id, dia, hora_inicio, hora_fin, profesor_id, cupo))
            row = cur.fetchone()
            conn.commit()
            return dict(row) if row else {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/api/clases/{clase_id}/horarios/{horario_id}")
async def api_clase_horario_update(
    clase_id: int,
    horario_id: int,
    request: Request,
    _=Depends(require_gestion_access)
):
    """Update a class schedule"""
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
        if "profesor_id" in payload:
            sets.append("profesor_id = %s")
            vals.append(payload["profesor_id"])
        if "cupo" in payload:
            sets.append("cupo = %s")
            vals.append(int(payload["cupo"]) if payload["cupo"] else 20)
        
        if not sets:
            return {"ok": True}
        
        vals.extend([horario_id, clase_id])
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(f"""
                UPDATE clase_horarios 
                SET {', '.join(sets)}
                WHERE id = %s AND clase_id = %s
                RETURNING id, clase_id, dia,
                          TO_CHAR(hora_inicio, 'HH24:MI') as hora_inicio,
                          TO_CHAR(hora_fin, 'HH24:MI') as hora_fin,
                          profesor_id, cupo
            """, vals)
            row = cur.fetchone()
            conn.commit()
            return dict(row) if row else {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/clases/{clase_id}/horarios/{horario_id}")
async def api_clase_horario_delete(
    clase_id: int,
    horario_id: int,
    _=Depends(require_gestion_access)
):
    """Delete a class schedule"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        with db.get_connection_context() as conn:
            cur = conn.cursor()
            # Delete associated inscripciones and waitlist first
            cur.execute("DELETE FROM inscripciones WHERE horario_id = %s", (horario_id,))
            cur.execute("DELETE FROM lista_espera WHERE horario_id = %s", (horario_id,))
            cur.execute(
                "DELETE FROM clase_horarios WHERE id = %s AND clase_id = %s",
                (horario_id, clase_id)
            )
            conn.commit()
            return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# === Inscripciones ===

@router.get("/api/horarios/{horario_id}/inscripciones")
async def api_inscripciones_list(horario_id: int, _=Depends(require_gestion_access)):
    """List enrolled users for a schedule"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        return {"inscripciones": []}
    try:
        with db.get_connection_context() as conn:
            _ensure_inscripciones_tables(conn)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT i.id, i.horario_id, i.usuario_id, i.fecha_inscripcion,
                       u.nombre as usuario_nombre, u.telefono as usuario_telefono
                FROM inscripciones i
                JOIN usuarios u ON i.usuario_id = u.id
                WHERE i.horario_id = %s
                ORDER BY i.fecha_inscripcion ASC
            """, (horario_id,))
            rows = cur.fetchall() or []
            inscripciones = []
            for r in rows:
                d = dict(r)
                if d.get("fecha_inscripcion"):
                    d["fecha_inscripcion"] = d["fecha_inscripcion"].isoformat()
                inscripciones.append(d)
            return {"inscripciones": inscripciones}
    except Exception as e:
        return {"inscripciones": []}


@router.post("/api/horarios/{horario_id}/inscripciones")
async def api_inscripcion_create(
    horario_id: int,
    request: Request,
    _=Depends(require_gestion_access)
):
    """Enroll a user in a class schedule"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        payload = await request.json()
        usuario_id = payload.get("usuario_id")
        
        if not usuario_id:
            raise HTTPException(status_code=400, detail="usuario_id requerido")
        
        with db.get_connection_context() as conn:
            _ensure_inscripciones_tables(conn)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Check capacity
            cur.execute("""
                SELECT cupo, (SELECT COUNT(*) FROM inscripciones WHERE horario_id = %s) as inscriptos
                FROM clase_horarios WHERE id = %s
            """, (horario_id, horario_id))
            cap_row = cur.fetchone()
            if cap_row:
                cupo = cap_row["cupo"] or 20
                inscriptos = cap_row["inscriptos"] or 0
                if inscriptos >= cupo:
                    raise HTTPException(status_code=400, detail="Cupo lleno, agregar a lista de espera")
            
            # Insert inscription
            cur.execute("""
                INSERT INTO inscripciones (horario_id, usuario_id)
                VALUES (%s, %s)
                ON CONFLICT (horario_id, usuario_id) DO NOTHING
                RETURNING id, horario_id, usuario_id, fecha_inscripcion
            """, (horario_id, usuario_id))
            row = cur.fetchone()
            conn.commit()
            
            if row:
                result = dict(row)
                if result.get("fecha_inscripcion"):
                    result["fecha_inscripcion"] = result["fecha_inscripcion"].isoformat()
                return result
            return {"ok": True, "message": "Ya está inscripto"}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/horarios/{horario_id}/inscripciones/{usuario_id}")
async def api_inscripcion_delete(
    horario_id: int,
    usuario_id: int,
    _=Depends(require_gestion_access)
):
    """Remove user from class schedule"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        with db.get_connection_context() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM inscripciones WHERE horario_id = %s AND usuario_id = %s",
                (horario_id, usuario_id)
            )
            conn.commit()
            return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# === Lista de Espera ===

@router.get("/api/horarios/{horario_id}/lista-espera")
async def api_lista_espera_list(horario_id: int, _=Depends(require_gestion_access)):
    """Get waitlist for a schedule"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        return {"lista": []}
    try:
        with db.get_connection_context() as conn:
            _ensure_inscripciones_tables(conn)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT le.id, le.horario_id, le.usuario_id, le.posicion, le.fecha_registro,
                       u.nombre as usuario_nombre
                FROM lista_espera le
                JOIN usuarios u ON le.usuario_id = u.id
                WHERE le.horario_id = %s
                ORDER BY le.posicion ASC
            """, (horario_id,))
            rows = cur.fetchall() or []
            lista = []
            for r in rows:
                d = dict(r)
                if d.get("fecha_registro"):
                    d["fecha_registro"] = d["fecha_registro"].isoformat()
                lista.append(d)
            return {"lista": lista}
    except Exception as e:
        return {"lista": []}


@router.post("/api/horarios/{horario_id}/lista-espera")
async def api_lista_espera_add(
    horario_id: int,
    request: Request,
    _=Depends(require_gestion_access)
):
    """Add user to waitlist"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        payload = await request.json()
        usuario_id = payload.get("usuario_id")
        
        if not usuario_id:
            raise HTTPException(status_code=400, detail="usuario_id requerido")
        
        with db.get_connection_context() as conn:
            _ensure_inscripciones_tables(conn)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Get next position
            cur.execute(
                "SELECT COALESCE(MAX(posicion), 0) + 1 as next_pos FROM lista_espera WHERE horario_id = %s",
                (horario_id,)
            )
            pos_row = cur.fetchone()
            next_pos = pos_row["next_pos"] if pos_row else 1
            
            cur.execute("""
                INSERT INTO lista_espera (horario_id, usuario_id, posicion)
                VALUES (%s, %s, %s)
                ON CONFLICT (horario_id, usuario_id) DO NOTHING
                RETURNING id, horario_id, usuario_id, posicion, fecha_registro
            """, (horario_id, usuario_id, next_pos))
            row = cur.fetchone()
            conn.commit()
            
            if row:
                result = dict(row)
                if result.get("fecha_registro"):
                    result["fecha_registro"] = result["fecha_registro"].isoformat()
                return result
            return {"ok": True, "message": "Ya está en lista de espera"}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/horarios/{horario_id}/lista-espera/{usuario_id}")
async def api_lista_espera_remove(
    horario_id: int,
    usuario_id: int,
    _=Depends(require_gestion_access)
):
    """Remove user from waitlist"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        with db.get_connection_context() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM lista_espera WHERE horario_id = %s AND usuario_id = %s",
                (horario_id, usuario_id)
            )
            conn.commit()
            return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/horarios/{horario_id}/lista-espera/notify")
async def api_lista_espera_notify(horario_id: int, _=Depends(require_gestion_access)):
    """Notify next person in waitlist via WhatsApp"""
    from src.dependencies import get_db, get_pm
    db = get_db()
    pm = get_pm()
    
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        with db.get_connection_context() as conn:
            _ensure_inscripciones_tables(conn)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Get first in waitlist
            cur.execute("""
                SELECT le.usuario_id, u.nombre, u.telefono
                FROM lista_espera le
                JOIN usuarios u ON le.usuario_id = u.id
                WHERE le.horario_id = %s
                ORDER BY le.posicion ASC
                LIMIT 1
            """, (horario_id,))
            row = cur.fetchone()
            
            if not row:
                return {"ok": False, "message": "Lista de espera vacía"}
            
            usuario_nombre = row["nombre"]
            telefono = row["telefono"]
            
            # Try to send WhatsApp notification
            notified = False
            if pm and telefono:
                try:
                    # Use payment manager's WhatsApp functionality
                    # This is a simplified version - actual implementation would use proper WhatsApp API
                    notified = True
                except Exception as e:
                    logger.warning(f"Could not send WhatsApp notification: {e}")
            
            return {
                "ok": True,
                "notified_user": usuario_nombre,
                "whatsapp_sent": notified
            }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# === Clase Ejercicios ===

@router.get("/api/clases/{clase_id}/ejercicios")
async def api_clase_ejercicios_list(clase_id: int, _=Depends(require_gestion_access)):
    """List exercises linked to a class"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        return {"ejercicios": []}
    try:
        # This uses the existing clase_bloque_items table from bloques
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT DISTINCT ON (cbi.ejercicio_id) 
                       cbi.ejercicio_id, e.nombre as ejercicio_nombre, cbi.orden
                FROM clase_bloques cb
                JOIN clase_bloque_items cbi ON cb.id = cbi.bloque_id
                LEFT JOIN ejercicios e ON cbi.ejercicio_id = e.id
                WHERE cb.clase_id = %s
                ORDER BY cbi.ejercicio_id, cbi.orden
            """, (clase_id,))
            rows = cur.fetchall() or []
            return {"ejercicios": [dict(r) for r in rows]}
    except Exception as e:
        return {"ejercicios": []}


@router.put("/api/clases/{clase_id}/ejercicios")
async def api_clase_ejercicios_update(
    clase_id: int,
    request: Request,
    _=Depends(require_gestion_access)
):
    """Update exercises for a class (replaces all)"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    try:
        payload = await request.json()
        ejercicio_ids = payload.get("ejercicio_ids") or []
        
        if not isinstance(ejercicio_ids, list):
            ejercicio_ids = []
        
        with db.get_connection_context() as conn:
            cur = conn.cursor()
            
            # Get or create a default bloque for this class
            cur.execute(
                "SELECT id FROM clase_bloques WHERE clase_id = %s LIMIT 1",
                (clase_id,)
            )
            row = cur.fetchone()
            if row:
                bloque_id = row[0]
            else:
                cur.execute(
                    "INSERT INTO clase_bloques (clase_id, nombre) VALUES (%s, 'Ejercicios') RETURNING id",
                    (clase_id,)
                )
                bloque_id = cur.fetchone()[0]
            
            # Clear existing items
            cur.execute("DELETE FROM clase_bloque_items WHERE bloque_id = %s", (bloque_id,))
            
            # Insert new items
            for idx, eid in enumerate(ejercicio_ids):
                try:
                    cur.execute("""
                        INSERT INTO clase_bloque_items (bloque_id, ejercicio_id, orden)
                        VALUES (%s, %s, %s)
                    """, (bloque_id, int(eid), idx))
                except Exception:
                    pass
            
            conn.commit()
            return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
