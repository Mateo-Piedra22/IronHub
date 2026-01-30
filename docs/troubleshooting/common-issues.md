# Troubleshooting

## Migración falla en un tenant

Pasos:

1. Correr migración individual:

```bash
cd apps/webapp-api
python -m src.cli.migrate --tenant <subdominio>
```

2. Correr auditor:

```bash
python -m src.cli.schema_audit --tenant <subdominio> --strict
```

3. Si hay divergencias, corregir con una migración nueva o reparar manualmente con runbook.

## Alta de gym falla (admin-api)

- Verificar conectividad Postgres.
- Verificar que `alembic` esté instalado en el runtime de admin-api.
- Verificar que el repo incluya `apps/webapp-api/alembic` en el artefacto deploy.
