"""Admin Service - SQLAlchemy ORM for admin operations."""
from typing import Optional, Dict, Any, List
import logging
import bcrypt

from sqlalchemy.orm import Session
from sqlalchemy import text

from src.services.base import BaseService

logger = logging.getLogger(__name__)


class AdminService(BaseService):
    """Service for admin operations like password management, user renumbering."""

    def __init__(self, db: Session):
        super().__init__(db)

    def cambiar_contrasena_dueno(self, current: str, new: str) -> Dict[str, Any]:
        """Change owner password."""
        try:
            row = self.db.execute(text("SELECT id, pin FROM usuarios WHERE rol IN ('dueno', 'owner', 'admin') ORDER BY id LIMIT 1")).fetchone()
            if not row:
                return {'ok': False, 'error': 'Owner not found'}
            
            owner_id, stored = row[0], row[1] or ""
            valid = False
            if stored.startswith("$2"):
                try: valid = bcrypt.checkpw(current.encode(), stored.encode())
                except: valid = False
            else:
                valid = (current == stored)
            
            if not valid:
                return {'ok': False, 'error': 'Current password incorrect'}
            
            new_hash = bcrypt.hashpw(new.encode(), bcrypt.gensalt()).decode()
            self.db.execute(text("UPDATE usuarios SET pin = :pin WHERE id = :id"), {'pin': new_hash, 'id': owner_id})
            self.db.commit()
            return {'ok': True}
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            self.db.rollback()
            return {'ok': False, 'error': str(e)}

    def secure_owner(self) -> Dict[str, Any]:
        """Ensure owner exists and has bcrypt password."""
        try:
            row = self.db.execute(text("SELECT id, nombre, pin, rol FROM usuarios WHERE rol IN ('dueno', 'owner', 'admin') ORDER BY id LIMIT 1")).fetchone()
            actions = []
            
            if not row:
                result = self.db.execute(text("INSERT INTO usuarios (nombre, rol, activo, pin) VALUES ('Administrador', 'dueno', TRUE, '1234') RETURNING id"))
                owner_id = result.fetchone()[0]
                actions.append(f"Created owner with ID {owner_id}")
                row = self.db.execute(text("SELECT id, nombre, pin, rol FROM usuarios WHERE id = :id"), {'id': owner_id}).fetchone()
            
            if row and row[2] and not row[2].startswith("$2"):
                new_hash = bcrypt.hashpw(row[2].encode(), bcrypt.gensalt()).decode()
                self.db.execute(text("UPDATE usuarios SET pin = :pin WHERE id = :id"), {'pin': new_hash, 'id': row[0]})
                actions.append("Upgraded to bcrypt")
            
            self.db.commit()
            return {'ok': True, 'owner_id': row[0] if row else None, 'actions': actions}
        except Exception as e:
            logger.error(f"Error securing owner: {e}")
            self.db.rollback()
            return {'ok': False, 'error': str(e)}

    def renumerar_usuarios(self, start_id: int = 1) -> Dict[str, Any]:
        """Renumber user IDs starting from start_id."""
        try:
            users = self.db.execute(text("SELECT id FROM usuarios ORDER BY id")).fetchall()
            if not users:
                return {'ok': True, 'message': 'No users'}
            
            mapping = {}
            new_id = start_id
            for u in users:
                if u[0] != new_id:
                    mapping[u[0]] = new_id
                new_id += 1
            
            if not mapping:
                return {'ok': True, 'message': 'IDs already correct'}
            
            related = [("pagos", "usuario_id"), ("asistencias", "usuario_id"), ("rutinas", "usuario_id"), ("inscripciones", "usuario_id"), ("lista_espera", "usuario_id")]
            self.db.execute(text("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS _new_id INTEGER"))
            
            for old, nid in mapping.items():
                self.db.execute(text("UPDATE usuarios SET _new_id = :nid WHERE id = :old"), {'nid': nid, 'old': old})
            self.db.execute(text("UPDATE usuarios SET _new_id = id WHERE _new_id IS NULL"))
            
            for table, col in related:
                try:
                    for old, nid in mapping.items():
                        self.db.execute(text(f"UPDATE {table} SET {col} = :temp WHERE {col} = :old"), {'temp': nid + 1000000, 'old': old})
                    for old, nid in mapping.items():
                        self.db.execute(text(f"UPDATE {table} SET {col} = :nid WHERE {col} = :temp"), {'nid': nid, 'temp': nid + 1000000})
                except: pass
            
            self.db.execute(text("UPDATE usuarios SET id = _new_id WHERE _new_id IS NOT NULL AND _new_id != id"))
            self.db.execute(text("ALTER TABLE usuarios DROP COLUMN IF EXISTS _new_id"))
            self.db.execute(text("SELECT setval(pg_get_serial_sequence('usuarios', 'id'), COALESCE((SELECT MAX(id) FROM usuarios), 1))"))
            self.db.commit()
            return {'ok': True, 'changes': len(mapping)}
        except Exception as e:
            logger.error(f"Error renumbering: {e}")
            self.db.rollback()
            return {'ok': False, 'error': str(e)}

    def obtener_reminder(self) -> Dict[str, Any]:
        """Get system reminder."""
        try:
            row = self.db.execute(text("SELECT valor FROM configuracion WHERE clave = 'system_reminder' AND activo = TRUE LIMIT 1")).fetchone()
            return {'active': bool(row), 'message': row[0] if row else None}
        except:
            return {'active': False, 'message': None}

    def establecer_reminder(self, message: str, active: bool = True) -> bool:
        """Set system reminder."""
        try:
            self.db.execute(text("CREATE TABLE IF NOT EXISTS configuracion (id SERIAL PRIMARY KEY, clave VARCHAR(100) UNIQUE, valor TEXT, activo BOOLEAN DEFAULT TRUE, updated_at TIMESTAMP DEFAULT NOW())"))
            self.db.execute(text("INSERT INTO configuracion (clave, valor, activo) VALUES ('system_reminder', :msg, :act) ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor, activo = EXCLUDED.activo, updated_at = NOW()"), {'msg': message, 'act': active})
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting reminder: {e}")
            self.db.rollback()
            return False
