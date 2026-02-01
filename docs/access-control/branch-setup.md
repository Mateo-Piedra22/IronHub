# Puesta en marcha por sucursal (enterprise, paso a paso)

Este documento está pensado para que una sucursal pueda “instalar y dejar andando” el control de accesos en una PC Windows con un molinete/puerta. Incluye hardware compatible, configuración y pruebas.

## Qué recibe la sucursal (kit típico)

- PC Windows conectada al molinete/puerta (o al relé/controlador que lo acciona)
- Access Agent (`IronHub.AccessAgent.exe`)
- Llaveros/tarjetas (RFID) + lector
- Teclado numérico (USB) para DNI / DNI#PIN

## Qué se considera “funcionando”

- El device figura **online** en Gestión y reporta `last_seen`.
- El test de apertura (`last_test`) da **ok**.
- Las lecturas (llavero/QR/DNI/DNI#PIN) generan eventos.
- La apertura abre realmente el molinete/puerta y queda auditada.

## Hardware compatible (guía práctica)

### Lectores de llaveros / tarjetas

Compatibles por cómo “entregan” el dato al agente:

- **USB HID tipo teclado (recomendado)**: “tipea” el UID y suele enviar Enter al final.
  - Pros: plug & play, mínimo mantenimiento.
  - Contras: a veces configura el formato del UID en el propio lector (decimal/hex) y hay que estandarizar.
- **USB Serial / RS232 (COMx)**: entrega líneas por puerto COM con baud configurable.
  - Pros: estable en entornos industriales, control fino del final de línea.
  - Contras: requiere seleccionar COM/baud y a veces drivers.
- **Wiegand**: es un estándar eléctrico (D0/D1), no se conecta directo a PC.
  - Para usarlo con PC, necesitás un **controlador/bridge** que convierta Wiegand a USB HID o a IP/TCP.

### Tipos de credenciales

- **RFID 125 kHz EM4100 / TK4100 (muy común, económico)**:
  - Se ve mucho en llaveros tipo “gota” o “disco”.
  - El lector suele entregar UID en decimal o hex según configuración.
- **RFID 13.56 MHz (MIFARE/ISO14443)**:
  - Más moderno, puede leer tarjetas tipo “MIFARE Classic/Ultralight”.
  - Importante: muchos sistemas entregan UID, pero algunos usan sectores/keys (eso ya es “controladora inteligente” y no entra en el modo simple).
- **PIN numérico**:
  - DNI#PIN: `12345678#1234` (o `|`/`;`) y Enter.
  - También se puede usar PIN puro como credencial, pero en esta instalación típicamente se usa DNI+PIN.
- **QR / token**:
  - Scanner USB tipo teclado o cámara con módulo (si emite texto).

### Molinetes / puertas (cómo se accionan)

El agente no “habla” con el molinete directamente: dispara una **salida** que acciona un relay/controlador.

Opciones típicas:

- **Relé IP (HTTP)**: un equipo en red recibe HTTP GET/POST y conmuta un relay.
- **Controlador TCP**: un equipo en red abre al recibir bytes/strings por socket.
- **Controlador Serial (COM)**: un equipo local abre al recibir bytes/strings por puerto serial.

El molinete/puerta usualmente se integra con:

- **Contacto seco (NO/NC)**: una bornera que abre con un pulso de relay.
- **Entrada de botón / push-to-open**: se simula el botón de apertura con relay.

Regla de oro: siempre validar con el instalador eléctrico cuál es la entrada correcta a accionar (y el tiempo de pulso).

### Caso común: molinete “genérico” con cable DB25 + adaptador USB

Si hoy el gimnasio ya tiene un sistema donde:

- una notebook valida DNI contra una base de datos, y
- “destraba” el molinete vía un adaptador DB25→USB,

entonces es muy probable que el adaptador sea uno de estos casos:

1) **USB–Serial real (COMx)** (lo más común)
   - Windows muestra un puerto `COM` en el Administrador de dispositivos.
   - El software viejo probablemente envía un comando por serial.
   - Esto es compatible con IronHub usando salida `serial`.
2) **USB que controla líneas (DTR/RTS/BREAK)** (menos común, pero existe)
   - Algunos sistemas destraban “levantando” una línea.
   - IronHub ahora soporta esto como payload especial.
3) **Adaptador “paralelo/impresora”** (raro si ya funciona hoy)
   - Si fuese este caso, normalmente no destraba con un programa serial común.

Cómo confirmarlo sin modelo:

- Abrir Administrador de dispositivos → “Puertos (COM y LPT)”.
- Conectar/desconectar el adaptador y ver si aparece/desaparece un `COMx`.

Si aparece un COM:

- Probar en el Access Agent con salida `serial` y el COM detectado.
- Baud típico inicial: `9600`.

Payload serial soportado por el agente:

- Enviar bytes ASCII (ej `OPEN`) o bytes hex (ej `0x02 0x31 0x03`).
- Alternativas por líneas:
  - `DTR_PULSE:500`
  - `RTS_PULSE:500`
  - `BREAK:300`

Si no aparece un COM:

- Lo más robusto es pasar a relé IP (HTTP) o a una controladora dedicada para evitar “cajas negras”.

## 1) Preparar el hardware

1) Conectar el molinete/puerta a un **actuador** que el PC pueda disparar:
   - Relé IP (HTTP GET/POST), o
   - Controlador TCP (socket), o
   - Controlador Serial (COM)
2) Confirmar con el instalador el comportamiento de apertura:
   - ¿Pulso único? (ej 1–3s)
   - ¿Necesita “ON” y luego “OFF”? (si es así se resuelve en el bridge/controlador; el agente hace un comando simple)
3) Conectar lector de llaveros:
   - Si es USB tipo teclado: no requiere drivers especiales, “tipea” el UID.
   - Si es serial/RS232/USB-Serial: anotar `COMx` y baud.
4) Conectar el teclado numérico USB.

## 2) Alta del device en IronHub (central)

En Gestión (por tenant):

1) Ir a **Gestión → Accesos → Dispositivos → Nuevo device**
2) Completar:
   - Nombre (ej “Molinete entrada”)
   - Sucursal
3) Configurar salida (`unlock_profile`):
   - Elegir preset (recomendado) o cargar manual:
     - HTTP GET: `http://RELAY_IP/unlock`
     - HTTP POST JSON: `http://RELAY_IP/unlock`
     - TCP: host/port/payload
     - Serial: COM/baud/payload
4) Activar si aplica:
   - `allow_remote_unlock` (permite abrir desde web/móvil)
   - `station_auto_unlock` (abre automáticamente al check-in)
5) Guardar. Luego, abrir **Pairing** y copiar:
   - `Device ID`
   - `Código` (expira)

## 3) Instalar y ejecutar el Access Agent en la PC de la sucursal

1) Copiar la carpeta/binario del agente a la PC (ideal: `C:\IronHub\AccessAgent\`).
2) Ejecutar `IronHub.AccessAgent.exe`.
3) En el agente: `Ctrl+Shift+C` → Configuración.
4) Completar:
   - Tenant (subdominio/tenant)
   - Base URL (ej `https://TU_DOMINIO`)
   - Device ID
   - Pairing code
   Tip: podés copiar el texto de “Pairing” desde la web y usar el botón **Pegar** en el agente.
5) Click **Pair**.
6) Verificar que muestre `Pair OK`.

El token queda guardado en `%AppData%\IronHubAccessAgent\config.json` protegido (DPAPI).

## 4) Configurar “entrada” (lecturas) en el agente

### A) Lector USB tipo teclado (recomendado)

1) Input source: `keyboard`
2) Submit:
   - Si el lector manda Enter: seleccionar `enter`
   - Si NO manda Enter: configurar `idle ms` (ej 150–300ms)
3) Input protocol:
   - `raw` si ya llega el UID limpio
   - `em4100` si llega en hex/dec y querés normalización

### B) Lector Serial

1) Input source: `serial`
2) Seleccionar `COMx` y baud correcto
3) Elegir `protocol` (raw/regex/drt/str/em4100) según el formato que emita el equipo

### C) DNI / DNI#PIN con teclado numérico

- Para DNI: tipear 7–9 dígitos y Enter.
- Para DNI#PIN: `12345678#1234` y Enter.

## 5) Probar apertura (salida) antes de enrolar

En el agente, sección “Pruebas de molinete”:

1) Probar HTTP/TCP/Serial según el `unlock_profile`.
2) Confirmar que el molinete abre.
3) Verificar en Gestión → Accesos → Dispositivos que aparezca `last_test` con ok.

## 6) Enrolar los 100 llaveros (RFID) y/o PINs

### Opción 1 (recomendada): asociar llavero a usuario real

1) Buscar/crear usuario.
2) En Gestión → Accesos → Dispositivos: elegir el device y activar “Enroll” para ese usuario.
3) Pasar el llavero por el lector conectado al agente.
4) Confirmar evento `ENROLLED` y que se desactive el enroll automáticamente.

### Opción 2: precarga en lote (operativo)

Si necesitás cargar 100 llaveros rápido:

- Crear usuarios “placeholder” o importar usuarios y luego asociar llaveros.
- Usar enroll consecutivo (90s) y pasar llaveros uno por uno.

## 7) Configurar check-in móvil con auto-apertura (opcional)

Requisitos por sucursal:

- Device con `allow_remote_unlock=true`
- Device con `station_auto_unlock=true`
- Agente online (polling habilitado)

Flujo:

- El usuario hace check-in → la API encola comando → el agente abre y ACKea.

## 8) Operación diaria

- El device debe figurar `online`.
- Revisar:
  - `last_seen`
  - `last_test`
  - `offline_queue` (si crece, hay conectividad/intermitencia hacia la API)

## 9) Troubleshooting rápido

- No abre:
  - Confirmar `unlock_profile` y re-test desde el agente.
  - Confirmar que el agente está en modo `validate_and_command` (no `observe_only`).
- Lector no dispara:
  - Ajustar `submit key` o `idle ms`.
- Doble apertura:
  - Ajustar anti-passback y rate limit por device en config avanzada.

## Checklist de instalación (para que la sucursal lo marque)

- Hardware: molinete/puerta + relay/controlador probado con pulsador manual
- PC: lector de llaveros operativo (escribe UID en un bloc de notas)
- PC: teclado numérico operativo
- Gestión: device creado, `unlock_profile` configurado y `allow_remote_unlock` según política
- Agente: Pair OK
- Test: apertura OK desde agente
- Enroll: al menos 1 llavero enrolado y validado
- Operación: aparece evento allow/deny y auditoría en Gestión
