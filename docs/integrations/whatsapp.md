# Integración WhatsApp

## Alcance

- Onboarding y configuración (Meta WABA/Phone ID/Token).
- Catálogo de templates y envío de mensajes.
- Webhooks y eventos de diagnóstico.
- Multi-sucursal: configuración por sucursal cuando aplica.

## Superadmin

- El panel superadmin gestiona credenciales y diagnóstico.
- Operaciones se auditan.

## Tenant

- `webapp-api` decide qué template/acción se ejecuta.
- Los mensajes se registran en tablas de WhatsApp en la Tenant DB.

## Seguridad

- Tokens deben almacenarse cifrados.
- No loguear tokens.
- Rotación planificada y runbook.
