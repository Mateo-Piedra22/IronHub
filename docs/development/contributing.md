# Contribución

## Flujo de cambios

- Cambios de schema: migración Alembic nueva.
- Cambios de servicios: agregar pruebas manuales/CLI cuando aplique.
- Cambios de UI: type-check + lint.

## Estándares mínimos

- No introducir SQL crudo si existe alternativa ORM clara.
- Si se usa SQL, debe ser parametrizado.
- Evitar acoplar admin y tenant.

## Checklist (PR)

- `apps/webapp-api`: `python -m py_compile` y comandos de migración/audit.
- `apps/admin-api`: `python -m py_compile`.
- `apps/admin-web`: `npm run type-check`.
- Documentación actualizada en `/docs`.
