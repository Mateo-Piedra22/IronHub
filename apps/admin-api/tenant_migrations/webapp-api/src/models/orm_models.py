"""
Tenant Bundle Models for Dynamic Template System

This module contains the ORM models needed for the tenant bundle
to support the dynamic template system migrations.
"""

from sqlalchemy.orm import declarative_base
from sqlalchemy import (
    Integer, String, Text, Boolean, DateTime, ForeignKey,
    Numeric, Index, func, Column, JSON, ARRAY
)

Base = declarative_base()

# Template system models for tenant bundle reference
class PlantillaRutina(Base):
    """Template for routine generation - Tenant Bundle Reference"""
    __tablename__ = "plantillas_rutina"
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text)
    categoria = Column(String(100), default="general")
    activa = Column(Boolean, default=True)
    publica = Column(Boolean, default=False)
    creada_por = Column(Integer, ForeignKey("usuarios.id"))
    fecha_creacion = Column(DateTime, server_default=func.current_timestamp())
    version_actual = Column(String(50), default="1.0.0")
    tags = Column(ARRAY(String), server_default="{}")
    uso_count = Column(Integer, default=0)

class PlantillaRutinaVersion(Base):
    """Template versioning - Tenant Bundle Reference"""
    __tablename__ = "plantillas_rutina_versiones"
    
    id = Column(Integer, primary_key=True)
    plantilla_id = Column(Integer, ForeignKey("plantillas_rutina.id"))
    version = Column(String(50), nullable=False)
    configuracion = Column(JSON)  # This would be JSONB in PostgreSQL
    creada_por = Column(Integer, ForeignKey("usuarios.id"))
    fecha_creacion = Column(DateTime, server_default=func.current_timestamp())
    es_actual = Column(Boolean, default=False)

class GimnasioPlantilla(Base):
    """Gym template assignments - Tenant Bundle Reference"""
    __tablename__ = "gimnasio_plantillas"
    
    id = Column(Integer, primary_key=True)
    gimnasio_id = Column(Integer, ForeignKey("gimnasios.id"))
    plantilla_id = Column(Integer, ForeignKey("plantillas_rutina.id"))
    activa = Column(Boolean, default=True)
    prioridad = Column(Integer, default=0)
    asignada_por = Column(Integer, ForeignKey("usuarios.id"))
    fecha_asignacion = Column(DateTime, server_default=func.current_timestamp())
    uso_count = Column(Integer, default=0)

class PlantillaAnalitica(Base):
    """Template analytics - Tenant Bundle Reference"""
    __tablename__ = "plantilla_analitica"
    
    id = Column(Integer, primary_key=True)
    plantilla_id = Column(Integer, ForeignKey("plantillas_rutina.id"))
    gimnasio_id = Column(Integer, ForeignKey("gimnasios.id"))
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    evento_tipo = Column(String(50), nullable=False)
    fecha_evento = Column(DateTime, server_default=func.current_timestamp())
    exitoso = Column(Boolean, default=True)

class PlantillaMercado(Base):
    """Template marketplace - Tenant Bundle Reference"""
    __tablename__ = "plantilla_mercado"
    
    id = Column(Integer, primary_key=True)
    plantilla_id = Column(Integer, ForeignKey("plantillas_rutina.id"))
    precio = Column(Numeric(10, 2), default=0.00)
    descargas = Column(Integer, default=0)
    rating_promedio = Column(Numeric(3, 2))
    featured = Column(Boolean, default=False)
    fecha_publicacion = Column(DateTime, server_default=func.current_timestamp())
