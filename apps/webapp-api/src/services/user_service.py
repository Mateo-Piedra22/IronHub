from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from src.services.base import BaseService
from src.database.repositories.user_repository import UserRepository
from src.database.repositories.payment_repository import PaymentRepository
from src.database.repositories.gym_repository import GymRepository

from src.database.orm_models import Usuario

class UserService(BaseService):
    def __init__(self, db: Session = None):
        super().__init__(db)
        self.user_repo = UserRepository(self.db, None, None) # Logger and Cache can be None for now or injected
        self.payment_repo = PaymentRepository(self.db, None, None)
        self.gym_repo = GymRepository(self.db, None, None)

    def get_user(self, user_id: int) -> Optional[Usuario]:
        return self.user_repo.obtener_usuario(user_id)

    def get_user_by_dni(self, dni: str) -> Optional[Usuario]:
        return self.user_repo.obtener_usuario_por_dni(dni)

    def list_users(self, q: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Dict]:
        return self.user_repo.listar_usuarios_paginados(q, limit, offset)

    def create_user(self, data: Dict[str, Any]) -> int:
        # Validation logic moved from router
        dni = data.get("dni")
        if self.user_repo.obtener_usuario_por_dni(dni):
            raise ValueError("DNI ya existe")
        
        # Create object
        usuario = Usuario(**data)
        return self.user_repo.crear_usuario(usuario)

    def update_user(self, user_id: int, data: Dict[str, Any], modifier_id: Optional[int] = None, is_owner: bool = False) -> bool:
        # Logic for PIN update and ID change
        current_user = self.user_repo.obtener_usuario(user_id)
        if not current_user:
            raise ValueError("Usuario no encontrado")
            
        # Handle PIN logic (preserve if not provided)
        if "pin" not in data or data["pin"] is None:
             data["pin"] = current_user.pin
             
        # Update fields
        for k, v in data.items():
            if k != "new_id" and hasattr(current_user, k):
                setattr(current_user, k, v)
                
        self.user_repo.actualizar_usuario(current_user)
        
        # Handle ID change
        new_id = data.get("new_id")
        if new_id and int(new_id) != user_id:
            if not is_owner:
                raise PermissionError("Solo el dueño puede cambiar el ID de usuario")
            self.user_repo.cambiar_usuario_id(user_id, int(new_id))
            
        return True

    def delete_user(self, user_id: int):
        self.user_repo.eliminar_usuario(user_id)

    def get_user_panel_data(self, user_id: int) -> Dict[str, Any]:
        u = self.user_repo.obtener_usuario(user_id)
        if not u:
            return None
            
        # Calculate days remaining
        dias_restantes = None
        fpv = u.fecha_proximo_vencimiento
        if fpv:
             delta = (fpv - date.today()).days
             dias_restantes = delta

        # Get last payments
        pagos = self.payment_repo.obtener_ultimos_pagos(user_id, limit=10)
        
        # Get routines via relationship
        rutinas = [r for r in u.rutinas if r.activa] if hasattr(u, 'rutinas') and u.rutinas else []
        
        return {
            "usuario": u,
            "dias_restantes": dias_restantes,
            "pagos": pagos,
            "rutinas": rutinas
        }

    def get_user_tags(self, user_id: int):
        return self.user_repo.obtener_etiquetas_usuario(user_id)

    def add_user_tag(self, user_id: int, tag_data: Dict[str, Any], assigned_by: Optional[int]):
        etiqueta_id = tag_data.get("etiqueta_id")
        nombre = tag_data.get("nombre")
        
        if not etiqueta_id and nombre:
            et = self.user_repo.obtener_o_crear_etiqueta(nombre)
            etiqueta_id = et.id
            
        if etiqueta_id:
            self.user_repo.asignar_etiqueta(user_id, etiqueta_id, assigned_by)
            return True
        return False

    def remove_user_tag(self, user_id: int, tag_id: int):
        self.user_repo.remover_etiqueta(user_id, tag_id)
        return True

    # --- Fixed: Using ORM instead of raw SQL ---
    
    def toggle_activo(self, user_id: int) -> Dict[str, Any]:
        """Toggle user active status using ORM."""
        user = self.user_repo.obtener_usuario(user_id)
        if not user:
            return {'error': 'not_found'}
        new_status = self.user_repo.alternar_estado_activo(user_id)
        return {'id': user_id, 'activo': new_status, 'nombre': user.nombre}

    def update_notas(self, user_id: int, notas: str) -> bool:
        """Update user notes using ORM."""
        user = self.user_repo.obtener_usuario(user_id)
        if not user:
            return False
        user.notas = notas
        self.db.commit()
        return True

    def generate_qr_token(self, user_id: int) -> Dict[str, str]:
        """Generate QR check-in token for user."""
        import secrets
        import time
        from src.database.orm_models import CheckinPending
        
        token = f"checkin_{user_id}_{int(time.time())}_{secrets.token_hex(8)}"
        
        # Use ORM model instead of raw CREATE TABLE
        expires_at = datetime.now() + timedelta(hours=24)
        checkin_pending = CheckinPending(
            usuario_id=user_id,
            token=token,
            expires_at=expires_at
        )
        self.db.add(checkin_pending)
        self.db.commit()
        
        return {'qr_url': f"/api/checkin?token={token}", 'token': token}

    def get_tag_suggestions(self) -> List[str]:
        """Get common tag suggestions using ORM."""
        return self.user_repo.obtener_sugerencias_etiquetas(limit=20)

    # --- User States (Estados) Management ---
    
    def get_user_states(self, user_id: int, solo_activos: bool = True) -> List[Dict]:
        """Get user states."""
        estados = self.user_repo.obtener_estados_usuario(user_id, solo_activos)
        return [
            {
                'id': e.id,
                'usuario_id': e.usuario_id,
                'estado': e.estado,
                'descripcion': e.descripcion,
                'fecha_inicio': e.fecha_inicio,
                'fecha_vencimiento': e.fecha_vencimiento,
                'activo': e.activo,
                'creado_por': e.creado_por
            }
            for e in estados
        ]

    def add_user_state(self, user_id: int, data: Dict[str, Any], creado_por: int = None) -> int:
        """Add a new state to user."""
        return self.user_repo.crear_estado_usuario(
            usuario_id=user_id,
            estado=data.get('estado'),
            descripcion=data.get('descripcion'),
            fecha_inicio=data.get('fecha_inicio'),
            fecha_vencimiento=data.get('fecha_vencimiento'),
            creado_por=creado_por
        )

    def update_user_state(self, estado_id: int, data: Dict[str, Any]) -> bool:
        """Update an existing user state."""
        return self.user_repo.actualizar_estado_usuario(estado_id, data)

    def delete_user_state(self, estado_id: int) -> bool:
        """Delete (soft) a user state."""
        return self.user_repo.eliminar_estado_usuario(estado_id)

    def get_state_templates(self) -> List[str]:
        """Get predefined state templates."""
        return self.user_repo.obtener_plantillas_estados()

    def get_morose_user_ids(self) -> List[int]:
        """Get IDs of users with overdue payments."""
        morosos = self.user_repo.obtener_usuarios_morosos()
        return [m['id'] for m in morosos]

