from typing import List, Optional, Any
from datetime import datetime, date, time
from sqlalchemy import (
    BigInteger,
    Integer,
    SmallInteger,
    String,
    Text,
    Boolean,
    Date,
    Time,
    DateTime,
    ForeignKey,
    Numeric,
    Index,
    CheckConstraint,
    func,
    text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, INET, ARRAY


class Base(DeclarativeBase):
    pass


# --- Usuarios y Roles ---


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    dni: Mapped[Optional[str]] = mapped_column(String(20), unique=True)
    telefono: Mapped[str] = mapped_column(String(50), nullable=False)
    pin: Mapped[Optional[str]] = mapped_column(String(100), server_default="123456")
    rol: Mapped[str] = mapped_column(String(50), nullable=False, server_default="socio")
    notas: Mapped[Optional[str]] = mapped_column(Text)
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")
    tipo_cuota: Mapped[Optional[str]] = mapped_column(
        String(100), server_default="estandar"
    )
    sucursal_registro_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sucursales.id", ondelete="SET NULL")
    )
    ultimo_pago: Mapped[Optional[date]] = mapped_column(Date)
    fecha_proximo_vencimiento: Mapped[Optional[date]] = mapped_column(Date)
    cuotas_vencidas: Mapped[Optional[int]] = mapped_column(Integer, server_default="0")

    # Relaciones
    pagos: Mapped[List["Pago"]] = relationship(
        "Pago", back_populates="usuario", cascade="all, delete-orphan"
    )
    pagos_idempotency: Mapped[List["PagoIdempotency"]] = relationship(
        "PagoIdempotency", back_populates="usuario", cascade="all, delete-orphan"
    )
    asistencias: Mapped[List["Asistencia"]] = relationship(
        "Asistencia", back_populates="usuario", cascade="all, delete-orphan"
    )
    clase_inscripciones: Mapped[List["ClaseUsuario"]] = relationship(
        "ClaseUsuario", back_populates="usuario", cascade="all, delete-orphan"
    )
    clase_lista_espera: Mapped[List["ClaseListaEspera"]] = relationship(
        "ClaseListaEspera", back_populates="usuario", cascade="all, delete-orphan"
    )
    notificaciones_cupo: Mapped[List["NotificacionCupo"]] = relationship(
        "NotificacionCupo", back_populates="usuario", cascade="all, delete-orphan"
    )
    rutinas: Mapped[List["Rutina"]] = relationship(
        "Rutina",
        back_populates="usuario",
        foreign_keys="[Rutina.usuario_id]",
        cascade="all, delete-orphan",
    )
    plantillas_creadas: Mapped[List["PlantillaRutina"]] = relationship(
        "PlantillaRutina",
        back_populates="creador",
        foreign_keys="[PlantillaRutina.creada_por]",
        cascade="all, delete-orphan",
    )
    plantillas_versiones: Mapped[List["PlantillaRutinaVersion"]] = relationship(
        "PlantillaRutinaVersion",
        back_populates="creador",
        foreign_keys="[PlantillaRutinaVersion.creada_por]",
        cascade="all, delete-orphan",
    )
    gimnasio_plantillas_asignadas: Mapped[List["GimnasioPlantilla"]] = relationship(
        "GimnasioPlantilla",
        back_populates="asignador",
        foreign_keys="[GimnasioPlantilla.asignada_por]",
        cascade="all, delete-orphan",
    )
    plantilla_analitica: Mapped[List["PlantillaAnalitica"]] = relationship(
        "PlantillaAnalitica",
        back_populates="usuario",
        foreign_keys="[PlantillaAnalitica.usuario_id]",
        cascade="all, delete-orphan",
    )
    usuario_notas: Mapped[List["UsuarioNota"]] = relationship(
        "UsuarioNota",
        back_populates="usuario",
        foreign_keys="[UsuarioNota.usuario_id]",
        cascade="all, delete-orphan",
    )
    usuario_estados: Mapped[List["UsuarioEstado"]] = relationship(
        "UsuarioEstado",
        back_populates="usuario",
        foreign_keys="[UsuarioEstado.usuario_id]",
        cascade="all, delete-orphan",
    )
    usuario_etiquetas: Mapped[List["UsuarioEtiqueta"]] = relationship(
        "UsuarioEtiqueta",
        back_populates="usuario",
        foreign_keys="[UsuarioEtiqueta.usuario_id]",
        cascade="all, delete-orphan",
    )
    historial_estados: Mapped[List["HistorialEstado"]] = relationship(
        "HistorialEstado",
        back_populates="usuario",
        foreign_keys="[HistorialEstado.usuario_id]",
        cascade="all, delete-orphan",
    )

    profesor_perfil: Mapped[Optional["Profesor"]] = relationship(
        "Profesor",
        back_populates="usuario",
        uselist=False,
        cascade="all, delete-orphan",
    )
    staff_profile: Mapped[Optional["StaffProfile"]] = relationship(
        "StaffProfile",
        back_populates="usuario",
        uselist=False,
        cascade="all, delete-orphan",
    )
    staff_permission: Mapped[Optional["StaffPermission"]] = relationship(
        "StaffPermission",
        back_populates="usuario",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_usuarios_nombre", "nombre"),
        Index("idx_usuarios_dni", "dni"),
        Index("idx_usuarios_activo", "activo"),
        Index("idx_usuarios_rol", "rol"),
        Index("idx_usuarios_rol_nombre", "rol", "nombre"),
        Index("idx_usuarios_activo_rol_nombre", "activo", "rol", "nombre"),
    )


# --- Pagos ---


class Pago(Base):
    __tablename__ = "pagos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    sucursal_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sucursales.id", ondelete="SET NULL")
    )
    tipo_cuota_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tipos_cuota.id", ondelete="SET NULL")
    )
    monto: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    mes: Mapped[int] = mapped_column(Integer, nullable=False)
    año: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_pago: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    metodo_pago_id: Mapped[Optional[int]] = mapped_column(
        Integer
    )  # Could link to metodos_pago if strict
    concepto: Mapped[Optional[str]] = mapped_column(String(100))
    metodo_pago: Mapped[Optional[str]] = mapped_column(String(50))
    estado: Mapped[Optional[str]] = mapped_column(String(20), server_default="pagado")

    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="pagos")
    detalles: Mapped[List["PagoDetalle"]] = relationship(
        "PagoDetalle", back_populates="pago", cascade="all, delete-orphan"
    )
    idempotency_records: Mapped[List["PagoIdempotency"]] = relationship(
        "PagoIdempotency", back_populates="pago", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("usuario_id", "mes", "año", name="idx_pagos_usuario_mes_año"),
        Index("idx_pagos_usuario_id", "usuario_id"),
        Index("idx_pagos_sucursal_id", "sucursal_id"),
        Index("idx_pagos_tipo_cuota_id", "tipo_cuota_id"),
        Index("idx_pagos_fecha", "fecha_pago"),
        Index(
            "idx_pagos_month_year",
            text("(EXTRACT(MONTH FROM fecha_pago))"),
            text("(EXTRACT(YEAR FROM fecha_pago))"),
        ),
        Index("idx_pagos_usuario_fecha_desc", "usuario_id", text("fecha_pago DESC")),
    )


class PagoDetalle(Base):
    __tablename__ = "pago_detalles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pago_id: Mapped[int] = mapped_column(
        ForeignKey("pagos.id", ondelete="CASCADE"), nullable=False
    )
    concepto_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("conceptos_pago.id", ondelete="SET NULL")
    )
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    cantidad: Mapped[float] = mapped_column(Numeric(10, 2), server_default="1")
    precio_unitario: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    descuento: Mapped[float] = mapped_column(Numeric(10, 2), server_default="0")
    total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    pago: Mapped["Pago"] = relationship("Pago", back_populates="detalles")
    concepto_rel: Mapped[Optional["ConceptoPago"]] = relationship("ConceptoPago")

    __table_args__ = (
        Index("idx_pago_detalles_pago_id", "pago_id"),
        Index("idx_pago_detalles_concepto_id", "concepto_id"),
    )


class MetodoPago(Base):
    __tablename__ = "metodos_pago"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    icono: Mapped[Optional[str]] = mapped_column(String(10))
    color: Mapped[str] = mapped_column(String(7), server_default="#3498db")
    comision: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2), server_default="0.0"
    )
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    descripcion: Mapped[Optional[str]] = mapped_column(Text)


class ConceptoPago(Base):
    __tablename__ = "conceptos_pago"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    precio_base: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), server_default="0.0"
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, server_default="fijo")
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )


class NumeracionComprobante(Base):
    __tablename__ = "numeracion_comprobantes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo_comprobante: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    prefijo: Mapped[str] = mapped_column(String(10), nullable=False, server_default="")
    numero_inicial: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )
    separador: Mapped[str] = mapped_column(
        String(5), nullable=False, server_default="-"
    )
    reiniciar_anual: Mapped[Optional[bool]] = mapped_column(
        Boolean, server_default="false"
    )
    longitud_numero: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="8"
    )
    activo: Mapped[Optional[bool]] = mapped_column(Boolean, server_default="true")
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )


class ComprobantePago(Base):
    __tablename__ = "comprobantes_pago"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    numero_comprobante: Mapped[str] = mapped_column(String(50), nullable=False)
    pago_id: Mapped[int] = mapped_column(
        ForeignKey("pagos.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    tipo_comprobante: Mapped[str] = mapped_column(String(50), server_default="recibo")
    monto_total: Mapped[float] = mapped_column(Numeric(10, 2), server_default="0.0")
    estado: Mapped[Optional[str]] = mapped_column(String(20), server_default="emitido")
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    archivo_pdf: Mapped[Optional[str]] = mapped_column(String(500))
    plantilla_id: Mapped[Optional[int]] = mapped_column(Integer)
    datos_comprobante: Mapped[Optional[dict]] = mapped_column(JSONB)
    emitido_por: Mapped[Optional[str]] = mapped_column(String(255))

    pago: Mapped["Pago"] = relationship("Pago")
    usuario: Mapped["Usuario"] = relationship("Usuario")

    __table_args__ = (
        Index("idx_comprobantes_pago_numero", "numero_comprobante"),
        Index("idx_comprobantes_pago_pago_id", "pago_id"),
        Index("idx_comprobantes_pago_usuario_id", "usuario_id"),
        Index("idx_comprobantes_pago_fecha", "fecha_creacion"),
    )


class TipoCuota(Base):
    __tablename__ = "tipos_cuota"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    precio: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    icono_path: Mapped[Optional[str]] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")
    all_sucursales: Mapped[bool] = mapped_column(Boolean, server_default="true")
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    duracion_dias: Mapped[Optional[int]] = mapped_column(Integer, server_default="30")
    fecha_modificacion: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )


# --- Sucursales (Multi-sucursal) ---


class PagoIdempotency(Base):
    __tablename__ = "pagos_idempotency"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    pago_id: Mapped[int] = mapped_column(
        ForeignKey("pagos.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    mes: Mapped[int] = mapped_column(Integer, nullable=False)
    año: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    pago: Mapped["Pago"] = relationship("Pago", back_populates="idempotency_records")
    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="pagos_idempotency")


class Sucursal(Base):
    __tablename__ = "sucursales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    codigo: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    direccion: Mapped[Optional[str]] = mapped_column(Text)
    timezone: Mapped[Optional[str]] = mapped_column(String(80))
    station_key: Mapped[Optional[str]] = mapped_column(String(64))
    activa: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    __table_args__ = (
        Index("idx_sucursales_activa", "activa"),
        Index(
            "uq_sucursales_station_key",
            "station_key",
            unique=True,
            postgresql_where=text("station_key IS NOT NULL AND TRIM(station_key) <> ''"),
        ),
    )


class UsuarioSucursal(Base):
    __tablename__ = "usuario_sucursales"

    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    sucursal_id: Mapped[int] = mapped_column(
        ForeignKey("sucursales.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )


class Membership(Base):
    __tablename__ = "memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    plan_name: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="active"
    )
    start_date: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    all_sucursales: Mapped[bool] = mapped_column(Boolean, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    __table_args__ = (
        Index("idx_memberships_usuario_status", "usuario_id", "status"),
        Index("idx_memberships_status_end_date", "status", "end_date"),
    )


class MembershipSucursal(Base):
    __tablename__ = "membership_sucursales"

    membership_id: Mapped[int] = mapped_column(
        ForeignKey("memberships.id", ondelete="CASCADE"), primary_key=True
    )
    sucursal_id: Mapped[int] = mapped_column(
        ForeignKey("sucursales.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )


class FeatureFlags(Base):
    __tablename__ = "feature_flags"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    flags: Mapped[Any] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )


class FeatureFlagsOverride(Base):
    __tablename__ = "feature_flags_overrides"

    sucursal_id: Mapped[int] = mapped_column(
        ForeignKey("sucursales.id", ondelete="CASCADE"), primary_key=True
    )
    flags: Mapped[Any] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )



class TipoCuotaSucursal(Base):
    __tablename__ = "tipo_cuota_sucursales"

    tipo_cuota_id: Mapped[int] = mapped_column(
        ForeignKey("tipos_cuota.id", ondelete="CASCADE"), primary_key=True
    )
    sucursal_id: Mapped[int] = mapped_column(
        ForeignKey("sucursales.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )


class TipoCuotaClasePermiso(Base):
    __tablename__ = "tipo_cuota_clases_permisos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo_cuota_id: Mapped[int] = mapped_column(
        ForeignKey("tipos_cuota.id", ondelete="CASCADE"), nullable=False
    )
    sucursal_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sucursales.id", ondelete="CASCADE")
    )
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    allow: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    __table_args__ = (
        UniqueConstraint(
            "tipo_cuota_id",
            "sucursal_id",
            "target_type",
            "target_id",
            name="uq_tipo_cuota_clases_permiso",
        ),
        Index("idx_tipo_cuota_clases_permiso_tipo_cuota", "tipo_cuota_id"),
        Index("idx_tipo_cuota_clases_permiso_sucursal", "sucursal_id"),
    )


class UsuarioAccesoSucursal(Base):
    __tablename__ = "usuario_accesos_sucursales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    sucursal_id: Mapped[int] = mapped_column(
        ForeignKey("sucursales.id", ondelete="CASCADE"), nullable=False
    )
    allow: Mapped[bool] = mapped_column(Boolean, nullable=False)
    motivo: Mapped[Optional[str]] = mapped_column(Text)
    starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    __table_args__ = (
        UniqueConstraint(
            "usuario_id", "sucursal_id", name="uq_usuario_accesos_sucursales"
        ),
        Index("idx_usuario_accesos_sucursales_usuario", "usuario_id"),
        Index("idx_usuario_accesos_sucursales_sucursal", "sucursal_id"),
    )


class UsuarioPermisoClase(Base):
    __tablename__ = "usuario_permisos_clases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    sucursal_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sucursales.id", ondelete="CASCADE")
    )
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    allow: Mapped[bool] = mapped_column(Boolean, nullable=False)
    motivo: Mapped[Optional[str]] = mapped_column(Text)
    starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    __table_args__ = (
        UniqueConstraint(
            "usuario_id",
            "sucursal_id",
            "target_type",
            "target_id",
            name="uq_usuario_permisos_clases",
        ),
        Index("idx_usuario_permisos_clases_usuario", "usuario_id"),
        Index("idx_usuario_permisos_clases_sucursal", "sucursal_id"),
    )


# --- Asistencias ---


class Asistencia(Base):
    __tablename__ = "asistencias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    sucursal_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sucursales.id", ondelete="SET NULL")
    )
    fecha: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    hora_registro: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    hora_entrada: Mapped[Optional[time]] = mapped_column(Time)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False, server_default="unknown")

    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="asistencias")

    __table_args__ = (
        Index("idx_asistencias_usuario_id", "usuario_id"),
        Index("idx_asistencias_fecha", "fecha"),
        Index("idx_asistencias_usuario_fecha", "usuario_id", "fecha"),
        Index("idx_asistencias_usuario_fecha_desc", "usuario_id", text("fecha DESC")),
        Index("idx_asistencias_sucursal_fecha", "sucursal_id", "fecha"),
    )


# --- Clases ---


class Clase(Base):
    __tablename__ = "clases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    activa: Mapped[bool] = mapped_column(Boolean, server_default="true")
    sucursal_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sucursales.id", ondelete="SET NULL")
    )
    tipo_clase_id: Mapped[Optional[int]] = mapped_column(
        Integer
    )  # Could be FK if table types_clases exists and we want to enforce

    horarios: Mapped[List["ClaseHorario"]] = relationship(
        "ClaseHorario", back_populates="clase", cascade="all, delete-orphan"
    )
    bloques: Mapped[List["ClaseBloque"]] = relationship(
        "ClaseBloque", back_populates="clase", cascade="all, delete-orphan"
    )
    ejercicios: Mapped[List["ClaseEjercicio"]] = relationship(
        "ClaseEjercicio", back_populates="clase", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_clases_nombre", "nombre"),
        Index(
            "idx_clases_activa_true_nombre",
            "nombre",
            postgresql_where=text("activa = TRUE"),
        ),
        Index("idx_clases_tipo_clase_id", "tipo_clase_id"),
        Index("idx_clases_sucursal_id", "sucursal_id"),
    )


class TipoClase(Base):
    __tablename__ = "tipos_clases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")


class ClaseHorario(Base):
    __tablename__ = "clases_horarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clase_id: Mapped[int] = mapped_column(
        ForeignKey("clases.id", ondelete="CASCADE"), nullable=False
    )
    dia_semana: Mapped[str] = mapped_column(String(20), nullable=False)
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time, nullable=False)
    cupo_maximo: Mapped[Optional[int]] = mapped_column(Integer, server_default="20")
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")

    clase: Mapped["Clase"] = relationship("Clase", back_populates="horarios")
    lista_espera: Mapped[List["ClaseListaEspera"]] = relationship(
        "ClaseListaEspera", back_populates="clase_horario", cascade="all, delete-orphan"
    )
    profesores_asignados: Mapped[List["ProfesorClaseAsignacion"]] = relationship(
        "ProfesorClaseAsignacion",
        back_populates="clase_horario",
        cascade="all, delete-orphan",
    )
    clase_usuarios: Mapped[List["ClaseUsuario"]] = relationship(
        "ClaseUsuario", back_populates="clase_horario", cascade="all, delete-orphan"
    )
    notificaciones_cupo: Mapped[List["NotificacionCupo"]] = relationship(
        "NotificacionCupo", back_populates="clase_horario", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_clases_horarios_clase_id", "clase_id"),)


class ClaseUsuario(Base):
    __tablename__ = "clase_usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clase_horario_id: Mapped[int] = mapped_column(
        ForeignKey("clases_horarios.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    fecha_inscripcion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    clase_horario: Mapped["ClaseHorario"] = relationship(
        "ClaseHorario", back_populates="clase_usuarios"
    )
    usuario: Mapped["Usuario"] = relationship(
        "Usuario", back_populates="clase_inscripciones"
    )

    __table_args__ = (
        UniqueConstraint(
            "clase_horario_id",
            "usuario_id",
            name="clase_usuarios_clase_horario_id_usuario_id_key",
        ),
        Index("idx_clase_usuarios_clase_horario_id", "clase_horario_id"),
        Index("idx_clase_usuarios_usuario_id", "usuario_id"),
    )


class ClaseListaEspera(Base):
    __tablename__ = "clase_lista_espera"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clase_horario_id: Mapped[int] = mapped_column(
        ForeignKey("clases_horarios.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    posicion: Mapped[int] = mapped_column(Integer, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    clase_horario: Mapped["ClaseHorario"] = relationship(
        "ClaseHorario", back_populates="lista_espera"
    )
    usuario: Mapped["Usuario"] = relationship(
        "Usuario", back_populates="clase_lista_espera"
    )

    __table_args__ = (
        UniqueConstraint(
            "clase_horario_id",
            "usuario_id",
            name="clase_lista_espera_clase_horario_id_usuario_id_key",
        ),
        Index("idx_clase_lista_espera_clase", "clase_horario_id"),
        Index("idx_clase_lista_espera_activo", "activo"),
        Index("idx_clase_lista_espera_posicion", "posicion"),
    )


class NotificacionCupo(Base):
    __tablename__ = "notificaciones_cupos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    clase_horario_id: Mapped[int] = mapped_column(
        ForeignKey("clases_horarios.id", ondelete="CASCADE"), nullable=False
    )
    tipo_notificacion: Mapped[str] = mapped_column(String(50), nullable=False)
    mensaje: Mapped[Optional[str]] = mapped_column(Text)
    leida: Mapped[bool] = mapped_column(Boolean, server_default="false")
    activa: Mapped[bool] = mapped_column(Boolean, server_default="true")
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    fecha_lectura: Mapped[Optional[datetime]] = mapped_column(DateTime)

    clase_horario: Mapped["ClaseHorario"] = relationship(
        "ClaseHorario", back_populates="notificaciones_cupo"
    )
    usuario: Mapped["Usuario"] = relationship(
        "Usuario", back_populates="notificaciones_cupo"
    )

    __table_args__ = (
        CheckConstraint(
            "tipo_notificacion IN ('cupo_liberado','promocion','recordatorio')",
            name="notificaciones_cupos_tipo_notificacion_check",
        ),
        Index("idx_notif_cupos_usuario_activa", "usuario_id", "activa"),
        Index("idx_notif_cupos_clase", "clase_horario_id"),
        Index("idx_notif_cupos_leida", "leida"),
        Index("idx_notif_cupos_tipo", "tipo_notificacion"),
    )


# --- Ejercicios y Rutinas ---


class Ejercicio(Base):
    __tablename__ = "ejercicios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    grupo_muscular: Mapped[Optional[str]] = mapped_column(String(100))
    objetivo: Mapped[Optional[str]] = mapped_column(
        String(100), server_default="general"
    )
    equipamiento: Mapped[Optional[str]] = mapped_column(String(100))
    variantes: Mapped[Optional[str]] = mapped_column(Text)
    video_url: Mapped[Optional[str]] = mapped_column(String(512))
    video_mime: Mapped[Optional[str]] = mapped_column(String(50))
    sucursal_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sucursales.id", ondelete="SET NULL")
    )


class Rutina(Base):
    __tablename__ = "rutinas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE")
    )
    creada_por_usuario_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL")
    )
    nombre_rutina: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    dias_semana: Mapped[Optional[int]] = mapped_column(Integer)
    semanas: Mapped[Optional[int]] = mapped_column(Integer, server_default="4")
    categoria: Mapped[Optional[str]] = mapped_column(
        String(100), server_default="general"
    )
    sucursal_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sucursales.id", ondelete="SET NULL")
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    activa: Mapped[bool] = mapped_column(Boolean, server_default="true")
    uuid_rutina: Mapped[Optional[str]] = mapped_column(String(36), unique=True)
    plantilla_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("plantillas_rutina.id", ondelete="SET NULL")
    )

    usuario: Mapped[Optional["Usuario"]] = relationship(
        "Usuario", back_populates="rutinas", foreign_keys=[usuario_id]
    )
    creada_por_usuario: Mapped[Optional["Usuario"]] = relationship(
        "Usuario", foreign_keys=[creada_por_usuario_id]
    )
    plantilla: Mapped[Optional["PlantillaRutina"]] = relationship(
        "PlantillaRutina", back_populates="rutinas"
    )
    ejercicios: Mapped[List["RutinaEjercicio"]] = relationship(
        "RutinaEjercicio", back_populates="rutina", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_rutinas_uuid_rutina", "uuid_rutina", unique=True),
        Index("idx_rutinas_usuario_id", "usuario_id"),
        Index("idx_rutinas_creada_por_usuario_id", "creada_por_usuario_id"),
        Index("idx_rutinas_sucursal_id", "sucursal_id"),
        Index("idx_rutinas_plantilla_id", "plantilla_id"),
        Index("idx_rutinas_semanas", "semanas"),
    )


class RutinaEjercicio(Base):
    __tablename__ = "rutina_ejercicios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rutina_id: Mapped[int] = mapped_column(
        ForeignKey("rutinas.id", ondelete="CASCADE"), nullable=False
    )
    ejercicio_id: Mapped[int] = mapped_column(
        ForeignKey("ejercicios.id", ondelete="CASCADE"), nullable=False
    )
    dia_semana: Mapped[Optional[int]] = mapped_column(Integer)
    series: Mapped[Optional[int]] = mapped_column(Integer)
    repeticiones: Mapped[Optional[str]] = mapped_column(String(50))
    orden: Mapped[Optional[int]] = mapped_column(Integer)

    rutina: Mapped["Rutina"] = relationship("Rutina", back_populates="ejercicios")
    ejercicio: Mapped["Ejercicio"] = relationship("Ejercicio")

    __table_args__ = (
        Index("idx_rutina_ejercicios_rutina_id", "rutina_id"),
        Index("idx_rutina_ejercicios_ejercicio_id", "ejercicio_id"),
        Index("idx_rutina_ejercicios_rutina_ejercicio", "rutina_id", "ejercicio_id"),
    )


class ClaseEjercicio(Base):
    __tablename__ = "clase_ejercicios"

    clase_id: Mapped[int] = mapped_column(
        ForeignKey("clases.id", ondelete="CASCADE"), primary_key=True
    )
    ejercicio_id: Mapped[int] = mapped_column(
        ForeignKey("ejercicios.id", ondelete="CASCADE"), primary_key=True
    )
    orden: Mapped[Optional[int]] = mapped_column(Integer, server_default="0")
    series: Mapped[Optional[int]] = mapped_column(Integer, server_default="0")
    repeticiones: Mapped[Optional[str]] = mapped_column(String(50), server_default="")
    descanso_segundos: Mapped[Optional[int]] = mapped_column(
        Integer, server_default="0"
    )
    notas: Mapped[Optional[str]] = mapped_column(Text)

    clase: Mapped["Clase"] = relationship("Clase", back_populates="ejercicios")
    ejercicio: Mapped["Ejercicio"] = relationship("Ejercicio")

    __table_args__ = (
        Index("idx_clase_ejercicios_ejercicio_id", "ejercicio_id"),
        Index("idx_clase_ejercicios_clase_orden", "clase_id", "orden"),
    )


class ClaseBloque(Base):
    __tablename__ = "clase_bloques"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clase_id: Mapped[int] = mapped_column(
        ForeignKey("clases.id", ondelete="CASCADE"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    clase: Mapped["Clase"] = relationship("Clase", back_populates="bloques")
    items: Mapped[List["ClaseBloqueItem"]] = relationship(
        "ClaseBloqueItem", back_populates="bloque", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_clase_bloques_clase", "clase_id"),
        Index("idx_clase_bloques_nombre", "nombre"),
    )


class ClaseBloqueItem(Base):
    __tablename__ = "clase_bloque_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bloque_id: Mapped[int] = mapped_column(
        ForeignKey("clase_bloques.id", ondelete="CASCADE"), nullable=False
    )
    ejercicio_id: Mapped[int] = mapped_column(
        ForeignKey("ejercicios.id", ondelete="CASCADE"), nullable=False
    )
    orden: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    series: Mapped[Optional[int]] = mapped_column(Integer, server_default="0")
    repeticiones: Mapped[Optional[str]] = mapped_column(Text)
    descanso_segundos: Mapped[Optional[int]] = mapped_column(
        Integer, server_default="0"
    )
    notas: Mapped[Optional[str]] = mapped_column(Text)

    bloque: Mapped["ClaseBloque"] = relationship("ClaseBloque", back_populates="items")
    ejercicio: Mapped["Ejercicio"] = relationship("Ejercicio")

    __table_args__ = (
        Index("idx_bloque_items_bloque", "bloque_id"),
        Index("idx_bloque_items_bloque_orden", "bloque_id", "orden"),
    )


class EjercicioGrupo(Base):
    __tablename__ = "ejercicio_grupos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    items: Mapped[List["EjercicioGrupoItem"]] = relationship(
        "EjercicioGrupoItem", back_populates="grupo", cascade="all, delete-orphan"
    )


class EjercicioGrupoItem(Base):
    __tablename__ = "ejercicio_grupo_items"

    grupo_id: Mapped[int] = mapped_column(
        ForeignKey("ejercicio_grupos.id", ondelete="CASCADE"), primary_key=True
    )
    ejercicio_id: Mapped[int] = mapped_column(
        ForeignKey("ejercicios.id", ondelete="CASCADE"), primary_key=True
    )

    grupo: Mapped["EjercicioGrupo"] = relationship(
        "EjercicioGrupo", back_populates="items"
    )
    ejercicio: Mapped["Ejercicio"] = relationship("Ejercicio")


# --- Profesores ---


class Profesor(Base):
    __tablename__ = "profesores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    tipo: Mapped[Optional[str]] = mapped_column(
        String(50), server_default="Musculación"
    )
    especialidades: Mapped[Optional[str]] = mapped_column(Text)
    certificaciones: Mapped[Optional[str]] = mapped_column(Text)
    experiencia_años: Mapped[Optional[int]] = mapped_column(Integer, server_default="0")
    tarifa_por_hora: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), server_default="0.0"
    )
    horario_disponible: Mapped[Optional[str]] = mapped_column(Text)
    fecha_contratacion: Mapped[Optional[date]] = mapped_column(Date)
    estado: Mapped[Optional[str]] = mapped_column(String(20), server_default="activo")
    biografia: Mapped[Optional[str]] = mapped_column(Text)
    foto_perfil: Mapped[Optional[str]] = mapped_column(String(255))
    telefono_emergencia: Mapped[Optional[str]] = mapped_column(String(50))
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    usuario: Mapped["Usuario"] = relationship(
        "Usuario", back_populates="profesor_perfil"
    )
    horarios_asignados: Mapped[List["HorarioProfesor"]] = relationship(
        "HorarioProfesor", back_populates="profesor", cascade="all, delete-orphan"
    )
    disponibilidad_horaria: Mapped[List["ProfesorHorarioDisponibilidad"]] = (
        relationship(
            "ProfesorHorarioDisponibilidad",
            back_populates="profesor",
            cascade="all, delete-orphan",
        )
    )
    evaluaciones: Mapped[List["ProfesorEvaluacion"]] = relationship(
        "ProfesorEvaluacion", back_populates="profesor", cascade="all, delete-orphan"
    )
    disponibilidad_especifica: Mapped[List["ProfesorDisponibilidad"]] = relationship(
        "ProfesorDisponibilidad",
        back_populates="profesor",
        cascade="all, delete-orphan",
    )
    asignaciones_clase: Mapped[List["ProfesorClaseAsignacion"]] = relationship(
        "ProfesorClaseAsignacion",
        back_populates="profesor",
        cascade="all, delete-orphan",
    )
    profesor_especialidades: Mapped[List["ProfesorEspecialidad"]] = relationship(
        "ProfesorEspecialidad", back_populates="profesor", cascade="all, delete-orphan"
    )
    profesor_certificaciones: Mapped[List["ProfesorCertificacion"]] = relationship(
        "ProfesorCertificacion", back_populates="profesor", cascade="all, delete-orphan"
    )
    horas_trabajadas: Mapped[List["ProfesorHoraTrabajada"]] = relationship(
        "ProfesorHoraTrabajada", back_populates="profesor", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "estado IN ('activo', 'inactivo', 'vacaciones')",
            name="profesores_estado_check",
        ),
    )


class HorarioProfesor(Base):
    __tablename__ = "horarios_profesores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profesor_id: Mapped[int] = mapped_column(
        ForeignKey("profesores.id", ondelete="CASCADE"), nullable=False
    )
    dia_semana: Mapped[str] = mapped_column(String(20), nullable=False)
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time, nullable=False)
    disponible: Mapped[bool] = mapped_column(Boolean, server_default="true")
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    profesor: Mapped["Profesor"] = relationship(
        "Profesor", back_populates="horarios_asignados"
    )
    suplencias_generales: Mapped[List["ProfesorSuplenciaGeneral"]] = relationship(
        "ProfesorSuplenciaGeneral", back_populates="horario_profesor"
    )

    __table_args__ = (Index("idx_horarios_profesores_profesor_id", "profesor_id"),)


class ProfesorHorarioDisponibilidad(Base):
    __tablename__ = "profesores_horarios_disponibilidad"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profesor_id: Mapped[int] = mapped_column(
        ForeignKey("profesores.id", ondelete="CASCADE"), nullable=False
    )
    dia_semana: Mapped[int] = mapped_column(Integer, nullable=False)
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time, nullable=False)
    disponible: Mapped[bool] = mapped_column(Boolean, server_default="true")
    tipo_disponibilidad: Mapped[Optional[str]] = mapped_column(
        String(50), server_default="regular"
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    profesor: Mapped["Profesor"] = relationship(
        "Profesor", back_populates="disponibilidad_horaria"
    )

    __table_args__ = (
        CheckConstraint(
            "dia_semana BETWEEN 0 AND 6",
            name="profesores_horarios_disponibilidad_dia_semana_check",
        ),
        Index("idx_profesores_horarios_disponibilidad_profesor_id", "profesor_id"),
    )


class ProfesorEvaluacion(Base):
    __tablename__ = "profesor_evaluaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profesor_id: Mapped[int] = mapped_column(
        ForeignKey("profesores.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    puntuacion: Mapped[int] = mapped_column(Integer)
    comentario: Mapped[Optional[str]] = mapped_column(Text)
    fecha_evaluacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    profesor: Mapped["Profesor"] = relationship(
        "Profesor", back_populates="evaluaciones"
    )
    usuario: Mapped["Usuario"] = relationship("Usuario")

    __table_args__ = (
        CheckConstraint(
            "puntuacion >= 1 AND puntuacion <= 5",
            name="profesor_evaluaciones_puntuacion_check",
        ),
        UniqueConstraint(
            "profesor_id",
            "usuario_id",
            name="profesor_evaluaciones_profesor_id_usuario_id_key",
        ),
        Index("idx_profesor_evaluaciones_profesor_id", "profesor_id"),
        Index("idx_profesor_evaluaciones_usuario_id", "usuario_id"),
    )


class ProfesorDisponibilidad(Base):
    __tablename__ = "profesor_disponibilidad"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profesor_id: Mapped[int] = mapped_column(
        ForeignKey("profesores.id", ondelete="CASCADE"), nullable=False
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    tipo_disponibilidad: Mapped[str] = mapped_column(String(50), nullable=False)
    hora_inicio: Mapped[Optional[time]] = mapped_column(Time)
    hora_fin: Mapped[Optional[time]] = mapped_column(Time)
    notas: Mapped[Optional[str]] = mapped_column(Text)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    fecha_modificacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    profesor: Mapped["Profesor"] = relationship(
        "Profesor", back_populates="disponibilidad_especifica"
    )

    __table_args__ = (
        CheckConstraint(
            "tipo_disponibilidad IN ('Disponible', 'No Disponible', 'Parcialmente Disponible')",
            name="profesor_disponibilidad_tipo_disponibilidad_check",
        ),
        UniqueConstraint(
            "profesor_id", "fecha", name="profesor_disponibilidad_profesor_id_fecha_key"
        ),
        Index("idx_profesor_disponibilidad_profesor_id", "profesor_id"),
        Index("idx_profesor_disponibilidad_fecha", "fecha"),
        Index("idx_profesor_disponibilidad_profesor_fecha", "profesor_id", "fecha"),
    )


class ProfesorClaseAsignacion(Base):
    __tablename__ = "profesor_clase_asignaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clase_horario_id: Mapped[int] = mapped_column(
        ForeignKey("clases_horarios.id", ondelete="CASCADE"), nullable=False
    )
    profesor_id: Mapped[int] = mapped_column(
        ForeignKey("profesores.id", ondelete="CASCADE"), nullable=False
    )
    fecha_asignacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    activa: Mapped[bool] = mapped_column(Boolean, server_default="true")

    clase_horario: Mapped["ClaseHorario"] = relationship(
        "ClaseHorario", back_populates="profesores_asignados"
    )
    profesor: Mapped["Profesor"] = relationship(
        "Profesor", back_populates="asignaciones_clase"
    )
    suplencias: Mapped[List["ProfesorSuplencia"]] = relationship(
        "ProfesorSuplencia", back_populates="asignacion", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "clase_horario_id",
            "profesor_id",
            name="profesor_clase_asignaciones_clase_horario_id_profesor_id_key",
        ),
        Index("idx_profesor_clase_asignaciones_profesor_id", "profesor_id"),
    )


class ProfesorSuplencia(Base):
    __tablename__ = "profesor_suplencias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asignacion_id: Mapped[int] = mapped_column(
        ForeignKey("profesor_clase_asignaciones.id", ondelete="CASCADE"), nullable=False
    )
    profesor_suplente_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("profesores.id", ondelete="SET NULL")
    )
    fecha_clase: Mapped[date] = mapped_column(Date, nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[Optional[str]] = mapped_column(
        String(20), server_default="Pendiente"
    )
    notas: Mapped[Optional[str]] = mapped_column(Text)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    fecha_resolucion: Mapped[Optional[datetime]] = mapped_column(DateTime)

    asignacion: Mapped["ProfesorClaseAsignacion"] = relationship(
        "ProfesorClaseAsignacion", back_populates="suplencias"
    )
    profesor_suplente: Mapped[Optional["Profesor"]] = relationship(
        "Profesor", foreign_keys=[profesor_suplente_id]
    )

    __table_args__ = (
        CheckConstraint(
            "estado IN ('Pendiente', 'Asignado', 'Confirmado', 'Cancelado')",
            name="profesor_suplencias_estado_check",
        ),
        Index(
            "idx_profesor_suplencias_asignacion_fecha", "asignacion_id", "fecha_clase"
        ),
        Index("idx_profesor_suplencias_asignacion", "asignacion_id"),
        Index("idx_profesor_suplencias_suplente", "profesor_suplente_id"),
        Index("idx_profesor_suplencias_estado", "estado"),
        Index("idx_profesor_suplencias_fecha_clase", "fecha_clase"),
    )


class ProfesorSuplenciaGeneral(Base):
    __tablename__ = "profesor_suplencias_generales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    horario_profesor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("horarios_profesores.id", ondelete="SET NULL")
    )
    profesor_original_id: Mapped[int] = mapped_column(
        ForeignKey("profesores.id", ondelete="CASCADE"), nullable=False
    )
    profesor_suplente_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("profesores.id", ondelete="SET NULL")
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time, nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[Optional[str]] = mapped_column(
        String(20), server_default="Pendiente"
    )
    notas: Mapped[Optional[str]] = mapped_column(Text)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    fecha_resolucion: Mapped[Optional[datetime]] = mapped_column(DateTime)

    horario_profesor: Mapped[Optional["HorarioProfesor"]] = relationship(
        "HorarioProfesor", back_populates="suplencias_generales"
    )
    profesor_original: Mapped["Profesor"] = relationship(
        "Profesor", foreign_keys=[profesor_original_id]
    )
    profesor_suplente: Mapped[Optional["Profesor"]] = relationship(
        "Profesor", foreign_keys=[profesor_suplente_id]
    )

    __table_args__ = (
        CheckConstraint(
            "estado IN ('Pendiente', 'Asignado', 'Confirmado', 'Cancelado')",
            name="profesor_suplencias_generales_estado_check",
        ),
        Index("idx_profesor_suplencias_generales_fecha", "fecha"),
        Index("idx_profesor_suplencias_generales_estado", "estado"),
    )


class Especialidad(Base):
    __tablename__ = "especialidades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    categoria: Mapped[Optional[str]] = mapped_column(String(50))
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    __table_args__ = (
        Index("idx_especialidades_nombre", "nombre"),
        Index("idx_especialidades_activo", "activo"),
    )


class ProfesorEspecialidad(Base):
    __tablename__ = "profesor_especialidades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profesor_id: Mapped[int] = mapped_column(
        ForeignKey("profesores.id", ondelete="CASCADE"), nullable=False
    )
    especialidad_id: Mapped[int] = mapped_column(
        ForeignKey("especialidades.id", ondelete="CASCADE"), nullable=False
    )
    fecha_asignacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")
    nivel_experiencia: Mapped[Optional[str]] = mapped_column(String(50))
    años_experiencia: Mapped[Optional[int]] = mapped_column(Integer, server_default="0")

    profesor: Mapped["Profesor"] = relationship(
        "Profesor", back_populates="profesor_especialidades"
    )
    especialidad: Mapped["Especialidad"] = relationship("Especialidad")

    __table_args__ = (
        UniqueConstraint(
            "profesor_id",
            "especialidad_id",
            name="profesor_especialidades_profesor_id_especialidad_id_key",
        ),
        Index("idx_profesor_especialidades_profesor_id", "profesor_id"),
        Index("idx_profesor_especialidades_especialidad_id", "especialidad_id"),
        Index("idx_profesor_especialidades_activo", "activo"),
    )


class ProfesorCertificacion(Base):
    __tablename__ = "profesor_certificaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profesor_id: Mapped[int] = mapped_column(
        ForeignKey("profesores.id", ondelete="CASCADE"), nullable=False
    )
    nombre_certificacion: Mapped[str] = mapped_column(String(200), nullable=False)
    institucion_emisora: Mapped[Optional[str]] = mapped_column(String(200))
    fecha_obtencion: Mapped[Optional[date]] = mapped_column(Date)
    fecha_vencimiento: Mapped[Optional[date]] = mapped_column(Date)
    numero_certificado: Mapped[Optional[str]] = mapped_column(String(100))
    archivo_adjunto: Mapped[Optional[str]] = mapped_column(String(500))
    estado: Mapped[Optional[str]] = mapped_column(String(20), server_default="vigente")
    notas: Mapped[Optional[str]] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    profesor: Mapped["Profesor"] = relationship(
        "Profesor", back_populates="profesor_certificaciones"
    )

    __table_args__ = (
        Index("idx_profesor_certificaciones_profesor_id", "profesor_id"),
        Index("idx_profesor_certificaciones_fecha_vencimiento", "fecha_vencimiento"),
        Index("idx_profesor_certificaciones_activo", "activo"),
    )


class ProfesorHoraTrabajada(Base):
    __tablename__ = "profesor_horas_trabajadas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profesor_id: Mapped[int] = mapped_column(
        ForeignKey("profesores.id", ondelete="CASCADE"), nullable=False
    )
    sucursal_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sucursales.id", ondelete="SET NULL")
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    hora_inicio: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    hora_fin: Mapped[Optional[datetime]] = mapped_column(DateTime)
    minutos_totales: Mapped[Optional[int]] = mapped_column(Integer)
    horas_totales: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    tipo_actividad: Mapped[Optional[str]] = mapped_column(String(50))
    clase_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("clases.id", ondelete="SET NULL")
    )
    notas: Mapped[Optional[str]] = mapped_column(Text)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    profesor: Mapped["Profesor"] = relationship(
        "Profesor", back_populates="horas_trabajadas"
    )
    clase: Mapped[Optional["Clase"]] = relationship("Clase")
    sucursal: Mapped[Optional["Sucursal"]] = relationship("Sucursal")

    __table_args__ = (
        Index(
            "uniq_sesion_activa_por_profesor",
            "profesor_id",
            unique=True,
            postgresql_where=text("hora_fin IS NULL"),
        ),
        Index("idx_profesor_horas_trabajadas_profesor_id", "profesor_id"),
        Index("idx_profesor_horas_trabajadas_fecha", "fecha"),
        Index("idx_profesor_horas_trabajadas_clase_id", "clase_id"),
        Index("idx_profesor_horas_trabajadas_sucursal_id", "sucursal_id"),
    )


# --- Staff / Empleados ---


class StaffProfile(Base):
    __tablename__ = "staff_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(50), nullable=False, server_default="empleado")
    estado: Mapped[str] = mapped_column(String(20), nullable=False, server_default="activo")
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="staff_profile")
    sesiones: Mapped[List["StaffSession"]] = relationship(
        "StaffSession", back_populates="staff", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "estado IN ('activo', 'inactivo', 'vacaciones')",
            name="staff_profiles_estado_check",
        ),
    )


class StaffSession(Base):
    __tablename__ = "staff_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    staff_id: Mapped[int] = mapped_column(
        ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False
    )
    sucursal_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sucursales.id", ondelete="SET NULL")
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    hora_inicio: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    hora_fin: Mapped[Optional[datetime]] = mapped_column(DateTime)
    minutos_totales: Mapped[Optional[int]] = mapped_column(Integer)
    notas: Mapped[Optional[str]] = mapped_column(Text)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    staff: Mapped["StaffProfile"] = relationship("StaffProfile", back_populates="sesiones")
    sucursal: Mapped[Optional["Sucursal"]] = relationship("Sucursal")

    __table_args__ = (
        Index(
            "uniq_sesion_activa_por_staff",
            "staff_id",
            unique=True,
            postgresql_where=text("hora_fin IS NULL"),
        ),
        Index("idx_staff_sessions_staff_id", "staff_id"),
        Index("idx_staff_sessions_fecha", "fecha"),
        Index("idx_staff_sessions_sucursal_id", "sucursal_id"),
    )


class WorkSessionPause(Base):
    __tablename__ = "work_session_pauses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    session_id: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    __table_args__ = (
        CheckConstraint(
            "session_kind IN ('profesor','staff')", name="work_session_pauses_kind_check"
        ),
        Index("idx_work_session_pauses_session", "session_kind", "session_id"),
        Index(
            "uniq_work_session_pause_active",
            "session_kind",
            "session_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
        Index("idx_work_session_pauses_started_at", "started_at"),
    )


class StaffPermission(Base):
    __tablename__ = "staff_permissions"

    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    scopes: Mapped[Any] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="staff_permission")


# --- Notas, Etiquetas, Estados ---


class UsuarioNota(Base):
    __tablename__ = "usuario_notas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    categoria: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="general"
    )
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    importancia: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="normal"
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    fecha_modificacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    activa: Mapped[bool] = mapped_column(Boolean, server_default="true")
    autor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL")
    )

    usuario: Mapped["Usuario"] = relationship(
        "Usuario", back_populates="usuario_notas", foreign_keys=[usuario_id]
    )
    autor: Mapped[Optional["Usuario"]] = relationship(
        "Usuario", foreign_keys=[autor_id]
    )

    __table_args__ = (
        CheckConstraint(
            "categoria IN ('general', 'medica', 'administrativa', 'comportamiento')",
            name="usuario_notas_categoria_check",
        ),
        CheckConstraint(
            "importancia IN ('baja', 'normal', 'alta', 'critica')",
            name="usuario_notas_importancia_check",
        ),
        Index("idx_usuario_notas_usuario_id", "usuario_id"),
        Index("idx_usuario_notas_autor_id", "autor_id"),
    )


class Etiqueta(Base):
    __tablename__ = "etiquetas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    color: Mapped[str] = mapped_column(
        String(7), nullable=False, server_default="#3498db"
    )
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")


class UsuarioEtiqueta(Base):
    __tablename__ = "usuario_etiquetas"

    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    etiqueta_id: Mapped[int] = mapped_column(
        ForeignKey("etiquetas.id", ondelete="CASCADE"), primary_key=True
    )
    fecha_asignacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    asignado_por: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL")
    )

    usuario: Mapped["Usuario"] = relationship(
        "Usuario", back_populates="usuario_etiquetas", foreign_keys=[usuario_id]
    )
    etiqueta: Mapped["Etiqueta"] = relationship("Etiqueta")
    asignador: Mapped[Optional["Usuario"]] = relationship(
        "Usuario", foreign_keys=[asignado_por]
    )

    __table_args__ = (
        Index("idx_usuario_etiquetas_usuario_id", "usuario_id"),
        Index("idx_usuario_etiquetas_etiqueta_id", "etiqueta_id"),
        Index("idx_usuario_etiquetas_asignado_por", "asignado_por"),
    )


class UsuarioEstado(Base):
    __tablename__ = "usuario_estados"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    estado: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    fecha_inicio: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    fecha_vencimiento: Mapped[Optional[datetime]] = mapped_column(DateTime)
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")
    creado_por: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL")
    )

    usuario: Mapped["Usuario"] = relationship(
        "Usuario", back_populates="usuario_estados", foreign_keys=[usuario_id]
    )
    creador: Mapped[Optional["Usuario"]] = relationship(
        "Usuario", foreign_keys=[creado_por]
    )

    __table_args__ = (
        Index("idx_usuario_estados_usuario_id", "usuario_id"),
        Index("idx_usuario_estados_creado_por", "creado_por"),
    )


class HistorialEstado(Base):
    __tablename__ = "historial_estados"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    estado_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuario_estados.id", ondelete="CASCADE")
    )
    accion: Mapped[str] = mapped_column(String(50), nullable=False)
    fecha_accion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    detalles: Mapped[Optional[str]] = mapped_column(Text)
    creado_por: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL")
    )

    usuario: Mapped["Usuario"] = relationship(
        "Usuario", back_populates="historial_estados", foreign_keys=[usuario_id]
    )
    estado_rel: Mapped[Optional["UsuarioEstado"]] = relationship("UsuarioEstado")
    creador: Mapped[Optional["Usuario"]] = relationship(
        "Usuario", foreign_keys=[creado_por]
    )

    __table_args__ = (
        Index("idx_historial_estados_usuario_id", "usuario_id"),
        Index("idx_historial_estados_estado_id", "estado_id"),
        Index("idx_historial_estados_fecha", "fecha_accion"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    table_name: Mapped[str] = mapped_column(String(100), nullable=False)
    record_id: Mapped[Optional[int]] = mapped_column(Integer)
    old_values: Mapped[Optional[str]] = mapped_column(Text)
    new_values: Mapped[Optional[str]] = mapped_column(Text)
    ip_address: Mapped[Optional[str]] = mapped_column(INET)
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    session_id: Mapped[Optional[str]] = mapped_column(String(255))
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    __table_args__ = (Index("idx_audit_logs_user_id", "user_id"),)


class CheckinPending(Base):
    __tablename__ = "checkin_pending"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    sucursal_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sucursales.id", ondelete="SET NULL")
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[Optional[bool]] = mapped_column(Boolean, server_default="false")

    __table_args__ = (
        Index("idx_checkin_pending_expires_at", "expires_at"),
        Index("idx_checkin_pending_used", "used"),
        Index("idx_checkin_pending_sucursal_expires", "sucursal_id", "expires_at"),
    )


class CheckinStationToken(Base):
    __tablename__ = "checkin_station_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    gym_id: Mapped[int] = mapped_column(Integer, server_default="0")
    sucursal_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sucursales.id", ondelete="SET NULL")
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_by: Mapped[Optional[int]] = mapped_column(Integer)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    __table_args__ = (
        Index("idx_checkin_station_tokens_sucursal_expires", "sucursal_id", "expires_at"),
        Index("idx_checkin_station_tokens_expires_at", "expires_at"),
        Index(
            "idx_checkin_station_tokens_sucursal_active",
            "sucursal_id",
            "created_at",
            postgresql_where=text("used_by IS NULL"),
        ),
    )


class GymConfig(Base):
    __tablename__ = "gym_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gym_name: Mapped[Optional[str]] = mapped_column(Text, server_default="")
    gym_slogan: Mapped[Optional[str]] = mapped_column(Text, server_default="")
    gym_address: Mapped[Optional[str]] = mapped_column(Text, server_default="")
    gym_phone: Mapped[Optional[str]] = mapped_column(Text, server_default="")
    gym_email: Mapped[Optional[str]] = mapped_column(Text, server_default="")
    gym_website: Mapped[Optional[str]] = mapped_column(Text, server_default="")
    facebook: Mapped[Optional[str]] = mapped_column(Text, server_default="")
    instagram: Mapped[Optional[str]] = mapped_column(Text, server_default="")
    twitter: Mapped[Optional[str]] = mapped_column(Text, server_default="")
    logo_url: Mapped[Optional[str]] = mapped_column(Text, server_default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )


class Configuracion(Base):
    __tablename__ = "configuracion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clave: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    valor: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[Optional[str]] = mapped_column(String(50), server_default="string")
    descripcion: Mapped[Optional[str]] = mapped_column(Text)


class ClaseAsistenciaHistorial(Base):
    __tablename__ = "clase_asistencia_historial"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clase_horario_id: Mapped[int] = mapped_column(
        ForeignKey("clases_horarios.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    fecha_clase: Mapped[date] = mapped_column(Date, nullable=False)
    estado_asistencia: Mapped[Optional[str]] = mapped_column(
        String(20), server_default="presente"
    )
    hora_llegada: Mapped[Optional[time]] = mapped_column(Time)
    observaciones: Mapped[Optional[str]] = mapped_column(Text)
    registrado_por: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL")
    )
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    __table_args__ = (
        UniqueConstraint("clase_horario_id", "usuario_id", "fecha_clase"),
        Index("idx_clase_asistencia_historial_clase_horario_id", "clase_horario_id"),
        Index("idx_clase_asistencia_historial_usuario_id", "usuario_id"),
        Index("idx_clase_asistencia_historial_fecha", "fecha_clase"),
        Index("idx_clase_asistencia_historial_estado", "estado_asistencia"),
    )


# --- WhatsApp ---


class WhatsappMessage(Base):
    __tablename__ = "whatsapp_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"))
    sucursal_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sucursales.id", ondelete="SET NULL")
    )
    event_key: Mapped[Optional[str]] = mapped_column(String(150))
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)
    template_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    message_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    status: Mapped[Optional[str]] = mapped_column(String(20), server_default="sent")
    message_content: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    __table_args__ = (
        Index("idx_whatsapp_messages_user_id", "user_id"),
        Index("idx_whatsapp_messages_sucursal_id", "sucursal_id"),
        Index("idx_whatsapp_messages_type_date", "message_type", text("sent_at DESC")),
        Index("idx_whatsapp_messages_phone", "phone_number"),
        Index("idx_whatsapp_messages_event_key", "event_key"),
    )


class WhatsappTemplate(Base):
    __tablename__ = "whatsapp_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    header_text: Mapped[Optional[str]] = mapped_column(String(60))
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[Optional[dict]] = mapped_column(JSONB)
    active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )


class ProfesorNotificacion(Base):
    __tablename__ = "profesor_notificaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profesor_id: Mapped[int] = mapped_column(
        ForeignKey("profesores.id", ondelete="CASCADE")
    )
    mensaje: Mapped[str] = mapped_column(Text)
    leida: Mapped[bool] = mapped_column(Boolean, server_default="false")
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    fecha_lectura: Mapped[Optional[datetime]] = mapped_column(DateTime)

    profesor: Mapped["Profesor"] = relationship("Profesor")

    __table_args__ = (
        Index("idx_profesor_notificaciones_profesor", "profesor_id"),
        Index("idx_profesor_notificaciones_leida", "leida"),
    )


class WhatsappConfig(Base):
    __tablename__ = "whatsapp_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone_id: Mapped[str] = mapped_column(String(50), nullable=False)
    waba_id: Mapped[str] = mapped_column(String(50), nullable=False)
    access_token: Mapped[Optional[str]] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    sucursal_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sucursales.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )


# --- Dynamic Template System ---


class PlantillaRutina(Base):
    __tablename__ = "plantillas_rutina"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    configuracion: Mapped[dict] = mapped_column(JSONB, nullable=False)
    categoria: Mapped[Optional[str]] = mapped_column(
        String(100), server_default="general"
    )
    dias_semana: Mapped[Optional[int]] = mapped_column(Integer)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False, server_default="export_pdf")
    activa: Mapped[bool] = mapped_column(Boolean, server_default="true")
    publica: Mapped[bool] = mapped_column(Boolean, server_default="false")
    creada_por: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL")
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    version_actual: Mapped[Optional[str]] = mapped_column(
        String(50), server_default="1.0.0"
    )
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), server_default="{}", default=list)
    preview_url: Mapped[Optional[str]] = mapped_column(String(500))
    uso_count: Mapped[int] = mapped_column(Integer, server_default="0")
    rating_promedio: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    rating_count: Mapped[int] = mapped_column(Integer, server_default="0")

    # Relaciones
    creador: Mapped[Optional["Usuario"]] = relationship(
        "Usuario", back_populates="plantillas_creadas", foreign_keys=[creada_por]
    )
    versiones: Mapped[List["PlantillaRutinaVersion"]] = relationship(
        "PlantillaRutinaVersion", back_populates="plantilla", cascade="all, delete-orphan"
    )
    gimnasio_asignaciones: Mapped[List["GimnasioPlantilla"]] = relationship(
        "GimnasioPlantilla", back_populates="plantilla", cascade="all, delete-orphan"
    )
    analitica: Mapped[List["PlantillaAnalitica"]] = relationship(
        "PlantillaAnalitica", back_populates="plantilla", cascade="all, delete-orphan"
    )
    mercado: Mapped[Optional["PlantillaMercado"]] = relationship(
        "PlantillaMercado", back_populates="plantilla", uselist=False, cascade="all, delete-orphan"
    )
    rutinas: Mapped[List["Rutina"]] = relationship(
        "Rutina", back_populates="plantilla", passive_deletes=True
    )

    __table_args__ = (
        Index("idx_plantillas_rutina_activa", "activa"),
        Index("idx_plantillas_rutina_categoria", "categoria"),
        Index("idx_plantillas_rutina_publica", "publica"),
        Index("idx_plantillas_rutina_creada_por", "creada_por"),
        Index("idx_plantillas_rutina_fecha_creacion", "fecha_creacion"),
        Index("idx_plantillas_rutina_tipo", "tipo"),
    )


class PlantillaRutinaVersion(Base):
    __tablename__ = "plantillas_rutina_versiones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plantilla_id: Mapped[int] = mapped_column(
        ForeignKey("plantillas_rutina.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    configuracion: Mapped[dict] = mapped_column(JSONB, nullable=False)
    cambios_descripcion: Mapped[Optional[str]] = mapped_column(Text)
    creada_por: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL")
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    es_actual: Mapped[bool] = mapped_column(Boolean, server_default="false")

    # Relaciones
    plantilla: Mapped["PlantillaRutina"] = relationship(
        "PlantillaRutina", back_populates="versiones"
    )
    creador: Mapped[Optional["Usuario"]] = relationship(
        "Usuario", back_populates="plantillas_versiones", foreign_keys=[creada_por]
    )

    __table_args__ = (
        UniqueConstraint("plantilla_id", "version", name="uq_plantilla_version"),
        Index("idx_plantillas_versiones_plantilla_id", "plantilla_id"),
        Index("idx_plantillas_versiones_es_actual", "es_actual"),
        Index("idx_plantillas_versiones_fecha_creacion", "fecha_creacion"),
    )


class GimnasioPlantilla(Base):
    __tablename__ = "gimnasio_plantillas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gimnasio_id: Mapped[int] = mapped_column(
        ForeignKey("gym_config.id", ondelete="CASCADE"), nullable=False
    )
    plantilla_id: Mapped[int] = mapped_column(
        ForeignKey("plantillas_rutina.id", ondelete="CASCADE"), nullable=False
    )
    activa: Mapped[bool] = mapped_column(Boolean, server_default="true")
    prioridad: Mapped[int] = mapped_column(Integer, server_default="0")
    configuracion_personalizada: Mapped[Optional[dict]] = mapped_column(JSONB)
    asignada_por: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL")
    )
    fecha_asignacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    fecha_ultima_uso: Mapped[Optional[datetime]] = mapped_column(DateTime)
    uso_count: Mapped[int] = mapped_column(Integer, server_default="0")
    notas: Mapped[Optional[str]] = mapped_column(Text)

    # Relaciones
    # gimnasio: Mapped["Gimnasio"] = relationship("Gimnasio") # Comentado hasta que exista el modelo Gimnasio
    plantilla: Mapped["PlantillaRutina"] = relationship(
        "PlantillaRutina", back_populates="gimnasio_asignaciones"
    )
    asignador: Mapped[Optional["Usuario"]] = relationship(
        "Usuario", back_populates="gimnasio_plantillas_asignadas", foreign_keys=[asignada_por]
    )

    __table_args__ = (
        UniqueConstraint("gimnasio_id", "plantilla_id", name="uq_gimnasio_plantilla"),
        Index("idx_gimnasio_plantillas_gimnasio_id", "gimnasio_id"),
        Index("idx_gimnasio_plantillas_plantilla_id", "plantilla_id"),
        Index("idx_gimnasio_plantillas_activa", "activa"),
        Index("idx_gimnasio_plantillas_prioridad", "prioridad"),
    )


class PlantillaAnalitica(Base):
    __tablename__ = "plantilla_analitica"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plantilla_id: Mapped[int] = mapped_column(
        ForeignKey("plantillas_rutina.id", ondelete="CASCADE"), nullable=False
    )
    gimnasio_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("gym_config.id", ondelete="SET NULL")
    )
    usuario_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL")
    )
    evento_tipo: Mapped[str] = mapped_column(String(50), nullable=False)  # 'view', 'export', 'create', 'edit'
    fecha_evento: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    datos_evento: Mapped[Optional[dict]] = mapped_column(JSONB)
    tiempo_render_ms: Mapped[Optional[int]] = mapped_column(Integer)
    exitoso: Mapped[bool] = mapped_column(Boolean, server_default="true")
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Relaciones
    plantilla: Mapped["PlantillaRutina"] = relationship(
        "PlantillaRutina", back_populates="analitica"
    )
    # gimnasio: Mapped[Optional["Gimnasio"]] = relationship("Gimnasio") # Comentado hasta que exista el modelo Gimnasio
    usuario: Mapped[Optional["Usuario"]] = relationship(
        "Usuario", back_populates="plantilla_analitica", foreign_keys=[usuario_id]
    )

    __table_args__ = (
        Index("idx_plantilla_analitica_plantilla_id", "plantilla_id"),
        Index("idx_plantilla_analitica_gimnasio_id", "gimnasio_id"),
        Index("idx_plantilla_analitica_usuario_id", "usuario_id"),
        Index("idx_plantilla_analitica_evento_tipo", "evento_tipo"),
        Index("idx_plantilla_analitica_fecha_evento", "fecha_evento"),
    )


class PlantillaMercado(Base):
    __tablename__ = "plantilla_mercado"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plantilla_id: Mapped[int] = mapped_column(
        ForeignKey("plantillas_rutina.id", ondelete="CASCADE"), nullable=False
    )
    precio: Mapped[float] = mapped_column(Numeric(10, 2), server_default="0.00")
    moneda: Mapped[str] = mapped_column(String(3), server_default="USD")
    descargas: Mapped[int] = mapped_column(Integer, server_default="0")
    rating_promedio: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    rating_count: Mapped[int] = mapped_column(Integer, server_default="0")
    resenas_count: Mapped[int] = mapped_column(Integer, server_default="0")
    featured: Mapped[bool] = mapped_column(Boolean, server_default="false")
    trending: Mapped[bool] = mapped_column(Boolean, server_default="false")
    categoria_mercado: Mapped[Optional[str]] = mapped_column(String(100))
    tags_mercado: Mapped[Optional[list]] = mapped_column(JSONB)
    fecha_publicacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    fecha_ultima_descarga: Mapped[Optional[datetime]] = mapped_column(DateTime)
    ingresos_totales: Mapped[float] = mapped_column(Numeric(12, 2), server_default="0.00")

    # Relaciones
    plantilla: Mapped["PlantillaRutina"] = relationship(
        "PlantillaRutina", back_populates="mercado"
    )

    __table_args__ = (
        Index("idx_plantilla_mercado_plantilla_id", "plantilla_id"),
        Index("idx_plantilla_mercado_featured", "featured"),
        Index("idx_plantilla_mercado_trending", "trending"),
        Index("idx_plantilla_mercado_categoria_mercado", "categoria_mercado"),
        Index("idx_plantilla_mercado_fecha_publicacion", "fecha_publicacion"),
    )
