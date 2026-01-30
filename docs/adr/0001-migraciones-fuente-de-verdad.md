# ADR 0001: Migraciones como fuente de verdad

## Estado

Aceptado.

## Contexto

El sistema necesita garantizar que al crear un gimnasio se inicialice la DB tenant de forma completa y que los cambios futuros se apliquen a todas las DBs tenant, evitando drift y cambios implícitos.

## Decisión

- El esquema tenant se gestiona exclusivamente con Alembic.
- El alta de gimnasio corre `upgrade head` automáticamente.
- El deploy corre migraciones de tenants como paso obligatorio.
- Se proveen herramientas de auditoría e idempotencia.

## Consecuencias

- No se usa `create_all` en runtime para schema.
- Las migraciones deben ser revisadas y versionadas.
- Se incorpora tooling de verificación para evitar divergencias.
