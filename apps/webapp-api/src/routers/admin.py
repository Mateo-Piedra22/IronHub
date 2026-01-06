"""
Admin Router - Owner management, system admin functions
"""
import logging
import os
import bcrypt
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse

from src.dependencies import get_db, require_gestion_access, require_owner

router = APIRouter()
logger = logging.getLogger(__name__)


# === Password Management ===

@router.post("/api/admin/cambiar_contrasena")
async def api_admin_cambiar_contrasena(
    request: Request,
    _=Depends(require_owner)
):
    """Change owner password"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    
    try:
        payload = await request.json()
        current_password = payload.get("current_password", "").strip()
        new_password = payload.get("new_password", "").strip()
        
        if not current_password or not new_password:
            raise HTTPException(status_code=400, detail="Contraseña actual y nueva son requeridas")
        
        if len(new_password) < 6:
            raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 6 caracteres")
        
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Get current password hash
            cur.execute("""
                SELECT id, pin FROM usuarios 
                WHERE rol = 'dueno' OR rol = 'admin' OR rol = 'owner'
                ORDER BY id LIMIT 1
            """)
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Usuario dueño no encontrado")
            
            owner_id = row["id"]
            stored_pin = row["pin"] or ""
            
            # Verify current password
            password_valid = False
            if stored_pin:
                if stored_pin.startswith("$2"):
                    # bcrypt hash
                    try:
                        password_valid = bcrypt.checkpw(
                            current_password.encode("utf-8"),
                            stored_pin.encode("utf-8")
                        )
                    except Exception:
                        password_valid = False
                else:
                    # Plaintext comparison (legacy)
                    password_valid = (current_password == stored_pin)
            
            if not password_valid:
                raise HTTPException(status_code=401, detail="Contraseña actual incorrecta")
            
            # Hash new password
            new_hash = bcrypt.hashpw(
                new_password.encode("utf-8"),
                bcrypt.gensalt()
            ).decode("utf-8")
            
            # Update password
            cur.execute(
                "UPDATE usuarios SET pin = %s WHERE id = %s",
                (new_hash, owner_id)
            )
            conn.commit()
            
            return {"ok": True, "message": "Contraseña actualizada"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error changing password")
        return JSONResponse({"error": str(e)}, status_code=500)


# === User ID Renumbering ===

@router.post("/api/admin/renumerar_usuarios")
async def api_admin_renumerar_usuarios(
    request: Request,
    _=Depends(require_owner)
):
    """
    Renumber user IDs starting from a specified value.
    Updates all foreign key references in related tables.
    """
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    
    try:
        payload = await request.json()
        start_id = int(payload.get("start_id", 1))
        
        if start_id < 1:
            raise HTTPException(status_code=400, detail="start_id debe ser >= 1")
        
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Get all current users ordered by ID
            cur.execute("SELECT id FROM usuarios ORDER BY id ASC")
            users = cur.fetchall() or []
            
            if not users:
                return {"ok": True, "message": "No hay usuarios para renumerar"}
            
            # Create mapping old_id -> new_id
            mapping = {}
            new_id = start_id
            for u in users:
                old_id = u["id"]
                if old_id != new_id:
                    mapping[old_id] = new_id
                new_id += 1
            
            if not mapping:
                return {"ok": True, "message": "Los IDs ya están correctamente numerados"}
            
            # Tables with foreign keys to usuarios.id
            related_tables = [
                ("pagos", "usuario_id"),
                ("asistencias", "usuario_id"),
                ("rutinas", "usuario_id"),
                ("inscripciones", "usuario_id"),
                ("lista_espera", "usuario_id"),
                ("usuario_etiquetas", "usuario_id"),
                ("usuario_estados", "usuario_id"),
                ("checkin_tokens", "usuario_id"),
            ]
            
            # Temporarily disable FK checks if needed
            # Use a temporary column to avoid conflicts
            
            # First, add a temp column
            cur.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS _new_id INTEGER")
            
            # Set new IDs
            for old_id, nid in mapping.items():
                cur.execute("UPDATE usuarios SET _new_id = %s WHERE id = %s", (nid, old_id))
            
            # For users not in mapping, keep their ID
            cur.execute("UPDATE usuarios SET _new_id = id WHERE _new_id IS NULL")
            
            # Update related tables
            for table, column in related_tables:
                try:
                    for old_id, nid in mapping.items():
                        cur.execute(f"UPDATE {table} SET {column} = %s WHERE {column} = %s", (nid + 1000000, old_id))
                    for old_id, nid in mapping.items():
                        cur.execute(f"UPDATE {table} SET {column} = %s WHERE {column} = %s", (nid, nid + 1000000))
                except Exception as e:
                    logger.warning(f"Could not update {table}: {e}")
            
            # Now update the actual IDs using the temp column
            cur.execute("""
                UPDATE usuarios SET id = _new_id 
                WHERE _new_id IS NOT NULL AND _new_id != id
            """)
            
            # Remove temp column
            cur.execute("ALTER TABLE usuarios DROP COLUMN IF EXISTS _new_id")
            
            # Reset sequence
            cur.execute("""
                SELECT setval(pg_get_serial_sequence('usuarios', 'id'), 
                              COALESCE((SELECT MAX(id) FROM usuarios), 1))
            """)
            
            conn.commit()
            
            return {
                "ok": True,
                "message": f"Renumerados {len(mapping)} usuarios",
                "changes": mapping
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error renumbering users")
        return JSONResponse({"error": str(e)}, status_code=500)


# === Owner Security ===

@router.post("/api/admin/secure_owner")
async def api_admin_secure_owner(
    request: Request,
    _=Depends(require_owner)
):
    """
    Ensure owner user exists and has proper protection.
    Creates owner if not exists, upgrades password from plaintext to bcrypt.
    """
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    
    try:
        with db.get_connection_context() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Check if owner exists
            cur.execute("""
                SELECT id, nombre, pin, rol FROM usuarios 
                WHERE rol IN ('dueno', 'owner', 'admin')
                ORDER BY id LIMIT 1
            """)
            owner = cur.fetchone()
            
            actions = []
            
            if not owner:
                # Create owner user
                cur.execute("""
                    INSERT INTO usuarios (nombre, rol, activo, pin)
                    VALUES ('Administrador', 'dueno', TRUE, '1234')
                    RETURNING id
                """)
                owner_id = cur.fetchone()["id"]
                actions.append(f"Created owner user with ID {owner_id}")
                
                # Re-fetch
                cur.execute("SELECT id, nombre, pin, rol FROM usuarios WHERE id = %s", (owner_id,))
                owner = cur.fetchone()
            
            # Check if password needs upgrading
            if owner and owner.get("pin"):
                stored_pin = owner["pin"]
                if not stored_pin.startswith("$2"):
                    # Upgrade to bcrypt
                    new_hash = bcrypt.hashpw(
                        stored_pin.encode("utf-8"),
                        bcrypt.gensalt()
                    ).decode("utf-8")
                    cur.execute(
                        "UPDATE usuarios SET pin = %s WHERE id = %s",
                        (new_hash, owner["id"])
                    )
                    actions.append("Upgraded password to bcrypt")
            
            conn.commit()
            
            return {
                "ok": True,
                "owner_id": owner["id"] if owner else None,
                "actions": actions
            }
    
    except Exception as e:
        logger.exception("Error securing owner")
        return JSONResponse({"error": str(e)}, status_code=500)


# === System Reminders ===

@router.get("/api/admin/reminder")
async def api_admin_reminder(request: Request):
    """Get system reminders/notices"""
    from src.dependencies import get_db
    db = get_db()
    
    # Check for active reminders in config or env
    reminder_message = os.getenv("SYSTEM_REMINDER", "")
    reminder_active = bool(reminder_message)
    
    if not reminder_active and db:
        try:
            with db.get_connection_context() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute("""
                    SELECT valor FROM configuracion 
                    WHERE clave = 'system_reminder' AND activo = TRUE
                    LIMIT 1
                """)
                row = cur.fetchone()
                if row:
                    reminder_message = row["valor"]
                    reminder_active = True
        except Exception:
            pass
    
    return {
        "active": reminder_active,
        "message": reminder_message if reminder_active else None
    }


@router.post("/api/admin/reminder")
async def api_admin_reminder_set(
    request: Request,
    _=Depends(require_owner)
):
    """Set system reminder"""
    from src.dependencies import get_db
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not available")
    
    try:
        payload = await request.json()
        message = (payload.get("message") or "").strip()
        active = payload.get("active", bool(message))
        
        with db.get_connection_context() as conn:
            cur = conn.cursor()
            
            # Ensure configuracion table exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS configuracion (
                    id SERIAL PRIMARY KEY,
                    clave VARCHAR(100) UNIQUE NOT NULL,
                    valor TEXT,
                    activo BOOLEAN DEFAULT TRUE,
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Upsert reminder
            cur.execute("""
                INSERT INTO configuracion (clave, valor, activo)
                VALUES ('system_reminder', %s, %s)
                ON CONFLICT (clave) DO UPDATE
                SET valor = EXCLUDED.valor, activo = EXCLUDED.activo, updated_at = NOW()
            """, (message, active))
            
            conn.commit()
            
            return {"ok": True}
    
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
