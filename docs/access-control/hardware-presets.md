# Presets de hardware (molinete/puerta)

## Concepto: “molinete bobo” vs “molinete inteligente”

- **Molinete/puerta “bobo”**: se abre por **contacto seco** (relé) o entrada digital. Es el escenario ideal: IronHub decide y el agente ejecuta.
- **Molinete “inteligente”**: puede tener lector y lógica propia. En este caso:
  - se recomienda `observe_only` si el molinete decide por su cuenta, o
  - integrar su salida de “datos” al agente (teclado/serial) y seguir usando un relé/bridge para abrir.

## Lo que soporta IronHub hoy (salida)

La apertura física se configura por device con `unlock_profile`:

- `http_get`
- `http_post_json`
- `tcp` (payload como bytes)
- `serial` (payload como bytes)
- `none` (no ejecuta apertura)

El agente implementa el envío y se valida con los tests del propio agente.

## Formato de payload (TCP/Serial)

El payload se interpreta así:

- Si el texto se puede parsear como lista de bytes hex (`0xA0 0x01 0xFF` o `A0 01 FF`), se envían esos bytes.
- Si no, se envía el texto como UTF-8 (por ejemplo `OPEN\\n`).

## Matriz de integración recomendada

| Caso | Input hacia el agente | Salida desde el agente | Recomendación |
|---|---|---|---|
| Molinete bobo + lector USB | Teclado (HID) | HTTP GET/POST a relé IP | Simple y robusto |
| Molinete bobo + lector integrado | Serial/Teclado desde el molinete | Relé IP / TCP / Serial | Depende del protocolo de salida del molinete |
| Controlador local (PLC) | Teclado/Serial | TCP/Serial | Usar payload bytes |
| Molinete inteligente que decide | Opcional | none | `observe_only` + auditoría |

## Presets (plantillas)

### 1) Relé IP genérico (HTTP GET)

Config de device (ejemplo):

```json
{
  "allow_remote_unlock": true,
  "station_auto_unlock": true,
  "unlock_ms": 2500,
  "unlock_profile": { "type": "http_get", "url": "http://RELAY_IP/unlock" }
}
```

### 2) Relé/PLC (HTTP POST JSON)

El agente envía:

```json
{ "action": "unlock", "ms": 2500 }
```

Config:

```json
{
  "unlock_profile": { "type": "http_post_json", "url": "http://RELAY_IP/unlock" }
}
```

### 3) TCP (texto)

```json
{
  "unlock_profile": {
    "type": "tcp",
    "host": "192.168.1.50",
    "port": 9100,
    "payload": "OPEN\n"
  }
}
```

### 4) TCP (bytes hex)

```json
{
  "unlock_profile": {
    "type": "tcp",
    "host": "192.168.1.50",
    "port": 9100,
    "payload": "0xA0 0x01 0x01 0xFF"
  }
}
```

### 5) Serial (texto)

```json
{
  "unlock_profile": {
    "type": "serial",
    "serial_port": "COM3",
    "serial_baud": 9600,
    "payload": "OPEN\n"
  }
}
```

## Ejemplos prácticos (referencia)

Estos ejemplos son solo “plantillas”; cada hardware tiene su propia API y seguridad.

### Shelly Gen1 (referencia)

```json
{ "type": "http_get", "url": "http://SHELLY_IP/relay/0?turn=on" }
```

### Shelly Gen2 (referencia)

```json
{ "type": "http_get", "url": "http://SHELLY_IP/rpc/Switch.Set?id=0&on=true" }
```

## Checklist de puesta en marcha (por sucursal)

- Confirmar cómo abre el molinete: contacto seco / entrada digital.
- Elegir un bridge (relé IP / PLC / controlador).
- Definir el `unlock_profile` y validarlo con tests del agente.
- Activar `allow_remote_unlock` si se quiere apertura desde móvil/web.
- Activar `station_auto_unlock` si el check-in móvil debe abrir el molinete.

