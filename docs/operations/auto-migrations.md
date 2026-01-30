# Migraciones automáticas (cero pasos manuales)

Este proyecto está configurado para que las migraciones de base de datos se ejecuten solas. No tenés que correr comandos manuales en el deploy.

## Conceptos (simple)

- **Admin DB**: la base “central” que tiene el catálogo de gimnasios (`gyms`, `branches`, etc.).
- **Tenant DB**: una base por gimnasio (los datos del gym: usuarios, pagos, asistencias, clases, WhatsApp, etc.).
- **webapp-api**: la API del gimnasio.
- **admin-api**: la API superadmin (alta de gimnasios, control global).

## Qué se migra y cuándo

### Admin DB

- **Quién la migra**: `webapp-api`.
- **Cuándo**: en el **startup** (cuando arranca el proceso/instancia).
- **Cómo**: Alembic `apps/webapp-api/alembic_admin`.

### Tenant DB (cada gimnasio)

- **Quién la migra**: `webapp-api`.
- **Cuándo**: automáticamente cuando se crea/usa la conexión del tenant (modo “lazy”).
- **Cómo**: Alembic `apps/webapp-api/alembic` con lock por tenant.

Esto significa que cuando deployás una versión nueva, el primer request de cada gimnasio hace que su DB se ponga al día sola.

## Variables de entorno (lo único que tenés que setear)

### webapp-api (obligatorio en producción)

#### Conexión a Admin DB (recomendado)

- `ADMIN_DATABASE_URL` = URL completa a la Admin DB.

Ejemplo:

```
ADMIN_DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:5432/ironhub_admin?sslmode=require
```

#### Alternativa (por partes)

Si no querés usar `ADMIN_DATABASE_URL`, podés setear:

- `ADMIN_DB_HOST`
- `ADMIN_DB_PORT` (default: 5432)
- `ADMIN_DB_NAME` (ej: `ironhub_admin`)
- `ADMIN_DB_USER`
- `ADMIN_DB_PASSWORD`
- `ADMIN_DB_SSLMODE` (ej: `require`)

#### Sesión (obligatorio)

- `TENANT_BASE_DOMAIN` (ej: `ironhub.motiona.xyz`)
- `SESSION_SECRET` (en producción tiene que ser fuerte; no uses `changeme`)

### admin-api (para alta de gimnasios sin problemas)

`admin-api` corre migraciones tenant al crear un gimnasio. Para eso necesita poder leer el proyecto `webapp-api` dentro del artefacto deploy.

Tenés dos opciones (elegí una):

#### Opción A (recomendada)

Asegurate de que el deploy de `admin-api` incluya también el directorio:

- `apps/webapp-api/` (incluye `alembic.ini`, `alembic/` y `src/`)

#### Opción B (si no podés incluir todo el repo)

Seteá:

- `TENANT_MIGRATIONS_ROOT=/path/absoluto/al/directorio/webapp-api`

Dentro de ese path tiene que existir:

- `alembic.ini`
- `alembic/`
- `src/`

## Flags de “modo estricto” (recomendado)

Estas variables ya tienen defaults seguros. Las listo para que sepas que existen.

### webapp-api

- `AUTO_MIGRATE_ADMIN_DB=true`
- `AUTO_MIGRATE_ADMIN_DB_REQUIRED=true`
- `AUTO_MIGRATE_TENANT=true`
- `AUTO_MIGRATE_TENANT_REQUIRED=true`
- `AUTO_MIGRATE_TENANT_CHECK_TTL_SECONDS=300`

Qué significan:

- `*_REQUIRED=true` => si migrar falla, la app **no sigue** (evita correr con schema roto).

## Pagos: recomendación de idempotencia (anti “doble cobro”)

Si el frontend reintenta una llamada por mala conexión, puede repetir el pago. Para evitarlo, el backend soporta un identificador idempotente:

- Header recomendado: `Idempotency-Key: <un string único por intento>`
- Alternativa: `{"idempotency_key": "..."}` en el JSON.

Si repetís el mismo `Idempotency-Key`, el backend devuelve el mismo `pago_id` sin duplicar.

## Si algo falla (troubleshooting rápido)

1. Mirá logs del deploy: el error suele decir qué DB falló (admin o tenant).
2. Si el error es de conexión, revisá `ADMIN_DATABASE_URL` (o los `ADMIN_DB_*`) y credenciales.
3. Si `admin-api` falla al crear un gimnasio, revisá `TENANT_MIGRATIONS_ROOT` o que el deploy incluya `apps/webapp-api/`.

