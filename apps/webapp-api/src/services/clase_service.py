"""
Clase Service - SQLAlchemy ORM Implementation

Handles classes (Clase) and schedule blocks (ClaseBloque, ClaseBloqueItem).
Replaces legacy GymService class management methods.
"""

import logging
from typing import List, Dict, Any, Optional

from sqlalchemy import select, delete
from sqlalchemy.orm import Session, joinedload

from src.services.base import BaseService
from src.database.orm_models import Clase, ClaseBloque, ClaseBloqueItem

logger = logging.getLogger(__name__)


class ClaseService(BaseService):
    """Service for managing classes and their schedule blocks."""

    def __init__(self, db: Session):
        super().__init__(db)

    def _scope_by_sucursal(self, stmt, model, sucursal_id: Optional[int]):
        if sucursal_id is None:
            return stmt
        try:
            sid = int(sucursal_id)
        except Exception:
            return stmt
        if sid <= 0:
            return stmt
        try:
            col = getattr(model, "sucursal_id", None)
        except Exception:
            col = None
        if col is None:
            return stmt
        return stmt.where((col.is_(None)) | (col == sid))

    # =========================================================================
    # CLASES (Classes)
    # =========================================================================

    def obtener_clases(self, sucursal_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all classes."""
        try:
            stmt = select(Clase).order_by(Clase.nombre)
            stmt = self._scope_by_sucursal(stmt, Clase, sucursal_id)
            clases = self.db.scalars(stmt).all()
            return [
                {
                    "id": c.id,
                    "nombre": c.nombre,
                    "descripcion": c.descripcion,
                    "activo": c.activa,
                    # Fallback for fields that might be missing in older schemas but present in API expectations
                    "capacidad": getattr(c, "capacidad", None),
                    "color": getattr(c, "color", "#3498db"),
                    "icono": getattr(c, "icono", None),
                    "duracion_minutos": getattr(c, "duracion_minutos", 60),
                }
                for c in clases
            ]
        except Exception as e:
            logger.error(f"Error getting clases: {e}")
            return []

    def obtener_clase(self, clase_id: int, sucursal_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get a single class by ID."""
        try:
            clase = self.db.get(Clase, clase_id)
            if not clase:
                return None
            if sucursal_id is not None and hasattr(clase, "sucursal_id"):
                try:
                    sid = int(sucursal_id)
                except Exception:
                    sid = None
                if sid is not None and sid > 0:
                    try:
                        own_sid = getattr(clase, "sucursal_id", None)
                        if own_sid is not None and int(own_sid) != sid:
                            return None
                    except Exception:
                        pass
            return {
                "id": clase.id,
                "nombre": clase.nombre,
                "descripcion": clase.descripcion,
                "activo": clase.activa,
                "capacidad": getattr(clase, "capacidad", None),
                "color": getattr(clase, "color", "#3498db"),
                "icono": getattr(clase, "icono", None),
                "duracion_minutos": getattr(clase, "duracion_minutos", 60),
            }
        except Exception as e:
            logger.error(f"Error getting clase {clase_id}: {e}")
            return None

    def crear_clase(self, data: Dict[str, Any]) -> Optional[int]:
        """Create a new class."""
        try:
            # We must be careful to only set fields that exist on the ORM model
            # or ensure the ORM model has these fields mixed in / dynamically added if schema differs
            # For now, we assume ORM model is authoritative but legacy code used extra fields.
            # We will try to set them if the model supports them.

            clase = Clase(
                nombre=data.get("nombre", ""),
                descripcion=data.get("descripcion"),
                activa=data.get("activo", True),
            )
            if hasattr(Clase, "sucursal_id") and "sucursal_id" in data:
                clase.sucursal_id = data.get("sucursal_id")
            # Optional attributes that might not be in standard ORM but used by Frontend
            # Check if model has them before setting
            if hasattr(Clase, "capacidad"):
                clase.capacidad = data.get("capacidad")
            if hasattr(Clase, "color"):
                clase.color = data.get("color", "#3498db")
            if hasattr(Clase, "icono"):
                clase.icono = data.get("icono")
            if hasattr(Clase, "duracion_minutos"):
                clase.duracion_minutos = data.get("duracion_minutos", 60)

            self.db.add(clase)
            self.db.commit()
            return clase.id
        except Exception as e:
            logger.error(f"Error creating clase: {e}")
            self.db.rollback()
            return None

    def actualizar_clase(self, clase_id: int, data: Dict[str, Any]) -> bool:
        """Update a class."""
        try:
            clase = self.db.get(Clase, clase_id)
            if not clase:
                return False

            if "nombre" in data:
                clase.nombre = data["nombre"]
            if "descripcion" in data:
                clase.descripcion = data["descripcion"]
            if "activo" in data:
                clase.activa = data["activo"]
            if hasattr(clase, "sucursal_id"):
                if "shared" in data:
                    try:
                        if bool(data.get("shared")):
                            clase.sucursal_id = None
                    except Exception:
                        pass
                if "sucursal_id" in data:
                    clase.sucursal_id = data.get("sucursal_id")

            # Optional fields
            if "capacidad" in data and hasattr(clase, "capacidad"):
                clase.capacidad = data["capacidad"]
            if "color" in data and hasattr(clase, "color"):
                clase.color = data["color"]
            if "icono" in data and hasattr(clase, "icono"):
                clase.icono = data["icono"]
            if "duracion_minutos" in data and hasattr(clase, "duracion_minutos"):
                clase.duracion_minutos = data["duracion_minutos"]

            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating clase {clase_id}: {e}")
            self.db.rollback()
            return False

    def eliminar_clase(self, clase_id: int) -> bool:
        """Delete a class."""
        try:
            clase = self.db.get(Clase, clase_id)
            if not clase:
                return False
            self.db.delete(clase)
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting clase {clase_id}: {e}")
            self.db.rollback()
            return False

    # =========================================================================
    # BLOQUES (Schedule Blocks)
    # =========================================================================

    def obtener_clase_bloques(self, clase_id: int) -> List[Dict[str, Any]]:
        """Get schedule blocks for a class (Alias for router compatibility)."""
        return self.obtener_bloques_clase(clase_id)

    def obtener_bloques_clase(self, clase_id: int) -> List[Dict[str, Any]]:
        """Get schedule blocks for a class."""
        try:
            bloques = self.db.scalars(
                select(ClaseBloque)
                .where(ClaseBloque.clase_id == clase_id)
                .order_by(ClaseBloque.id)  # Order by ID by default
            ).all()

            results = []
            for b in bloques:
                results.append({"id": b.id, "clase_id": b.clase_id, "nombre": b.nombre})
            return results
        except Exception as e:
            logger.error(f"Error getting bloques: {e}")
            return []

    def crear_clase_bloque(
        self, clase_id: int, nombre: str, items: List[Dict[str, Any]]
    ) -> Optional[int]:
        """Create a new schedule block with items."""
        try:
            # Ensure class exists before creating child records
            clase = self.db.get(Clase, clase_id)
            if not clase:
                return None

            bloque = ClaseBloque(clase_id=clase_id, nombre=nombre)
            self.db.add(bloque)
            self.db.flush()  # Get ID

            for it in items:
                b_item = ClaseBloqueItem(
                    bloque_id=bloque.id,
                    ejercicio_id=it.get("ejercicio_id"),
                    orden=it.get("orden", 0),
                    series=it.get("series", 0),
                    repeticiones=it.get("repeticiones"),
                    descanso_segundos=it.get("descanso_segundos", 0),
                    notas=it.get("notas"),
                )
                self.db.add(b_item)

            self.db.commit()
            return bloque.id
        except Exception as e:
            logger.error(f"Error creating bloque: {e}")
            self.db.rollback()
            return None

    def actualizar_clase_bloque(
        self, bloque_id: int, nombre: str, items: List[Dict[str, Any]]
    ) -> bool:
        """Update a workout block and its items."""
        try:
            bloque = self.db.get(ClaseBloque, bloque_id)
            if not bloque:
                return False

            if nombre:
                bloque.nombre = nombre

            # Replace items: Delete existing, add new
            # This is a simple strategy; could be optimized to strict diff but replacement is safer for consistency
            self.db.execute(
                delete(ClaseBloqueItem).where(ClaseBloqueItem.bloque_id == bloque_id)
            )

            for it in items:
                b_item = ClaseBloqueItem(
                    bloque_id=bloque.id,
                    ejercicio_id=it.get("ejercicio_id"),
                    orden=it.get("orden", 0),
                    series=it.get("series", 0),
                    repeticiones=it.get("repeticiones"),
                    descanso_segundos=it.get("descanso_segundos", 0),
                    notas=it.get("notas"),
                )
                self.db.add(b_item)

            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating bloque: {e}")
            self.db.rollback()
            return False

    def eliminar_clase_bloque(self, bloque_id: int) -> bool:
        """Delete a schedule block."""
        try:
            bloque = self.db.get(ClaseBloque, bloque_id)
            if not bloque:
                return False
            self.db.delete(bloque)
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting bloque: {e}")
            self.db.rollback()
            return False

    def obtener_bloque_items(
        self, clase_id: int, bloque_id: int
    ) -> Optional[List[Dict[str, Any]]]:
        """Get items in a block (Alias for router compatibility)."""
        try:
            bloque = self.db.get(ClaseBloque, bloque_id)
            if not bloque or int(getattr(bloque, "clase_id", 0) or 0) != int(clase_id):
                return None
        except Exception:
            return None
        return self.obtener_items_bloque(bloque_id)

    def obtener_items_bloque(self, bloque_id: int) -> List[Dict[str, Any]]:
        """Get items/exercises in a schedule block."""
        try:
            items = self.db.scalars(
                select(ClaseBloqueItem)
                .options(joinedload(ClaseBloqueItem.ejercicio))
                .where(ClaseBloqueItem.bloque_id == bloque_id)
                .order_by(ClaseBloqueItem.orden)
            ).all()

            return [
                {
                    "id": i.id,
                    "bloque_id": i.bloque_id,
                    "ejercicio_id": i.ejercicio_id,
                    "nombre_ejercicio": i.ejercicio.nombre
                    if i.ejercicio
                    else "Unknown",
                    "orden": i.orden,
                    "series": i.series,
                    "repeticiones": i.repeticiones,
                    "descanso_segundos": i.descanso_segundos,
                    "notas": i.notas,
                }
                for i in items
            ]
        except Exception as e:
            logger.error(f"Error getting bloque items: {e}")
            return []
