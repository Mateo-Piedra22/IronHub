"""
Gym Configuration Service - SQLAlchemy ORM Implementation

Handles gym configuration, themes, and system settings.
Replaces legacy GymService configuration methods.
"""
import json
import logging
from typing import Dict, Any, Optional

from sqlalchemy import select, text
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from src.services.base import BaseService
from src.database.orm_models import GymConfig, Configuracion, CustomTheme, ThemeSchedule

logger = logging.getLogger(__name__)

class GymConfigService(BaseService):
    """Service for gym configuration, branding, and themes."""

    def __init__(self, db: Session):
        super().__init__(db)

    # =========================================================================
    # GYM CONFIG (GymConfig & Configuracion tables)
    # =========================================================================

    def obtener_configuracion_gimnasio(self) -> Dict[str, Any]:
        """
        Get gym configuration merging 'gym_config' table (single row) 
        and 'configuracion' table (key-value pairs).
        """
        config = {}
        try:
            # 1. Load from GymConfig table (assuming single row for gym details)
            gym_info = self.db.execute(select(GymConfig).limit(1)).scalar_one_or_none()
            if gym_info:
                config.update({
                    'gym_name': gym_info.gym_name,
                    'gym_slogan': gym_info.gym_slogan,
                    'gym_address': gym_info.gym_address,
                    'gym_phone': gym_info.gym_phone,
                    'gym_email': gym_info.gym_email,
                    'gym_website': gym_info.gym_website,
                    'facebook': gym_info.facebook,
                    'instagram': gym_info.instagram,
                    'twitter': gym_info.twitter,
                    'logo_url': gym_info.logo_url,
                })

            # 2. Load from Configuracion table (general key-value settings)
            settings = self.db.execute(select(Configuracion)).scalars().all()
            for setting in settings:
                key = setting.clave
                value = setting.valor
                # Try to parse JSON values
                try:
                    config[key] = json.loads(value) if value else None
                except (json.JSONDecodeError, TypeError):
                    config[key] = value

            return config
        except Exception as e:
            logger.error(f"Error getting gym config: {e}")
            return {}

    def actualizar_configuracion_gimnasio(self, updates: Dict[str, Any]) -> bool:
        """Update gym configuration (handles both GymConfig and Configuracion tables)."""
        try:
            # Separate updates for GymConfig vs generic Configuracion
            gym_config_fields = [
                'gym_name', 'gym_slogan', 'gym_address', 'gym_phone', 
                'gym_email', 'gym_website', 'facebook', 'instagram', 
                'twitter', 'logo_url'
            ]
            
            gym_updates = {k: v for k, v in updates.items() if k in gym_config_fields}
            generic_updates = {k: v for k, v in updates.items() if k not in gym_config_fields}

            # 1. Update GymConfig table
            if gym_updates:
                gym_info = self.db.execute(select(GymConfig).limit(1)).scalar_one_or_none()
                if not gym_info:
                    gym_info = GymConfig()
                    self.db.add(gym_info)
                
                for key, value in gym_updates.items():
                    setattr(gym_info, key, value)

            # 2. Update Configuracion table
            for key, value in generic_updates.items():
                valor = json.dumps(value) if not isinstance(value, str) else value
                stmt = insert(Configuracion).values(
                    clave=key, 
                    valor=valor
                ).on_conflict_do_update(
                    index_elements=['clave'],
                    set_={'valor': valor}
                )
                self.db.execute(stmt)

            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating gym config: {e}")
            self.db.rollback()
            return False

    def actualizar_configuracion(self, clave: str, valor: str) -> bool:
        """Update a single configuration value."""
        return self.actualizar_configuracion_gimnasio({clave: valor})

    def actualizar_logo_url(self, url: str) -> bool:
        """Update gym logo URL."""
        # Using the GymConfig field 'logo_url' AND legacy 'gym_logo_url' key for compatibility
        return self.actualizar_configuracion_gimnasio({
            'logo_url': url,
            'gym_logo_url': url
        })

    # =========================================================================
    # THEMES (CustomTheme & ThemeSchedule)
    # =========================================================================

    def obtener_temas(self) -> list[CustomTheme]:
        """Obtener todos los temas personalizados."""
        return self.db.scalars(select(CustomTheme)).all()

    def obtener_tema(self, tema_id: int) -> Optional[CustomTheme]:
        """Obtener un tema por ID."""
        return self.db.get(CustomTheme, tema_id)

    def crear_tema(self, datos: Dict[str, Any]) -> CustomTheme:
        """Crear un nuevo tema."""
        tema = CustomTheme(
            nombre=datos['nombre'],
            name=datos['name'],
            colores=datos['colores'],
            activo=datos.get('activo', True),
            usuario_creador_id=datos.get('usuario_creador_id')
        )
        self.db.add(tema)
        self.db.commit()
        return tema

    # =========================================================================
    # SUBSCRIPTION STATUS (Admin DB Integration)
    # =========================================================================

    def get_subscription_status(self) -> Dict[str, Any]:
        """
        Get gym subscription status from Admin DB.
        """
        try:
            from src.dependencies import get_current_tenant
            from src.database.connection import AdminSessionLocal
            
            tenant = get_current_tenant()
            if not tenant:
                return {}

            admin_db = AdminSessionLocal()
            try:
                # 1. Get Gym ID
                row = admin_db.execute(
                    text("SELECT id, nombre FROM gyms WHERE subdominio = :sub"),
                    {"sub": tenant}
                ).fetchone()
                
                if not row:
                    return {}
                
                gym_id = row[0]
                
                # 2. Get Active Subscription
                sub_row = admin_db.execute(
                    text("""
                        SELECT p.name, gs.status, gs.next_due_date, gs.start_date
                        FROM gym_subscriptions gs
                        JOIN plans p ON p.id = gs.plan_id
                        WHERE gs.gym_id = :gym_id AND gs.status = 'active'
                        ORDER BY gs.id DESC
                        LIMIT 1
                    """),
                    {"gym_id": gym_id}
                ).fetchone()
                
                if not sub_row:
                    return {"status": "inactive", "plan": "None"}
                
                # Calculate days remaining
                days_remaining = None
                valid_until = None
                if sub_row[2]:
                    today = datetime.now().date()
                    due_date = sub_row[2] # might be date or datetime
                    if isinstance(due_date, datetime):
                        due_date = due_date.date()
                    
                    days_remaining = (due_date - today).days
                    valid_until = str(due_date)

                return {
                    "plan": sub_row[0],
                    "status": sub_row[1],
                    "valid_until": valid_until,
                    "days_remaining": days_remaining,
                    "start_date": str(sub_row[3]) if sub_row[3] else None
                }
            finally:
                admin_db.close()
        except Exception as e:
            logger.error(f"Error getting subscription status: {e}")
            return {}
