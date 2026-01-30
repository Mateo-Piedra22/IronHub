# Deploy y operaciones

## Requisitos

- Postgres accesible para Admin DB y para cada Tenant DB.
- Variables de entorno de conexión correctamente configuradas.
- Acceso a storage/CDN si aplica.

## Secuencia recomendada

1. Desplegar `admin-api`.
2. Ejecutar migraciones tenant para todas las DBs (si cambia `webapp-api`).
3. Desplegar `webapp-api`.
4. Desplegar frontends.

## Migraciones obligatorias (tenant)

```bash
cd apps/webapp-api
python -m src.cli.migrate
```

Alternativa (admin + tenants):

```bash
cd apps/webapp-api
python -m src.cli.migrate_all
```

Si hay fallas, el deploy debe considerarse fallido.

## Alta de tenant

El alta corre migraciones automáticamente en el flujo de `admin-api`.
Si falla, el tenant no debe quedar marcado como provisionado.
