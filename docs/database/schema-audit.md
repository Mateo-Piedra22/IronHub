# Schema audit e idempotencia

## Objetivo

- Detectar divergencias entre el esquema real de la DB y el esquema esperado por el código.
- Validar que `upgrade head` es idempotente (correr dos veces no cambia nada).

## Auditor de schema

CLI:

```bash
cd apps/webapp-api
python -m src.cli.schema_audit --tenant <subdominio> --strict
```

También se puede apuntar por URL:

```bash
python -m src.cli.schema_audit --db-url "<postgres-url>" --strict
```

## Verificador de idempotencia

```bash
cd apps/webapp-api
python -m src.cli.migrate_verify --db-name <tenant_db_name>
```

Comportamiento:

- Ejecuta `upgrade head` dos veces.
- Verifica que `alembic_version.version_num == head`.
