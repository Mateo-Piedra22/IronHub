from alembic import op

revision = "0006_fix_fk_integer_types"
down_revision = "0005_rutinas_creada_por_usuario"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'usuarios' AND column_name = 'sucursal_registro_id'
            ) THEN
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_usuarios_sucursal_registro_id') THEN
                        EXECUTE 'ALTER TABLE usuarios DROP CONSTRAINT fk_usuarios_sucursal_registro_id';
                    END IF;
                EXCEPTION WHEN others THEN
                    NULL;
                END;
                BEGIN
                    EXECUTE 'ALTER TABLE usuarios ALTER COLUMN sucursal_registro_id TYPE INTEGER USING sucursal_registro_id::integer';
                EXCEPTION WHEN others THEN
                    NULL;
                END;
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_usuarios_sucursal_registro_id') THEN
                        EXECUTE 'ALTER TABLE usuarios ADD CONSTRAINT fk_usuarios_sucursal_registro_id FOREIGN KEY (sucursal_registro_id) REFERENCES sucursales(id) ON DELETE SET NULL';
                    END IF;
                EXCEPTION WHEN others THEN
                    NULL;
                END;
                BEGIN
                    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_usuarios_sucursal_registro_id ON usuarios(sucursal_registro_id)';
                EXCEPTION WHEN others THEN
                    NULL;
                END;
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'rutinas' AND column_name = 'creada_por_usuario_id'
            ) THEN
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_rutinas_creada_por_usuario_id') THEN
                        EXECUTE 'ALTER TABLE rutinas DROP CONSTRAINT fk_rutinas_creada_por_usuario_id';
                    END IF;
                EXCEPTION WHEN others THEN
                    NULL;
                END;
                BEGIN
                    EXECUTE 'ALTER TABLE rutinas ALTER COLUMN creada_por_usuario_id TYPE INTEGER USING creada_por_usuario_id::integer';
                EXCEPTION WHEN others THEN
                    NULL;
                END;
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_rutinas_creada_por_usuario_id') THEN
                        EXECUTE 'ALTER TABLE rutinas ADD CONSTRAINT fk_rutinas_creada_por_usuario_id FOREIGN KEY (creada_por_usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL';
                    END IF;
                EXCEPTION WHEN others THEN
                    NULL;
                END;
                BEGIN
                    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_rutinas_creada_por_usuario_id ON rutinas(creada_por_usuario_id)';
                EXCEPTION WHEN others THEN
                    NULL;
                END;
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'pagos_idempotency'
            ) THEN
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'pagos_idempotency_pago_id_fkey') THEN
                        EXECUTE 'ALTER TABLE pagos_idempotency DROP CONSTRAINT pagos_idempotency_pago_id_fkey';
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'pagos_idempotency_usuario_id_fkey') THEN
                        EXECUTE 'ALTER TABLE pagos_idempotency DROP CONSTRAINT pagos_idempotency_usuario_id_fkey';
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_pagos_idempotency_pago_id') THEN
                        EXECUTE 'ALTER TABLE pagos_idempotency DROP CONSTRAINT fk_pagos_idempotency_pago_id';
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_pagos_idempotency_usuario_id') THEN
                        EXECUTE 'ALTER TABLE pagos_idempotency DROP CONSTRAINT fk_pagos_idempotency_usuario_id';
                    END IF;
                EXCEPTION WHEN others THEN
                    NULL;
                END;
                BEGIN
                    EXECUTE 'ALTER TABLE pagos_idempotency ALTER COLUMN pago_id TYPE INTEGER USING pago_id::integer';
                    EXECUTE 'ALTER TABLE pagos_idempotency ALTER COLUMN usuario_id TYPE INTEGER USING usuario_id::integer';
                EXCEPTION WHEN others THEN
                    NULL;
                END;
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_pagos_idempotency_pago_id') THEN
                        EXECUTE 'ALTER TABLE pagos_idempotency ADD CONSTRAINT fk_pagos_idempotency_pago_id FOREIGN KEY (pago_id) REFERENCES pagos(id) ON DELETE CASCADE';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_pagos_idempotency_usuario_id') THEN
                        EXECUTE 'ALTER TABLE pagos_idempotency ADD CONSTRAINT fk_pagos_idempotency_usuario_id FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE';
                    END IF;
                EXCEPTION WHEN others THEN
                    NULL;
                END;
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'checkin_station_tokens'
            ) THEN
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_checkin_station_tokens_sucursal_id') THEN
                        EXECUTE 'ALTER TABLE checkin_station_tokens DROP CONSTRAINT fk_checkin_station_tokens_sucursal_id';
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'checkin_station_tokens_sucursal_id_fkey') THEN
                        EXECUTE 'ALTER TABLE checkin_station_tokens DROP CONSTRAINT checkin_station_tokens_sucursal_id_fkey';
                    END IF;
                EXCEPTION WHEN others THEN
                    NULL;
                END;
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'checkin_station_tokens' AND column_name = 'gym_id'
                    ) THEN
                        EXECUTE 'ALTER TABLE checkin_station_tokens ALTER COLUMN gym_id TYPE INTEGER USING gym_id::integer';
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'checkin_station_tokens' AND column_name = 'sucursal_id'
                    ) THEN
                        EXECUTE 'ALTER TABLE checkin_station_tokens ALTER COLUMN sucursal_id TYPE INTEGER USING sucursal_id::integer';
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'checkin_station_tokens' AND column_name = 'used_by'
                    ) THEN
                        EXECUTE 'ALTER TABLE checkin_station_tokens ALTER COLUMN used_by TYPE INTEGER USING used_by::integer';
                    END IF;
                EXCEPTION WHEN others THEN
                    NULL;
                END;
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_checkin_station_tokens_sucursal_id') THEN
                        EXECUTE 'ALTER TABLE checkin_station_tokens ADD CONSTRAINT fk_checkin_station_tokens_sucursal_id FOREIGN KEY (sucursal_id) REFERENCES sucursales(id) ON DELETE SET NULL';
                    END IF;
                EXCEPTION WHEN others THEN
                    NULL;
                END;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    return
