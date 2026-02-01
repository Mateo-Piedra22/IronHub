# Operación y runbook (Access Control)

## Preparación por tenant (DB)

Requiere que el tenant tenga migraciones aplicadas hasta `0012_access_commands` (incluye `access_commands`).

## Alta de un device (Gestión)

1) Gestión → Accesos → Dispositivos → “Nuevo device”.
2) Asignar sucursal (recomendado).
3) Configurar:
   - Input (si aplica) y reglas avanzadas (anti-passback, rate limit).
   - `unlock_profile` según hardware (HTTP/TCP/Serial).
4) (Opcional) Activar:
   - “Permitir unlock remoto (web/móvil)”
   - “Auto abrir al check-in (Station QR / checkin)”
5) Tomar `Device ID` y `Pairing code`.

## Pairing del agente

En el Access Agent:

- `Ctrl+Shift+C` → Configuración
- Completar `Tenant`, `Base URL`, `Device ID`, `Pairing code` → `Pair`

El agente guarda el token en `%AppData%\\IronHubAccessAgent\\config.json` usando DPAPI (no plano).

## Validación rápida (antes de abrir al público)

1) Confirmar que el device aparece “online” en Gestión (actualiza `last_seen_at`).
2) Correr tests de salida desde el agente:
   - HTTP GET/POST
   - TCP / Serial
3) Ver en Gestión → Accesos → Dispositivos el `last_test`.
4) Probar un acceso real (credencial/DNI/QR).

## Checklist para check-in móvil con auto-apertura

- Al menos un device en la sucursal con:
  - `allow_remote_unlock=true`
  - `station_auto_unlock=true`
  - `unlock_profile` válido
- El agente del device debe estar `online`.
- El usuario debe estar autenticado en el check-in (sesión).

## Troubleshooting

### El check-in registra pero no abre

- Verificar `allow_remote_unlock` y `station_auto_unlock` en el device.
- Verificar `unlock_profile` y testear desde el agente.
- Verificar que el agente tenga polling habilitado (“Remote commands”).
- Verificar que el device esté online y pareado.

### El lector USB “tipea” pero no dispara evento

- Configurar “Keyboard submit” y/o “idle ms”.
- Si el lector no manda Enter, usar `idle ms` (ej 150–300ms).

### A veces abre doble / reintentos

- Verificar `event_nonce_hash` (idempotencia por evento).
- Ajustar rate limit y anti-passback en el device.

