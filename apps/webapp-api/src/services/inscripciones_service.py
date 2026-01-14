"""
Inscripciones Service - SQLAlchemy ORM Implementation

Provides class enrollment, schedule, and waitlist operations using SQLAlchemy.
Replaces raw SQL usage in inscripciones.py with proper ORM queries.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
import os

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
import logging

from sqlalchemy.orm import Session
from sqlalchemy import text

from src.services.base import BaseService

logger = logging.getLogger(__name__)


class InscripcionesService(BaseService):
    """Service for class enrollments and schedule management."""

    def __init__(self, db: Session):
        super().__init__(db)
        self.ensure_tables()

    def _get_app_timezone(self):
        tz_name = (
            os.getenv("APP_TIMEZONE")
            or os.getenv("TIMEZONE")
            or os.getenv("TZ")
            or "America/Argentina/Buenos_Aires"
        )
        if ZoneInfo is not None:
            try:
                return ZoneInfo(tz_name)
            except Exception:
                pass
        return timezone(timedelta(hours=-3))

    def _now_utc_naive(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def _clase_exists(self, clase_id: int) -> bool:
        try:
            row = self.db.execute(text("SELECT 1 FROM clases WHERE id = :id LIMIT 1"), {'id': int(clase_id)}).fetchone()
            return bool(row)
        except Exception:
            return False

    def _get_horario_profesor_id(self, horario_id: int) -> Optional[int]:
        try:
            row = self.db.execute(text("SELECT profesor_id FROM clase_horarios WHERE id = :id LIMIT 1"), {'id': int(horario_id)}).fetchone()
            if row and row[0] is not None:
                return int(row[0])
        except Exception:
            pass
        return None

    def _horario_exists(self, horario_id: int) -> bool:
        try:
            row = self.db.execute(text("SELECT 1 FROM clase_horarios WHERE id = :id LIMIT 1"), {'id': int(horario_id)}).fetchone()
            return bool(row)
        except Exception:
            return False

    def _horario_belongs_to_clase(self, horario_id: int, clase_id: int) -> bool:
        try:
            row = self.db.execute(
                text("SELECT 1 FROM clase_horarios WHERE id = :id AND clase_id = :clase_id LIMIT 1"),
                {'id': int(horario_id), 'clase_id': int(clase_id)}
            ).fetchone()
            return bool(row)
        except Exception:
            return False

    def ensure_tables(self) -> None:
        """Ensure all inscripciones-related tables exist."""
        try:
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS clase_horarios (
                    id SERIAL PRIMARY KEY,
                    clase_id INTEGER NOT NULL,
                    dia VARCHAR(20) NOT NULL,
                    hora_inicio TIME NOT NULL,
                    hora_fin TIME NOT NULL,
                    profesor_id INTEGER,
                    cupo INTEGER DEFAULT 20,
                    created_at TIMESTAMP
                )
            """))
            self.db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_clase_horarios_cid ON clase_horarios(clase_id)
            """))
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS clase_tipos (
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(100) NOT NULL,
                    color VARCHAR(20),
                    activo BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP
                )
            """))
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS inscripciones (
                    id SERIAL PRIMARY KEY,
                    horario_id INTEGER NOT NULL,
                    usuario_id INTEGER NOT NULL,
                    fecha_inscripcion TIMESTAMP,
                    UNIQUE(horario_id, usuario_id)
                )
            """))
            self.db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_inscripciones_hid ON inscripciones(horario_id)
            """))
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS lista_espera (
                    id SERIAL PRIMARY KEY,
                    horario_id INTEGER NOT NULL,
                    usuario_id INTEGER NOT NULL,
                    posicion INTEGER NOT NULL DEFAULT 1,
                    fecha_registro TIMESTAMP,
                    UNIQUE(horario_id, usuario_id)
                )
            """))
            self.db.commit()
        except Exception as e:
            logger.error(f"Error ensuring inscripciones tables: {e}")
            self.db.rollback()

    # ========== Clase Tipos ==========

    def obtener_tipos(self) -> List[Dict[str, Any]]:
        """Get all active class types."""
        try:
            result = self.db.execute(text("""
                SELECT id, nombre, color, activo 
                FROM clase_tipos WHERE activo = TRUE ORDER BY nombre
            """))
            return [{'id': r[0], 'nombre': r[1], 'color': r[2], 'activo': r[3]} for r in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting class types: {e}")
            return []

    def crear_tipo(self, nombre: str, color: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Create a class type."""
        try:
            result = self.db.execute(
                text("INSERT INTO clase_tipos (nombre, color) VALUES (:nombre, :color) RETURNING id, nombre, color, activo"),
                {'nombre': nombre, 'color': color}
            )
            row = result.fetchone()
            self.db.commit()
            return {'id': row[0], 'nombre': row[1], 'color': row[2], 'activo': row[3]} if row else None
        except Exception as e:
            logger.error(f"Error creating class type: {e}")
            self.db.rollback()
            return None

    def eliminar_tipo(self, tipo_id: int) -> bool:
        """Soft delete a class type."""
        try:
            self.db.execute(text("UPDATE clase_tipos SET activo = FALSE WHERE id = :id"), {'id': tipo_id})
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting class type: {e}")
            self.db.rollback()
            return False

    # ========== Clase Horarios ==========

    def obtener_horarios(self, clase_id: int) -> List[Dict[str, Any]]:
        """Get schedules for a class."""
        try:
            result = self.db.execute(
                text("""
                    SELECT ch.id, ch.clase_id, ch.dia,
                           TO_CHAR(ch.hora_inicio, 'HH24:MI') as hora_inicio,
                           TO_CHAR(ch.hora_fin, 'HH24:MI') as hora_fin,
                           ch.profesor_id, ch.cupo,
                           COALESCE(u.nombre,'') as profesor_nombre,
                           (SELECT COUNT(*) FROM inscripciones i WHERE i.horario_id = ch.id) as inscriptos_count
                    FROM clase_horarios ch
                    LEFT JOIN profesores p ON ch.profesor_id = p.id
                    LEFT JOIN usuarios u ON u.id = p.usuario_id
                    WHERE ch.clase_id = :clase_id
                    ORDER BY 
                        CASE ch.dia 
                            WHEN 'lunes' THEN 1 WHEN 'martes' THEN 2 WHEN 'miércoles' THEN 3 
                            WHEN 'jueves' THEN 4 WHEN 'viernes' THEN 5 WHEN 'sábado' THEN 6 WHEN 'domingo' THEN 7 
                        END, ch.hora_inicio
                """),
                {'clase_id': clase_id}
            )
            return [
                {'id': r[0], 'clase_id': r[1], 'dia': r[2], 'hora_inicio': r[3], 'hora_fin': r[4],
                 'profesor_id': r[5], 'cupo': r[6], 'profesor_nombre': r[7], 'inscriptos_count': r[8]}
                for r in result.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting schedules: {e}")
            return []

    def crear_horario(self, clase_id: int, dia: str, hora_inicio: str, hora_fin: str, 
                      profesor_id: Optional[int] = None, cupo: int = 20) -> Optional[Dict[str, Any]]:
        """Create a class schedule."""
        try:
            if not self._clase_exists(int(clase_id)):
                return None
            result = self.db.execute(
                text("""
                    INSERT INTO clase_horarios (clase_id, dia, hora_inicio, hora_fin, profesor_id, cupo)
                    VALUES (:clase_id, :dia, :hora_inicio, :hora_fin, :profesor_id, :cupo)
                    RETURNING id, clase_id, dia, TO_CHAR(hora_inicio, 'HH24:MI') as hora_inicio,
                              TO_CHAR(hora_fin, 'HH24:MI') as hora_fin, profesor_id, cupo
                """),
                {'clase_id': clase_id, 'dia': dia.lower(), 'hora_inicio': hora_inicio, 
                 'hora_fin': hora_fin, 'profesor_id': profesor_id, 'cupo': cupo}
            )
            row = result.fetchone()
            self.db.commit()
            return {'id': row[0], 'clase_id': row[1], 'dia': row[2], 'hora_inicio': row[3],
                    'hora_fin': row[4], 'profesor_id': row[5], 'cupo': row[6]} if row else None
        except Exception as e:
            logger.error(f"Error creating schedule: {e}")
            self.db.rollback()
            return None

    def actualizar_horario(self, horario_id: int, clase_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a class schedule."""
        try:
            # Ensure horario exists for that clase
            if not self._horario_belongs_to_clase(int(horario_id), int(clase_id)):
                return None

            sets = []
            params = {'id': horario_id, 'clase_id': clase_id}
            if 'dia' in updates:
                sets.append("dia = :dia")
                params['dia'] = (updates['dia'] or '').lower()
            if 'hora_inicio' in updates:
                sets.append("hora_inicio = :hora_inicio")
                params['hora_inicio'] = updates['hora_inicio']
            if 'hora_fin' in updates:
                sets.append("hora_fin = :hora_fin")
                params['hora_fin'] = updates['hora_fin']
            if 'profesor_id' in updates:
                sets.append("profesor_id = :profesor_id")
                params['profesor_id'] = updates['profesor_id']
            if 'cupo' in updates:
                sets.append("cupo = :cupo")
                params['cupo'] = int(updates['cupo']) if updates['cupo'] else 20
            
            if not sets:
                # No updates requested but horario exists
                return {'ok': True}
            
            result = self.db.execute(
                text(f"""
                    UPDATE clase_horarios SET {', '.join(sets)}
                    WHERE id = :id AND clase_id = :clase_id
                    RETURNING id, clase_id, dia, TO_CHAR(hora_inicio, 'HH24:MI') as hora_inicio,
                              TO_CHAR(hora_fin, 'HH24:MI') as hora_fin, profesor_id, cupo
                """),
                params
            )
            row = result.fetchone()
            self.db.commit()
            if not row:
                return None
            return {
                'id': row[0],
                'clase_id': row[1],
                'dia': row[2],
                'hora_inicio': row[3],
                'hora_fin': row[4],
                'profesor_id': row[5],
                'cupo': row[6]
            }
        except Exception as e:
            logger.error(f"Error updating schedule: {e}")
            self.db.rollback()
            return None

    def eliminar_horario(self, horario_id: int, clase_id: int) -> bool:
        """Delete a class schedule and its enrollments."""
        try:
            if not self._horario_belongs_to_clase(int(horario_id), int(clase_id)):
                return False

            self.db.execute(text("DELETE FROM inscripciones WHERE horario_id = :id"), {'id': int(horario_id)})
            self.db.execute(text("DELETE FROM lista_espera WHERE horario_id = :id"), {'id': int(horario_id)})
            res = self.db.execute(
                text("DELETE FROM clase_horarios WHERE id = :id AND clase_id = :clase_id"),
                {'id': int(horario_id), 'clase_id': int(clase_id)}
            )
            self.db.commit()
            try:
                return (getattr(res, 'rowcount', 0) or 0) > 0
            except Exception:
                return True
        except Exception as e:
            logger.error(f"Error deleting schedule: {e}")
            self.db.rollback()
            return False

    # ========== Inscripciones ==========

    def obtener_inscripciones(self, horario_id: int) -> List[Dict[str, Any]]:
        """Get enrollments for a schedule."""
        try:
            result = self.db.execute(
                text("""
                    SELECT i.id, i.horario_id, i.usuario_id, i.fecha_inscripcion,
                           u.nombre as usuario_nombre, u.telefono as usuario_telefono
                    FROM inscripciones i
                    JOIN usuarios u ON i.usuario_id = u.id
                    WHERE i.horario_id = :horario_id ORDER BY i.fecha_inscripcion
                """),
                {'horario_id': horario_id}
            )
            return [
                {'id': r[0], 'horario_id': r[1], 'usuario_id': r[2], 
                 'fecha_inscripcion': r[3].isoformat() if r[3] else None,
                 'usuario_nombre': r[4], 'usuario_telefono': r[5]}
                for r in result.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting enrollments: {e}")
            return []

    def crear_inscripcion(self, horario_id: int, usuario_id: int) -> Dict[str, Any]:
        """Enroll a user in a schedule."""
        try:
            fecha_inscripcion = self._now_utc_naive()
            # Check capacity
            cap = self.db.execute(
                text("""SELECT cupo, (SELECT COUNT(*) FROM inscripciones WHERE horario_id = :id) as inscriptos
                        FROM clase_horarios WHERE id = :id"""),
                {'id': horario_id}
            ).fetchone()

            if not cap:
                return {'error': 'Horario no encontrado'}
            
            if cap:
                cupo = cap[0] or 20
                inscriptos = cap[1] or 0
                if inscriptos >= cupo:
                    return {'error': 'Cupo lleno', 'full': True}
            
            result = self.db.execute(
                text("""INSERT INTO inscripciones (horario_id, usuario_id, fecha_inscripcion) VALUES (:horario_id, :usuario_id, :fecha_inscripcion)
                        ON CONFLICT (horario_id, usuario_id) DO NOTHING RETURNING id, horario_id, usuario_id, fecha_inscripcion"""),
                {'horario_id': horario_id, 'usuario_id': usuario_id, 'fecha_inscripcion': fecha_inscripcion}
            )
            row = result.fetchone()
            self.db.commit()
            
            if row:
                return {'id': row[0], 'horario_id': row[1], 'usuario_id': row[2],
                        'fecha_inscripcion': row[3].isoformat() if row[3] else None}
            return {'ok': True, 'message': 'Ya está inscripto'}
        except Exception as e:
            logger.error(f"Error creating enrollment: {e}")
            self.db.rollback()
            return {'error': str(e)}

    def eliminar_inscripcion(self, horario_id: int, usuario_id: int) -> bool:
        """Remove enrollment."""
        try:
            self.db.execute(text("DELETE FROM inscripciones WHERE horario_id = :hid AND usuario_id = :uid"),
                          {'hid': horario_id, 'uid': usuario_id})
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting enrollment: {e}")
            self.db.rollback()
            return False

    # ========== Lista de Espera ==========

    def obtener_lista_espera(self, horario_id: int) -> List[Dict[str, Any]]:
        """Get waitlist for a schedule."""
        try:
            result = self.db.execute(
                text("""
                    SELECT le.id, le.horario_id, le.usuario_id, le.posicion, le.fecha_registro,
                           u.nombre as usuario_nombre
                    FROM lista_espera le JOIN usuarios u ON le.usuario_id = u.id
                    WHERE le.horario_id = :horario_id ORDER BY le.posicion
                """),
                {'horario_id': horario_id}
            )
            return [
                {'id': r[0], 'horario_id': r[1], 'usuario_id': r[2], 'posicion': r[3],
                 'fecha_registro': r[4].isoformat() if r[4] else None, 'usuario_nombre': r[5]}
                for r in result.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting waitlist: {e}")
            return []

    def agregar_lista_espera(self, horario_id: int, usuario_id: int) -> Dict[str, Any]:
        """Add user to waitlist."""
        try:
            if not self._horario_exists(int(horario_id)):
                return {'error': 'Horario no encontrado'}
            fecha_registro = self._now_utc_naive()
            pos = self.db.execute(
                text("SELECT COALESCE(MAX(posicion), 0) + 1 FROM lista_espera WHERE horario_id = :id"),
                {'id': horario_id}
            ).fetchone()
            next_pos = pos[0] if pos else 1
            
            result = self.db.execute(
                text("""INSERT INTO lista_espera (horario_id, usuario_id, posicion, fecha_registro) VALUES (:hid, :uid, :pos, :fecha_registro)
                        ON CONFLICT (horario_id, usuario_id) DO NOTHING 
                        RETURNING id, horario_id, usuario_id, posicion, fecha_registro"""),
                {'hid': horario_id, 'uid': usuario_id, 'pos': next_pos, 'fecha_registro': fecha_registro}
            )
            row = result.fetchone()
            self.db.commit()
            
            if row:
                return {'id': row[0], 'horario_id': row[1], 'usuario_id': row[2], 'posicion': row[3],
                        'fecha_registro': row[4].isoformat() if row[4] else None}
            return {'ok': True, 'message': 'Ya está en lista de espera'}
        except Exception as e:
            logger.error(f"Error adding to waitlist: {e}")
            self.db.rollback()
            return {'error': str(e)}

    def eliminar_lista_espera(self, horario_id: int, usuario_id: int) -> bool:
        """Remove from waitlist."""
        try:
            self.db.execute(text("DELETE FROM lista_espera WHERE horario_id = :hid AND usuario_id = :uid"),
                          {'hid': horario_id, 'uid': usuario_id})
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error removing from waitlist: {e}")
            self.db.rollback()
            return False

    def obtener_primero_lista_espera(self, horario_id: int) -> Optional[Dict[str, Any]]:
        """Get first person in waitlist."""
        try:
            result = self.db.execute(
                text("""SELECT le.usuario_id, u.nombre, u.telefono FROM lista_espera le
                        JOIN usuarios u ON le.usuario_id = u.id WHERE le.horario_id = :id ORDER BY le.posicion LIMIT 1"""),
                {'id': horario_id}
            )
            row = result.fetchone()
            return {'usuario_id': row[0], 'nombre': row[1], 'telefono': row[2]} if row else None
        except Exception as e:
            logger.error(f"Error getting first in waitlist: {e}")
            return None

    # ========== Clase Ejercicios ==========

    def obtener_clase_ejercicios(self, clase_id: int) -> List[Dict[str, Any]]:
        """Get exercises linked to a class."""
        try:
            result = self.db.execute(
                text("""
                    SELECT DISTINCT ON (cbi.ejercicio_id) cbi.ejercicio_id, e.nombre as ejercicio_nombre, cbi.orden
                    FROM clase_bloques cb JOIN clase_bloque_items cbi ON cb.id = cbi.bloque_id
                    LEFT JOIN ejercicios e ON cbi.ejercicio_id = e.id
                    WHERE cb.clase_id = :clase_id ORDER BY cbi.ejercicio_id, cbi.orden
                """),
                {'clase_id': clase_id}
            )
            return [{'ejercicio_id': r[0], 'ejercicio_nombre': r[1], 'orden': r[2]} for r in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting class exercises: {e}")
            return []

    def actualizar_clase_ejercicios(self, clase_id: int, ejercicio_ids: List[int]) -> bool:
        """Update exercises for a class."""
        try:
            # Get or create default bloque
            bloque = self.db.execute(text("SELECT id FROM clase_bloques WHERE clase_id = :id LIMIT 1"),
                                    {'id': clase_id}).fetchone()
            if bloque:
                bloque_id = bloque[0]
            else:
                result = self.db.execute(
                    text("INSERT INTO clase_bloques (clase_id, nombre) VALUES (:id, 'Ejercicios') RETURNING id"),
                    {'id': clase_id}
                )
                bloque_id = result.fetchone()[0]
            
            self.db.execute(text("DELETE FROM clase_bloque_items WHERE bloque_id = :id"), {'id': bloque_id})
            
            for idx, eid in enumerate(ejercicio_ids):
                self.db.execute(
                    text("INSERT INTO clase_bloque_items (bloque_id, ejercicio_id, orden) VALUES (:bid, :eid, :idx)"),
                    {'bid': bloque_id, 'eid': int(eid), 'idx': idx}
                )
            
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating class exercises: {e}")
            self.db.rollback()
            return False
