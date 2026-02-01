# Pack para enviar a cada gimnasio (qué se entrega y cómo lo usan)

Objetivo: que cada sucursal pueda instalar el Access Agent y dejar el molinete funcionando **sin editar archivos**, configurando todo desde **Gestión** y desde la **interfaz del .exe**.

## Qué le enviás a cada gimnasio (entregables)

### 1) Software

- `IronHub.AccessAgent.exe` (Access Agent para Windows)
- `Puesta en marcha por sucursal (enterprise, paso a paso).md` (este runbook):
  - [branch-setup.md](file:///c:/Users/mateo/OneDrive/Escritorio/Work/Programas/IronHub/docs/access-control/branch-setup.md)

### 2) Hardware (kit típico)

- Llaveros RFID 125kHz (ej EM4100/TK4100) o tarjetas compatibles con el lector
- Lector RFID (ideal USB tipo teclado; o USB–Serial si corresponde)
- Teclado numérico USB
- Si el molinete requiere un actuador: relé IP / controladora TCP / controladora Serial (según la instalación)

### 3) Datos que se le pasan al gimnasio

- Tenant (nombre del tenant)
- Base URL (dominio del sistema)
- `Device ID` y `Pairing code` (se obtienen desde Gestión al crear el device)

## Qué se configura 100% desde interfaces (sin tocar JSON/archivos)

### En Gestión (web)

En **Gestión → Accesos → Dispositivos**, para cada device se configura:

- Sucursal, nombre, habilitado
- Salida de apertura (`unlock_profile`): HTTP GET / HTTP POST JSON / TCP / Serial / none
- Tiempos: `unlock_ms`, `station_unlock_ms`
- Permisos: manual unlock, remote unlock, auto unlock en check-in
- Reglas: timezone, horarios permitidos, anti-passback, rate limit, tipos de eventos permitidos, DNI requiere PIN
- Monitoreo: online/offline, `last_seen`, `last_test`, versión del agente, cola offline, comandos y resultados

### En el Access Agent (.exe)

En la interfaz del agente se configura:

- Pairing: tenant, base URL, device id, pairing code
- Entrada (lecturas): keyboard o serial, protocolo (raw/regex/em4100), submit key / idle ms
- Salida (apertura local): HTTP/TCP/Serial, puerto/baud/payload
- Tests de apertura y diagnóstico (reporta `last_test` y runtime)

## Formato recomendado del “pack” (carpeta)

Ejemplo de carpeta a enviar:

- `AccessAgent/`
  - `IronHub.AccessAgent.exe`
  - `README_INSTALACION.md` (copiar el runbook)

## Nota operativa (muy importante)

Si el molinete “genérico” usa DB25→USB y hoy destraba desde una notebook, casi siempre el adaptador es un **USB–Serial (COMx)**.
En ese caso se configura el método `serial` desde la UI y listo.

