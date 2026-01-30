# Documentación IronHub

## Índice

- [Arquitectura](architecture/overview.md)
- [Servicios y apps](architecture/components.md)
- [Multi-tenant](architecture/multi-tenancy.md)
- [Migraciones](database/migrations.md)
- [Schema audit](database/schema-audit.md)
- [Deploy y operaciones](operations/deployment.md)
- [Migraciones automáticas (cero manual)](operations/auto-migrations.md)
- [Operación del panel admin (producción)](operations/admin-panel.md)
- [Runbooks](operations/runbooks.md)
- [Seguridad](security/overview.md)
- [Integración WhatsApp](integrations/whatsapp.md)
- [Storage/CDN](integrations/storage-cdn.md)
- [Contribución](development/contributing.md)
- [Troubleshooting](troubleshooting/common-issues.md)
- [ADRs](adr/README.md)
- [Auditoría histórica](AUDIT_REPORT.md)

## Principios

- La base de datos tenant es la unidad de aislamiento: una DB por gimnasio.
- Los cambios de esquema se hacen exclusivamente con Alembic.
- Las migraciones tenant se ejecutan en todas las DBs de gimnasios.
- Admin DB y tenant DB no se cruzan (migraciones separadas, credenciales separadas).
