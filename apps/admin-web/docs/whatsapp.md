# WhatsApp (Admin) — Catálogo, Bindings y Provisionamiento

## Objetivo
Centralizar plantillas (Meta) y controlar por gimnasio:
- qué plantillas existen (catálogo estándar)
- qué versión usa cada acción (bindings)
- qué gimnasios las tienen creadas en su WABA (provisionamiento)
- qué acciones están habilitadas por gimnasio (switches)

## Componentes
- **admin-web**: UI para catálogo, bindings y configuración por gimnasio.
- **admin-api**: orquesta catálogo/bindings y provisiona hacia WABA del gimnasio.
- **tenant DB**: persiste configuración efectiva por gimnasio (claves `wa_*`).

## Catálogo estándar
- Tabla: `whatsapp_template_catalog` (admin DB)
- Convención: `ih_<evento>_vN`
- Propiedades:
  - `category`: `UTILITY | MARKETING | AUTHENTICATION`
  - `language`: ej. `es_AR`
  - `body_text`: texto con `{{1}}..{{N}}`
  - `active`: si aparece para provisionar/seleccionar

### Sincronizar defaults
Acción: “Sincronizar defaults”
- Hace upsert de los defaults del código al catálogo (no borra custom).
- Endpoint: `POST /whatsapp/templates/sync-defaults?overwrite=1`

## Bindings (acciones → plantilla)
- Tabla: `whatsapp_template_bindings` (admin DB)
- Define el “template recomendado” por acción.
- Endpoint:
  - `GET /whatsapp/bindings`
  - `PUT /whatsapp/bindings/{binding_key}`
  - `POST /whatsapp/bindings/sync-defaults?overwrite=1`

## Provisionar al gimnasio
Acción: “Provisionar plantillas estándar”
- Crea en Meta únicamente las plantillas que faltan (por `name`).
- Luego sincroniza al tenant, pero solo para plantillas en estado **APPROVED**:
  - `wa_meta_template_<accion>` = nombre de template Meta aprobado

Endpoint: `POST /gyms/{id}/whatsapp/provision-templates`

## Acciones por gimnasio (switch + versión)
En Gym → WhatsApp → “Acciones y versiones”:
- `enabled` por acción: `wa_action_enabled_<accion>`
- template por acción (aprobado): `wa_meta_template_<accion>`

Endpoints:
- `GET /gyms/{id}/whatsapp/actions`
- `PUT /gyms/{id}/whatsapp/actions/{accion}`

## Regla de actualización en Meta
Meta no “actualiza” una plantilla aprobada por nombre.
- Si cambia el contenido: crear `*_v2` (Bump) y cambiar el binding/acción a esa versión cuando esté APPROVED.
