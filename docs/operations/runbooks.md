# Runbooks

## Migración tenant masiva

```bash
cd apps/webapp-api
python -m src.cli.migrate --fail-fast
```

Acciones ante fallas:

- Identificar tenant/db_name en el output.
- Correr `schema_audit` para confirmar divergencias.
- Reintentar en forma individual con `--tenant`.

## Validación de schema (pre y post deploy)

```bash
cd apps/webapp-api
python -m src.cli.schema_audit --tenant <subdominio> --strict
```

## Idempotencia de migraciones

```bash
cd apps/webapp-api
python -m src.cli.migrate_verify --db-name <tenant_db_name>
```
