# Bootstrap producción (desde cero)

Este documento define el flujo **definitivo** para levantar IronHub en producción cuando se parte desde 0:
- DB admin vacía (o no existente)
- 0 gimnasios registrados
- 0 DBs tenant existentes

## 1) Requisitos

- Variables de entorno correctas en:
  - `apps/admin-api/.env`
  - `apps/webapp-api/.env`
  - `apps/admin-web/.env`
  - `apps/webapp-web/.env`
- Conectividad a Postgres (o Neon) desde el host donde corren los servicios.

## 2) Orden de arranque (recomendado)

1) **admin-api**
   - Objetivo: crear/asegurar la **admin DB** y su schema (incluye `gyms`, `gym_branding`, rate limit, onboarding, bindings, etc.).
2) **admin-web**
   - Objetivo: operar el alta de gimnasios y el branding (tema estático por gym).
3) **webapp-api**
   - Objetivo: servir API tenant + bootstrap público (`/api/bootstrap`) con tema/logo desde admin DB.
4) **webapp-web**
   - Objetivo: UI tenant, aplica tema en runtime desde el bootstrap.

## 3) Alta de gimnasio (creación tenant desde 0)

La creación del gimnasio se hace desde **admin-web** (o el endpoint equivalente en admin-api). El flujo esperado es:

- Se inserta `gyms` en admin DB con `subdominio` y `db_name`.
- Se crea la DB tenant (si no existe).
- Se corren migraciones Alembic tenant hasta `head`.
- Se ejecuta bootstrap mínimo de tenant (config base, owner, etc.).
- Se guarda branding en admin DB (`gym_branding`) desde la sección Branding.

Resultado esperado:
- La URL del tenant responde `GET /api/bootstrap` con:
  - `gym_name`
  - `logo_url`
  - `theme` (colores)
- El frontend `webapp-web` aplica el tema al cargar.

## 4) Migraciones (política)

### Tenant DB (por gimnasio)

- La fuente de verdad es Alembic en `apps/webapp-api/alembic/`.
- En instalaciones desde cero, el baseline tenant ya refleja el schema final: no se crean tablas legacy eliminadas.

### Admin DB

- La fuente de verdad es el bootstrap idempotente de `admin-api` (crea tablas si no existen).
- Esto evita depender de ejecutar migraciones separadas para admin DB.

## 5) Chequeos finales de producción

- admin-web:
  - Listar gimnasios
  - Editar Branding de un gimnasio (logo + colores) y recargar `webapp-web`
- webapp-web:
  - Verificar que los componentes con `text-primary-*` / `bg-primary-*` cambian según el gym
- webapp-api:
  - `GET /api/bootstrap` devuelve `gym.theme`
  - Login y endpoints principales operativos

