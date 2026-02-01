# IronHub Access Agent

Aplicación Windows para control de acceso (lector tipo teclado, DNI, QR, llavero/tarjeta) conectada al módulo `/api/access/*`.

## Uso

1) En Gestión → Accesos → Dispositivos, crear un device y copiar:
- Device ID
- Pairing code

2) Abrir el agente, ir a Configuración (o `Ctrl+Shift+C`), completar:
- Tenant (subdominio)
- Base URL API (ej: `https://testingiron.ironhub.motiona.xyz`)
- Device ID
- Pairing code → `Pair`

3) Escanear:
- DNI (7–9 dígitos) → registra asistencia si corresponde y autoriza
- DNI#PIN (ej: `12345678#1234`) → usa evento `dni_pin` (si el device lo requiere)
- QR token (string largo) → valida token y registra asistencia
- Llavero/tarjeta (cualquier string) → busca credencial registrada

## Configuración centralizada

El agente consulta periódicamente `GET /api/access/device/config` y aplica:
- unlock_profile (none / http_get / http_post_json / tcp / serial)
- unlock_ms
- allow_manual_unlock
- manual_hotkey
- allow_remote_unlock / station_auto_unlock (en el backend)
- enroll_mode (portal temporal para cargar credenciales)

## Comandos remotos (backend → agente)

El agente hace polling de:

- `GET /api/access/device/commands`
- `POST /api/access/device/commands/{id}/ack`

Esto habilita:

- Apertura remota desde Gestión (“Abrir”)
- Apertura automática al check-in móvil (si el device lo permite)

## Offline queue

Si la API está caída (errores 5xx/red), el agente encola los eventos en `%AppData%\\IronHubAccessAgent\\events.ndjson` y reintenta en segundo plano.

## Teclado / lectores USB (fin de lectura)

Muchos lectores USB actúan como teclado. Para disparar el procesamiento, el agente soporta:

- Submit por tecla (`enter` o `tab`)
- Submit automático por “idle ms” (si el lector no manda Enter)

## Enrolamiento (portal temporal)

Desde Gestión (sidebar del usuario → Credenciales → Portal temporal), se habilita un enroll por device (solo si el device tiene sucursal).

En el agente de ese device, al estar activo, el banner indica:

`ENROLL · usuario <id> · FOB/CARD · escaneá ahora`

El siguiente scan queda asociado al usuario y el portal se cierra automáticamente.

## Pruebas de molinete

En Configuración del agente hay un bloque de tests para probar aperturas por:
- HTTP GET
- HTTP POST JSON
- TCP payload
- Serial payload

Esto sirve para validar qué conexión abre el molinete sin tocar el flujo normal de eventos.

Cada test reporta el resultado a la API (`/api/access/device/status`) y queda visible en Gestión → Accesos → Dispositivos como `last_test`.

## Seguridad del token

El token del device se guarda cifrado con DPAPI (usuario actual de Windows) en `config.json` como `tokenProtected`.

## Build / Publish

Desde repo root:

```powershell
dotnet build apps/access-agent/IronHub.AccessAgent.csproj -c Release
dotnet publish apps/access-agent/IronHub.AccessAgent.csproj -c Release -r win-x64 -p:PublishSingleFile=true -p:SelfContained=false
```

Salida típica:

`apps/access-agent/bin/Release/net8.0-windows/win-x64/publish/IronHub.AccessAgent.exe`
