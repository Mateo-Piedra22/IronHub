# Arquitectura (Access Control)

## Objetivo

Proveer un control de acceso robusto, auditable y altamente configurable, desacoplando:

- Validación (reglas, membresías, anti-passback, rate limit)
- Ejecución física (salida eléctrica hacia molinete/puerta)

## Componentes

- **Webapp (Gestión)**: administra devices, credenciales y visualiza eventos.
- **Web (Station / Check-in)**: pantalla de estación y check-in de usuarios.
- **API (webapp-api)**:
  - Recibe eventos del agente (`/api/access/events`) y decide allow/deny.
  - Expone config por device (`/api/access/device/config`).
  - Recibe status/tests del agente (`/api/access/device/status`).
  - Encola comandos “backend → agente” (`access_commands`) para apertura remota/automática.
- **Access Agent (Windows .exe)**:
  - Captura input (teclado/serial), normaliza (protocolos) y envía eventos.
  - Hace polling de comandos y ejecuta apertura física.
  - Implementa offline queue cuando la API no está disponible.

## Flujo principal (evento en puerta)

1) El agente recibe un input: `credential`, `dni`, `dni_pin`, `qr_token`, etc.
2) El agente llama `POST /api/access/events` con `X-Tenant`, `X-Device-Id` y token bearer del device.
3) La API valida:
   - device habilitado
   - rate limit por device
   - idempotencia por nonce (anti-replay)
   - reglas de sucursal/usuario/anti-passback
4) La API responde `allow/deny` y, si corresponde, `unlock=true`.
5) El agente ejecuta salida física (HTTP/TCP/Serial) si está en `validate_and_command`.

## Flujo de comando (backend → agente)

1) La web/API decide que corresponde abrir por un evento “remoto” (ej: check-in móvil o botón “Abrir” en Gestión).
2) La API inserta un comando `unlock` en `access_commands` con TTL corto.
3) El agente hace polling `GET /api/access/device/commands`, claim-ea comandos pendientes y ejecuta.
4) El agente confirma ejecución con `POST /api/access/device/commands/{id}/ack`.
5) La web tiene auditoría por evento `remote_unlock` en `access_events`.

## Datos (tablas)

- `access_devices`: dispositivo físico vinculado a sucursal, con `config` JSONB.
- `access_credentials`: credenciales registradas (hash) asociadas a usuario.
- `access_events`: auditoría de cada intento/decisión (incluye `event_nonce_hash`).
- `access_commands`: cola de comandos por device (claimed/acked).

## Configuración por device (resumen)

El `config` del device define el comportamiento. Campos clave:

- Input: `input_source`, `input_protocol`, `uid_format`, `uid_endian`, `uid_bits`.
- Seguridad: `max_events_per_minute`, `anti_passback_seconds`, `allowed_event_types`.
- Apertura: `unlock_profile` + `unlock_ms`.
- Remoto: `allow_remote_unlock`, `station_auto_unlock`, `station_unlock_ms`.

