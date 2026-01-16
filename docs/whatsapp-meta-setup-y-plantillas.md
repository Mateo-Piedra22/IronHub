# WhatsApp (Meta) — Setup, Webhook y Plantillas (IronHub)

Este documento describe:
- Cómo configurar el **Webhook** de WhatsApp Cloud API en Meta para cada gimnasio (tenant).
- Qué datos pide Meta (Callback URL, Verify Token, App Secret, etc.) y cómo obtenerlos.
- Un catálogo “ultra pro” de **plantillas** (más de 10) para crear en WhatsApp Manager, con textos, variables y ejemplos.

> Notas oficiales de Meta:
> - Webhooks: GET de verificación con `hub.challenge` + POST firmado con `X-Hub-Signature-256` (HMAC-SHA256 con tu **App Secret**) y reintentos hasta ~36h si falla. Ver “Create a webhook endpoint” (actualizado 2025-11-07).  
> - Plantillas: nombre en minúsculas con `_`, categorías (utility/marketing/authentication), variables `{{1}}` o formato “named” y ejemplos obligatorios cuando hay parámetros. Ver “Templates” (actualizado 2025-12-05) y “Template categorization” (actualizado 2025-11-14).

---

## 1) Datos que vas a necesitar en Meta (por gimnasio)

Para cada gimnasio (WABA/phone number):
- **WhatsApp Business Account ID (WABA ID)**
- **Phone Number ID**
- **Access Token** (idealmente permanente mediante System User)
- **App Secret** (del Meta App; NO confundir con Verify Token)
- **Verify Token** (string que elegís vos; se usa solo para el “handshake” GET)

Recomendación:
- Mantener **una convención** de Verify Token por gimnasio (p.ej. `ih_<subdominio>_<random>`).
- Mantener idioma default por gimnasio (p.ej. `es_AR`).

---

## 2) Webhook — cómo configurarlo en Meta (Cloud API)

### 2.1 URL exacta del webhook (Callback URL)

IronHub expone el webhook en:
- `GET  /webhooks/whatsapp` (verificación)
- `POST /webhooks/whatsapp` (eventos)

Por lo tanto, la **Callback URL** debe ser:

```
https://{SUBDOMINIO}.{TENANT_BASE_DOMAIN}/webhooks/whatsapp
```

Ejemplo típico (según la config `TENANT_BASE_DOMAIN`):
```
https://mi-gym.ironhub.motiona.xyz/webhooks/whatsapp
```

### 2.2 Verify Token (Meta → Webhooks)

En el panel de configuración de WhatsApp en Meta:
- Campo **Verify token**: pegar el mismo token que tenés guardado para ese gimnasio.

Cómo funciona:
- Meta hace un `GET` con query params `hub.mode=subscribe`, `hub.verify_token=...`, `hub.challenge=...`.
- Tu endpoint debe responder `200` con el `hub.challenge` si el token coincide; si no, 4xx.

### 2.3 App Secret + verificación de firma (POST)

Para cada `POST` Meta incluye:
- Header: `X-Hub-Signature-256: sha256=<HASH>`

Tu servidor valida:
- `expected = HMAC_SHA256(raw_body, app_secret)`
- Comparar con el hash recibido (sin el prefijo `sha256=`).

Si falla:
- Responder 4xx y **no** procesar el payload.

### 2.4 Qué eventos suscribir en Meta

En la suscripción de Webhooks (WhatsApp product):
- Suscribirse al campo de **messages** (incluye mensajes entrantes y `statuses` en muchos casos).

---

## 3) Plantillas — reglas clave (para aprobación y “categoría correcta”)

### 3.1 Nombres y límites
- Nombres: minúsculas + números + `_` (no espacios), hasta 512 chars.
- Idioma obligatorio (Meta no traduce).
- Si usás variables, Meta exige ejemplos para cada variable.

### 3.2 Categorías (muy importante por aprobación y pricing)
- **UTILITY**: seguimiento de una acción del usuario / info transaccional; sin “venta/promo”.
- **MARKETING**: promos, descuentos, invitaciones a comprar, etc.
- **AUTHENTICATION**: códigos OTP / verificación de identidad.

Meta puede recategorizar templates automáticamente si detecta mal uso.

---

## 4) Catálogo “Ultra Pro” de plantillas (crear en WhatsApp Manager)

### 4.0 Cómo crearlas en WhatsApp Manager (UI)

En Meta Business Suite / WhatsApp Manager:
1) Ir a **WhatsApp Manager → Message templates → Create template**.
2) Completar:
   - **Name**: usar el nombre exacto (solo minúsculas + `_`).
   - **Category**: UTILITY / MARKETING / AUTHENTICATION.
   - **Language**: `es_AR` (o el idioma que uses en tu WABA).
3) Configurar componentes (según aplique):
   - **Header** (opcional): texto corto o media (si necesitás).
   - **Body** (obligatorio): pegar el texto con variables `{{1}}`, `{{2}}`, etc.
   - **Footer** (opcional): texto corto (p.ej. nombre del gimnasio).
   - **Buttons** (opcional): quick replies / URL / phone.
4) Cuando uses variables:
   - Cargar **examples** (Meta pide ejemplos por variable para aprobación).
5) Enviar a aprobación y esperar estado **Approved**.

Requisitos importantes:
- El endpoint del webhook debe ser **HTTPS con certificado válido** (no self-signed).  
- La categoría debe ser coherente: si mezclás “promo” con info transaccional, Meta puede recategorizar a marketing.

Convenciones:
- Idioma: `es_AR` (ajustable).
- Variables: formato posicional `{{1}}`, `{{2}}`, etc (compatible con WhatsApp Manager).
- Todas las plantillas de UTILITY evitan lenguaje promocional para minimizar recategorización.

### 4.1 UTILITY (operativo)

1) `ih_welcome_v1` (UTILITY)
- Body:
  - `Hola {{1}}. ¡Bienvenido/a! Si necesitás ayuda, respondé a este mensaje.`
- Variables:
  - `{{1}} = nombre`
- Ejemplos:
  - nombre: `Mateo`

2) `ih_payment_confirmed_v1` (UTILITY)
- Body:
  - `Hola {{1}}. Confirmamos tu pago de ${{2}} correspondiente a {{3}}. ¡Gracias!`
- Variables:
  - `{{1}} nombre` | `{{2}} monto` | `{{3}} periodo (MM/AAAA)`
- Ejemplos:
  - `Mateo`, `25000`, `01/2026`

3) `ih_membership_due_today_v1` (UTILITY)
- Body:
  - `Hola {{1}}. Recordatorio: tu cuota vence hoy ({{2}}). Si ya abonaste, ignorá este mensaje.`
- Variables:
  - `{{1}} nombre` | `{{2}} fecha (DD/MM)`
- Ejemplos:
  - `Mateo`, `16/01`

4) `ih_membership_due_soon_v1` (UTILITY)
- Body:
  - `Hola {{1}}. Tu cuota vence el {{2}}. Si querés, respondé a este mensaje y te ayudamos a regularizar.`
- Variables:
  - `{{1}} nombre` | `{{2}} fecha (DD/MM)`
- Ejemplos:
  - `Mateo`, `20/01`

5) `ih_membership_overdue_v1` (UTILITY)
- Body:
  - `Hola {{1}}. Tu cuota está vencida. Si ya abonaste, ignorá este mensaje. Si necesitás ayuda, respondé “AYUDA”.`
- Variables:
  - `{{1}} nombre`
- Ejemplos:
  - `Mateo`

6) `ih_membership_deactivated_v1` (UTILITY)
- Body:
  - `Hola {{1}}. Tu acceso está temporalmente suspendido. Motivo: {{2}}. Respondé a este mensaje si necesitás asistencia.`
- Variables:
  - `{{1}} nombre` | `{{2}} motivo`
- Ejemplos:
  - `Mateo`, `cuotas vencidas`

7) `ih_membership_reactivated_v1` (UTILITY)
- Body:
  - `Hola {{1}}. Tu acceso fue reactivado. ¡Gracias!`
- Variables:
  - `{{1}} nombre`
- Ejemplos:
  - `Mateo`

8) `ih_class_booking_confirmed_v1` (UTILITY)
- Body:
  - `Reserva confirmada: {{1}} el {{2}} a las {{3}}. Si no podés asistir, respondé “CANCELAR”.`
- Variables:
  - `{{1}} clase` | `{{2}} fecha` | `{{3}} hora`
- Ejemplos:
  - `Funcional`, `16/01`, `19:00`

9) `ih_class_booking_cancelled_v1` (UTILITY)
- Body:
  - `Tu reserva para {{1}} ({{2}} {{3}}) fue cancelada.`
- Variables:
  - `{{1}} clase` | `{{2}} fecha` | `{{3}} hora`
- Ejemplos:
  - `Funcional`, `16/01`, `19:00`

10) `ih_class_reminder_v1` (UTILITY)
- Body:
  - `Hola {{1}}. Recordatorio: {{2}} el {{3}} a las {{4}}.`
- Variables:
  - `{{1}} nombre` | `{{2}} clase` | `{{3}} fecha` | `{{4}} hora`
- Ejemplos:
  - `Mateo`, `Funcional`, `16/01`, `19:00`

11) `ih_waitlist_spot_available_v1` (UTILITY)
- Body:
  - `Hola {{1}}. Se liberó un cupo para {{2}} ({{3}} {{4}}). Respondé “SI” para tomarlo.`
- Variables:
  - `{{1}} nombre` | `{{2}} clase` | `{{3}} día` | `{{4}} hora`
- Ejemplos:
  - `Mateo`, `Funcional`, `viernes`, `19:00`

12) `ih_waitlist_confirmed_v1` (UTILITY)
- Body:
  - `Listo {{1}}. Te anotamos en {{2}} ({{3}} {{4}}).`
- Variables:
  - `{{1}} nombre` | `{{2}} clase` | `{{3}} día` | `{{4}} hora`
- Ejemplos:
  - `Mateo`, `Funcional`, `viernes`, `19:00`

13) `ih_schedule_change_v1` (UTILITY)
- Body:
  - `Aviso: hubo un cambio en {{1}}. Nuevo horario: {{2}} {{3}}.`
- Variables:
  - `{{1}} clase` | `{{2}} día` | `{{3}} hora`
- Ejemplos:
  - `Funcional`, `viernes`, `20:00`

### 4.2 AUTHENTICATION (OTP / verificación)

14) `ih_auth_code_v1` (AUTHENTICATION)
- Body:
  - `Tu código de verificación es {{1}}. Vence en {{2}} minutos. No lo compartas con nadie.`
- Variables:
  - `{{1}} código` | `{{2}} minutos`
- Ejemplos:
  - `928314`, `10`

### 4.3 MARKETING (opcionales, solo con opt-in)

15) `ih_marketing_promo_v1` (MARKETING)
- Body:
  - `Hola {{1}}. Esta semana tenemos {{2}}. Si querés más info, respondé a este mensaje.`
- Variables:
  - `{{1}} nombre` | `{{2}} promo`
- Ejemplos:
  - `Mateo`, `descuento del 10% en el plan trimestral`

16) `ih_marketing_new_class_v1` (MARKETING)
- Body:
  - `Nueva clase disponible: {{1}}. Primer horario: {{2}} {{3}}. ¿Querés que te reservemos un lugar?`
- Variables:
  - `{{1}} clase` | `{{2}} día` | `{{3}} hora`
- Ejemplos:
  - `Movilidad`, `miércoles`, `18:00`

---

## 5) Relación con IronHub (qué templates usa el sistema hoy)

En el backend actual, IronHub intenta enviar templates con estos nombres (y si no existen, cae a texto):
- `ih_welcome_v1`
- `ih_payment_confirmed_v1`
- `ih_membership_overdue_v1`
- `ih_membership_deactivated_v1`
- `ih_class_reminder_v1`
- `ih_waitlist_spot_available_v1`

Idioma:
- Default: `es_AR`
- Configurable por gimnasio con `wa_template_language` (tabla `configuracion`).

---

## 6) Checklist final “Meta Web + IronHub”

Por cada gimnasio:
1) En Admin: setear `Phone ID`, `WABA ID`, `Access Token`, `Verify Token`, `App Secret`.
2) Confirmar que el admin push replicó a la DB tenant:
   - `whatsapp_config` con `active=true`
   - `configuracion` con `WHATSAPP_VERIFY_TOKEN` y `WHATSAPP_APP_SECRET`
3) En Meta → WhatsApp → Configuration:
   - Callback URL = `https://{subdominio}.{base}/webhooks/whatsapp`
   - Verify token = el token configurado
   - Subscribe fields = `messages`
4) En Meta → WhatsApp Manager → Message templates:
   - Crear las plantillas de la sección 4.
5) En IronHub:
   - Activar triggers (si corresponde) y probar envíos manuales desde Gestión.

---

## Referencias oficiales (Meta)

- Webhook endpoint (verificación GET, firma `X-Hub-Signature-256`, reintentos):  
  https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/create-webhook-endpoint/
- Templates (nombres, variables, ejemplos, envío de template messages):  
  https://developers.facebook.com/docs/whatsapp/message-templates/guidelines/
- Categorías y criterios (utility/marketing/authentication):  
  https://developers.facebook.com/documentation/business-messaging/whatsapp/templates/template-categorization
- Utility templates (componentes soportados y creación):  
  https://developers.facebook.com/documentation/business-messaging/whatsapp/templates/utility-templates/utility-templates/
