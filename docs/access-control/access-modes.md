# Modos de acceso (qué quedó andando)

Este documento describe “formas de entrar” al gimnasio y qué hace cada una.

## 1) Credencial física (llavero/tarjeta)

**Cómo se usa**
- Un lector (típicamente USB HID tipo teclado) “tipea” el UID en el Access Agent.

**Qué hace el sistema**
- El agente normaliza el UID (según `input_protocol`, ej `em4100`) y envía `event_type=credential` a `POST /api/access/events`.
- La API busca la credencial en `access_credentials`, valida reglas y responde allow/deny.
- Si allow y el device está en `validate_and_command`, el agente ejecuta la apertura.

**Enrolamiento**
- Gestión puede habilitar un “portal temporal” por device para asociar la próxima lectura a un usuario.

## 2) QR token escaneado en puerta (scanner como teclado)

**Cómo se usa**
- Un scanner QR USB (o lector integrado que emite por teclado/serial) envía el token al agente.

**Qué hace el sistema**
- El agente clasifica como `event_type=qr_token` y la API valida el token (expiración/uso) y registra asistencia si corresponde.

## 3) Check-in móvil (celular) → apertura automática del molinete

**Cómo se usa**
- El usuario inicia sesión en el flujo de check-in y escanea:
  - Station QR (`/station/[key]`) o
  - un token QR de usuario (según el flujo del frontend).

**Qué hace el sistema**
- La API registra asistencia en el endpoint de check-in correspondiente.
- Si la sucursal tiene un device configurado con:
  - `allow_remote_unlock=true`
  - `station_auto_unlock=true`
  - `unlock_profile` configurado
  entonces la API encola un comando `unlock` en `access_commands`.
- El Access Agent hace polling, ejecuta la apertura y ACKea.

## 4) DNI por teclado (en el Access Agent)

**Cómo se usa**
- Un teclado conectado al equipo del molinete permite tipear:
  - DNI (7–9 dígitos) o
  - DNI#PIN (ej `12345678#1234`)

**Qué hace el sistema**
- El agente envía `dni` o `dni_pin` a `POST /api/access/events`.
- La API valida reglas y responde allow/deny.
- Si allow, el agente abre (en `validate_and_command`).

## 5) Apertura manual local (hotkey)

**Cómo se usa**
- El operador usa una hotkey local configurada (ej `F10`).

**Qué hace el sistema**
- El agente envía `event_type=manual_unlock`.
- La API permite o niega según `allow_manual_unlock`.

## 6) Apertura remota desde Gestión (staff/owner)

**Cómo se usa**
- En Gestión → Accesos → Dispositivos se puede presionar “Abrir” para un device online.

**Qué hace el sistema**
- La API encola un comando `unlock` y registra un evento `remote_unlock`.
- El agente ejecuta la apertura y ACKea.

## Modos operativos del device

- `validate_and_command`: el agente ejecuta apertura física cuando la API devuelve allow/unlock o cuando hay comando remoto.
- `observe_only`: el agente registra y valida, pero nunca abre (sirve para hardware que decide por cuenta propia).

