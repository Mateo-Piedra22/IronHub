# Admin: Bindings y Versionado de Plantillas

## Conceptos
- Catálogo estándar: base de plantillas `ih_*_vN` centralizadas (admin).
- Bindings: asigna qué plantilla usa cada acción (`welcome`, `payment`, etc.).
- Provisionar: crea plantillas faltantes en la WABA del gym y sincroniza bindings al tenant (`wa_meta_template_*`).
- Versionado: no se actualizan plantillas aprobadas; se crea `*_vN+1` y luego se cambia el binding.

## Endpoints clave
- Listar/editar catálogo: [admin-api main.py](file:///c:/Users/mateo/OneDrive/Escritorio/Work/Programas/IronHub/apps/admin-api/src/main.py)
- Sincronizar defaults: `/whatsapp/templates/sync-defaults`
- Bump versión: `/whatsapp/templates/bump-version`
- Bindings:
  - Listar: `/whatsapp/bindings`
  - Upsert: `/whatsapp/bindings/{binding_key}`
  - Sincronizar defaults: `/whatsapp/bindings/sync-defaults`
- Provisionar al gym: `/gyms/{id}/whatsapp/provision-templates`

## Flujo recomendado
1. Crear/editar `ih_*_vN` en catálogo.
2. Bump si querés nueva versión.
3. Provisionar al gym (crea en Meta y sincroniza `wa_meta_template_*`).
4. Cambiar binding a la nueva versión cuando esté APPROVED.

## Acciones soportadas
- welcome, payment, overdue, deactivation, class_reminder, waitlist
- adicionales: membership_due_today, membership_due_soon, membership_reactivated, class_booking_confirmed, class_booking_cancelled, schedule_change, marketing_promo, marketing_new_class

## Robustez
- Tokens cifrados con `WABA_ENCRYPTION_KEY`.
- `cryptography` en admin-api para desencriptar.
- Health con errores legibles (200 + `ok:false`).
