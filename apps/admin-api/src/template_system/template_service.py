from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from .preview_engine import PreviewConfig, PreviewEngine, PreviewFormat, PreviewQuality
from .models import PlantillaAnalitica, PlantillaRutina
from .template_repository import TemplateRepository
from .template_validator import ValidationResult


class TemplateService:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.repository = TemplateRepository(db_session)
        self.preview_engine = PreviewEngine()

    def create_template(self, payload: Dict[str, Any], creada_por: Optional[int] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        nombre = str(payload.get("nombre") or "").strip()
        if not nombre:
            return None, "nombre requerido"
        configuracion = payload.get("configuracion")
        if not isinstance(configuracion, dict):
            return None, "configuracion requerida"
        descripcion = payload.get("descripcion")
        categoria = str(payload.get("categoria") or "general")
        dias_semana = payload.get("dias_semana")
        try:
            dias_semana = int(dias_semana) if dias_semana is not None else None
        except Exception:
            dias_semana = None
        tags = payload.get("tags")
        if tags is not None and not isinstance(tags, list):
            tags = None
        publica = bool(payload.get("publica") or False)
        activa = bool(payload.get("activa") if payload.get("activa") is not None else True)

        tpl, err = self.repository.create_template(
            nombre=nombre,
            configuracion=configuracion,
            descripcion=str(descripcion) if descripcion else None,
            categoria=categoria,
            dias_semana=dias_semana,
            creada_por=creada_por,
            tags=[str(t) for t in tags] if isinstance(tags, list) else None,
            publica=publica,
            activa=activa,
        )
        if not tpl:
            return None, err or "create_failed"
        return self._template_to_dict(tpl), None

    def get_template(self, template_id: int) -> Optional[Dict[str, Any]]:
        tpl = self.repository.get_template(int(template_id))
        if not tpl:
            return None
        return self._template_to_dict(tpl)

    def update_template(self, template_id: int, payload: Dict[str, Any], creada_por: Optional[int] = None, cambios_descripcion: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        allowed = {"nombre", "configuracion", "descripcion", "categoria", "dias_semana", "tags", "publica", "activa", "preview_url"}
        updates: Dict[str, Any] = {}
        for k, v in payload.items():
            if k in allowed:
                updates[k] = v
        if "nombre" in updates:
            updates["nombre"] = str(updates["nombre"] or "").strip()
        if "categoria" in updates:
            updates["categoria"] = str(updates["categoria"] or "general")
        if "dias_semana" in updates:
            try:
                updates["dias_semana"] = int(updates["dias_semana"]) if updates["dias_semana"] is not None else None
            except Exception:
                updates["dias_semana"] = None
        if "tags" in updates and updates["tags"] is not None and not isinstance(updates["tags"], list):
            updates["tags"] = None

        tpl, err = self.repository.update_template(int(template_id), updates=updates, creada_por=creada_por, cambios_descripcion=cambios_descripcion)
        if not tpl:
            return None, err or "update_failed"
        return self._template_to_dict(tpl), None

    def delete_template(self, template_id: int) -> Tuple[bool, Optional[str]]:
        return self.repository.delete_template(int(template_id))

    def search_templates(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = params.get("query")
        categoria = params.get("categoria")
        activa = params.get("activa")
        if activa is not None:
            activa = True if str(activa).lower() == "true" else False if str(activa).lower() == "false" else None
        sort_by = str(params.get("sort_by") or "fecha_creacion")
        sort_order = str(params.get("sort_order") or "desc")
        limit = int(params.get("limit") or 50)
        offset = int(params.get("offset") or 0)

        templates, total = self.repository.search_templates(
            query=str(query) if query else None,
            categoria=str(categoria) if categoria else None,
            activa=activa,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
            export_only=True,
        )
        has_more = offset + limit < total
        return {
            "success": True,
            "templates": [self._template_to_dict(t) for t in templates],
            "total": total,
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        }

    def validate_template_config(self, configuracion: Dict[str, Any]) -> ValidationResult:
        return self.repository.validate_template(configuracion)

    def generate_template_preview(self, template_config: Dict[str, Any], format: str, quality: str, page_number: int, sample_data: Optional[Dict[str, Any]]) -> Tuple[Optional[str], Optional[str]]:
        try:
            pf = PreviewFormat(format.lower())
        except Exception:
            return None, "Invalid format"
        try:
            pq = PreviewQuality(quality.lower())
        except Exception:
            return None, "Invalid quality"

        cfg = PreviewConfig(format=pf, quality=pq, page_number=int(page_number or 1), use_cache=True, generate_sample_data=sample_data is None)
        result = self.preview_engine.generate_preview(template_config=template_config, config=cfg, custom_data=sample_data)
        if not result.success:
            return None, result.error_message or "preview_failed"
        uri = self.preview_engine.build_data_uri(result)
        if not uri:
            return None, "preview_failed"
        return uri, None

    def generate_and_store_thumbnail(self, template_id: int) -> None:
        tpl = self.repository.get_template(int(template_id))
        if not tpl:
            return
        uri, err = self.generate_template_preview(tpl.configuracion, format="thumbnail", quality="medium", page_number=1, sample_data=None)
        if err or not uri:
            return
        self.repository.update_template(int(template_id), updates={"preview_url": uri}, creada_por=None, cambios_descripcion=None)

    def get_template_versions(self, template_id: int) -> List[Dict[str, Any]]:
        versions = self.repository.get_template_versions(int(template_id))
        return [self._version_to_dict(v) for v in versions]

    def create_template_version(self, template_id: int, version: str, configuracion: Dict[str, Any], descripcion: Optional[str], creada_por: Optional[int]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        v, err = self.repository.create_template_version(int(template_id), version=str(version), configuracion=configuracion, cambios_descripcion=descripcion, creada_por=creada_por)
        if not v:
            return None, err or "create_version_failed"
        return self._version_to_dict(v), None

    def restore_template_version(self, template_id: int, version: str) -> Tuple[bool, Optional[str]]:
        return self.repository.restore_template_version(int(template_id), version=str(version))

    def get_template_analytics(self, template_id: int, days: int = 30) -> Dict[str, Any]:
        return self.repository.get_template_analytics(int(template_id), days=int(days or 30))

    def get_analytics_dashboard(self, days: int = 30) -> Dict[str, Any]:
        days = int(days or 30)
        now = datetime.utcnow()
        inicio = now - timedelta(days=max(1, days))

        export_filter = [
            PlantillaRutina.configuracion.has_key("pages"),  # type: ignore[attr-defined]
            PlantillaRutina.configuracion.has_key("metadata"),  # type: ignore[attr-defined]
            PlantillaRutina.configuracion.has_key("layout"),  # type: ignore[attr-defined]
            PlantillaRutina.configuracion.has_key("variables"),  # type: ignore[attr-defined]
        ]

        total_templates = int(self.db.query(func.count(PlantillaRutina.id)).filter(*export_filter).scalar() or 0)
        active_templates = int(
            self.db.query(func.count(PlantillaRutina.id)).filter(*export_filter, PlantillaRutina.activa == True).scalar() or 0
        )

        total_events = int(
            self.db.query(func.count(PlantillaAnalitica.id))
            .filter(PlantillaAnalitica.fecha_evento >= inicio)
            .scalar()
            or 0
        )
        unique_users = int(
            self.db.query(func.count(distinct(PlantillaAnalitica.usuario_id)))
            .filter(PlantillaAnalitica.fecha_evento >= inicio, PlantillaAnalitica.usuario_id.isnot(None))
            .scalar()
            or 0
        )

        category_rows = (
            self.db.query(PlantillaRutina.categoria, func.count(PlantillaRutina.id))
            .filter(*export_filter)
            .group_by(PlantillaRutina.categoria)
            .order_by(func.count(PlantillaRutina.id).desc())
            .all()
        )
        category_analytics = [{"categoria": str(c or "general"), "count": int(n or 0)} for (c, n) in category_rows]

        popular_rows = (
            self.db.query(PlantillaRutina.id, PlantillaRutina.nombre, PlantillaRutina.categoria, func.count(PlantillaAnalitica.id).label("cnt"))
            .join(PlantillaAnalitica, PlantillaAnalitica.plantilla_id == PlantillaRutina.id)
            .filter(PlantillaAnalitica.fecha_evento >= inicio)
            .group_by(PlantillaRutina.id, PlantillaRutina.nombre, PlantillaRutina.categoria)
            .order_by(func.count(PlantillaAnalitica.id).desc())
            .limit(10)
            .all()
        )
        popular_templates = [
            {"template_id": int(tid), "nombre": str(nombre), "categoria": str(cat or "general"), "count": int(cnt or 0)}
            for (tid, nombre, cat, cnt) in popular_rows
        ]

        return {
            "overview": {
                "total_templates": total_templates,
                "active_templates": active_templates,
                "total_events": total_events,
                "unique_users": unique_users,
            },
            "popular_templates": popular_templates,
            "category_analytics": category_analytics,
        }

    def export_template(self, template_id: int) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        tpl = self.repository.get_template(int(template_id))
        if not tpl:
            return None, "Template not found"
        return {"template": self._template_to_dict(tpl)}, None

    def _template_to_dict(self, tpl) -> Dict[str, Any]:
        return {
            "id": int(tpl.id),
            "nombre": str(tpl.nombre),
            "descripcion": tpl.descripcion,
            "configuracion": tpl.configuracion,
            "categoria": str(tpl.categoria or "general"),
            "dias_semana": tpl.dias_semana,
            "activa": bool(tpl.activa),
            "publica": bool(tpl.publica),
            "creada_por": tpl.creada_por,
            "fecha_creacion": tpl.fecha_creacion.isoformat() if getattr(tpl, "fecha_creacion", None) else None,
            "fecha_actualizacion": tpl.fecha_actualizacion.isoformat() if getattr(tpl, "fecha_actualizacion", None) else None,
            "version_actual": str(tpl.version_actual or "1.0.0"),
            "tags": list(tpl.tags or []),
            "preview_url": tpl.preview_url,
            "uso_count": int(tpl.uso_count or 0),
            "rating_promedio": float(tpl.rating_promedio) if tpl.rating_promedio is not None else None,
            "rating_count": int(tpl.rating_count or 0),
        }

    def _version_to_dict(self, v) -> Dict[str, Any]:
        return {
            "id": int(v.id),
            "plantilla_id": int(v.plantilla_id),
            "version": str(v.version),
            "configuracion": v.configuracion,
            "cambios_descripcion": v.cambios_descripcion,
            "creada_por": v.creada_por,
            "fecha_creacion": v.fecha_creacion.isoformat() if getattr(v, "fecha_creacion", None) else None,
            "es_actual": bool(v.es_actual),
        }
