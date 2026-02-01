from alembic import op

revision = "0001_tenant_schema_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""\nDO $$
        BEGIN
            BEGIN
                CREATE EXTENSION IF NOT EXISTS pg_trgm;
            EXCEPTION
                WHEN insufficient_privilege THEN
                    NULL;
            END;
        END $$;\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS conceptos_pago (
	id SERIAL NOT NULL, 
	nombre VARCHAR(100) NOT NULL, 
	descripcion TEXT, 
	precio_base NUMERIC(10, 2) DEFAULT '0.0', 
	tipo VARCHAR(20) DEFAULT 'fijo' NOT NULL, 
	activo BOOLEAN DEFAULT 'true' NOT NULL, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (nombre)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS configuracion (
	id SERIAL NOT NULL, 
	clave VARCHAR(255) NOT NULL, 
	valor TEXT NOT NULL, 
	tipo VARCHAR(50) DEFAULT 'string', 
	descripcion TEXT, 
	PRIMARY KEY (id), 
	UNIQUE (clave)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS ejercicio_grupos (
	id SERIAL NOT NULL, 
	nombre VARCHAR(255) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (nombre)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS especialidades (
	id SERIAL NOT NULL, 
	nombre VARCHAR(100) NOT NULL, 
	descripcion TEXT, 
	categoria VARCHAR(50), 
	activo BOOLEAN DEFAULT 'true' NOT NULL, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (nombre)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS etiquetas (
	id SERIAL NOT NULL, 
	nombre VARCHAR(100) NOT NULL, 
	color VARCHAR(7) DEFAULT '#3498db' NOT NULL, 
	descripcion TEXT, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	activo BOOLEAN DEFAULT 'true' NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (nombre)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS feature_flags (
	id SMALLSERIAL NOT NULL, 
	flags JSONB DEFAULT '{}'::jsonb NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS gym_config (
	id SERIAL NOT NULL, 
	gym_name TEXT DEFAULT '', 
	gym_slogan TEXT DEFAULT '', 
	gym_address TEXT DEFAULT '', 
	gym_phone TEXT DEFAULT '', 
	gym_email TEXT DEFAULT '', 
	gym_website TEXT DEFAULT '', 
	facebook TEXT DEFAULT '', 
	instagram TEXT DEFAULT '', 
	twitter TEXT DEFAULT '', 
	logo_url TEXT DEFAULT '', 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS metodos_pago (
	id SERIAL NOT NULL, 
	nombre VARCHAR(100) NOT NULL, 
	icono VARCHAR(10), 
	color VARCHAR(7) DEFAULT '#3498db' NOT NULL, 
	comision NUMERIC(5, 2) DEFAULT '0.0', 
	activo BOOLEAN DEFAULT 'true' NOT NULL, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	descripcion TEXT, 
	PRIMARY KEY (id), 
	UNIQUE (nombre)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS numeracion_comprobantes (
	id SERIAL NOT NULL, 
	tipo_comprobante VARCHAR(50) NOT NULL, 
	prefijo VARCHAR(10) DEFAULT '' NOT NULL, 
	numero_inicial INTEGER DEFAULT '1' NOT NULL, 
	separador VARCHAR(5) DEFAULT '-' NOT NULL, 
	reiniciar_anual BOOLEAN DEFAULT 'false', 
	longitud_numero INTEGER DEFAULT '8' NOT NULL, 
	activo BOOLEAN DEFAULT 'true', 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (tipo_comprobante)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS sucursales (
	id SERIAL NOT NULL, 
	nombre VARCHAR(255) NOT NULL, 
	codigo VARCHAR(80) NOT NULL, 
	direccion TEXT, 
	timezone VARCHAR(80), 
	station_key VARCHAR(64), 
	activa BOOLEAN DEFAULT 'true' NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (codigo)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS tipos_clases (
	id SERIAL NOT NULL, 
	nombre VARCHAR(255) NOT NULL, 
	descripcion TEXT, 
	activo BOOLEAN DEFAULT 'true' NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (nombre)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS tipos_cuota (
	id SERIAL NOT NULL, 
	nombre VARCHAR(100) NOT NULL, 
	precio NUMERIC(10, 2) NOT NULL, 
	icono_path VARCHAR(255), 
	activo BOOLEAN DEFAULT 'true' NOT NULL, 
	all_sucursales BOOLEAN DEFAULT 'true' NOT NULL, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	descripcion TEXT, 
	duracion_dias INTEGER DEFAULT '30', 
	fecha_modificacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	UNIQUE (nombre)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS usuarios (
	id SERIAL NOT NULL, 
	nombre VARCHAR(255) NOT NULL, 
	dni VARCHAR(20), 
	telefono VARCHAR(50) NOT NULL, 
	pin VARCHAR(100) DEFAULT '123456', 
	rol VARCHAR(50) DEFAULT 'socio' NOT NULL, 
	notas TEXT, 
	fecha_registro TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	activo BOOLEAN DEFAULT 'true' NOT NULL, 
	tipo_cuota VARCHAR(100) DEFAULT 'estandar', 
	ultimo_pago DATE, 
	fecha_proximo_vencimiento DATE, 
	cuotas_vencidas INTEGER DEFAULT '0', 
	PRIMARY KEY (id), 
	UNIQUE (dni)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS whatsapp_templates (
	id SERIAL NOT NULL, 
	template_name VARCHAR(255) NOT NULL, 
	header_text VARCHAR(60), 
	body_text TEXT NOT NULL, 
	variables JSONB, 
	active BOOLEAN DEFAULT 'true' NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (template_name)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS work_session_pauses (
	id SERIAL NOT NULL, 
	session_kind VARCHAR(20) NOT NULL, 
	session_id INTEGER NOT NULL, 
	started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	ended_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT work_session_pauses_kind_check CHECK (session_kind IN ('profesor','staff'))
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS asistencias (
	id SERIAL NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	sucursal_id INTEGER, 
	fecha DATE DEFAULT CURRENT_DATE NOT NULL, 
	hora_registro TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	hora_entrada TIME WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
	FOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS audit_logs (
	id SERIAL NOT NULL, 
	user_id INTEGER, 
	action VARCHAR(50) NOT NULL, 
	table_name VARCHAR(100) NOT NULL, 
	record_id INTEGER, 
	old_values TEXT, 
	new_values TEXT, 
	ip_address INET, 
	user_agent TEXT, 
	session_id VARCHAR(255), 
	timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES usuarios (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS checkin_pending (
	id SERIAL NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	sucursal_id INTEGER, 
	token VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	used BOOLEAN DEFAULT 'false', 
	PRIMARY KEY (id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
	FOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE SET NULL, 
	UNIQUE (token)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS clases (
	id SERIAL NOT NULL, 
	nombre VARCHAR(255) NOT NULL, 
	descripcion TEXT, 
	activa BOOLEAN DEFAULT 'true' NOT NULL, 
	sucursal_id INTEGER, 
	tipo_clase_id INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (nombre), 
	FOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS ejercicios (
	id SERIAL NOT NULL, 
	nombre VARCHAR(255) NOT NULL, 
	descripcion TEXT, 
	grupo_muscular VARCHAR(100), 
	objetivo VARCHAR(100) DEFAULT 'general', 
	equipamiento VARCHAR(100), 
	variantes TEXT, 
	video_url VARCHAR(512), 
	video_mime VARCHAR(50), 
	sucursal_id INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (nombre), 
	FOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS feature_flags_overrides (
	sucursal_id INTEGER NOT NULL, 
	flags JSONB DEFAULT '{}'::jsonb NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (sucursal_id), 
	FOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS memberships (
	id SERIAL NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	plan_name TEXT, 
	status VARCHAR(20) DEFAULT 'active' NOT NULL, 
	start_date DATE DEFAULT CURRENT_DATE NOT NULL, 
	end_date DATE, 
	all_sucursales BOOLEAN DEFAULT 'false' NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS pagos (
	id SERIAL NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	sucursal_id INTEGER, 
	tipo_cuota_id INTEGER, 
	monto NUMERIC(10, 2) NOT NULL, 
	mes INTEGER NOT NULL, 
	"año" INTEGER NOT NULL, 
	fecha_pago TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	metodo_pago_id INTEGER, 
	concepto VARCHAR(100), 
	metodo_pago VARCHAR(50), 
	estado VARCHAR(20) DEFAULT 'pagado', 
	PRIMARY KEY (id), 
	CONSTRAINT "idx_pagos_usuario_mes_año" UNIQUE (usuario_id, mes, "año"), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
	FOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE SET NULL, 
	FOREIGN KEY(tipo_cuota_id) REFERENCES tipos_cuota (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS profesores (
	id SERIAL NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	tipo VARCHAR(50) DEFAULT 'Musculación', 
	especialidades TEXT, 
	certificaciones TEXT, 
	"experiencia_años" INTEGER DEFAULT '0', 
	tarifa_por_hora NUMERIC(10, 2) DEFAULT '0.0', 
	horario_disponible TEXT, 
	fecha_contratacion DATE, 
	estado VARCHAR(20) DEFAULT 'activo', 
	biografia TEXT, 
	foto_perfil VARCHAR(255), 
	telefono_emergencia VARCHAR(50), 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	fecha_actualizacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT profesores_estado_check CHECK (estado IN ('activo', 'inactivo', 'vacaciones')), 
	UNIQUE (usuario_id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS rutinas (
	id SERIAL NOT NULL, 
	usuario_id INTEGER, 
	nombre_rutina VARCHAR(255) NOT NULL, 
	descripcion TEXT, 
	dias_semana INTEGER, 
	categoria VARCHAR(100) DEFAULT 'general', 
	sucursal_id INTEGER, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	activa BOOLEAN DEFAULT 'true' NOT NULL, 
	uuid_rutina VARCHAR(36), 
	PRIMARY KEY (id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
	FOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE SET NULL, 
	UNIQUE (uuid_rutina)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS staff_permissions (
	usuario_id INTEGER NOT NULL, 
	scopes JSONB DEFAULT '[]'::jsonb NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (usuario_id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS staff_profiles (
	id SERIAL NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	tipo VARCHAR(50) DEFAULT 'empleado' NOT NULL, 
	estado VARCHAR(20) DEFAULT 'activo' NOT NULL, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	fecha_actualizacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT staff_profiles_estado_check CHECK (estado IN ('activo', 'inactivo', 'vacaciones')), 
	UNIQUE (usuario_id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS tipo_cuota_clases_permisos (
	id SERIAL NOT NULL, 
	tipo_cuota_id INTEGER NOT NULL, 
	sucursal_id INTEGER, 
	target_type VARCHAR(20) NOT NULL, 
	target_id INTEGER NOT NULL, 
	allow BOOLEAN DEFAULT 'true' NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_tipo_cuota_clases_permiso UNIQUE (tipo_cuota_id, sucursal_id, target_type, target_id), 
	FOREIGN KEY(tipo_cuota_id) REFERENCES tipos_cuota (id) ON DELETE CASCADE, 
	FOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS tipo_cuota_sucursales (
	tipo_cuota_id INTEGER NOT NULL, 
	sucursal_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (tipo_cuota_id, sucursal_id), 
	FOREIGN KEY(tipo_cuota_id) REFERENCES tipos_cuota (id) ON DELETE CASCADE, 
	FOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS usuario_accesos_sucursales (
	id SERIAL NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	sucursal_id INTEGER NOT NULL, 
	allow BOOLEAN NOT NULL, 
	motivo TEXT, 
	starts_at TIMESTAMP WITHOUT TIME ZONE, 
	ends_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_usuario_accesos_sucursales UNIQUE (usuario_id, sucursal_id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
	FOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS usuario_estados (
	id SERIAL NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	estado VARCHAR(100) NOT NULL, 
	descripcion TEXT, 
	fecha_inicio TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	fecha_vencimiento TIMESTAMP WITHOUT TIME ZONE, 
	activo BOOLEAN DEFAULT 'true' NOT NULL, 
	creado_por INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
	FOREIGN KEY(creado_por) REFERENCES usuarios (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS usuario_etiquetas (
	usuario_id INTEGER NOT NULL, 
	etiqueta_id INTEGER NOT NULL, 
	fecha_asignacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	asignado_por INTEGER, 
	PRIMARY KEY (usuario_id, etiqueta_id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
	FOREIGN KEY(etiqueta_id) REFERENCES etiquetas (id) ON DELETE CASCADE, 
	FOREIGN KEY(asignado_por) REFERENCES usuarios (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS usuario_notas (
	id SERIAL NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	categoria VARCHAR(50) DEFAULT 'general' NOT NULL, 
	titulo VARCHAR(255) NOT NULL, 
	contenido TEXT NOT NULL, 
	importancia VARCHAR(20) DEFAULT 'normal' NOT NULL, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	fecha_modificacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	activa BOOLEAN DEFAULT 'true' NOT NULL, 
	autor_id INTEGER, 
	PRIMARY KEY (id), 
	CONSTRAINT usuario_notas_categoria_check CHECK (categoria IN ('general', 'medica', 'administrativa', 'comportamiento')), 
	CONSTRAINT usuario_notas_importancia_check CHECK (importancia IN ('baja', 'normal', 'alta', 'critica')), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
	FOREIGN KEY(autor_id) REFERENCES usuarios (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS usuario_permisos_clases (
	id SERIAL NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	sucursal_id INTEGER, 
	target_type VARCHAR(20) NOT NULL, 
	target_id INTEGER NOT NULL, 
	allow BOOLEAN NOT NULL, 
	motivo TEXT, 
	starts_at TIMESTAMP WITHOUT TIME ZONE, 
	ends_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_usuario_permisos_clases UNIQUE (usuario_id, sucursal_id, target_type, target_id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
	FOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS usuario_sucursales (
	usuario_id INTEGER NOT NULL, 
	sucursal_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (usuario_id, sucursal_id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
	FOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS whatsapp_config (
	id SERIAL NOT NULL, 
	phone_id VARCHAR(50) NOT NULL, 
	waba_id VARCHAR(50) NOT NULL, 
	access_token TEXT, 
	active BOOLEAN DEFAULT 'true' NOT NULL, 
	sucursal_id INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS whatsapp_messages (
	id SERIAL NOT NULL, 
	user_id INTEGER, 
	sucursal_id INTEGER, 
	event_key VARCHAR(150), 
	message_type VARCHAR(50) NOT NULL, 
	template_name VARCHAR(255) NOT NULL, 
	phone_number VARCHAR(20) NOT NULL, 
	message_id VARCHAR(100), 
	sent_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	status VARCHAR(20) DEFAULT 'sent', 
	message_content TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES usuarios (id), 
	FOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE SET NULL, 
	UNIQUE (message_id)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS clase_bloques (
	id SERIAL NOT NULL, 
	clase_id INTEGER NOT NULL, 
	nombre TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(clase_id) REFERENCES clases (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS clase_ejercicios (
	clase_id INTEGER NOT NULL, 
	ejercicio_id INTEGER NOT NULL, 
	orden INTEGER DEFAULT '0', 
	series INTEGER DEFAULT '0', 
	repeticiones VARCHAR(50) DEFAULT '', 
	descanso_segundos INTEGER DEFAULT '0', 
	notas TEXT, 
	PRIMARY KEY (clase_id, ejercicio_id), 
	FOREIGN KEY(clase_id) REFERENCES clases (id) ON DELETE CASCADE, 
	FOREIGN KEY(ejercicio_id) REFERENCES ejercicios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS clases_horarios (
	id SERIAL NOT NULL, 
	clase_id INTEGER NOT NULL, 
	dia_semana VARCHAR(20) NOT NULL, 
	hora_inicio TIME WITHOUT TIME ZONE NOT NULL, 
	hora_fin TIME WITHOUT TIME ZONE NOT NULL, 
	cupo_maximo INTEGER DEFAULT '20', 
	activo BOOLEAN DEFAULT 'true' NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(clase_id) REFERENCES clases (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS comprobantes_pago (
	id SERIAL NOT NULL, 
	numero_comprobante VARCHAR(50) NOT NULL, 
	pago_id INTEGER NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	tipo_comprobante VARCHAR(50) DEFAULT 'recibo' NOT NULL, 
	monto_total NUMERIC(10, 2) DEFAULT '0.0' NOT NULL, 
	estado VARCHAR(20) DEFAULT 'emitido', 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	archivo_pdf VARCHAR(500), 
	plantilla_id INTEGER, 
	datos_comprobante JSONB, 
	emitido_por VARCHAR(255), 
	PRIMARY KEY (id), 
	FOREIGN KEY(pago_id) REFERENCES pagos (id) ON DELETE CASCADE, 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS ejercicio_grupo_items (
	grupo_id INTEGER NOT NULL, 
	ejercicio_id INTEGER NOT NULL, 
	PRIMARY KEY (grupo_id, ejercicio_id), 
	FOREIGN KEY(grupo_id) REFERENCES ejercicio_grupos (id) ON DELETE CASCADE, 
	FOREIGN KEY(ejercicio_id) REFERENCES ejercicios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS historial_estados (
	id SERIAL NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	estado_id INTEGER, 
	accion VARCHAR(50) NOT NULL, 
	fecha_accion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	detalles TEXT, 
	creado_por INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
	FOREIGN KEY(estado_id) REFERENCES usuario_estados (id) ON DELETE CASCADE, 
	FOREIGN KEY(creado_por) REFERENCES usuarios (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS horarios_profesores (
	id SERIAL NOT NULL, 
	profesor_id INTEGER NOT NULL, 
	dia_semana VARCHAR(20) NOT NULL, 
	hora_inicio TIME WITHOUT TIME ZONE NOT NULL, 
	hora_fin TIME WITHOUT TIME ZONE NOT NULL, 
	disponible BOOLEAN DEFAULT 'true' NOT NULL, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(profesor_id) REFERENCES profesores (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS membership_sucursales (
	membership_id INTEGER NOT NULL, 
	sucursal_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (membership_id, sucursal_id), 
	FOREIGN KEY(membership_id) REFERENCES memberships (id) ON DELETE CASCADE, 
	FOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS pago_detalles (
	id SERIAL NOT NULL, 
	pago_id INTEGER NOT NULL, 
	concepto_id INTEGER, 
	descripcion TEXT, 
	cantidad NUMERIC(10, 2) DEFAULT '1' NOT NULL, 
	precio_unitario NUMERIC(10, 2) NOT NULL, 
	subtotal NUMERIC(10, 2) NOT NULL, 
	descuento NUMERIC(10, 2) DEFAULT '0' NOT NULL, 
	total NUMERIC(10, 2) NOT NULL, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(pago_id) REFERENCES pagos (id) ON DELETE CASCADE, 
	FOREIGN KEY(concepto_id) REFERENCES conceptos_pago (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS profesor_certificaciones (
	id SERIAL NOT NULL, 
	profesor_id INTEGER NOT NULL, 
	nombre_certificacion VARCHAR(200) NOT NULL, 
	institucion_emisora VARCHAR(200), 
	fecha_obtencion DATE, 
	fecha_vencimiento DATE, 
	numero_certificado VARCHAR(100), 
	archivo_adjunto VARCHAR(500), 
	estado VARCHAR(20) DEFAULT 'vigente', 
	notas TEXT, 
	activo BOOLEAN DEFAULT 'true' NOT NULL, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(profesor_id) REFERENCES profesores (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS profesor_disponibilidad (
	id SERIAL NOT NULL, 
	profesor_id INTEGER NOT NULL, 
	fecha DATE NOT NULL, 
	tipo_disponibilidad VARCHAR(50) NOT NULL, 
	hora_inicio TIME WITHOUT TIME ZONE, 
	hora_fin TIME WITHOUT TIME ZONE, 
	notas TEXT, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	fecha_modificacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT profesor_disponibilidad_tipo_disponibilidad_check CHECK (tipo_disponibilidad IN ('Disponible', 'No Disponible', 'Parcialmente Disponible')), 
	CONSTRAINT profesor_disponibilidad_profesor_id_fecha_key UNIQUE (profesor_id, fecha), 
	FOREIGN KEY(profesor_id) REFERENCES profesores (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS profesor_especialidades (
	id SERIAL NOT NULL, 
	profesor_id INTEGER NOT NULL, 
	especialidad_id INTEGER NOT NULL, 
	fecha_asignacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	activo BOOLEAN DEFAULT 'true' NOT NULL, 
	nivel_experiencia VARCHAR(50), 
	"años_experiencia" INTEGER DEFAULT '0', 
	PRIMARY KEY (id), 
	CONSTRAINT profesor_especialidades_profesor_id_especialidad_id_key UNIQUE (profesor_id, especialidad_id), 
	FOREIGN KEY(profesor_id) REFERENCES profesores (id) ON DELETE CASCADE, 
	FOREIGN KEY(especialidad_id) REFERENCES especialidades (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS profesor_evaluaciones (
	id SERIAL NOT NULL, 
	profesor_id INTEGER NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	puntuacion INTEGER NOT NULL, 
	comentario TEXT, 
	fecha_evaluacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT profesor_evaluaciones_puntuacion_check CHECK (puntuacion >= 1 AND puntuacion <= 5), 
	CONSTRAINT profesor_evaluaciones_profesor_id_usuario_id_key UNIQUE (profesor_id, usuario_id), 
	FOREIGN KEY(profesor_id) REFERENCES profesores (id) ON DELETE CASCADE, 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS profesor_horas_trabajadas (
	id SERIAL NOT NULL, 
	profesor_id INTEGER NOT NULL, 
	sucursal_id INTEGER, 
	fecha DATE NOT NULL, 
	hora_inicio TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	hora_fin TIMESTAMP WITHOUT TIME ZONE, 
	minutos_totales INTEGER, 
	horas_totales NUMERIC(8, 2), 
	tipo_actividad VARCHAR(50), 
	clase_id INTEGER, 
	notas TEXT, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(profesor_id) REFERENCES profesores (id) ON DELETE CASCADE, 
	FOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE SET NULL, 
	FOREIGN KEY(clase_id) REFERENCES clases (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS profesor_notificaciones (
	id SERIAL NOT NULL, 
	profesor_id INTEGER NOT NULL, 
	mensaje TEXT NOT NULL, 
	leida BOOLEAN DEFAULT 'false' NOT NULL, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	fecha_lectura TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(profesor_id) REFERENCES profesores (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS profesores_horarios_disponibilidad (
	id SERIAL NOT NULL, 
	profesor_id INTEGER NOT NULL, 
	dia_semana INTEGER NOT NULL, 
	hora_inicio TIME WITHOUT TIME ZONE NOT NULL, 
	hora_fin TIME WITHOUT TIME ZONE NOT NULL, 
	disponible BOOLEAN DEFAULT 'true' NOT NULL, 
	tipo_disponibilidad VARCHAR(50) DEFAULT 'regular', 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	fecha_actualizacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT profesores_horarios_disponibilidad_dia_semana_check CHECK (dia_semana BETWEEN 0 AND 6), 
	FOREIGN KEY(profesor_id) REFERENCES profesores (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS rutina_ejercicios (
	id SERIAL NOT NULL, 
	rutina_id INTEGER NOT NULL, 
	ejercicio_id INTEGER NOT NULL, 
	dia_semana INTEGER, 
	series INTEGER, 
	repeticiones VARCHAR(50), 
	orden INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(rutina_id) REFERENCES rutinas (id) ON DELETE CASCADE, 
	FOREIGN KEY(ejercicio_id) REFERENCES ejercicios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS staff_sessions (
	id SERIAL NOT NULL, 
	staff_id INTEGER NOT NULL, 
	sucursal_id INTEGER, 
	fecha DATE NOT NULL, 
	hora_inicio TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	hora_fin TIMESTAMP WITHOUT TIME ZONE, 
	minutos_totales INTEGER, 
	notas TEXT, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(staff_id) REFERENCES staff_profiles (id) ON DELETE CASCADE, 
	FOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS clase_asistencia_historial (
	id SERIAL NOT NULL, 
	clase_horario_id INTEGER NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	fecha_clase DATE NOT NULL, 
	estado_asistencia VARCHAR(20) DEFAULT 'presente', 
	hora_llegada TIME WITHOUT TIME ZONE, 
	observaciones TEXT, 
	registrado_por INTEGER, 
	fecha_registro TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (clase_horario_id, usuario_id, fecha_clase), 
	FOREIGN KEY(clase_horario_id) REFERENCES clases_horarios (id) ON DELETE CASCADE, 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
	FOREIGN KEY(registrado_por) REFERENCES usuarios (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS clase_bloque_items (
	id SERIAL NOT NULL, 
	bloque_id INTEGER NOT NULL, 
	ejercicio_id INTEGER NOT NULL, 
	orden INTEGER DEFAULT '0' NOT NULL, 
	series INTEGER DEFAULT '0', 
	repeticiones TEXT, 
	descanso_segundos INTEGER DEFAULT '0', 
	notas TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(bloque_id) REFERENCES clase_bloques (id) ON DELETE CASCADE, 
	FOREIGN KEY(ejercicio_id) REFERENCES ejercicios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS clase_lista_espera (
	id SERIAL NOT NULL, 
	clase_horario_id INTEGER NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	posicion INTEGER NOT NULL, 
	activo BOOLEAN DEFAULT 'true' NOT NULL, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT clase_lista_espera_clase_horario_id_usuario_id_key UNIQUE (clase_horario_id, usuario_id), 
	FOREIGN KEY(clase_horario_id) REFERENCES clases_horarios (id) ON DELETE CASCADE, 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS clase_usuarios (
	id SERIAL NOT NULL, 
	clase_horario_id INTEGER NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	fecha_inscripcion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT clase_usuarios_clase_horario_id_usuario_id_key UNIQUE (clase_horario_id, usuario_id), 
	FOREIGN KEY(clase_horario_id) REFERENCES clases_horarios (id) ON DELETE CASCADE, 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS notificaciones_cupos (
	id SERIAL NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	clase_horario_id INTEGER NOT NULL, 
	tipo_notificacion VARCHAR(50) NOT NULL, 
	mensaje TEXT, 
	leida BOOLEAN DEFAULT 'false' NOT NULL, 
	activa BOOLEAN DEFAULT 'true' NOT NULL, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	fecha_lectura TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT notificaciones_cupos_tipo_notificacion_check CHECK (tipo_notificacion IN ('cupo_liberado','promocion','recordatorio')), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
	FOREIGN KEY(clase_horario_id) REFERENCES clases_horarios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS profesor_clase_asignaciones (
	id SERIAL NOT NULL, 
	clase_horario_id INTEGER NOT NULL, 
	profesor_id INTEGER NOT NULL, 
	fecha_asignacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	activa BOOLEAN DEFAULT 'true' NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT profesor_clase_asignaciones_clase_horario_id_profesor_id_key UNIQUE (clase_horario_id, profesor_id), 
	FOREIGN KEY(clase_horario_id) REFERENCES clases_horarios (id) ON DELETE CASCADE, 
	FOREIGN KEY(profesor_id) REFERENCES profesores (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS profesor_suplencias_generales (
	id SERIAL NOT NULL, 
	horario_profesor_id INTEGER, 
	profesor_original_id INTEGER NOT NULL, 
	profesor_suplente_id INTEGER, 
	fecha DATE NOT NULL, 
	hora_inicio TIME WITHOUT TIME ZONE NOT NULL, 
	hora_fin TIME WITHOUT TIME ZONE NOT NULL, 
	motivo TEXT NOT NULL, 
	estado VARCHAR(20) DEFAULT 'Pendiente', 
	notas TEXT, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	fecha_resolucion TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT profesor_suplencias_generales_estado_check CHECK (estado IN ('Pendiente', 'Asignado', 'Confirmado', 'Cancelado')), 
	FOREIGN KEY(horario_profesor_id) REFERENCES horarios_profesores (id) ON DELETE SET NULL, 
	FOREIGN KEY(profesor_original_id) REFERENCES profesores (id) ON DELETE CASCADE, 
	FOREIGN KEY(profesor_suplente_id) REFERENCES profesores (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS profesor_suplencias (
	id SERIAL NOT NULL, 
	asignacion_id INTEGER NOT NULL, 
	profesor_suplente_id INTEGER, 
	fecha_clase DATE NOT NULL, 
	motivo TEXT NOT NULL, 
	estado VARCHAR(20) DEFAULT 'Pendiente', 
	notas TEXT, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	fecha_resolucion TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT profesor_suplencias_estado_check CHECK (estado IN ('Pendiente', 'Asignado', 'Confirmado', 'Cancelado')), 
	FOREIGN KEY(asignacion_id) REFERENCES profesor_clase_asignaciones (id) ON DELETE CASCADE, 
	FOREIGN KEY(profesor_suplente_id) REFERENCES profesores (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_especialidades_activo ON especialidades (activo);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_especialidades_nombre ON especialidades (nombre);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_sucursales_activa ON sucursales (activa);\n    """)

    op.execute("""\nCREATE UNIQUE INDEX IF NOT EXISTS uq_sucursales_station_key ON sucursales (station_key) WHERE station_key IS NOT NULL AND TRIM(station_key) <> '';\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_usuarios_activo ON usuarios (activo);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_usuarios_activo_rol_nombre ON usuarios (activo, rol, nombre);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_usuarios_dni ON usuarios (dni);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_usuarios_nombre ON usuarios (nombre);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_usuarios_rol ON usuarios (rol);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_usuarios_rol_nombre ON usuarios (rol, nombre);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_work_session_pauses_session ON work_session_pauses (session_kind, session_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_work_session_pauses_started_at ON work_session_pauses (started_at);\n    """)

    op.execute("""\nCREATE UNIQUE INDEX IF NOT EXISTS uniq_work_session_pause_active ON work_session_pauses (session_kind, session_id) WHERE ended_at IS NULL;\n    """)

    op.execute("ALTER TABLE IF EXISTS asistencias ADD COLUMN IF NOT EXISTS sucursal_id INTEGER;")
    op.execute("ALTER TABLE IF EXISTS checkin_pending ADD COLUMN IF NOT EXISTS sucursal_id INTEGER;")
    op.execute("ALTER TABLE IF EXISTS clases ADD COLUMN IF NOT EXISTS sucursal_id INTEGER;")
    op.execute("ALTER TABLE IF EXISTS clases ADD COLUMN IF NOT EXISTS tipo_clase_id INTEGER;")
    op.execute("ALTER TABLE IF EXISTS pagos ADD COLUMN IF NOT EXISTS sucursal_id INTEGER;")
    op.execute("ALTER TABLE IF EXISTS pagos ADD COLUMN IF NOT EXISTS tipo_cuota_id INTEGER;")
    op.execute("ALTER TABLE IF EXISTS rutinas ADD COLUMN IF NOT EXISTS sucursal_id INTEGER;")
    op.execute("ALTER TABLE IF EXISTS tipo_cuota_clases_permisos ADD COLUMN IF NOT EXISTS sucursal_id INTEGER;")
    op.execute("ALTER TABLE IF EXISTS usuario_accesos_sucursales ADD COLUMN IF NOT EXISTS sucursal_id INTEGER;")
    op.execute("ALTER TABLE IF EXISTS usuario_permisos_clases ADD COLUMN IF NOT EXISTS sucursal_id INTEGER;")
    op.execute("ALTER TABLE IF EXISTS whatsapp_messages ADD COLUMN IF NOT EXISTS sucursal_id INTEGER;")
    op.execute("ALTER TABLE IF EXISTS whatsapp_messages ADD COLUMN IF NOT EXISTS event_key VARCHAR(150);")
    op.execute("ALTER TABLE IF EXISTS profesor_horas_trabajadas ADD COLUMN IF NOT EXISTS sucursal_id INTEGER;")
    op.execute("ALTER TABLE IF EXISTS staff_sessions ADD COLUMN IF NOT EXISTS sucursal_id INTEGER;")

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_asistencias_fecha ON asistencias (fecha);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_asistencias_sucursal_fecha ON asistencias (sucursal_id, fecha);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_asistencias_usuario_fecha ON asistencias (usuario_id, fecha);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_asistencias_usuario_fecha_desc ON asistencias (usuario_id, fecha DESC);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_asistencias_usuario_id ON asistencias (usuario_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs (user_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_checkin_pending_expires_at ON checkin_pending (expires_at);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_checkin_pending_sucursal_expires ON checkin_pending (sucursal_id, expires_at);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_checkin_pending_used ON checkin_pending (used);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_clases_activa_true_nombre ON clases (nombre) WHERE activa = TRUE;\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_clases_nombre ON clases (nombre);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_clases_sucursal_id ON clases (sucursal_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_clases_tipo_clase_id ON clases (tipo_clase_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_memberships_status_end_date ON memberships (status, end_date);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_memberships_usuario_status ON memberships (usuario_id, status);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_pagos_fecha ON pagos (fecha_pago);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_pagos_month_year ON pagos ((EXTRACT(MONTH FROM fecha_pago)), (EXTRACT(YEAR FROM fecha_pago)));\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_pagos_sucursal_id ON pagos (sucursal_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_pagos_tipo_cuota_id ON pagos (tipo_cuota_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_pagos_usuario_fecha_desc ON pagos (usuario_id, fecha_pago DESC);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_pagos_usuario_id ON pagos (usuario_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_rutinas_sucursal_id ON rutinas (sucursal_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_rutinas_usuario_id ON rutinas (usuario_id);\n    """)

    op.execute("""\nCREATE UNIQUE INDEX IF NOT EXISTS idx_rutinas_uuid_rutina ON rutinas (uuid_rutina);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_tipo_cuota_clases_permiso_sucursal ON tipo_cuota_clases_permisos (sucursal_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_tipo_cuota_clases_permiso_tipo_cuota ON tipo_cuota_clases_permisos (tipo_cuota_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_usuario_accesos_sucursales_sucursal ON usuario_accesos_sucursales (sucursal_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_usuario_accesos_sucursales_usuario ON usuario_accesos_sucursales (usuario_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_usuario_estados_creado_por ON usuario_estados (creado_por);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_usuario_estados_usuario_id ON usuario_estados (usuario_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_usuario_etiquetas_asignado_por ON usuario_etiquetas (asignado_por);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_usuario_etiquetas_etiqueta_id ON usuario_etiquetas (etiqueta_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_usuario_etiquetas_usuario_id ON usuario_etiquetas (usuario_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_usuario_notas_autor_id ON usuario_notas (autor_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_usuario_notas_usuario_id ON usuario_notas (usuario_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_usuario_permisos_clases_sucursal ON usuario_permisos_clases (sucursal_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_usuario_permisos_clases_usuario ON usuario_permisos_clases (usuario_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_whatsapp_messages_event_key ON whatsapp_messages (event_key);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_whatsapp_messages_phone ON whatsapp_messages (phone_number);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_whatsapp_messages_sucursal_id ON whatsapp_messages (sucursal_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_whatsapp_messages_type_date ON whatsapp_messages (message_type, sent_at DESC);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_whatsapp_messages_user_id ON whatsapp_messages (user_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_clase_bloques_clase ON clase_bloques (clase_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_clase_bloques_nombre ON clase_bloques (nombre);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_clase_ejercicios_clase_orden ON clase_ejercicios (clase_id, orden);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_clase_ejercicios_ejercicio_id ON clase_ejercicios (ejercicio_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_clases_horarios_clase_id ON clases_horarios (clase_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_comprobantes_pago_fecha ON comprobantes_pago (fecha_creacion);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_comprobantes_pago_numero ON comprobantes_pago (numero_comprobante);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_comprobantes_pago_pago_id ON comprobantes_pago (pago_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_comprobantes_pago_usuario_id ON comprobantes_pago (usuario_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_historial_estados_estado_id ON historial_estados (estado_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_historial_estados_fecha ON historial_estados (fecha_accion);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_historial_estados_usuario_id ON historial_estados (usuario_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_horarios_profesores_profesor_id ON horarios_profesores (profesor_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_pago_detalles_concepto_id ON pago_detalles (concepto_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_pago_detalles_pago_id ON pago_detalles (pago_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_certificaciones_activo ON profesor_certificaciones (activo);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_certificaciones_fecha_vencimiento ON profesor_certificaciones (fecha_vencimiento);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_certificaciones_profesor_id ON profesor_certificaciones (profesor_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_disponibilidad_fecha ON profesor_disponibilidad (fecha);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_disponibilidad_profesor_fecha ON profesor_disponibilidad (profesor_id, fecha);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_disponibilidad_profesor_id ON profesor_disponibilidad (profesor_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_especialidades_activo ON profesor_especialidades (activo);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_especialidades_especialidad_id ON profesor_especialidades (especialidad_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_especialidades_profesor_id ON profesor_especialidades (profesor_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_evaluaciones_profesor_id ON profesor_evaluaciones (profesor_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_evaluaciones_usuario_id ON profesor_evaluaciones (usuario_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_horas_trabajadas_clase_id ON profesor_horas_trabajadas (clase_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_horas_trabajadas_fecha ON profesor_horas_trabajadas (fecha);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_horas_trabajadas_profesor_id ON profesor_horas_trabajadas (profesor_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_horas_trabajadas_sucursal_id ON profesor_horas_trabajadas (sucursal_id);\n    """)

    op.execute("""\nCREATE UNIQUE INDEX IF NOT EXISTS uniq_sesion_activa_por_profesor ON profesor_horas_trabajadas (profesor_id) WHERE hora_fin IS NULL;\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_notificaciones_leida ON profesor_notificaciones (leida);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_notificaciones_profesor ON profesor_notificaciones (profesor_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesores_horarios_disponibilidad_profesor_id ON profesores_horarios_disponibilidad (profesor_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_rutina_ejercicios_ejercicio_id ON rutina_ejercicios (ejercicio_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_rutina_ejercicios_rutina_ejercicio ON rutina_ejercicios (rutina_id, ejercicio_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_rutina_ejercicios_rutina_id ON rutina_ejercicios (rutina_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_staff_sessions_fecha ON staff_sessions (fecha);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_staff_sessions_staff_id ON staff_sessions (staff_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_staff_sessions_sucursal_id ON staff_sessions (sucursal_id);\n    """)

    op.execute("""\nCREATE UNIQUE INDEX IF NOT EXISTS uniq_sesion_activa_por_staff ON staff_sessions (staff_id) WHERE hora_fin IS NULL;\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_clase_asistencia_historial_clase_horario_id ON clase_asistencia_historial (clase_horario_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_clase_asistencia_historial_estado ON clase_asistencia_historial (estado_asistencia);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_clase_asistencia_historial_fecha ON clase_asistencia_historial (fecha_clase);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_clase_asistencia_historial_usuario_id ON clase_asistencia_historial (usuario_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_bloque_items_bloque ON clase_bloque_items (bloque_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_bloque_items_bloque_orden ON clase_bloque_items (bloque_id, orden);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_clase_lista_espera_activo ON clase_lista_espera (activo);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_clase_lista_espera_clase ON clase_lista_espera (clase_horario_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_clase_lista_espera_posicion ON clase_lista_espera (posicion);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_clase_usuarios_clase_horario_id ON clase_usuarios (clase_horario_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_clase_usuarios_usuario_id ON clase_usuarios (usuario_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_notif_cupos_clase ON notificaciones_cupos (clase_horario_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_notif_cupos_leida ON notificaciones_cupos (leida);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_notif_cupos_tipo ON notificaciones_cupos (tipo_notificacion);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_notif_cupos_usuario_activa ON notificaciones_cupos (usuario_id, activa);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_clase_asignaciones_profesor_id ON profesor_clase_asignaciones (profesor_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_suplencias_generales_estado ON profesor_suplencias_generales (estado);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_suplencias_generales_fecha ON profesor_suplencias_generales (fecha);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_suplencias_asignacion ON profesor_suplencias (asignacion_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_suplencias_asignacion_fecha ON profesor_suplencias (asignacion_id, fecha_clase);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_suplencias_estado ON profesor_suplencias (estado);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_suplencias_fecha_clase ON profesor_suplencias (fecha_clase);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_profesor_suplencias_suplente ON profesor_suplencias (profesor_suplente_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_usuarios_telefono ON usuarios(telefono);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_usuarios_fecha_proximo_vencimiento ON usuarios(fecha_proximo_vencimiento);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_pagos_fecha_pago ON pagos(fecha_pago);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_pagos_estado ON pagos(estado);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_ejercicios_nombre ON ejercicios(nombre);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_rutina_ejercicios_rutina_id ON rutina_ejercicios(rutina_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_rutina_ejercicios_ejercicio_id ON rutina_ejercicios(ejercicio_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_comprobantes_pago_pago_id ON comprobantes_pago(pago_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_comprobantes_pago_numero ON comprobantes_pago(numero_comprobante);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_checkin_pending_usuario_id ON checkin_pending(usuario_id);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_checkin_pending_expires_at ON checkin_pending(expires_at);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_rutina_ejercicios_rutina_dia_orden ON rutina_ejercicios (rutina_id, dia_semana, orden);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_comprobantes_pago_emitido_pago_fecha_desc ON comprobantes_pago (pago_id, fecha_creacion DESC) WHERE estado = 'emitido';\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_pagos_metodo_fecha_desc ON pagos (metodo_pago_id, fecha_pago DESC);\n    """)

    op.execute("""\nDO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm') THEN EXECUTE 'CREATE INDEX IF NOT EXISTS idx_usuarios_nombre_trgm ON usuarios USING gin (lower(nombre) gin_trgm_ops)'; END IF; END $$;\n    """)

    op.execute("""\nDO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm') THEN EXECUTE 'CREATE INDEX IF NOT EXISTS idx_rutinas_nombre_trgm ON rutinas USING gin (lower(nombre_rutina) gin_trgm_ops)'; END IF; END $$;\n    """)

    op.execute("""\nDO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm') THEN EXECUTE 'CREATE INDEX IF NOT EXISTS idx_ejercicios_nombre_trgm ON ejercicios USING gin (lower(nombre) gin_trgm_ops)'; END IF; END $$;\n    """)

    op.execute("""\nALTER TABLE IF EXISTS ejercicios ADD COLUMN IF NOT EXISTS variantes TEXT;\n    """)

    op.execute("""\nALTER TABLE IF EXISTS sucursales ADD COLUMN IF NOT EXISTS station_key VARCHAR(64);\n    """)

    op.execute("""\nALTER TABLE IF EXISTS usuarios ALTER COLUMN pin TYPE VARCHAR(100);\n    """)

    op.execute("""\nALTER TABLE IF EXISTS usuarios ALTER COLUMN pin SET DEFAULT '123456';\n    """)

    op.execute("""\nINSERT INTO sucursales (nombre, codigo)
        SELECT 'Sucursal Principal', 'principal'
        WHERE NOT EXISTS (SELECT 1 FROM sucursales);\n    """)

    op.execute("""\nDO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'asistencias' AND column_name = 'sucursal_id'
            ) THEN
                UPDATE asistencias
                SET sucursal_id = (SELECT id FROM sucursales ORDER BY id ASC LIMIT 1)
                WHERE sucursal_id IS NULL;
            END IF;
        END $$;\n    """)

    op.execute("""\nDO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'checkin_pending' AND column_name = 'sucursal_id'
            ) THEN
                UPDATE checkin_pending
                SET sucursal_id = (SELECT id FROM sucursales ORDER BY id ASC LIMIT 1)
                WHERE sucursal_id IS NULL;
            END IF;
        END $$;\n    """)


def downgrade() -> None:
    return
