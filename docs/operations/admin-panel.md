# Admin Panel (admin-web + admin-api) — Operación en producción

Este documento explica el flujo recomendado para **crear** y **mantener** gimnasios y sucursales desde el panel superadmin.

## Componentes

- **admin-web**: panel superadmin (Next.js). Es el UI que usás.
- **admin-api**: backend superadmin (FastAPI). Admin-web consume esta API.
- **webapp-api / webapp-web**: aplicaciones del gimnasio (tenant) que operan en el subdominio del gym.

## Variables de entorno mínimas

### admin-web

- `NEXT_PUBLIC_API_URL` = URL pública de `admin-api` (ej: `https://admin-api.ironhub.motiona.xyz`)
- `NEXT_PUBLIC_TENANT_DOMAIN` = dominio base de tenants (ej: `ironhub.motiona.xyz`)

### admin-api

- `ADMIN_SESSION_SECRET` (obligatorio en producción)
- Conexión Admin DB (usar URL completa o por partes). Ver [auto-migrations.md](auto-migrations.md).
- `TENANT_BASE_DOMAIN` (para CORS regex y links coherentes)

## Flujo recomendado: crear gimnasio (wizard)

En **admin-web → Dashboard → Gyms → Nuevo Gimnasio** el wizard guía el alta completa:

1. **Datos del gimnasio**
   - Nombre: visible en admin.
   - Subdominio: define la URL final del tenant: `https://{subdominio}.{TENANT_DOMAIN}`
   - Si no definís subdominio, se sugiere uno único.
2. **Sucursales iniciales**
   - Cargá al menos una sucursal.
   - Recomendado: crear una “Principal” con código `principal`.
3. **Credenciales del Owner**
   - Por defecto se **genera una contraseña segura**.
   - El panel la muestra para copiar (es lo que se usa para el primer login).
4. (Opcional) **WhatsApp**
   - Podés cargar credenciales de Meta en el alta o hacerlo luego desde el detalle.

Resultado:
- Se crea el gym y su tenant DB.
- Se crea al menos una sucursal inicial (si cargaste varias, se importan todas).
- Se setea un hash bcrypt del owner password en Admin DB y se replica en el tenant (hash).

## Primer login del Owner (tenant)

1. Abrí el link del tenant desde la lista de gyms o desde el wizard.
2. Ingresá con el password del owner.
3. Recomendación: cambiar el password del owner desde el panel del gym (en el tenant) o desde admin-web según la política que uses.

## Gestión de sucursales (detalle del gym)

En **admin-web → Gyms → (abrir gym) → Sucursales**:

- **Nueva**: alta guiada por modal (nombre, código, timezone, dirección).
- **Editar**: modal por fila con cambios rápidos (incluye activar/desactivar).
- **Desactivar**: confirma por modal. No elimina físicamente.
- **Carga masiva**:
  - Pegá líneas con formato: `nombre;codigo;timezone;direccion`
  - Separador recomendado: `;` o tab. Ej:
    - `Principal;principal;America/Argentina/Buenos_Aires;Calle 123`
    - `Centro;centro;America/Argentina/Buenos_Aires;Av. Siempre Viva 742`
- **Sincronizar**:
  - Fuerza una sincronización desde la Tenant DB a la Admin DB si hubo divergencias.

Reglas importantes:
- El código debe ser único por gym y en minúsculas (`a-z0-9_-`).
- No se puede dejar al gym sin sucursales activas.

## Mantenimiento del gimnasio (qué tocar y cuándo)

En el detalle del gym hay secciones. Esta es la guía práctica:

- **Suscripción / Pagos**: controlar vencimientos, asignar plan manual, registrar pagos.
- **WhatsApp**: configurar credenciales, probar envío, provisionar templates y validar health.
- **Módulos / Feature Flags**: habilitar/deshabilitar funcionalidades por gym o por sucursal.
- **Entitlements**: limitar tipos de cuotas/clases por sucursal (útil para planes).
- **Branding**: logo/colores/datos públicos (impacta en tenant).
- **Health**: revisar eventos/estado general.
- **Password**: rotación de credenciales del owner cuando sea necesario.

## Checklist “listo para producción” por gym

- Tiene al menos 1 sucursal activa.
- Owner password set y entregado al cliente.
- Status del gym = `active`.
- Plan/suscripción configurada (si aplican restricciones de acceso).
- WhatsApp configurado (si se usa):
  - Access token + Phone ID + WABA ID
  - Templates provisionados
  - Test de envío OK
- Feature flags revisadas (configuración no bloqueada).
- Marcar el gym como “Listo para producción” en el panel (Primeros pasos) para tracking interno.

## API útil (para automatizaciones internas)

admin-api expone endpoints listos para integrar tooling interno:

- `POST /gyms/v2` (alta de gym con branches iniciales y password owner seguro)
- `POST /gyms/{id}/branches/bulk` (carga masiva)
- `POST /gyms/{id}/branches/sync` (reconciliación Admin DB ↔ Tenant DB)
- `POST /gyms/{id}/production-ready` (marcar/desmarcar “listo para producción”)
