# Arquitectura

## Contexto

IronHub es un sistema multi-tenant para gimnasios. El tenant se resuelve por subdominio y se valida contra una base de datos de administración.

## Componentes principales

- **admin-api**: API superadmin para alta/gestión de gimnasios y operaciones globales.
- **admin-web**: panel superadmin.
- **webapp-api**: API de negocio del gimnasio (tenant).
- **webapp-web**: app del gimnasio.
- **landing**: sitio público.

## Datos

- **Admin DB**: catálogo de gimnasios (`gyms`), sucursales sincronizadas (`branches`), planes/pagos, auditoría.
- **Tenant DB**: datos del gimnasio (usuarios, pagos, clases, rutinas, asistencia, WhatsApp, entitlements, staff, sucursales).

## Flujos críticos

- **Alta de gimnasio**: admin-api crea DB tenant y corre migraciones tenant.
- **Request tenant**: webapp-api resuelve tenant → abre engine/session de la DB tenant.
- **Migraciones**: se ejecutan como paso obligatorio de deploy y/o por mantenimiento.
