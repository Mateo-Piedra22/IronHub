# Meta Embedded Signup (WhatsApp BYOC) — Setup para IronHub

## Objetivo
- IronHub actúa como Tech Provider (ISV) y cada gimnasio conecta su propia WABA (BYOC).
- El dueño del gimnasio completa el wizard nativo de Meta (Embedded Signup) y IronHub guarda `waba_id`, `phone_number_id` y `access_token` en la DB del tenant.
- Luego se provisionan automáticamente las plantillas estándar en la WABA del cliente.

## 1) Meta App (Settings → Basic) LISTO
- App ID: ya lo tenés (es el que va en `META_APP_ID`).
- App Secret: guardalo solo como secreto del entorno (no lo subas al repo).
- Privacy Policy URL: obligatorio para pasar a Live.
- Terms of Service URL: recomendado.
- Data Deletion:
  - Instrucciones: `https://ironhub.motiona.xyz/data-deletion`
  - Callback: `https://ironhub.motiona.xyz/api/meta/data-deletion`
- App Domains:
  - `ironhub.motiona.xyz`
  - `connect.ironhub.motiona.xyz` (recomendado para evitar whitelists por tenant)
  - (y cualquier dominio custom adicional si lo usás).

## 2) Agregar productos LISTO
- Agregar producto **WhatsApp** y completar el setup (Quickstart).
- Agregar producto **Facebook Login for Business** (es el que genera el `config_id`).

## 3) Facebook Login for Business → Settings (pantalla del screenshot)
### Toggles recomendados LISTO
- Acceso del cliente de OAuth: **Sí**
- Acceso de OAuth web: **Sí**
- Aplicar HTTPS: **Sí**
- Usar modo estricto para URI de redireccionamiento: **Sí**
- Inicio de sesión con el SDK de JavaScript: **Sí**

### Dominios admitidos para el SDK de JavaScript
Recomendación IronHub (robusta multi-tenant): ejecutar el wizard de Meta en un dominio único (ej. `connect.ironhub.motiona.xyz`) y abrirlo como popup desde cualquier tenant.
- `connect.ironhub.motiona.xyz`
- (opcional) `ironhub.motiona.xyz` si también probás desde el dominio base
- En desarrollo local, agregá `localhost` si lo usás.

### URI de redireccionamiento de OAuth válidos
Meta exige al menos uno aunque uses SDK/popup. Recomendado:
- `https://connect.ironhub.motiona.xyz/`
- (opcional) `https://ironhub.motiona.xyz/`

Si tenés un dominio dedicado “conector” (por ej. `https://connect.ironhub.motiona.xyz/`), agregalo también.

## 4) Facebook Login for Business → Configurations (de acá sale el config_id) LISTO
Cómo obtener `META_WA_EMBEDDED_SIGNUP_CONFIG_ID`:
- Ir a **Facebook Login for Business → Configurations**
- Create configuration
- Login variation: **WhatsApp Embedded Signup**
- Assets: **WhatsApp accounts**
- Permissions:
  - `whatsapp_business_management`
  - `whatsapp_business_messaging`
  - `business_management` (si tu flujo lo requiere)
- Crear y copiar el **Configuration ID** generado.

Eso es lo que va en:
- `META_WA_EMBEDDED_SIGNUP_CONFIG_ID=<CONFIGURATION_ID>`

Referencia (guía externa que describe el mismo lugar del “Configuration ID”):
- Chatwoot docs: “Facebook Login for Business → Configurations → Create Configuration → WhatsApp Embedded Signup” (buscar “WHATSAPP_CONFIGURATION_ID”).

## Checklist
Ver checklist actualizado en [meta-tech-provider-checklist.md](file:///c:/Users/mateo/OneDrive/Escritorio/Work/Programas/IronHub/docs/meta-tech-provider-checklist.md).

## 5) Qué va en META_OAUTH_REDIRECT_URI LISTO
En IronHub el flujo usa el SDK JS (popup) y devuelve un `code`. En este caso el `redirect_uri` efectivo suele ser interno del SDK.
- Recomendación: dejar `META_OAUTH_REDIRECT_URI` vacío (equivale a `""`) salvo que Meta te exija un valor explícito para el intercambio del code.
- Si Meta devuelve error de validación del code por mismatch de redirect_uri, recién ahí fijar un valor estable y migrar el flujo a redirect-based OAuth.

Nota práctica:
- Meta no soporta comodines en “Valid OAuth Redirect URIs” para subdominios dinámicos; por eso el patrón robusto es el dominio único `connect.*` para ejecutar el SDK.

## 6) Variables de entorno (webapp-api) LISTO
- `META_APP_ID`
- `META_APP_SECRET` (solo secreto del entorno)
- `META_WA_EMBEDDED_SIGNUP_CONFIG_ID`
- `META_GRAPH_API_VERSION` (ej: `v19.0`)
- `META_OAUTH_REDIRECT_URI` (vacío por defecto)
- `WABA_ENCRYPTION_KEY` (misma key en webapp-api y admin-api si querés que admin pueda leer tokens cifrados)

Importante (seguridad):
- En producción IronHub requiere `WABA_ENCRYPTION_KEY` fuerte para guardar tokens.
- Evitá claves triviales (ej. solo números); usá una passphrase larga aleatoria.

## 7) Operación en IronHub
- En el tenant: Gestión → WhatsApp → **Conectar con Meta**
- Admin (dueño del sistema): Admin → WhatsApp → catálogo estándar de plantillas (Meta) y provisión por gimnasio.

## 8) Videos para App Review (checklist IronHub)
Meta suele pedir 2 videos separados:

### Video A — permiso whatsapp_business_messaging
Objetivo: demostrar que IronHub puede enviar un mensaje y que llega a WhatsApp.
- Abrir el tenant del gimnasio (sesión de dueño).
- Ir a **Gestión → Meta Review**.
- Completar número destino (ideal: tu número de prueba agregado como destinatario permitido).
- Click en **Enviar mensaje (real)**.
- Mostrar en cámara la respuesta JSON (message id) y luego la app de WhatsApp recibiendo el mensaje.

### Video B — permiso whatsapp_business_management
Objetivo: demostrar que IronHub crea plantillas de mensaje.
- Abrir el tenant del gimnasio (dueño).
- Ir a **Gestión → Meta Review**.
- Completar nombre/cuerpo/idioma y click en **Crear plantilla (real)**.
- Mostrar la respuesta JSON y luego click en **Health** para evidenciar que la plantilla aparece listada (count/pending/approved).

Notas:
- Estos endpoints están protegidos (owner-only) y operan contra el Graph API real.
- No “simulan” resultados: si Meta falla (tokens/roles/limitaciones), el error queda visible y grabable.

## 9) Webhooks (recomendado para producción)
Para enviar mensajes no es obligatorio, pero para un sistema “ultra pro” sí conviene:
- Recibir mensajes entrantes
- Recibir estados de entrega (sent/delivered/read/failed)

### URL multi-tenant (IronHub)
Meta no puede enviar headers custom (como `x-tenant`). En IronHub, la configuración recomendada es usar **una sola Callback URL** para toda la app y que el backend rutee al tenant correcto usando el `phone_number_id` del payload.

- Callback URL (única, la que tenés que pegar en Meta): `https://api.ironhub.motiona.xyz/webhooks/whatsapp`
- Verify Token: usar un valor global en `WHATSAPP_VERIFY_TOKEN` (env) y pegar el mismo en Meta.

Notas:
- Existe también el endpoint `/webhooks/whatsapp/{tenant}` para debugging, pero no es el recomendado para operación normal porque Meta solo permite una callback por app.

### Verify Token
En Meta “Verify token” debe coincidir con:
- `WHATSAPP_VERIFY_TOKEN` (global en env) **o**
- el valor configurado por tenant en IronHub (Gestión → WhatsApp → Webhook Verify Token)

### App Secret (firma X-Hub-Signature-256)
Para máxima seguridad, configurá el App Secret y dejá la validación de firma activa:
- En IronHub: `WHATSAPP_APP_SECRET` en env o en el tenant (clave `WHATSAPP_APP_SECRET` en `configuracion`)
- En dev podés permitir sin firma con `ALLOW_UNSIGNED_WHATSAPP_WEBHOOK=1` (no recomendado en producción)
