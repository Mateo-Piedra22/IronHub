# Seguridad

## Principios

- No loguear secretos.
- Variables de entorno para credenciales.
- Conexiones TLS/SSL a Postgres (cuando corresponda).
- Separación admin/tenant (credenciales y permisos).

## Autenticación

- `webapp-api`: autenticación por sesión/rol y dependencias.
- `admin-api`: autenticación superadmin.

## Gestión de secretos

- Tokens (WhatsApp, B2, etc.) deben guardarse cifrados donde aplique.
- Rotación documentada y runbook.
