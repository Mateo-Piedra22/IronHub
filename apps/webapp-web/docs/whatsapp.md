# WhatsApp (WebApp) — Envío por acciones, switches y reintentos

## Fuente de verdad por gimnasio
La configuración efectiva del gimnasio vive en su tenant DB:
- `wa_action_enabled_<accion>`: habilita/deshabilita envío por acción
- `wa_meta_template_<accion>`: template Meta aprobado usado por acción

Estas claves se setean desde Admin (Gym → WhatsApp) y/o durante provisionamiento.

## Acciones soportadas (y parámetros)
- welcome: 1 (nombre)
- payment: 3 (nombre, monto, periodo)
- membership_due_today: 2 (nombre, fecha)
- membership_due_soon: 2 (nombre, fecha)
- overdue: 1 (nombre)
- deactivation: 2 (nombre, motivo)
- membership_reactivated: 1 (nombre)
- class_booking_confirmed: 3 (clase, fecha, hora)
- class_booking_cancelled: 1 (clase)
- class_reminder: 4 (nombre, clase, día/fecha, hora)
- waitlist: 4 (nombre, clase, día, hora)
- waitlist_confirmed: 4 (nombre, clase, día, hora)
- schedule_change: 3 (clase, día, hora)
- marketing_promo: 2 (nombre, promo) — default desactivado
- marketing_new_class: 3 (clase, día, hora) — default desactivado

## Implementación de envío
Ruta recomendada: `WhatsAppDispatchService`
- Lee configuración (tenant DB)
- Aplica allowlist si está habilitado
- Envía a Meta por `/messages` con `type=template`

Archivos:
- Servicio: [whatsapp_dispatch_service.py](file:///c:/Users/mateo/OneDrive/Escritorio/Work/Programas/IronHub/apps/webapp-api/src/services/whatsapp_dispatch_service.py)
- Reintentos: [whatsapp.py](file:///c:/Users/mateo/OneDrive/Escritorio/Work/Programas/IronHub/apps/webapp-api/src/routers/whatsapp.py)

## Meta Review (Gestión → Meta Review)
Herramienta owner-only para:
- enviar texto real
- enviar plantilla real
- crear plantilla real
- health real

Sigue siendo útil aun con Embedded Signup (config_id) como:
- debug de tokens/phone_id/waba_id
- validación para App Review
- soporte y QA

Si se quiere ocultar en producción, se recomienda un feature flag.
