# Checklist Tech Provider (Meta WhatsApp) — IronHub

Fecha: 2026-01-17

## Objetivo (en términos de producto)
Que cada dueño de gimnasio conecte su WhatsApp (BYOC) dentro de IronHub con Embedded Signup, sin copiar tokens ni tocar Business Manager manualmente.

## URLs que Meta suele pedir (IronHub)
- Privacy Policy: `https://ironhub.motiona.xyz/privacy`
- Terms: `https://ironhub.motiona.xyz/terms`
- Data deletion instructions: `https://ironhub.motiona.xyz/data-deletion`
- Data deletion callback: `https://ironhub.motiona.xyz/api/meta/data-deletion`

## Prerrequisitos (Meta)
- Cuenta en Meta for Developers.
- Un Business Portfolio (Meta Business) con verificación (recomendado para producción).
- Dominio estable para el wizard: `connect.ironhub.motiona.xyz` (recomendado).

## 1) Meta App (Settings → Basic)
- Completar:
  - App Domains: `ironhub.motiona.xyz` y `connect.ironhub.motiona.xyz`
  - Privacy Policy URL
  - Terms of Service URL
  - Data Deletion: configurar callback y URL de instrucciones
- Poner la app en modo Live cuando corresponda.

## 2) Agregar productos
- WhatsApp
- Facebook Login for Business

## 3) Facebook Login for Business → Settings
- Habilitar OAuth web + SDK JS.
- Allowed Domains (SDK): `connect.ironhub.motiona.xyz`
- Valid OAuth Redirect URIs:
  - `https://connect.ironhub.motiona.xyz/`
  - (opcional) `https://ironhub.motiona.xyz/`

## 4) Facebook Login for Business → Configurations (obtener config_id)
- Create configuration
- Login variation: WhatsApp Embedded Signup
- Assets: WhatsApp accounts
- Permissions:
  - `whatsapp_business_management`
  - `whatsapp_business_messaging`
  - `business_management` (solo si tu caso lo requiere)
- Copiar el Configuration ID y guardarlo como `META_WA_EMBEDDED_SIGNUP_CONFIG_ID`.

## 5) Variables de entorno (IronHub)
**webapp-api**
- `META_APP_ID`
- `META_APP_SECRET`
- `META_WA_EMBEDDED_SIGNUP_CONFIG_ID`
- `META_GRAPH_API_VERSION`
- `WABA_ENCRYPTION_KEY` (compartida con admin-api si admin necesita leer tokens)

**webapp-web**
- `NEXT_PUBLIC_META_APP_ID`
- `NEXT_PUBLIC_META_WA_EMBEDDED_SIGNUP_CONFIG_ID`
- `NEXT_PUBLIC_META_GRAPH_API_VERSION`
- `NEXT_PUBLIC_WHATSAPP_CONNECT_BASE_URL=https://connect.ironhub.motiona.xyz` (recomendado)

## 6) App Review / permisos (si Meta lo exige)
- Preparar evidencia para:
  - Envío real con `whatsapp_business_messaging`
  - Creación/listado de templates con `whatsapp_business_management`
- Grabar videos como en [meta-embedded-signup-setup.md](file:///c:/Users/mateo/OneDrive/Escritorio/Work/Programas/IronHub/docs/meta-embedded-signup-setup.md).

## 7) Webhooks (recomendado para operación “pro”)
- Callback URL (multi-tenant):
  - `https://api.ironhub.motiona.xyz/webhooks/whatsapp/{tenant}`
- Verify token y validación de firma (App Secret) en producción.

## 8) Validación end-to-end (prueba real)
1. En el tenant (dueño): Gestión → WhatsApp → Conectar con Meta.
2. Verificar que se guardaron:
   - `phone_number_id`
   - `whatsapp_business_account_id (waba_id)`
   - `access_token_present=true`
3. Ejecutar Health check.
4. Provisionar plantillas (admin o auto).
5. Enviar un mensaje de prueba y verificar delivery status.

## Recomendación operativa
- Mantener Meta Review como herramienta owner-only para diagnóstico y para App Review.
- Automatizar “provision + sync + health” por gimnasio en un job programado (diario/semanal).

