from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import asc, desc, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .models import PlantillaAnalitica, PlantillaRutina, PlantillaRutinaVersion
from .template_validator import TemplateValidator, ValidationResult


def _is_export_template_config(cfg: Any) -> bool:
    if not isinstance(cfg, dict):
        return False
    return all(k in cfg for k in ("metadata", "layout", "pages", "variables"))


class TemplateRepository:
    def __init__(self, db: Session):
        self.db = db
        self.validator = TemplateValidator()

    def create_template(
        self,
        nombre: str,
        configuracion: Dict[str, Any],
        descripcion: Optional[str] = None,
        categoria: str = "general",
        dias_semana: Optional[int] = None,
        creada_por: Optional[int] = None,
        tags: Optional[List[str]] = None,
        publica: bool = False,
        activa: bool = True,
    ) -> Tuple[Optional[PlantillaRutina], Optional[str]]:
        try:
            validation = self.validator.validate_template(configuracion)
            if not validation.is_valid:
                msg = "; ".join([str(e.get("message") or "") for e in validation.errors if isinstance(e, dict)])
                return None, f"Template validation failed: {msg}"

            tpl = PlantillaRutina(
                nombre=nombre,
                descripcion=descripcion,
                configuracion=configuracion,
                categoria=categoria,
                dias_semana=dias_semana,
                tipo="export_pdf",
                creada_por=creada_por,
                publica=publica,
                activa=activa,
                tags=tags or [],
                version_actual="1.0.0",
            )
            self.db.add(tpl)
            self.db.flush()

            v = PlantillaRutinaVersion(
                plantilla_id=tpl.id,
                version="1.0.0",
                configuracion=configuracion,
                cambios_descripcion="Initial version",
                creada_por=creada_por,
                es_actual=True,
            )
            self.db.add(v)
            self.db.commit()
            self._log_analytics(tpl.id, evento_tipo="create", exitoso=True)
            return tpl, None
        except SQLAlchemyError as e:
            self.db.rollback()
            return None, f"Database error: {str(e)}"

    def get_template(self, template_id: int) -> Optional[PlantillaRutina]:
        try:
            return self.db.query(PlantillaRutina).filter(PlantillaRutina.id == int(template_id)).first()
        except SQLAlchemyError:
            return None

    def update_template(
        self,
        template_id: int,
        updates: Dict[str, Any],
        creada_por: Optional[int] = None,
        cambios_descripcion: Optional[str] = None,
    ) -> Tuple[Optional[PlantillaRutina], Optional[str]]:
        try:
            tpl = self.get_template(int(template_id))
            if not tpl:
                return None, "Template not found"

            if "configuracion" in updates:
                validation = self.validator.validate_template(updates["configuracion"])
                if not validation.is_valid:
                    msg = "; ".join([str(e.get("message") or "") for e in validation.errors if isinstance(e, dict)])
                    return None, f"Template validation failed: {msg}"

            for field, value in updates.items():
                if field == "configuracion":
                    continue
                if hasattr(tpl, field):
                    setattr(tpl, field, value)

            tpl.fecha_actualizacion = datetime.utcnow()

            if "configuracion" in updates:
                new_version = self._increment_version(str(tpl.version_actual or "1.0.0"))
                self.db.query(PlantillaRutinaVersion).filter(
                    PlantillaRutinaVersion.plantilla_id == int(template_id),
                    PlantillaRutinaVersion.es_actual == True,
                ).update({"es_actual": False})
                v = PlantillaRutinaVersion(
                    plantilla_id=int(template_id),
                    version=new_version,
                    configuracion=updates["configuracion"],
                    cambios_descripcion=cambios_descripcion or "Updated configuration",
                    creada_por=creada_por,
                    es_actual=True,
                )
                tpl.configuracion = updates["configuracion"]
                tpl.version_actual = new_version
                self.db.add(v)

            self.db.commit()
            self._log_analytics(int(template_id), evento_tipo="edit", exitoso=True)
            return tpl, None
        except SQLAlchemyError as e:
            self.db.rollback()
            return None, f"Database error: {str(e)}"

    def delete_template(self, template_id: int) -> Tuple[bool, Optional[str]]:
        try:
            tpl = self.db.query(PlantillaRutina).filter(PlantillaRutina.id == int(template_id)).first()
            if not tpl:
                return False, "Template not found"
            tpl.activa = False
            self.db.commit()
            self._log_analytics(int(template_id), evento_tipo="delete", exitoso=True)
            return True, None
        except SQLAlchemyError as e:
            self.db.rollback()
            return False, f"Database error: {str(e)}"

    def search_templates(
        self,
        query: Optional[str] = None,
        categoria: Optional[str] = None,
        dias_semana: Optional[int] = None,
        publica: Optional[bool] = None,
        activa: Optional[bool] = True,
        creada_por: Optional[int] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "fecha_creacion",
        sort_order: str = "desc",
        export_only: bool = True,
    ) -> Tuple[List[PlantillaRutina], int]:
        try:
            q = self.db.query(PlantillaRutina)
            if export_only:
                q = q.filter(PlantillaRutina.tipo == "export_pdf")

            if query:
                q = q.filter(or_(PlantillaRutina.nombre.ilike(f"%{query}%"), PlantillaRutina.descripcion.ilike(f"%{query}%")))
            if categoria:
                q = q.filter(PlantillaRutina.categoria == categoria)
            if dias_semana:
                q = q.filter(PlantillaRutina.dias_semana == dias_semana)
            if publica is not None:
                q = q.filter(PlantillaRutina.publica == publica)
            if activa is not None:
                q = q.filter(PlantillaRutina.activa == activa)
            if creada_por:
                q = q.filter(PlantillaRutina.creada_por == creada_por)
            if tags:
                q = q.filter(PlantillaRutina.tags.overlap(tags))

            total = int(q.count())

            sort_column = getattr(PlantillaRutina, sort_by, PlantillaRutina.fecha_creacion)
            q = q.order_by(desc(sort_column) if str(sort_order).lower() == "desc" else asc(sort_column))
            items = q.offset(int(offset or 0)).limit(int(limit or 50)).all()
            return items, total
        except SQLAlchemyError:
            return [], 0

    def get_template_versions(self, template_id: int) -> List[PlantillaRutinaVersion]:
        try:
            return (
                self.db.query(PlantillaRutinaVersion)
                .filter(PlantillaRutinaVersion.plantilla_id == int(template_id))
                .order_by(desc(PlantillaRutinaVersion.fecha_creacion), desc(PlantillaRutinaVersion.id))
                .all()
            )
        except SQLAlchemyError:
            return []

    def create_template_version(
        self,
        template_id: int,
        version: str,
        configuracion: Dict[str, Any],
        cambios_descripcion: Optional[str],
        creada_por: Optional[int],
    ) -> Tuple[Optional[PlantillaRutinaVersion], Optional[str]]:
        try:
            tpl = self.get_template(int(template_id))
            if not tpl:
                return None, "Template not found"
            validation = self.validator.validate_template(configuracion)
            if not validation.is_valid:
                msg = "; ".join([str(e.get("message") or "") for e in validation.errors if isinstance(e, dict)])
                return None, f"Template validation failed: {msg}"

            self.db.query(PlantillaRutinaVersion).filter(
                PlantillaRutinaVersion.plantilla_id == int(template_id),
                PlantillaRutinaVersion.es_actual == True,
            ).update({"es_actual": False})

            v = PlantillaRutinaVersion(
                plantilla_id=int(template_id),
                version=str(version),
                configuracion=configuracion,
                cambios_descripcion=cambios_descripcion,
                creada_por=creada_por,
                es_actual=True,
            )
            tpl.configuracion = configuracion
            tpl.version_actual = str(version)
            tpl.fecha_actualizacion = datetime.utcnow()
            self.db.add(v)
            self.db.commit()
            return v, None
        except SQLAlchemyError as e:
            self.db.rollback()
            return None, f"Database error: {str(e)}"

    def restore_template_version(self, template_id: int, version: str) -> Tuple[bool, Optional[str]]:
        try:
            tpl = self.get_template(int(template_id))
            if not tpl:
                return False, "Template not found"
            v = (
                self.db.query(PlantillaRutinaVersion)
                .filter(PlantillaRutinaVersion.plantilla_id == int(template_id), PlantillaRutinaVersion.version == str(version))
                .first()
            )
            if not v:
                return False, "Version not found"
            if bool(v.es_actual) and str(tpl.version_actual or "") == str(v.version):
                return True, None
            validation = self.validator.validate_template(v.configuracion)
            if not validation.is_valid:
                msg = "; ".join([str(e.get("message") or "") for e in validation.errors if isinstance(e, dict)])
                return False, f"Template validation failed: {msg}"
            self.db.query(PlantillaRutinaVersion).filter(
                PlantillaRutinaVersion.plantilla_id == int(template_id),
                PlantillaRutinaVersion.es_actual == True,
            ).update({"es_actual": False})
            v.es_actual = True
            tpl.configuracion = v.configuracion
            tpl.version_actual = v.version
            tpl.fecha_actualizacion = datetime.utcnow()
            self.db.commit()
            return True, None
        except SQLAlchemyError as e:
            self.db.rollback()
            return False, f"Database error: {str(e)}"

    def get_template_analytics(self, template_id: int, days: int = 30) -> Dict[str, Any]:
        try:
            fecha_inicio = datetime.utcnow() - timedelta(days=max(1, int(days)))
            rows = (
                self.db.query(PlantillaAnalitica)
                .filter(PlantillaAnalitica.plantilla_id == int(template_id), PlantillaAnalitica.fecha_evento >= fecha_inicio)
                .all()
            )
            total_events = len(rows)
            successful = sum(1 for r in rows if r.exitoso)
            avg_render = (sum((r.tiempo_render_ms or 0) for r in rows) / total_events) if total_events else 0.0
            by_type: Dict[str, int] = {}
            for r in rows:
                by_type[r.evento_tipo] = by_type.get(r.evento_tipo, 0) + 1
            return {
                "usos_totales": total_events,
                "eventos_exitosos": successful,
                "tasa_exito": (successful / total_events * 100) if total_events else 0.0,
                "tiempo_promedio_render_ms": avg_render,
                "eventos_por_tipo": by_type,
            }
        except SQLAlchemyError:
            return {"usos_totales": 0, "eventos_exitosos": 0, "tasa_exito": 0.0, "tiempo_promedio_render_ms": 0.0, "eventos_por_tipo": {}}

    def get_template_categories(self) -> List[str]:
        try:
            rows = self.db.query(PlantillaRutina.categoria).filter(
                PlantillaRutina.tipo == "export_pdf"
            ).distinct().all()
            return [r[0] for r in rows if r and r[0]]
        except SQLAlchemyError:
            return []

    def get_template_tags(self) -> List[str]:
        try:
            templates = self.db.query(PlantillaRutina.tags).filter(
                PlantillaRutina.tipo == "export_pdf"
            ).all()
            all_tags = set()
            for (tags,) in templates:
                if tags:
                    all_tags.update(tags)
            return sorted(list(all_tags))
        except SQLAlchemyError:
            return []

    def validate_template(self, configuracion: Dict[str, Any]) -> ValidationResult:
        return self.validator.validate_template(configuracion)

    def _increment_version(self, current: str) -> str:
        try:
            parts = current.split(".")
            if len(parts) != 3:
                return "1.0.1"
            major, minor, patch = map(int, parts)
            patch += 1
            return f"{major}.{minor}.{patch}"
        except Exception:
            return "1.0.1"

    def _log_analytics(
        self,
        template_id: int,
        evento_tipo: str,
        exitoso: bool = True,
        gimnasio_id: Optional[int] = None,
        usuario_id: Optional[int] = None,
        datos_evento: Optional[Dict[str, Any]] = None,
        tiempo_render_ms: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        try:
            a = PlantillaAnalitica(
                plantilla_id=int(template_id),
                gimnasio_id=gimnasio_id,
                usuario_id=usuario_id,
                evento_tipo=str(evento_tipo),
                datos_evento=datos_evento,
                tiempo_render_ms=tiempo_render_ms,
                exitoso=bool(exitoso),
                error_message=error_message,
            )
            self.db.add(a)
            self.db.commit()
        except SQLAlchemyError:
            try:
                self.db.rollback()
            except Exception:
                pass
