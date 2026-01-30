# Migraciones (Alembic)

## Principio

- El esquema de base de datos se modifica únicamente mediante migraciones.
- Las migraciones de tenant se aplican a todas las DBs de gimnasios.
- La creación de DB (CREATE DATABASE) sigue siendo una operación de infraestructura.

## Ubicación

- Tenant migrations: [apps/webapp-api/alembic](file:///c:/Users/mateo/OneDrive/Escritorio/Work/Programas/IronHub/apps/webapp-api/alembic)
- Tenant baseline: [0001_tenant_schema_baseline.py](file:///c:/Users/mateo/OneDrive/Escritorio/Work/Programas/IronHub/apps/webapp-api/alembic/versions/0001_tenant_schema_baseline.py)

## Alta de gimnasio (automático)

Al crear un gimnasio, **admin-api** crea la base de datos tenant y ejecuta `upgrade head` contra esa DB.

- Runner: [tenant_migrations.py](file:///c:/Users/mateo/OneDrive/Escritorio/Work/Programas/IronHub/apps/admin-api/src/tenant_migrations.py)
- Bootstrap: [admin_service.py](file:///c:/Users/mateo/OneDrive/Escritorio/Work/Programas/IronHub/apps/admin-api/src/services/admin_service.py)

Requisito de deploy:

- El runtime de `admin-api` debe tener disponible el directorio `apps/webapp-api` (para cargar `alembic.ini`, `alembic/` y `src/`).
- Si no es posible, setear `TENANT_MIGRATIONS_ROOT` apuntando al path absoluto del directorio `webapp-api` dentro del artefacto de deploy.

## Migración masiva (deploy)

Ejecutar en cada deploy (obligatorio):

```bash
cd apps/webapp-api
python -m src.cli.migrate
```

Alternativa (admin + tenants en un solo comando):

```bash
cd apps/webapp-api
python -m src.cli.migrate_all
```

Opciones:

```bash
python -m src.cli.migrate --include-inactive
python -m src.cli.migrate --fail-fast
python -m src.cli.migrate --tenant <subdominio>
python -m src.cli.migrate --verify-idempotent
python -m src.cli.migrate --lock-timeout-seconds 300
```

## Reglas para nuevas migraciones

- Agregar una nueva revisión en `apps/webapp-api/alembic/versions/`.
- Nunca editar migraciones ya publicadas.
- Evitar data migrations destructivas sin runbook y rollback.
