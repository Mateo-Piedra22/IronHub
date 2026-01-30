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
\tid SERIAL NOT NULL, 
\tnombre VARCHAR(100) NOT NULL, 
\tdescripcion TEXT, 
\tprecio_base NUMERIC(10, 2) DEFAULT '0.0', 
\ttipo VARCHAR(20) DEFAULT 'fijo' NOT NULL, 
\tactivo BOOLEAN DEFAULT 'true' NOT NULL, 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tUNIQUE (nombre)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS configuracion (
\tid SERIAL NOT NULL, 
\tclave VARCHAR(255) NOT NULL, 
\tvalor TEXT NOT NULL, 
\ttipo VARCHAR(50) DEFAULT 'string', 
\tdescripcion TEXT, 
\tPRIMARY KEY (id), 
\tUNIQUE (clave)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS ejercicio_grupos (
\tid SERIAL NOT NULL, 
\tnombre VARCHAR(255) NOT NULL, 
\tPRIMARY KEY (id), 
\tUNIQUE (nombre)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS especialidades (
\tid SERIAL NOT NULL, 
\tnombre VARCHAR(100) NOT NULL, 
\tdescripcion TEXT, 
\tcategoria VARCHAR(50), 
\tactivo BOOLEAN DEFAULT 'true' NOT NULL, 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tUNIQUE (nombre)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS etiquetas (
\tid SERIAL NOT NULL, 
\tnombre VARCHAR(100) NOT NULL, 
\tcolor VARCHAR(7) DEFAULT '#3498db' NOT NULL, 
\tdescripcion TEXT, 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tactivo BOOLEAN DEFAULT 'true' NOT NULL, 
\tPRIMARY KEY (id), 
\tUNIQUE (nombre)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS feature_flags (
\tid SMALLSERIAL NOT NULL, 
\tflags JSONB DEFAULT '{}'::jsonb NOT NULL, 
\tupdated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS gym_config (
\tid SERIAL NOT NULL, 
\tgym_name TEXT DEFAULT '', 
\tgym_slogan TEXT DEFAULT '', 
\tgym_address TEXT DEFAULT '', 
\tgym_phone TEXT DEFAULT '', 
\tgym_email TEXT DEFAULT '', 
\tgym_website TEXT DEFAULT '', 
\tfacebook TEXT DEFAULT '', 
\tinstagram TEXT DEFAULT '', 
\ttwitter TEXT DEFAULT '', 
\tlogo_url TEXT DEFAULT '', 
\tupdated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS metodos_pago (
\tid SERIAL NOT NULL, 
\tnombre VARCHAR(100) NOT NULL, 
\ticono VARCHAR(10), 
\tcolor VARCHAR(7) DEFAULT '#3498db' NOT NULL, 
\tcomision NUMERIC(5, 2) DEFAULT '0.0', 
\tactivo BOOLEAN DEFAULT 'true' NOT NULL, 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tdescripcion TEXT, 
\tPRIMARY KEY (id), 
\tUNIQUE (nombre)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS numeracion_comprobantes (
\tid SERIAL NOT NULL, 
\ttipo_comprobante VARCHAR(50) NOT NULL, 
\tprefijo VARCHAR(10) DEFAULT '' NOT NULL, 
\tnumero_inicial INTEGER DEFAULT '1' NOT NULL, 
\tseparador VARCHAR(5) DEFAULT '-' NOT NULL, 
\treiniciar_anual BOOLEAN DEFAULT 'false', 
\tlongitud_numero INTEGER DEFAULT '8' NOT NULL, 
\tactivo BOOLEAN DEFAULT 'true', 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tUNIQUE (tipo_comprobante)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS sucursales (
\tid SERIAL NOT NULL, 
\tnombre VARCHAR(255) NOT NULL, 
\tcodigo VARCHAR(80) NOT NULL, 
\tdireccion TEXT, 
\ttimezone VARCHAR(80), 
\tstation_key VARCHAR(64), 
\tactiva BOOLEAN DEFAULT 'true' NOT NULL, 
\tcreated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tUNIQUE (codigo)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS theme_scheduling_config (
\tid SERIAL NOT NULL, 
\tclave VARCHAR(100) NOT NULL, 
\tvalor TEXT NOT NULL, 
\tconfig_data JSONB, 
\tconfig_type VARCHAR(50) DEFAULT 'general', 
\tdescripcion TEXT, 
\tfecha_actualizacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tUNIQUE (clave)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS tipos_clases (
\tid SERIAL NOT NULL, 
\tnombre VARCHAR(255) NOT NULL, 
\tdescripcion TEXT, 
\tactivo BOOLEAN DEFAULT 'true' NOT NULL, 
\tPRIMARY KEY (id), 
\tUNIQUE (nombre)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS tipos_cuota (
\tid SERIAL NOT NULL, 
\tnombre VARCHAR(100) NOT NULL, 
\tprecio NUMERIC(10, 2) NOT NULL, 
\ticono_path VARCHAR(255), 
\tactivo BOOLEAN DEFAULT 'true' NOT NULL, 
\tall_sucursales BOOLEAN DEFAULT 'true' NOT NULL, 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tdescripcion TEXT, 
\tduracion_dias INTEGER DEFAULT '30', 
\tfecha_modificacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
\tPRIMARY KEY (id), 
\tUNIQUE (nombre)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS usuarios (
\tid SERIAL NOT NULL, 
\tnombre VARCHAR(255) NOT NULL, 
\tdni VARCHAR(20), 
\ttelefono VARCHAR(50) NOT NULL, 
\tpin VARCHAR(100) DEFAULT '123456', 
\trol VARCHAR(50) DEFAULT 'socio' NOT NULL, 
\tnotas TEXT, 
\tfecha_registro TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tactivo BOOLEAN DEFAULT 'true' NOT NULL, 
\ttipo_cuota VARCHAR(100) DEFAULT 'estandar', 
\tultimo_pago DATE, 
\tfecha_proximo_vencimiento DATE, 
\tcuotas_vencidas INTEGER DEFAULT '0', 
\tPRIMARY KEY (id), 
\tUNIQUE (dni)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS whatsapp_templates (
\tid SERIAL NOT NULL, 
\ttemplate_name VARCHAR(255) NOT NULL, 
\theader_text VARCHAR(60), 
\tbody_text TEXT NOT NULL, 
\tvariables JSONB, 
\tactive BOOLEAN DEFAULT 'true' NOT NULL, 
\tcreated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tUNIQUE (template_name)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS work_session_pauses (
\tid SERIAL NOT NULL, 
\tsession_kind VARCHAR(20) NOT NULL, 
\tsession_id INTEGER NOT NULL, 
\tstarted_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
\tended_at TIMESTAMP WITHOUT TIME ZONE, 
\tcreated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tCONSTRAINT work_session_pauses_kind_check CHECK (session_kind IN ('profesor','staff'))
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS acciones_masivas_pendientes (
\tid SERIAL NOT NULL, 
\toperation_id VARCHAR(100) NOT NULL, 
\ttipo VARCHAR(50) NOT NULL, 
\tdescripcion TEXT, 
\tusuario_ids INTEGER[] NOT NULL, 
\tparametros JSONB, 
\testado VARCHAR(20) DEFAULT 'pendiente', 
\tfecha_programada TIMESTAMP WITHOUT TIME ZONE, 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tfecha_ejecucion TIMESTAMP WITHOUT TIME ZONE, 
\tcreado_por INTEGER, 
\tresultado JSONB, 
\terror_message TEXT, 
\tPRIMARY KEY (id), 
\tUNIQUE (operation_id), 
\tFOREIGN KEY(creado_por) REFERENCES usuarios (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS asistencias (
\tid SERIAL NOT NULL, 
\tusuario_id INTEGER NOT NULL, 
\tsucursal_id INTEGER, 
\tfecha DATE DEFAULT CURRENT_DATE NOT NULL, 
\thora_registro TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\thora_entrada TIME WITHOUT TIME ZONE, 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
\tFOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS audit_logs (
\tid SERIAL NOT NULL, 
\tuser_id INTEGER, 
\taction VARCHAR(50) NOT NULL, 
\ttable_name VARCHAR(100) NOT NULL, 
\trecord_id INTEGER, 
\told_values TEXT, 
\tnew_values TEXT, 
\tip_address INET, 
\tuser_agent TEXT, 
\tsession_id VARCHAR(255), 
\ttimestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(user_id) REFERENCES usuarios (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS checkin_pending (
\tid SERIAL NOT NULL, 
\tusuario_id INTEGER NOT NULL, 
\tsucursal_id INTEGER, 
\ttoken VARCHAR(64) NOT NULL, 
\tcreated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\texpires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
\tused BOOLEAN DEFAULT 'false', 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
\tFOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE SET NULL, 
\tUNIQUE (token)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS clases (
\tid SERIAL NOT NULL, 
\tnombre VARCHAR(255) NOT NULL, 
\tdescripcion TEXT, 
\tactiva BOOLEAN DEFAULT 'true' NOT NULL, 
\tsucursal_id INTEGER, 
\ttipo_clase_id INTEGER, 
\tPRIMARY KEY (id), 
\tUNIQUE (nombre), 
\tFOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS custom_themes (
\tid SERIAL NOT NULL, 
\tnombre VARCHAR(100) NOT NULL, 
\tname VARCHAR(100) NOT NULL, 
\tdata JSONB, 
\tcolores JSONB NOT NULL, 
\tactivo BOOLEAN DEFAULT 'true' NOT NULL, 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tusuario_creador_id INTEGER, 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(usuario_creador_id) REFERENCES usuarios (id)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS ejercicios (
\tid SERIAL NOT NULL, 
\tnombre VARCHAR(255) NOT NULL, 
\tdescripcion TEXT, 
\tgrupo_muscular VARCHAR(100), 
\tobjetivo VARCHAR(100) DEFAULT 'general', 
\tequipamiento VARCHAR(100), 
\tvariantes TEXT, 
\tvideo_url VARCHAR(512), 
\tvideo_mime VARCHAR(50), 
\tsucursal_id INTEGER, 
\tPRIMARY KEY (id), 
\tUNIQUE (nombre), 
\tFOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS feature_flags_overrides (
\tsucursal_id INTEGER NOT NULL, 
\tflags JSONB DEFAULT '{}'::jsonb NOT NULL, 
\tupdated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (sucursal_id), 
\tFOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS maintenance_tasks (
\tid SERIAL NOT NULL, 
\ttask_name TEXT NOT NULL, 
\ttask_type TEXT NOT NULL, 
\tdescription TEXT, 
\tscheduled_at TIMESTAMP WITHOUT TIME ZONE, 
\texecuted_at TIMESTAMP WITHOUT TIME ZONE, 
\tstatus TEXT DEFAULT 'pending', 
\tresult TEXT, 
\terror_message TEXT, 
\tcreated_by INTEGER, 
\texecuted_by INTEGER, 
\tauto_schedule BOOLEAN DEFAULT 'false', 
\tfrequency_days INTEGER, 
\tnext_execution TIMESTAMP WITHOUT TIME ZONE, 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(created_by) REFERENCES usuarios (id), 
\tFOREIGN KEY(executed_by) REFERENCES usuarios (id)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS memberships (
\tid SERIAL NOT NULL, 
\tusuario_id INTEGER NOT NULL, 
\tplan_name TEXT, 
\tstatus VARCHAR(20) DEFAULT 'active' NOT NULL, 
\tstart_date DATE DEFAULT CURRENT_DATE NOT NULL, 
\tend_date DATE, 
\tall_sucursales BOOLEAN DEFAULT 'false' NOT NULL, 
\tcreated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tupdated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS pagos (
\tid SERIAL NOT NULL, 
\tusuario_id INTEGER NOT NULL, 
\tsucursal_id INTEGER, 
\ttipo_cuota_id INTEGER, 
\tmonto NUMERIC(10, 2) NOT NULL, 
\tmes INTEGER NOT NULL, 
\t\"año\" INTEGER NOT NULL, 
\tfecha_pago TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tmetodo_pago_id INTEGER, 
\tconcepto VARCHAR(100), 
\tmetodo_pago VARCHAR(50), 
\testado VARCHAR(20) DEFAULT 'pagado', 
\tPRIMARY KEY (id), 
\tCONSTRAINT \"idx_pagos_usuario_mes_año\" UNIQUE (usuario_id, mes, \"año\"), 
\tFOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
\tFOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE SET NULL, 
\tFOREIGN KEY(tipo_cuota_id) REFERENCES tipos_cuota (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS profesores (
\tid SERIAL NOT NULL, 
\tusuario_id INTEGER NOT NULL, 
\ttipo VARCHAR(50) DEFAULT 'Musculación', 
\tespecialidades TEXT, 
\tcertificaciones TEXT, 
\t\"experiencia_años\" INTEGER DEFAULT '0', 
\ttarifa_por_hora NUMERIC(10, 2) DEFAULT '0.0', 
\thorario_disponible TEXT, 
\tfecha_contratacion DATE, 
\testado VARCHAR(20) DEFAULT 'activo', 
\tbiografia TEXT, 
\tfoto_perfil VARCHAR(255), 
\ttelefono_emergencia VARCHAR(50), 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tfecha_actualizacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tCONSTRAINT profesores_estado_check CHECK (estado IN ('activo', 'inactivo', 'vacaciones')), 
\tUNIQUE (usuario_id), 
\tFOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS rutinas (
\tid SERIAL NOT NULL, 
\tusuario_id INTEGER, 
\tnombre_rutina VARCHAR(255) NOT NULL, 
\tdescripcion TEXT, 
\tdias_semana INTEGER, 
\tcategoria VARCHAR(100) DEFAULT 'general', 
\tsucursal_id INTEGER, 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tactiva BOOLEAN DEFAULT 'true' NOT NULL, 
\tuuid_rutina VARCHAR(36), 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
\tFOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE SET NULL, 
\tUNIQUE (uuid_rutina)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS staff_permissions (
\tusuario_id INTEGER NOT NULL, 
\tscopes JSONB DEFAULT '[]'::jsonb NOT NULL, 
\tupdated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (usuario_id), 
\tFOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS staff_profiles (
\tid SERIAL NOT NULL, 
\tusuario_id INTEGER NOT NULL, 
\ttipo VARCHAR(50) DEFAULT 'empleado' NOT NULL, 
\testado VARCHAR(20) DEFAULT 'activo' NOT NULL, 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tfecha_actualizacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tCONSTRAINT staff_profiles_estado_check CHECK (estado IN ('activo', 'inactivo', 'vacaciones')), 
\tUNIQUE (usuario_id), 
\tFOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS system_diagnostics (
\tid SERIAL NOT NULL, 
\ttimestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tdiagnostic_type TEXT NOT NULL, 
\tcomponent TEXT NOT NULL, 
\tstatus TEXT NOT NULL, 
\tdetails TEXT, 
\tmetrics TEXT, 
\tresolved BOOLEAN DEFAULT 'false', 
\tresolved_at TIMESTAMP WITHOUT TIME ZONE, 
\tresolved_by INTEGER, 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(resolved_by) REFERENCES usuarios (id)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS tipo_cuota_clases_permisos (
\tid SERIAL NOT NULL, 
\ttipo_cuota_id INTEGER NOT NULL, 
\tsucursal_id INTEGER, 
\ttarget_type VARCHAR(20) NOT NULL, 
\ttarget_id INTEGER NOT NULL, 
\tallow BOOLEAN DEFAULT 'true' NOT NULL, 
\tcreated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tCONSTRAINT uq_tipo_cuota_clases_permiso UNIQUE (tipo_cuota_id, sucursal_id, target_type, target_id), 
\tFOREIGN KEY(tipo_cuota_id) REFERENCES tipos_cuota (id) ON DELETE CASCADE, 
\tFOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS tipo_cuota_sucursales (
\ttipo_cuota_id INTEGER NOT NULL, 
\tsucursal_id INTEGER NOT NULL, 
\tcreated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (tipo_cuota_id, sucursal_id), 
\tFOREIGN KEY(tipo_cuota_id) REFERENCES tipos_cuota (id) ON DELETE CASCADE, 
\tFOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS usuario_accesos_sucursales (
\tid SERIAL NOT NULL, 
\tusuario_id INTEGER NOT NULL, 
\tsucursal_id INTEGER NOT NULL, 
\tallow BOOLEAN NOT NULL, 
\tmotivo TEXT, 
\tstarts_at TIMESTAMP WITHOUT TIME ZONE, 
\tends_at TIMESTAMP WITHOUT TIME ZONE, 
\tcreated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tCONSTRAINT uq_usuario_accesos_sucursales UNIQUE (usuario_id, sucursal_id), 
\tFOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
\tFOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS usuario_estados (
\tid SERIAL NOT NULL, 
\tusuario_id INTEGER NOT NULL, 
\testado VARCHAR(100) NOT NULL, 
\tdescripcion TEXT, 
\tfecha_inicio TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tfecha_vencimiento TIMESTAMP WITHOUT TIME ZONE, 
\tactivo BOOLEAN DEFAULT 'true' NOT NULL, 
\tcreado_por INTEGER, 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
\tFOREIGN KEY(creado_por) REFERENCES usuarios (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS usuario_etiquetas (
\tusuario_id INTEGER NOT NULL, 
\tetiqueta_id INTEGER NOT NULL, 
\tfecha_asignacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tasignado_por INTEGER, 
\tPRIMARY KEY (usuario_id, etiqueta_id), 
\tFOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
\tFOREIGN KEY(etiqueta_id) REFERENCES etiquetas (id) ON DELETE CASCADE, 
\tFOREIGN KEY(asignado_por) REFERENCES usuarios (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS usuario_notas (
\tid SERIAL NOT NULL, 
\tusuario_id INTEGER NOT NULL, 
\tcategoria VARCHAR(50) DEFAULT 'general' NOT NULL, 
\ttitulo VARCHAR(255) NOT NULL, 
\tcontenido TEXT NOT NULL, 
\timportancia VARCHAR(20) DEFAULT 'normal' NOT NULL, 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tfecha_modificacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tactiva BOOLEAN DEFAULT 'true' NOT NULL, 
\tautor_id INTEGER, 
\tPRIMARY KEY (id), 
\tCONSTRAINT usuario_notas_categoria_check CHECK (categoria IN ('general', 'medica', 'administrativa', 'comportamiento')), 
\tCONSTRAINT usuario_notas_importancia_check CHECK (importancia IN ('baja', 'normal', 'alta', 'critica')), 
\tFOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
\tFOREIGN KEY(autor_id) REFERENCES usuarios (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS usuario_permisos_clases (
\tid SERIAL NOT NULL, 
\tusuario_id INTEGER NOT NULL, 
\tsucursal_id INTEGER, 
\ttarget_type VARCHAR(20) NOT NULL, 
\ttarget_id INTEGER NOT NULL, 
\tallow BOOLEAN NOT NULL, 
\tmotivo TEXT, 
\tstarts_at TIMESTAMP WITHOUT TIME ZONE, 
\tends_at TIMESTAMP WITHOUT TIME ZONE, 
\tcreated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tCONSTRAINT uq_usuario_permisos_clases UNIQUE (usuario_id, sucursal_id, target_type, target_id), 
\tFOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
\tFOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS usuario_sucursales (
\tusuario_id INTEGER NOT NULL, 
\tsucursal_id INTEGER NOT NULL, 
\tcreated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (usuario_id, sucursal_id), 
\tFOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
\tFOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS whatsapp_config (
\tid SERIAL NOT NULL, 
\tphone_id VARCHAR(50) NOT NULL, 
\twaba_id VARCHAR(50) NOT NULL, 
\taccess_token TEXT, 
\tactive BOOLEAN DEFAULT 'true' NOT NULL, 
\tsucursal_id INTEGER, 
\tcreated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS whatsapp_messages (
\tid SERIAL NOT NULL, 
\tuser_id INTEGER, 
\tsucursal_id INTEGER, 
\tevent_key VARCHAR(150), 
\tmessage_type VARCHAR(50) NOT NULL, 
\ttemplate_name VARCHAR(255) NOT NULL, 
\tphone_number VARCHAR(20) NOT NULL, 
\tmessage_id VARCHAR(100), 
\tsent_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tstatus VARCHAR(20) DEFAULT 'sent', 
\tmessage_content TEXT, 
\tcreated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(user_id) REFERENCES usuarios (id), 
\tFOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE SET NULL, 
\tUNIQUE (message_id)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS clase_bloques (
\tid SERIAL NOT NULL, 
\tclase_id INTEGER NOT NULL, 
\tnombre TEXT NOT NULL, 
\tcreated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tupdated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(clase_id) REFERENCES clases (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS clase_ejercicios (
\tclase_id INTEGER NOT NULL, 
\tejercicio_id INTEGER NOT NULL, 
\torden INTEGER DEFAULT '0', 
\tseries INTEGER DEFAULT '0', 
\trepeticiones VARCHAR(50) DEFAULT '', 
\tdescanso_segundos INTEGER DEFAULT '0', 
\tnotas TEXT, 
\tPRIMARY KEY (clase_id, ejercicio_id), 
\tFOREIGN KEY(clase_id) REFERENCES clases (id) ON DELETE CASCADE, 
\tFOREIGN KEY(ejercicio_id) REFERENCES ejercicios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS clases_horarios (
\tid SERIAL NOT NULL, 
\tclase_id INTEGER NOT NULL, 
\tdia_semana VARCHAR(20) NOT NULL, 
\thora_inicio TIME WITHOUT TIME ZONE NOT NULL, 
\thora_fin TIME WITHOUT TIME ZONE NOT NULL, 
\tcupo_maximo INTEGER DEFAULT '20', 
\tactivo BOOLEAN DEFAULT 'true' NOT NULL, 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(clase_id) REFERENCES clases (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS comprobantes_pago (
\tid SERIAL NOT NULL, 
\tnumero_comprobante VARCHAR(50) NOT NULL, 
\tpago_id INTEGER NOT NULL, 
\tusuario_id INTEGER NOT NULL, 
\ttipo_comprobante VARCHAR(50) DEFAULT 'recibo' NOT NULL, 
\tmonto_total NUMERIC(10, 2) DEFAULT '0.0' NOT NULL, 
\testado VARCHAR(20) DEFAULT 'emitido', 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tarchivo_pdf VARCHAR(500), 
\tplantilla_id INTEGER, 
\tdatos_comprobante JSONB, 
\temitido_por VARCHAR(255), 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(pago_id) REFERENCES pagos (id) ON DELETE CASCADE, 
\tFOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS ejercicio_grupo_items (
\tgrupo_id INTEGER NOT NULL, 
\tejercicio_id INTEGER NOT NULL, 
\tPRIMARY KEY (grupo_id, ejercicio_id), 
\tFOREIGN KEY(grupo_id) REFERENCES ejercicio_grupos (id) ON DELETE CASCADE, 
\tFOREIGN KEY(ejercicio_id) REFERENCES ejercicios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS historial_estados (
\tid SERIAL NOT NULL, 
\tusuario_id INTEGER NOT NULL, 
\testado_id INTEGER, 
\taccion VARCHAR(50) NOT NULL, 
\tfecha_accion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tdetalles TEXT, 
\tcreado_por INTEGER, 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
\tFOREIGN KEY(estado_id) REFERENCES usuario_estados (id) ON DELETE CASCADE, 
\tFOREIGN KEY(creado_por) REFERENCES usuarios (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS horarios_profesores (
\tid SERIAL NOT NULL, 
\tprofesor_id INTEGER NOT NULL, 
\tdia_semana VARCHAR(20) NOT NULL, 
\thora_inicio TIME WITHOUT TIME ZONE NOT NULL, 
\thora_fin TIME WITHOUT TIME ZONE NOT NULL, 
\tdisponible BOOLEAN DEFAULT 'true' NOT NULL, 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(profesor_id) REFERENCES profesores (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS membership_sucursales (
\tmembership_id INTEGER NOT NULL, 
\tsucursal_id INTEGER NOT NULL, 
\tcreated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (membership_id, sucursal_id), 
\tFOREIGN KEY(membership_id) REFERENCES memberships (id) ON DELETE CASCADE, 
\tFOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS pago_detalles (
\tid SERIAL NOT NULL, 
\tpago_id INTEGER NOT NULL, 
\tconcepto_id INTEGER, 
\tdescripcion TEXT, 
\tcantidad NUMERIC(10, 2) DEFAULT '1' NOT NULL, 
\tprecio_unitario NUMERIC(10, 2) NOT NULL, 
\tsubtotal NUMERIC(10, 2) NOT NULL, 
\tdescuento NUMERIC(10, 2) DEFAULT '0' NOT NULL, 
\ttotal NUMERIC(10, 2) NOT NULL, 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(pago_id) REFERENCES pagos (id) ON DELETE CASCADE, 
\tFOREIGN KEY(concepto_id) REFERENCES conceptos_pago (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS profesor_certificaciones (
\tid SERIAL NOT NULL, 
\tprofesor_id INTEGER NOT NULL, 
\tnombre_certificacion VARCHAR(200) NOT NULL, 
\tinstitucion_emisora VARCHAR(200), 
\tfecha_obtencion DATE, 
\tfecha_vencimiento DATE, 
\tnumero_certificado VARCHAR(100), 
\tarchivo_adjunto VARCHAR(500), 
\testado VARCHAR(20) DEFAULT 'vigente', 
\tnotas TEXT, 
\tactivo BOOLEAN DEFAULT 'true' NOT NULL, 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(profesor_id) REFERENCES profesores (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS profesor_disponibilidad (
\tid SERIAL NOT NULL, 
\tprofesor_id INTEGER NOT NULL, 
\tfecha DATE NOT NULL, 
\ttipo_disponibilidad VARCHAR(50) NOT NULL, 
\thora_inicio TIME WITHOUT TIME ZONE, 
\thora_fin TIME WITHOUT TIME ZONE, 
\tnotas TEXT, 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tfecha_modificacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tCONSTRAINT profesor_disponibilidad_tipo_disponibilidad_check CHECK (tipo_disponibilidad IN ('Disponible', 'No Disponible', 'Parcialmente Disponible')), 
\tCONSTRAINT profesor_disponibilidad_profesor_id_fecha_key UNIQUE (profesor_id, fecha), 
\tFOREIGN KEY(profesor_id) REFERENCES profesores (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS profesor_especialidades (
\tid SERIAL NOT NULL, 
\tprofesor_id INTEGER NOT NULL, 
\tespecialidad_id INTEGER NOT NULL, 
\tfecha_asignacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tactivo BOOLEAN DEFAULT 'true' NOT NULL, 
\tnivel_experiencia VARCHAR(50), 
\t\"años_experiencia\" INTEGER DEFAULT '0', 
\tPRIMARY KEY (id), 
\tCONSTRAINT profesor_especialidades_profesor_id_especialidad_id_key UNIQUE (profesor_id, especialidad_id), 
\tFOREIGN KEY(profesor_id) REFERENCES profesores (id) ON DELETE CASCADE, 
\tFOREIGN KEY(especialidad_id) REFERENCES especialidades (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS profesor_evaluaciones (
\tid SERIAL NOT NULL, 
\tprofesor_id INTEGER NOT NULL, 
\tusuario_id INTEGER NOT NULL, 
\tpuntuacion INTEGER NOT NULL, 
\tcomentario TEXT, 
\tfecha_evaluacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tCONSTRAINT profesor_evaluaciones_puntuacion_check CHECK (puntuacion >= 1 AND puntuacion <= 5), 
\tCONSTRAINT profesor_evaluaciones_profesor_id_usuario_id_key UNIQUE (profesor_id, usuario_id), 
\tFOREIGN KEY(profesor_id) REFERENCES profesores (id) ON DELETE CASCADE, 
\tFOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS profesor_horas_trabajadas (
\tid SERIAL NOT NULL, 
\tprofesor_id INTEGER NOT NULL, 
\tsucursal_id INTEGER, 
\tfecha DATE NOT NULL, 
\thora_inicio TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
\thora_fin TIMESTAMP WITHOUT TIME ZONE, 
\tminutos_totales INTEGER, 
\thoras_totales NUMERIC(8, 2), 
\ttipo_actividad VARCHAR(50), 
\tclase_id INTEGER, 
\tnotas TEXT, 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(profesor_id) REFERENCES profesores (id) ON DELETE CASCADE, 
\tFOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE SET NULL, 
\tFOREIGN KEY(clase_id) REFERENCES clases (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS profesor_notificaciones (
\tid SERIAL NOT NULL, 
\tprofesor_id INTEGER NOT NULL, 
\tmensaje TEXT NOT NULL, 
\tleida BOOLEAN DEFAULT 'false' NOT NULL, 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tfecha_lectura TIMESTAMP WITHOUT TIME ZONE, 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(profesor_id) REFERENCES profesores (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS profesores_horarios_disponibilidad (
\tid SERIAL NOT NULL, 
\tprofesor_id INTEGER NOT NULL, 
\tdia_semana INTEGER NOT NULL, 
\thora_inicio TIME WITHOUT TIME ZONE NOT NULL, 
\thora_fin TIME WITHOUT TIME ZONE NOT NULL, 
\tdisponible BOOLEAN DEFAULT 'true' NOT NULL, 
\ttipo_disponibilidad VARCHAR(50) DEFAULT 'regular', 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tfecha_actualizacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tCONSTRAINT profesores_horarios_disponibilidad_dia_semana_check CHECK (dia_semana BETWEEN 0 AND 6), 
\tFOREIGN KEY(profesor_id) REFERENCES profesores (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS rutina_ejercicios (
\tid SERIAL NOT NULL, 
\trutina_id INTEGER NOT NULL, 
\tejercicio_id INTEGER NOT NULL, 
\tdia_semana INTEGER, 
\tseries INTEGER, 
\trepeticiones VARCHAR(50), 
\torden INTEGER, 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(rutina_id) REFERENCES rutinas (id) ON DELETE CASCADE, 
\tFOREIGN KEY(ejercicio_id) REFERENCES ejercicios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS staff_sessions (
\tid SERIAL NOT NULL, 
\tstaff_id INTEGER NOT NULL, 
\tsucursal_id INTEGER, 
\tfecha DATE NOT NULL, 
\thora_inicio TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
\thora_fin TIMESTAMP WITHOUT TIME ZONE, 
\tminutos_totales INTEGER, 
\tnotas TEXT, 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(staff_id) REFERENCES staff_profiles (id) ON DELETE CASCADE, 
\tFOREIGN KEY(sucursal_id) REFERENCES sucursales (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS theme_schedules (
\tid SERIAL NOT NULL, 
\tname VARCHAR(200) NOT NULL, 
\ttheme_name VARCHAR(100) NOT NULL, 
\ttheme_id INTEGER, 
\tstart_time TIME WITHOUT TIME ZONE NOT NULL, 
\tend_time TIME WITHOUT TIME ZONE NOT NULL, 
\tmonday BOOLEAN DEFAULT 'false', 
\ttuesday BOOLEAN DEFAULT 'false', 
\twednesday BOOLEAN DEFAULT 'false', 
\tthursday BOOLEAN DEFAULT 'false', 
\tfriday BOOLEAN DEFAULT 'false', 
\tsaturday BOOLEAN DEFAULT 'false', 
\tsunday BOOLEAN DEFAULT 'false', 
\tis_active BOOLEAN DEFAULT 'true', 
\tfecha_inicio DATE, 
\tfecha_fin DATE, 
\tactivo BOOLEAN DEFAULT 'true', 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(theme_id) REFERENCES custom_themes (id)
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS clase_asistencia_historial (
\tid SERIAL NOT NULL, 
\tclase_horario_id INTEGER NOT NULL, 
\tusuario_id INTEGER NOT NULL, 
\tfecha_clase DATE NOT NULL, 
\testado_asistencia VARCHAR(20) DEFAULT 'presente', 
\thora_llegada TIME WITHOUT TIME ZONE, 
\tobservaciones TEXT, 
\tregistrado_por INTEGER, 
\tfecha_registro TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tUNIQUE (clase_horario_id, usuario_id, fecha_clase), 
\tFOREIGN KEY(clase_horario_id) REFERENCES clases_horarios (id) ON DELETE CASCADE, 
\tFOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
\tFOREIGN KEY(registrado_por) REFERENCES usuarios (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS clase_bloque_items (
\tid SERIAL NOT NULL, 
\tbloque_id INTEGER NOT NULL, 
\tejercicio_id INTEGER NOT NULL, 
\torden INTEGER DEFAULT '0' NOT NULL, 
\tseries INTEGER DEFAULT '0', 
\trepeticiones TEXT, 
\tdescanso_segundos INTEGER DEFAULT '0', 
\tnotas TEXT, 
\tPRIMARY KEY (id), 
\tFOREIGN KEY(bloque_id) REFERENCES clase_bloques (id) ON DELETE CASCADE, 
\tFOREIGN KEY(ejercicio_id) REFERENCES ejercicios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS clase_lista_espera (
\tid SERIAL NOT NULL, 
\tclase_horario_id INTEGER NOT NULL, 
\tusuario_id INTEGER NOT NULL, 
\tposicion INTEGER NOT NULL, 
\tactivo BOOLEAN DEFAULT 'true' NOT NULL, 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tCONSTRAINT clase_lista_espera_clase_horario_id_usuario_id_key UNIQUE (clase_horario_id, usuario_id), 
\tFOREIGN KEY(clase_horario_id) REFERENCES clases_horarios (id) ON DELETE CASCADE, 
\tFOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS clase_usuarios (
\tid SERIAL NOT NULL, 
\tclase_horario_id INTEGER NOT NULL, 
\tusuario_id INTEGER NOT NULL, 
\tfecha_inscripcion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tPRIMARY KEY (id), 
\tCONSTRAINT clase_usuarios_clase_horario_id_usuario_id_key UNIQUE (clase_horario_id, usuario_id), 
\tFOREIGN KEY(clase_horario_id) REFERENCES clases_horarios (id) ON DELETE CASCADE, 
\tFOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS notificaciones_cupos (
\tid SERIAL NOT NULL, 
\tusuario_id INTEGER NOT NULL, 
\tclase_horario_id INTEGER NOT NULL, 
\ttipo_notificacion VARCHAR(50) NOT NULL, 
\tmensaje TEXT, 
\tleida BOOLEAN DEFAULT 'false' NOT NULL, 
\tactiva BOOLEAN DEFAULT 'true' NOT NULL, 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tfecha_lectura TIMESTAMP WITHOUT TIME ZONE, 
\tPRIMARY KEY (id), 
\tCONSTRAINT notificaciones_cupos_tipo_notificacion_check CHECK (tipo_notificacion IN ('cupo_liberado','promocion','recordatorio')), 
\tFOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
\tFOREIGN KEY(clase_horario_id) REFERENCES clases_horarios (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS profesor_clase_asignaciones (
\tid SERIAL NOT NULL, 
\tclase_horario_id INTEGER NOT NULL, 
\tprofesor_id INTEGER NOT NULL, 
\tfecha_asignacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tactiva BOOLEAN DEFAULT 'true' NOT NULL, 
\tPRIMARY KEY (id), 
\tCONSTRAINT profesor_clase_asignaciones_clase_horario_id_profesor_id_key UNIQUE (clase_horario_id, profesor_id), 
\tFOREIGN KEY(clase_horario_id) REFERENCES clases_horarios (id) ON DELETE CASCADE, 
\tFOREIGN KEY(profesor_id) REFERENCES profesores (id) ON DELETE CASCADE
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS profesor_suplencias_generales (
\tid SERIAL NOT NULL, 
\thorario_profesor_id INTEGER, 
\tprofesor_original_id INTEGER NOT NULL, 
\tprofesor_suplente_id INTEGER, 
\tfecha DATE NOT NULL, 
\thora_inicio TIME WITHOUT TIME ZONE NOT NULL, 
\thora_fin TIME WITHOUT TIME ZONE NOT NULL, 
\tmotivo TEXT NOT NULL, 
\testado VARCHAR(20) DEFAULT 'Pendiente', 
\tnotas TEXT, 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tfecha_resolucion TIMESTAMP WITHOUT TIME ZONE, 
\tPRIMARY KEY (id), 
\tCONSTRAINT profesor_suplencias_generales_estado_check CHECK (estado IN ('Pendiente', 'Asignado', 'Confirmado', 'Cancelado')), 
\tFOREIGN KEY(horario_profesor_id) REFERENCES horarios_profesores (id) ON DELETE SET NULL, 
\tFOREIGN KEY(profesor_original_id) REFERENCES profesores (id) ON DELETE CASCADE, 
\tFOREIGN KEY(profesor_suplente_id) REFERENCES profesores (id) ON DELETE SET NULL
);\n    """)

    op.execute("""\nCREATE TABLE IF NOT EXISTS profesor_suplencias (
\tid SERIAL NOT NULL, 
\tasignacion_id INTEGER NOT NULL, 
\tprofesor_suplente_id INTEGER, 
\tfecha_clase DATE NOT NULL, 
\tmotivo TEXT NOT NULL, 
\testado VARCHAR(20) DEFAULT 'Pendiente', 
\tnotas TEXT, 
\tfecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
\tfecha_resolucion TIMESTAMP WITHOUT TIME ZONE, 
\tPRIMARY KEY (id), 
\tCONSTRAINT profesor_suplencias_estado_check CHECK (estado IN ('Pendiente', 'Asignado', 'Confirmado', 'Cancelado')), 
\tFOREIGN KEY(asignacion_id) REFERENCES profesor_clase_asignaciones (id) ON DELETE CASCADE, 
\tFOREIGN KEY(profesor_suplente_id) REFERENCES profesores (id) ON DELETE SET NULL
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

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_acciones_masivas_estado ON acciones_masivas_pendientes (estado);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_acciones_masivas_fecha_programada ON acciones_masivas_pendientes (fecha_programada);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_acciones_masivas_usuario_ids ON acciones_masivas_pendientes USING gin (usuario_ids);\n    """)

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

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_custom_themes_activo ON custom_themes (activo);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_maintenance_tasks_next_execution ON maintenance_tasks (next_execution);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_maintenance_tasks_scheduled ON maintenance_tasks (scheduled_at);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_maintenance_tasks_status ON maintenance_tasks (status);\n    """)

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

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_system_diagnostics_status ON system_diagnostics (status);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_system_diagnostics_timestamp ON system_diagnostics (timestamp);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_system_diagnostics_type ON system_diagnostics (diagnostic_type);\n    """)

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

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_theme_schedules_activo ON theme_schedules (activo);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_theme_schedules_fechas ON theme_schedules (fecha_inicio, fecha_fin);\n    """)

    op.execute("""\nCREATE INDEX IF NOT EXISTS idx_theme_schedules_theme_id ON theme_schedules (theme_id);\n    """)

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
