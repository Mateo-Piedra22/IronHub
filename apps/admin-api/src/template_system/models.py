from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class TenantBase(DeclarativeBase):
    pass


class PlantillaRutina(TenantBase):
    __tablename__ = "plantillas_rutina"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    configuracion: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    categoria: Mapped[Optional[str]] = mapped_column(String(100), server_default="general")
    dias_semana: Mapped[Optional[int]] = mapped_column(Integer)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False, server_default="export_pdf")
    activa: Mapped[bool] = mapped_column(Boolean, server_default="true")
    publica: Mapped[bool] = mapped_column(Boolean, server_default="false")
    creada_por: Mapped[Optional[int]] = mapped_column(Integer)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    fecha_actualizacion: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    version_actual: Mapped[Optional[str]] = mapped_column(String(50), server_default="1.0.0")
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), server_default="{}", default=list)
    preview_url: Mapped[Optional[str]] = mapped_column(String(500))
    uso_count: Mapped[int] = mapped_column(Integer, server_default="0")
    rating_promedio: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    rating_count: Mapped[int] = mapped_column(Integer, server_default="0")

    versiones: Mapped[List["PlantillaRutinaVersion"]] = relationship(
        "PlantillaRutinaVersion",
        back_populates="plantilla",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    analitica: Mapped[List["PlantillaAnalitica"]] = relationship(
        "PlantillaAnalitica",
        back_populates="plantilla",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("idx_plantillas_rutina_activa", "activa"),
        Index("idx_plantillas_rutina_categoria", "categoria"),
        Index("idx_plantillas_rutina_publica", "publica"),
        Index("idx_plantillas_rutina_creada_por", "creada_por"),
        Index("idx_plantillas_rutina_fecha_creacion", "fecha_creacion"),
        Index("idx_plantillas_rutina_tipo", "tipo"),
    )


class PlantillaRutinaVersion(TenantBase):
    __tablename__ = "plantillas_rutina_versiones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plantilla_id: Mapped[int] = mapped_column(ForeignKey("plantillas_rutina.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    configuracion: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    cambios_descripcion: Mapped[Optional[str]] = mapped_column(Text)
    creada_por: Mapped[Optional[int]] = mapped_column(Integer)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    es_actual: Mapped[bool] = mapped_column(Boolean, server_default="false")

    plantilla: Mapped["PlantillaRutina"] = relationship("PlantillaRutina", back_populates="versiones")

    __table_args__ = (
        UniqueConstraint("plantilla_id", "version", name="uq_plantilla_version"),
        Index("idx_plantillas_versiones_plantilla_id", "plantilla_id"),
        Index("idx_plantillas_versiones_es_actual", "es_actual"),
        Index("idx_plantillas_versiones_fecha_creacion", "fecha_creacion"),
    )


class PlantillaAnalitica(TenantBase):
    __tablename__ = "plantilla_analitica"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plantilla_id: Mapped[int] = mapped_column(ForeignKey("plantillas_rutina.id", ondelete="CASCADE"), nullable=False)
    gimnasio_id: Mapped[Optional[int]] = mapped_column(Integer)
    usuario_id: Mapped[Optional[int]] = mapped_column(Integer)
    evento_tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    fecha_evento: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    datos_evento: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    tiempo_render_ms: Mapped[Optional[int]] = mapped_column(Integer)
    exitoso: Mapped[bool] = mapped_column(Boolean, server_default="true")
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    plantilla: Mapped["PlantillaRutina"] = relationship("PlantillaRutina", back_populates="analitica")

    __table_args__ = (
        Index("idx_plantilla_analitica_plantilla_id", "plantilla_id"),
        Index("idx_plantilla_analitica_gimnasio_id", "gimnasio_id"),
        Index("idx_plantilla_analitica_usuario_id", "usuario_id"),
        Index("idx_plantilla_analitica_evento_tipo", "evento_tipo"),
        Index("idx_plantilla_analitica_fecha_evento", "fecha_evento"),
    )
