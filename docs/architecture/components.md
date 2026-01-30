# Servicios y apps

## apps/admin-api

- Responsabilidad: alta y administración global.
- Datos: Admin DB.
- Puntos clave:
  - Crea bases tenant.
  - Corre migraciones tenant al bootstrap.

## apps/admin-web

- Responsabilidad: UI superadmin (Next.js).
- Consume: admin-api.

## apps/webapp-api

- Responsabilidad: API del gimnasio.
- Datos: Tenant DB.
- Infra:
  - Resolución del tenant y pooling de engines.

## apps/webapp-web

- Responsabilidad: UI del gimnasio.
- Consume: webapp-api.

## Contratos y separación

- Admin DB y tenant DB usan schemas/migraciones separadas.
- Nunca se ejecutan migraciones de tenant sobre admin DB ni viceversa.
