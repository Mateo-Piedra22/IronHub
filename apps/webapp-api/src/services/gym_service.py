"""
Gym Service - SQLAlchemy ORM Implementation

Provides gym configuration and class management operations using SQLAlchemy ORM.
Replaces raw SQL usage in gym.py with proper ORM queries.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import json

from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete, text

from src.services.base import BaseService
from src.database.orm_models import Usuario

logger = logging.getLogger(__name__)


class GymService(BaseService):
    """Service for gym configuration and class management using SQLAlchemy."""

    def __init__(self, db: Session):
        super().__init__(db)

    # ========== Gym Configuration ==========

    def obtener_configuracion_gimnasio(self) -> Dict[str, Any]:
        """Get gym configuration."""
        try:
            result = self.db.execute(
                text("SELECT clave, valor FROM gym_config")
            )
            config = {}
            for row in result.fetchall():
                key = row[0]
                value = row[1]
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
        """Update gym configuration with multiple values."""
        try:
            for key, value in updates.items():
                valor = json.dumps(value) if not isinstance(value, str) else value
                self.db.execute(
                    text("""
                        INSERT INTO gym_config (clave, valor)
                        VALUES (:clave, :valor)
                        ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor
                    """),
                    {'clave': key, 'valor': valor}
                )
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
        return self.actualizar_configuracion('gym_logo_url', url)

    def get_table_columns(self, table_name: str) -> List[str]:
        """Get column names for a table."""
        try:
            result = self.db.execute(
                text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = :table_name
                """),
                {'table_name': table_name}
            )
            return [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting table columns: {e}")
            return []

    # ========== Clases (Classes) ==========

    def obtener_clases(self) -> List[Dict[str, Any]]:
        """Get all classes."""
        try:
            result = self.db.execute(
                text("""
                    SELECT id, nombre, descripcion, activo, capacidad, 
                           color, icono, duracion_minutos
                    FROM clases
                    ORDER BY nombre
                """)
            )
            return [
                {
                    'id': row[0],
                    'nombre': row[1],
                    'descripcion': row[2],
                    'activo': row[3],
                    'capacidad': row[4],
                    'color': row[5],
                    'icono': row[6],
                    'duracion_minutos': row[7]
                }
                for row in result.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting clases: {e}")
            return []

    def crear_clase(self, data: Dict[str, Any]) -> Optional[int]:
        """Create a new class."""
        try:
            result = self.db.execute(
                text("""
                    INSERT INTO clases (nombre, descripcion, activo, capacidad, color, icono, duracion_minutos)
                    VALUES (:nombre, :descripcion, :activo, :capacidad, :color, :icono, :duracion)
                    RETURNING id
                """),
                {
                    'nombre': data.get('nombre', ''),
                    'descripcion': data.get('descripcion'),
                    'activo': data.get('activo', True),
                    'capacidad': data.get('capacidad'),
                    'color': data.get('color', '#3498db'),
                    'icono': data.get('icono'),
                    'duracion': data.get('duracion_minutos', 60)
                }
            )
            row = result.fetchone()
            self.db.commit()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Error creating clase: {e}")
            self.db.rollback()
            return None

    # ========== Bloques (Schedule Blocks) ==========

    def obtener_bloques_clase(self, clase_id: int) -> List[Dict[str, Any]]:
        """Get schedule blocks for a class."""
        try:
            result = self.db.execute(
                text("""
                    SELECT id, clase_id, nombre, dia_semana, hora_inicio, hora_fin, activo
                    FROM bloques_clase
                    WHERE clase_id = :clase_id
                    ORDER BY dia_semana, hora_inicio
                """),
                {'clase_id': clase_id}
            )
            return [
                {
                    'id': row[0],
                    'clase_id': row[1],
                    'nombre': row[2],
                    'dia_semana': row[3],
                    'hora_inicio': str(row[4]) if row[4] else None,
                    'hora_fin': str(row[5]) if row[5] else None,
                    'activo': row[6]
                }
                for row in result.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting bloques: {e}")
            return []

    def obtener_items_bloque(self, bloque_id: int) -> List[Dict[str, Any]]:
        """Get items/participants in a schedule block."""
        try:
            result = self.db.execute(
                text("""
                    SELECT bi.id, bi.bloque_id, bi.usuario_id, bi.fecha_inscripcion,
                           u.nombre as usuario_nombre, u.dni
                    FROM bloque_inscripciones bi
                    LEFT JOIN usuarios u ON bi.usuario_id = u.id
                    WHERE bi.bloque_id = :bloque_id
                    ORDER BY bi.fecha_inscripcion
                """),
                {'bloque_id': bloque_id}
            )
            return [
                {
                    'id': row[0],
                    'bloque_id': row[1],
                    'usuario_id': row[2],
                    'fecha_inscripcion': row[3].isoformat() if row[3] else None,
                    'usuario_nombre': row[4],
                    'dni': row[5]
                }
                for row in result.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting bloque items: {e}")
            return []

    def crear_bloque(self, clase_id: int, data: Dict[str, Any]) -> Optional[int]:
        """Create a new schedule block."""
        try:
            result = self.db.execute(
                text("""
                    INSERT INTO bloques_clase (clase_id, nombre, dia_semana, hora_inicio, hora_fin, activo)
                    VALUES (:clase_id, :nombre, :dia_semana, :hora_inicio, :hora_fin, :activo)
                    RETURNING id
                """),
                {
                    'clase_id': clase_id,
                    'nombre': data.get('nombre', ''),
                    'dia_semana': data.get('dia_semana', 1),
                    'hora_inicio': data.get('hora_inicio'),
                    'hora_fin': data.get('hora_fin'),
                    'activo': data.get('activo', True)
                }
            )
            row = result.fetchone()
            self.db.commit()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Error creating bloque: {e}")
            self.db.rollback()
            return None

    # ========== User Lookup ==========

    def obtener_usuario(self, usuario_id: int) -> Optional[Usuario]:
        """Get user by ID."""
        return self.db.get(Usuario, usuario_id)

    def obtener_usuario_por_id(self, usuario_id: int) -> Optional[Usuario]:
        """Alias for obtener_usuario."""
        return self.obtener_usuario(usuario_id)

    # ========== Ejercicios (Exercises) ==========

    def obtener_ejercicios_catalog(self) -> List[Dict[str, Any]]:
        """Get exercises catalog for routine building."""
        try:
            # Check what columns exist
            cols = self.get_table_columns('ejercicios')
            select_cols = ['id', 'nombre']
            if 'video_url' in cols:
                select_cols.append('video_url')
            if 'video_mime' in cols:
                select_cols.append('video_mime')
            if 'grupo_muscular' in cols:
                select_cols.append('grupo_muscular')
            
            result = self.db.execute(
                text(f"SELECT {', '.join(select_cols)} FROM ejercicios")
            )
            
            exercises = []
            for row in result.fetchall():
                exercise = {
                    'id': row[0],
                    'nombre': row[1],
                }
                idx = 2
                if 'video_url' in select_cols:
                    exercise['video_url'] = row[idx]
                    idx += 1
                if 'video_mime' in select_cols:
                    exercise['video_mime'] = row[idx]
                    idx += 1
                if 'grupo_muscular' in select_cols:
                    exercise['grupo_muscular'] = row[idx]
                exercises.append(exercise)
            
            return exercises
        except Exception as e:
            logger.error(f"Error getting ejercicios catalog: {e}")
            return []

    def obtener_ejercicios(self) -> List[Dict[str, Any]]:
        """Get all exercises for listing."""
        try:
            cols = self.get_table_columns('ejercicios')
            select_cols = ['id', 'nombre']
            if 'grupo_muscular' in cols:
                select_cols.append('grupo_muscular')
            if 'video_url' in cols:
                select_cols.append('video_url')
            if 'video_mime' in cols:
                select_cols.append('video_mime')
            if 'descripcion' in cols:
                select_cols.append('descripcion')
            
            result = self.db.execute(
                text(f"SELECT {', '.join(select_cols)} FROM ejercicios ORDER BY nombre")
            )
            
            exercises = []
            for row in result.fetchall():
                exercise = {'id': row[0], 'nombre': row[1]}
                idx = 2
                if 'grupo_muscular' in select_cols:
                    exercise['grupo_muscular'] = row[idx]
                    idx += 1
                if 'video_url' in select_cols:
                    exercise['video_url'] = row[idx]
                    idx += 1
                if 'video_mime' in select_cols:
                    exercise['video_mime'] = row[idx]
                    idx += 1
                if 'descripcion' in select_cols:
                    exercise['descripcion'] = row[idx]
                exercises.append(exercise)
            return exercises
        except Exception as e:
            logger.error(f"Error getting ejercicios: {e}")
            return []

    def crear_ejercicio(self, data: Dict[str, Any]) -> Optional[int]:
        """Create a new exercise."""
        try:
            result = self.db.execute(
                text("""
                    INSERT INTO ejercicios (nombre, grupo_muscular, video_url, video_mime)
                    VALUES (:nombre, :grupo, :video_url, :video_mime)
                    RETURNING id
                """),
                {
                    'nombre': data.get('nombre', ''),
                    'grupo': data.get('grupo_muscular'),
                    'video_url': data.get('video_url'),
                    'video_mime': data.get('video_mime')
                }
            )
            row = result.fetchone()
            self.db.commit()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Error creating ejercicio: {e}")
            self.db.rollback()
            return None

    def actualizar_ejercicio(self, ejercicio_id: int, data: Dict[str, Any]) -> bool:
        """Update an exercise."""
        try:
            sets = []
            params = {'id': ejercicio_id}
            if 'nombre' in data and data['nombre']:
                sets.append("nombre = :nombre")
                params['nombre'] = data['nombre']
            if 'grupo_muscular' in data:
                sets.append("grupo_muscular = :grupo")
                params['grupo'] = data['grupo_muscular']
            if 'video_url' in data:
                sets.append("video_url = :video_url")
                params['video_url'] = data['video_url']
            if 'video_mime' in data:
                sets.append("video_mime = :video_mime")
                params['video_mime'] = data['video_mime']
            
            if sets:
                self.db.execute(
                    text(f"UPDATE ejercicios SET {', '.join(sets)} WHERE id = :id"),
                    params
                )
                self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating ejercicio: {e}")
            self.db.rollback()
            return False

    def eliminar_ejercicio(self, ejercicio_id: int) -> bool:
        """Delete an exercise."""
        try:
            self.db.execute(
                text("DELETE FROM ejercicios WHERE id = :id"),
                {'id': ejercicio_id}
            )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting ejercicio: {e}")
            self.db.rollback()
            return False

    # ========== Rutinas (Basic) ==========

    def obtener_rutinas(self, usuario_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get routines, optionally filtered by user."""
        try:
            if usuario_id:
                result = self.db.execute(
                    text("""
                        SELECT id, nombre_rutina, descripcion, usuario_id, dias_semana, categoria, activa
                        FROM rutinas WHERE usuario_id = :usuario_id ORDER BY nombre_rutina
                    """),
                    {'usuario_id': usuario_id}
                )
            else:
                result = self.db.execute(
                    text("""
                        SELECT id, nombre_rutina, descripcion, usuario_id, dias_semana, categoria, activa
                        FROM rutinas ORDER BY nombre_rutina
                    """)
                )
            return [
                {
                    'id': row[0],
                    'nombre_rutina': row[1],
                    'descripcion': row[2],
                    'usuario_id': row[3],
                    'dias_semana': row[4],
                    'categoria': row[5],
                    'activa': row[6]
                }
                for row in result.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting rutinas: {e}")
            return []

    def crear_rutina(self, data: Dict[str, Any]) -> Optional[int]:
        """Create a new routine."""
        try:
            result = self.db.execute(
                text("""
                    INSERT INTO rutinas (nombre_rutina, descripcion, usuario_id, dias_semana, categoria, activa)
                    VALUES (:nombre, :descripcion, :usuario_id, :dias, :categoria, :activa)
                    RETURNING id
                """),
                {
                    'nombre': data.get('nombre_rutina', ''),
                    'descripcion': data.get('descripcion'),
                    'usuario_id': data.get('usuario_id'),
                    'dias': data.get('dias_semana', 1),
                    'categoria': data.get('categoria', 'general'),
                    'activa': data.get('activa', True)
                }
            )
            row = result.fetchone()
            self.db.commit()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Error creating rutina: {e}")
            self.db.rollback()
            return None

    # ========== Clase Bloques (Class Workout Blocks) ==========

    def ensure_clase_bloques_schema(self) -> None:
        """Ensure clase_bloques and clase_bloque_items tables exist."""
        try:
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS clase_bloques (
                    id SERIAL PRIMARY KEY,
                    clase_id INTEGER NOT NULL,
                    nombre TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            self.db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_clase_bloques_clase ON clase_bloques(clase_id)
            """))
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS clase_bloque_items (
                    id SERIAL PRIMARY KEY,
                    bloque_id INTEGER NOT NULL REFERENCES clase_bloques(id) ON DELETE CASCADE,
                    ejercicio_id INTEGER NOT NULL,
                    orden INTEGER NOT NULL DEFAULT 0,
                    series INTEGER DEFAULT 0,
                    repeticiones TEXT DEFAULT '',
                    descanso_segundos INTEGER DEFAULT 0,
                    notas TEXT DEFAULT ''
                )
            """))
            self.db.commit()
        except Exception as e:
            logger.error(f"Error ensuring clase_bloques schema: {e}")
            self.db.rollback()

    def obtener_clase_bloques(self, clase_id: int) -> List[Dict[str, Any]]:
        """Get workout blocks for a class."""
        try:
            self.ensure_clase_bloques_schema()
            result = self.db.execute(
                text("""
                    SELECT id, nombre FROM clase_bloques 
                    WHERE clase_id = :clase_id 
                    ORDER BY nombre ASC, id DESC
                """),
                {'clase_id': clase_id}
            )
            return [{'id': row[0], 'nombre': (row[1] or 'Bloque').strip()} for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting clase bloques: {e}")
            return []

    def obtener_bloque_items(self, clase_id: int, bloque_id: int) -> Optional[List[Dict[str, Any]]]:
        """Get items in a workout block. Returns None if bloque not found."""
        try:
            self.ensure_clase_bloques_schema()
            # Verify bloque exists and belongs to class
            check = self.db.execute(
                text("SELECT id FROM clase_bloques WHERE id = :bloque_id AND clase_id = :clase_id"),
                {'bloque_id': bloque_id, 'clase_id': clase_id}
            )
            if not check.fetchone():
                return None  # Not found
            
            result = self.db.execute(
                text("""
                    SELECT ejercicio_id, orden, series, repeticiones, descanso_segundos, notas
                    FROM clase_bloque_items
                    WHERE bloque_id = :bloque_id
                    ORDER BY orden ASC, id ASC
                """),
                {'bloque_id': bloque_id}
            )
            return [
                {
                    'ejercicio_id': row[0] or 0,
                    'orden': row[1] or 0,
                    'series': row[2] or 0,
                    'repeticiones': row[3] or '',
                    'descanso_segundos': row[4] or 0,
                    'notas': row[5] or ''
                }
                for row in result.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting bloque items: {e}")
            return []

    def crear_clase_bloque(self, clase_id: int, nombre: str, items: List[Dict]) -> Optional[int]:
        """Create a workout block with items."""
        try:
            self.ensure_clase_bloques_schema()
            result = self.db.execute(
                text("""
                    INSERT INTO clase_bloques (clase_id, nombre)
                    VALUES (:clase_id, :nombre)
                    RETURNING id
                """),
                {'clase_id': clase_id, 'nombre': nombre}
            )
            row = result.fetchone()
            if not row:
                return None
            bloque_id = row[0]
            
            # Insert items
            for idx, item in enumerate(items or []):
                self.db.execute(
                    text("""
                        INSERT INTO clase_bloque_items 
                        (bloque_id, ejercicio_id, orden, series, repeticiones, descanso_segundos, notas)
                        VALUES (:bloque_id, :ejercicio_id, :orden, :series, :repeticiones, :descanso, :notas)
                    """),
                    {
                        'bloque_id': bloque_id,
                        'ejercicio_id': item.get('ejercicio_id', 0),
                        'orden': item.get('orden', idx),
                        'series': item.get('series', 0),
                        'repeticiones': item.get('repeticiones', ''),
                        'descanso': item.get('descanso_segundos', 0),
                        'notas': item.get('notas', '')
                    }
                )
            
            self.db.commit()
            return bloque_id
        except Exception as e:
            logger.error(f"Error creating clase bloque: {e}")
            self.db.rollback()
            return None

    def actualizar_clase_bloque(self, bloque_id: int, nombre: str, items: List[Dict]) -> bool:
        """Update a workout block and its items."""
        try:
            self.ensure_clase_bloques_schema()
            # Update block name
            self.db.execute(
                text("UPDATE clase_bloques SET nombre = :nombre, updated_at = NOW() WHERE id = :id"),
                {'nombre': nombre, 'id': bloque_id}
            )
            # Delete old items and insert new
            self.db.execute(
                text("DELETE FROM clase_bloque_items WHERE bloque_id = :bloque_id"),
                {'bloque_id': bloque_id}
            )
            for idx, item in enumerate(items or []):
                self.db.execute(
                    text("""
                        INSERT INTO clase_bloque_items 
                        (bloque_id, ejercicio_id, orden, series, repeticiones, descanso_segundos, notas)
                        VALUES (:bloque_id, :ejercicio_id, :orden, :series, :repeticiones, :descanso, :notas)
                    """),
                    {
                        'bloque_id': bloque_id,
                        'ejercicio_id': item.get('ejercicio_id', 0),
                        'orden': item.get('orden', idx),
                        'series': item.get('series', 0),
                        'repeticiones': item.get('repeticiones', ''),
                        'descanso': item.get('descanso_segundos', 0),
                        'notas': item.get('notas', '')
                    }
                )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating clase bloque: {e}")
            self.db.rollback()
            return False

    def eliminar_clase_bloque(self, bloque_id: int) -> bool:
        """Delete a workout block."""
        try:
            self.db.execute(
                text("DELETE FROM clase_bloques WHERE id = :id"),
                {'id': bloque_id}
            )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting clase bloque: {e}")
            self.db.rollback()
            return False

    # ========== Subscription Info ==========

    def obtener_gym_subscription_info(self, subdomain: str) -> Dict[str, Any]:
        """Get gym subscription info from admin DB. Returns default if not found."""
        return {
            'active': True,
            'plan': 'pro',
            'source': 'default'
        }
