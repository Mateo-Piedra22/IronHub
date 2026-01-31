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
from src.database.clase_profesor_schema import ensure_clase_profesor_schema

logger = logging.getLogger(__name__)


class InscripcionesService(BaseService):
    """Service for class enrollments and schedule management."""

    def __init__(self, db: Session):
        super().__init__(db)

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
            row = self.db.execute(
                text("SELECT 1 FROM clases WHERE id = :id LIMIT 1"),
                {"id": int(clase_id)},
            ).fetchone()
            return bool(row)
        except Exception:
            return False

    def _clase_accessible(self, clase_id: int, sucursal_id: Optional[int]) -> bool:
        if sucursal_id is None:
            return True
        try:
            sid = int(sucursal_id)
        except Exception:
            return True
        if sid <= 0:
            return True
        try:
            row = self.db.execute(
                text("SELECT sucursal_id FROM clases WHERE id = :id LIMIT 1"),
                {"id": int(clase_id)},
            ).fetchone()
            if not row:
                return False
            own_sid = row[0]
            if own_sid is None:
                return True
            return int(own_sid) == sid
        except Exception:
            return False

    def _get_horario_profesor_id(self, horario_id: int) -> Optional[int]:
        try:
            row = self.db.execute(
                text("SELECT profesor_id FROM clase_horarios WHERE id = :id LIMIT 1"),
                {"id": int(horario_id)},
            ).fetchone()
            if row and row[0] is not None:
                return int(row[0])
        except Exception:
            pass
        return None

    def _horario_exists(self, horario_id: int) -> bool:
        try:
            row = self.db.execute(
                text("SELECT 1 FROM clase_horarios WHERE id = :id LIMIT 1"),
                {"id": int(horario_id)},
            ).fetchone()
            return bool(row)
        except Exception:
            return False

    def _horario_belongs_to_clase(self, horario_id: int, clase_id: int) -> bool:
        try:
            row = self.db.execute(
                text(
                    "SELECT 1 FROM clase_horarios WHERE id = :id AND clase_id = :clase_id LIMIT 1"
                ),
                {"id": int(horario_id), "clase_id": int(clase_id)},
            ).fetchone()
            return bool(row)
        except Exception:
            return False

    def obtener_horario_info(self, horario_id: int) -> Optional[Dict[str, Any]]:
        try:
            row = self.db.execute(
                text("""
                    SELECT ch.dia,
                           TO_CHAR(ch.hora_inicio, 'HH24:MI') as hora_inicio,
                           COALESCE(c.nombre,'') as clase_nombre
                    FROM clase_horarios ch
                    JOIN clases c ON c.id = ch.clase_id
                    WHERE ch.id = :id
                    LIMIT 1
                """),
                {"id": int(horario_id)},
            ).fetchone()
            if not row:
                return None
            return {"dia": row[0], "hora_inicio": row[1], "clase_nombre": row[2]}
        except Exception as e:
            logger.error(f"Error getting horario info: {e}")
            return None


    def obtener_agenda(self, profesor_id: Optional[int] = None, sucursal_id: Optional[int] = None) -> List[Dict[str, Any]]:
        try:
            params: Dict[str, Any] = {}
            clauses: List[str] = []
            if profesor_id is not None:
                params["pid"] = int(profesor_id)
                clauses.append("ch.profesor_id = :pid")
            try:
                sid = int(sucursal_id) if sucursal_id is not None else None
            except Exception:
                sid = None
            if sid is not None and sid > 0:
                params["sid"] = int(sid)
                clauses.append("(c.sucursal_id IS NULL OR c.sucursal_id = :sid)")
            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            result = self.db.execute(
                text(f"""
                SELECT
                    ch.id,
                    ch.clase_id,
                    COALESCE(c.nombre,'') as clase_nombre,
                    COALESCE(c.descripcion,'') as clase_descripcion,
                    ch.dia,
                    TO_CHAR(ch.hora_inicio, 'HH24:MI') as hora_inicio,
                    TO_CHAR(ch.hora_fin, 'HH24:MI') as hora_fin,
                    ch.profesor_id,
                    ch.cupo,
                    COALESCE(u.nombre,'') as profesor_nombre,
                    COUNT(i.id) as inscriptos_count
                FROM clase_horarios ch
                JOIN clases c ON c.id = ch.clase_id
                LEFT JOIN profesores p ON ch.profesor_id = p.id
                LEFT JOIN usuarios u ON u.id = p.usuario_id
                LEFT JOIN inscripciones i ON i.horario_id = ch.id
                {where}
                GROUP BY
                    ch.id, ch.clase_id, c.nombre, c.descripcion, ch.dia, ch.hora_inicio, ch.hora_fin,
                    ch.profesor_id, ch.cupo, u.nombre
                ORDER BY 
                    CASE ch.dia 
                        WHEN 'lunes' THEN 1 WHEN 'martes' THEN 2 WHEN 'miércoles' THEN 3 
                        WHEN 'miercoles' THEN 3 WHEN 'jueves' THEN 4 WHEN 'viernes' THEN 5 
                        WHEN 'sábado' THEN 6 WHEN 'sabado' THEN 6 WHEN 'domingo' THEN 7 
                    END, ch.hora_inicio
            """),
                params,
            )
            return [
                {
                    "horario_id": r[0],
                    "clase_id": r[1],
                    "clase_nombre": r[2],
                    "clase_descripcion": r[3] or None,
                    "dia": r[4],
                    "hora_inicio": r[5],
                    "hora_fin": r[6],
                    "profesor_id": r[7],
                    "cupo": r[8],
                    "profesor_nombre": r[9] or None,
                    "inscriptos_count": int(r[10] or 0),
                }
                for r in result.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting agenda: {e}")
            return []

    # ========== Clase Tipos ==========

    def obtener_tipos(self) -> List[Dict[str, Any]]:
        """Get all active class types."""
        try:
            result = self.db.execute(
                text("""
                SELECT id, nombre, descripcion, activo
                FROM tipos_clases WHERE activo = TRUE ORDER BY nombre
            """)
            )
            return [
                {
                    "id": r[0],
                    "nombre": r[1],
                    "descripcion": r[2],
                    "color": None,
                    "activo": r[3],
                }
                for r in result.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting class types: {e}")
            return []

    def crear_tipo(
        self, nombre: str, color: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a class type."""
        try:
            result = self.db.execute(
                text(
                    "INSERT INTO tipos_clases (nombre, descripcion, activo, created_at, updated_at) VALUES (:nombre, NULL, TRUE, NOW(), NOW()) RETURNING id, nombre, descripcion, activo"
                ),
                {"nombre": nombre},
            )
            row = result.fetchone()
            self.db.commit()
            return (
                {
                    "id": row[0],
                    "nombre": row[1],
                    "descripcion": row[2],
                    "color": None,
                    "activo": row[3],
                }
                if row
                else None
            )
        except Exception as e:
            logger.error(f"Error creating class type: {e}")
            self.db.rollback()
            return None

    def eliminar_tipo(self, tipo_id: int) -> bool:
        """Soft delete a class type."""
        try:
            self.db.execute(
                text("UPDATE tipos_clases SET activo = FALSE, updated_at = NOW() WHERE id = :id"),
                {"id": tipo_id},
            )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting class type: {e}")
            self.db.rollback()
            return False

    def obtener_profesores_asignados_a_clase(
        self, clase_id: int, *, sucursal_id: Optional[int] = None
    ) -> List[int]:
        try:
            sid = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sid = None
        if sid is not None and not self._clase_accessible(int(clase_id), sid):
            return []
        try:
            ensure_clase_profesor_schema(self.db)
            rows = self.db.execute(
                text(
                    """
                    SELECT a.profesor_id
                    FROM clase_profesor_asignaciones a
                    JOIN clases c ON c.id = a.clase_id
                    WHERE a.clase_id = :cid
                      AND a.activa = TRUE
                      AND (:sid IS NULL OR c.sucursal_id = :sid)
                    ORDER BY a.profesor_id ASC
                    """
                ),
                {"cid": int(clase_id), "sid": sid},
            ).fetchall()
            out: List[int] = []
            for r in rows or []:
                try:
                    out.append(int(r[0]))
                except Exception:
                    pass
            return out
        except Exception:
            return []

    # ========== Clase Horarios ==========

    def obtener_horarios(self, clase_id: int, sucursal_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get schedules for a class."""
        try:
            if not self._clase_accessible(int(clase_id), sucursal_id):
                return []
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
                {"clase_id": clase_id},
            )
            return [
                {
                    "id": r[0],
                    "clase_id": r[1],
                    "dia": r[2],
                    "hora_inicio": r[3],
                    "hora_fin": r[4],
                    "profesor_id": r[5],
                    "cupo": r[6],
                    "profesor_nombre": r[7],
                    "inscriptos_count": r[8],
                }
                for r in result.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting schedules: {e}")
            return []

    def crear_horario(
        self,
        clase_id: int,
        dia: str,
        hora_inicio: str,
        hora_fin: str,
        profesor_id: Optional[int] = None,
        cupo: int = 20,
        sucursal_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a class schedule."""
        try:
            if not self._clase_accessible(int(clase_id), sucursal_id):
                return None
            if not self._clase_exists(int(clase_id)):
                return None
            result = self.db.execute(
                text("""
                    INSERT INTO clase_horarios (clase_id, dia, hora_inicio, hora_fin, profesor_id, cupo)
                    VALUES (:clase_id, :dia, :hora_inicio, :hora_fin, :profesor_id, :cupo)
                    RETURNING id, clase_id, dia, TO_CHAR(hora_inicio, 'HH24:MI') as hora_inicio,
                              TO_CHAR(hora_fin, 'HH24:MI') as hora_fin, profesor_id, cupo
                """),
                {
                    "clase_id": clase_id,
                    "dia": dia.lower(),
                    "hora_inicio": hora_inicio,
                    "hora_fin": hora_fin,
                    "profesor_id": profesor_id,
                    "cupo": cupo,
                },
            )
            row = result.fetchone()
            self.db.commit()
            return (
                {
                    "id": row[0],
                    "clase_id": row[1],
                    "dia": row[2],
                    "hora_inicio": row[3],
                    "hora_fin": row[4],
                    "profesor_id": row[5],
                    "cupo": row[6],
                }
                if row
                else None
            )
        except Exception as e:
            logger.error(f"Error creating schedule: {e}")
            self.db.rollback()
            return None

    def actualizar_horario(
        self, horario_id: int, clase_id: int, updates: Dict[str, Any], sucursal_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a class schedule."""
        try:
            if not self._clase_accessible(int(clase_id), sucursal_id):
                return None
            # Ensure horario exists for that clase
            if not self._horario_belongs_to_clase(int(horario_id), int(clase_id)):
                return None

            sets = []
            params = {"id": horario_id, "clase_id": clase_id}
            if "dia" in updates:
                sets.append("dia = :dia")
                params["dia"] = (updates["dia"] or "").lower()
            if "hora_inicio" in updates:
                sets.append("hora_inicio = :hora_inicio")
                params["hora_inicio"] = updates["hora_inicio"]
            if "hora_fin" in updates:
                sets.append("hora_fin = :hora_fin")
                params["hora_fin"] = updates["hora_fin"]
            if "profesor_id" in updates:
                sets.append("profesor_id = :profesor_id")
                params["profesor_id"] = updates["profesor_id"]
            if "cupo" in updates:
                sets.append("cupo = :cupo")
                params["cupo"] = int(updates["cupo"]) if updates["cupo"] else 20

            if not sets:
                # No updates requested but horario exists
                return {"ok": True}

            result = self.db.execute(
                text(f"""
                    UPDATE clase_horarios SET {", ".join(sets)}
                    WHERE id = :id AND clase_id = :clase_id
                    RETURNING id, clase_id, dia, TO_CHAR(hora_inicio, 'HH24:MI') as hora_inicio,
                              TO_CHAR(hora_fin, 'HH24:MI') as hora_fin, profesor_id, cupo
                """),
                params,
            )
            row = result.fetchone()
            self.db.commit()
            if not row:
                return None
            return {
                "id": row[0],
                "clase_id": row[1],
                "dia": row[2],
                "hora_inicio": row[3],
                "hora_fin": row[4],
                "profesor_id": row[5],
                "cupo": row[6],
            }
        except Exception as e:
            logger.error(f"Error updating schedule: {e}")
            self.db.rollback()
            return None

    def eliminar_horario(self, horario_id: int, clase_id: int, sucursal_id: Optional[int] = None) -> bool:
        """Delete a class schedule and its enrollments."""
        try:
            if not self._clase_accessible(int(clase_id), sucursal_id):
                return False
            if not self._horario_belongs_to_clase(int(horario_id), int(clase_id)):
                return False

            self.db.execute(
                text("DELETE FROM inscripciones WHERE horario_id = :id"),
                {"id": int(horario_id)},
            )
            self.db.execute(
                text("DELETE FROM lista_espera WHERE horario_id = :id"),
                {"id": int(horario_id)},
            )
            res = self.db.execute(
                text(
                    "DELETE FROM clase_horarios WHERE id = :id AND clase_id = :clase_id"
                ),
                {"id": int(horario_id), "clase_id": int(clase_id)},
            )
            self.db.commit()
            try:
                return (getattr(res, "rowcount", 0) or 0) > 0
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
                {"horario_id": horario_id},
            )
            return [
                {
                    "id": r[0],
                    "horario_id": r[1],
                    "usuario_id": r[2],
                    "fecha_inscripcion": r[3].isoformat() if r[3] else None,
                    "usuario_nombre": r[4],
                    "usuario_telefono": r[5],
                }
                for r in result.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting enrollments: {e}")
            return []

    def crear_inscripcion(self, horario_id: int, usuario_id: int) -> Dict[str, Any]:
        """Enroll a user in a schedule."""
        try:
            fecha_inscripcion = self._now_utc_naive()
            ctx = (
                self.db.execute(
                    text(
                        """
                        SELECT ch.clase_id, c.sucursal_id, c.tipo_clase_id
                        FROM clase_horarios ch
                        JOIN clases c ON c.id = ch.clase_id
                        WHERE ch.id = :id
                        LIMIT 1
                        """
                    ),
                    {"id": int(horario_id)},
                )
                .mappings()
                .first()
            )
            if not ctx:
                return {"error": "Horario no encontrado"}
            clase_id = ctx.get("clase_id")
            sucursal_id = ctx.get("sucursal_id")
            tipo_clase_id = ctx.get("tipo_clase_id")
            from src.services.attendance_service import AttendanceService

            ok_access, reason = AttendanceService(self.db).verificar_acceso_usuario_sucursal(
                int(usuario_id), int(sucursal_id) if sucursal_id is not None else None
            )
            if ok_access is False:
                return {"error": reason or "Forbidden", "forbidden": True}
            from src.services.entitlements_service import EntitlementsService

            try:
                ok_opt, reason2 = EntitlementsService(self.db).check_class_access(
                    int(usuario_id),
                    int(sucursal_id) if sucursal_id is not None else 0,
                    clase_id=int(clase_id) if clase_id is not None else None,
                    tipo_clase_id=int(tipo_clase_id) if tipo_clase_id is not None else None,
                )
            except Exception:
                return {
                    "error": "No se pudo validar permisos de clase",
                    "forbidden": True,
                }
            if ok_opt is False:
                return {"error": reason2 or "Clase no habilitada", "forbidden": True}
            # Check capacity
            cap = self.db.execute(
                text("""SELECT cupo, (SELECT COUNT(*) FROM inscripciones WHERE horario_id = :id) as inscriptos
                        FROM clase_horarios WHERE id = :id"""),
                {"id": horario_id},
            ).fetchone()

            if not cap:
                return {"error": "Horario no encontrado"}

            if cap:
                cupo = cap[0] or 20
                inscriptos = cap[1] or 0
                if inscriptos >= cupo:
                    return {"error": "Cupo lleno", "full": True}

            result = self.db.execute(
                text("""INSERT INTO inscripciones (horario_id, usuario_id, fecha_inscripcion) VALUES (:horario_id, :usuario_id, :fecha_inscripcion)
                        ON CONFLICT (horario_id, usuario_id) DO NOTHING RETURNING id, horario_id, usuario_id, fecha_inscripcion"""),
                {
                    "horario_id": horario_id,
                    "usuario_id": usuario_id,
                    "fecha_inscripcion": fecha_inscripcion,
                },
            )
            row = result.fetchone()
            self.db.commit()

            if row:
                return {
                    "id": row[0],
                    "horario_id": row[1],
                    "usuario_id": row[2],
                    "fecha_inscripcion": row[3].isoformat() if row[3] else None,
                }
            return {"ok": True, "message": "Ya está inscripto"}
        except Exception as e:
            logger.error(f"Error creating enrollment: {e}")
            self.db.rollback()
            return {"error": str(e)}

    def eliminar_inscripcion(self, horario_id: int, usuario_id: int) -> bool:
        """Remove enrollment."""
        try:
            self.db.execute(
                text(
                    "DELETE FROM inscripciones WHERE horario_id = :hid AND usuario_id = :uid"
                ),
                {"hid": horario_id, "uid": usuario_id},
            )
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
                {"horario_id": horario_id},
            )
            return [
                {
                    "id": r[0],
                    "horario_id": r[1],
                    "usuario_id": r[2],
                    "posicion": r[3],
                    "fecha_registro": r[4].isoformat() if r[4] else None,
                    "usuario_nombre": r[5],
                }
                for r in result.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting waitlist: {e}")
            return []

    def agregar_lista_espera(self, horario_id: int, usuario_id: int) -> Dict[str, Any]:
        """Add user to waitlist."""
        try:
            if not self._horario_exists(int(horario_id)):
                return {"error": "Horario no encontrado"}
            ctx = (
                self.db.execute(
                    text(
                        """
                        SELECT ch.clase_id, c.sucursal_id, c.tipo_clase_id
                        FROM clase_horarios ch
                        JOIN clases c ON c.id = ch.clase_id
                        WHERE ch.id = :id
                        LIMIT 1
                        """
                    ),
                    {"id": int(horario_id)},
                )
                .mappings()
                .first()
            )
            if not ctx:
                return {"error": "Horario no encontrado"}
            clase_id = ctx.get("clase_id")
            sucursal_id = ctx.get("sucursal_id")
            tipo_clase_id = ctx.get("tipo_clase_id")
            from src.services.attendance_service import AttendanceService

            ok_access, reason = AttendanceService(self.db).verificar_acceso_usuario_sucursal(
                int(usuario_id), int(sucursal_id) if sucursal_id is not None else None
            )
            if ok_access is False:
                return {"error": reason or "Forbidden", "forbidden": True}
            from src.services.entitlements_service import EntitlementsService

            try:
                ok_opt, reason2 = EntitlementsService(self.db).check_class_access(
                    int(usuario_id),
                    int(sucursal_id) if sucursal_id is not None else 0,
                    clase_id=int(clase_id) if clase_id is not None else None,
                    tipo_clase_id=int(tipo_clase_id) if tipo_clase_id is not None else None,
                )
            except Exception:
                return {
                    "error": "No se pudo validar permisos de clase",
                    "forbidden": True,
                }
            if ok_opt is False:
                return {"error": reason2 or "Clase no habilitada", "forbidden": True}
            fecha_registro = self._now_utc_naive()
            pos = self.db.execute(
                text(
                    "SELECT COALESCE(MAX(posicion), 0) + 1 FROM lista_espera WHERE horario_id = :id"
                ),
                {"id": horario_id},
            ).fetchone()
            next_pos = pos[0] if pos else 1

            result = self.db.execute(
                text("""INSERT INTO lista_espera (horario_id, usuario_id, posicion, fecha_registro) VALUES (:hid, :uid, :pos, :fecha_registro)
                        ON CONFLICT (horario_id, usuario_id) DO NOTHING 
                        RETURNING id, horario_id, usuario_id, posicion, fecha_registro"""),
                {
                    "hid": horario_id,
                    "uid": usuario_id,
                    "pos": next_pos,
                    "fecha_registro": fecha_registro,
                },
            )
            row = result.fetchone()
            self.db.commit()

            if row:
                return {
                    "id": row[0],
                    "horario_id": row[1],
                    "usuario_id": row[2],
                    "posicion": row[3],
                    "fecha_registro": row[4].isoformat() if row[4] else None,
                }
            return {"ok": True, "message": "Ya está en lista de espera"}
        except Exception as e:
            logger.error(f"Error adding to waitlist: {e}")
            self.db.rollback()
            return {"error": str(e)}

    def eliminar_lista_espera(self, horario_id: int, usuario_id: int) -> bool:
        """Remove from waitlist."""
        try:
            self.db.execute(
                text(
                    "DELETE FROM lista_espera WHERE horario_id = :hid AND usuario_id = :uid"
                ),
                {"hid": horario_id, "uid": usuario_id},
            )
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
                {"id": horario_id},
            )
            row = result.fetchone()
            return (
                {"usuario_id": row[0], "nombre": row[1], "telefono": row[2]}
                if row
                else None
            )
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
                {"clase_id": clase_id},
            )
            return [
                {"ejercicio_id": r[0], "ejercicio_nombre": r[1], "orden": r[2]}
                for r in result.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting class exercises: {e}")
            return []

    def actualizar_clase_ejercicios(
        self, clase_id: int, ejercicio_ids: List[int]
    ) -> bool:
        """Update exercises for a class."""
        try:
            # Get or create default bloque
            bloque = self.db.execute(
                text("SELECT id FROM clase_bloques WHERE clase_id = :id LIMIT 1"),
                {"id": clase_id},
            ).fetchone()
            if bloque:
                bloque_id = bloque[0]
            else:
                result = self.db.execute(
                    text(
                        "INSERT INTO clase_bloques (clase_id, nombre) VALUES (:id, 'Ejercicios') RETURNING id"
                    ),
                    {"id": clase_id},
                )
                bloque_id = result.fetchone()[0]

            self.db.execute(
                text("DELETE FROM clase_bloque_items WHERE bloque_id = :id"),
                {"id": bloque_id},
            )

            for idx, eid in enumerate(ejercicio_ids):
                self.db.execute(
                    text(
                        "INSERT INTO clase_bloque_items (bloque_id, ejercicio_id, orden) VALUES (:bid, :eid, :idx)"
                    ),
                    {"bid": bloque_id, "eid": int(eid), "idx": idx},
                )

            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating class exercises: {e}")
            self.db.rollback()
            return False
