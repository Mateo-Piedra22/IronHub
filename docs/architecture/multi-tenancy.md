# Multi-tenant

## Modelo

- Un gimnasio = un tenant.
- Cada tenant tiene su propia base de datos (aislamiento fuerte).
- La Admin DB contiene el catálogo de tenants y su estado.

## Resolución de tenant

- Entrada: `Host`/subdominio.
- Validación: status del tenant (active/suspended/maintenance) en Admin DB.
- Conexión: engine/session a la Tenant DB correspondiente.

## Estado del tenant

- El estado gobierna admisión de requests en webapp-api.
- El superadmin puede forzar mantenimiento/suspensión.

## Operaciones globales

- Migraciones tenant se aplican a todas las DBs de gimnasios.
- Las operaciones globales se registran como auditoría en Admin DB.
