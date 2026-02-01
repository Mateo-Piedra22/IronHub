# Limpieza del esquema tenant (por gimnasio)

## Contexto: “DB por gimnasio”

Hoy IronHub ya está en un modelo **multi-tenant** donde cada gimnasio opera sobre su **esquema tenant** (migraciones en `apps/webapp-api/alembic`). Eso ya cumple el objetivo de “estructura de DB de cada gimnasio” en el sentido operativo.

Lo que sí es totalmente válido (y recomendable) es hacer **higiene del esquema tenant**: detectar tablas legacy/duplicadas, consolidar fuentes de verdad, y dejar el esquema más chico y consistente para futuras features y performance.

## Fuente de verdad del esquema

- Migraciones tenant:
  - Baseline: `apps/webapp-api/alembic/versions/0001_tenant_schema_baseline.py`
  - Post-baseline: `0002_multisucursal_hardening.py`, `0003_pagos_idempotency.py`, `0004_usuario_sucursal_registro.py`, `0005_rutinas_creada_por_usuario.py`, `0006_fix_fk_integer_types.py`
- ORM:
  - `apps/webapp-api/src/models/orm_models.py`

## Inventario alto nivel (dominios)

### Usuarios / Sucursales / Accesos
- `usuarios`
- `sucursales`, `usuario_sucursales`
- Entitlements finos:
  - `usuario_accesos_sucursales`
  - `usuario_permisos_clases`
  - `tipo_cuota_clases_permisos`
- Tags:
  - `etiquetas`, `usuario_etiquetas`
- Otros:
  - `usuario_notas`
  - `usuario_estados`, `historial_estados`

### Pagos
- `pagos`, `pago_detalles`
- `metodos_pago`, `conceptos_pago`
- `numeracion_comprobantes`, `comprobantes_pago`
- `pagos_idempotency`

### Asistencias / Check-in
- `asistencias`
- `checkin_pending`
- `checkin_station_tokens`

### Clases / Inscripciones
- `clases`, `tipos_clases`, `clases_horarios`
- `clase_usuarios`, `clase_lista_espera`
- `notificaciones_cupos`
- `clase_bloques`, `clase_bloque_items`
- `clase_ejercicios`, `clase_asistencia_historial`
- `clase_profesor_asignaciones`

### Rutinas / Ejercicios
- `ejercicios`
- `rutinas`, `rutina_ejercicios`
- `ejercicio_grupos`, `ejercicio_grupo_items`

### Profesores (extensión de Usuario)
- Perfil: `profesores`
- Horarios/disponibilidad:
  - `horarios_profesores`
  - `profesores_horarios_disponibilidad`
  - `profesor_disponibilidad`
- Asignaciones y extras:
  - `profesor_clase_asignaciones`
  - `profesor_suplencias`, `profesor_suplencias_generales`
  - `especialidades`, `profesor_especialidades`
  - `profesor_certificaciones`, `profesor_evaluaciones`
  - `profesor_horas_trabajadas`, `profesor_notificaciones`

### Staff (extensión de Usuario)
- Perfil/permisos/sesiones:
  - `staff_profiles`, `staff_permissions`, `staff_sessions`
  - `work_session_pauses`

### WhatsApp
- `whatsapp_config`, `whatsapp_messages`, `whatsapp_templates`

### Configuración / Flags
- Config:
  - `gym_config` (fila “principal” del gym)
  - `configuracion` (KV/legacy)
- Flags:
  - `feature_flags`, `feature_flags_overrides`
- Otros:
  - `audit_logs`

## Duplicaciones / solapamientos (dónde conviene consolidar)

### 1) Sucursales: múltiples fuentes de “pertenencia” y “acceso”

Tablas involucradas:
- `usuario_sucursales` (asignación/relación usuario↔sucursal)
- `usuario_accesos_sucursales` (entitlements por sucursal)
- `membership_sucursales` (membresías por sucursal)
- `tipo_cuota_sucursales` (tipo de cuota habilitado por sucursal)

Riesgo actual:
- Diferentes features consultan diferentes tablas para decidir “qué ve/puede hacer” un usuario.

Recomendación (Opción A coherente y práctica):
- Definir **jerarquía** y consolidar la resolución en un solo lugar (servicio):
  1) Socios: acceso nace de membresía/tipo cuota (`membership_*`, `tipo_cuota_*`)
  2) Excepciones: `usuario_accesos_sucursales` (override explícito)
  3) Staff/profesores: `usuario_sucursales` (asignación operativa)
- Crear un único “resolver” (ej. `EntitlementsPayloadService` o un `BranchAccessService`) y hacer que TODO pase por ahí.

### 2) Configuración: `gym_config` vs `configuracion` (KV)

Hecho:
- `GymConfigService` actualmente mergea ambos.

Problema:
- Fuente de verdad ambigua: una clave puede existir en `gym_config` y también en `configuracion`.

Recomendación:
- Migrar gradualmente claves “estructuradas” a `gym_config` y dejar `configuracion` para:
  - compatibilidad,
  - flags/keys no estructuradas,
  - o como “feature toggles legacy” hasta migrar.
- En paralelo, definir un set de keys “permitidas” en `configuracion` (lista blanca) para evitar crecimiento infinito.

### 3) Equipo: rol en `usuarios` vs perfiles (`profesores`, `staff_profiles`)

Hecho:
- `usuarios.rol` define el rol global
- `profesores` y `staff_profiles` agregan campos específicos

Recomendación:
- Mantener la extensión (no aplanar), pero estandarizar el “promote” y el “listado”:
  - `POST /api/team/promote` como punto de verdad para “promover” a staff/profesor.
  - `GET /api/team` como punto de verdad para listados.

## Tablas candidatas a “legacy” (posibles inutilizadas o subutilizadas)

Estas no recomiendo borrarlas hoy sin medición, pero sí:
1) Identificar si el front o jobs las consumen.
2) Medir si tienen filas reales.
3) Si no se usan, marcar deprecación y dejar un plan de retiro.

### Estados/Notas legacy
- `usuario_estados`, `historial_estados`
  - En `users.py` hay un import “fallback” de `UsuarioEstado` pero no se usa en rutas actuales.
- `usuario_notas`
  - Existe y se referencia a nivel repositorio; conviene decidir si se mantiene o se migra a `usuarios.notas` (columna) para simplificar.

## Plan seguro de limpieza (sin romper producción)

1) **Mapeo de uso real**
   - grep por tablas/modelos en routers/servicios
   - query por conteo de filas por tabla (por tenant) para ver tablas 100% vacías
2) **Marcar “read-only”/“write-only”**
   - si un feature viejo escribe pero nadie lee, o al revés, es señal de deuda.
3) **Consolidar**
   - mover el “source of truth” a un único servicio/tabla
   - migración de datos (batch) + compat (views/dual write si hace falta)
4) **Deprecar y retirar**
   - dejar 1-2 releases con warnings
   - luego drop definitivo (o mover a schema `legacy_` si querés preservar)

## Próximo paso recomendado (si querés que lo deje cerrado)

- Generar un CSV automático con:
  - tabla, modelo ORM, migración donde aparece, routers/servicios donde se referencia, recomendación (keep/consolidate/deprecate)
- Luego proponerte una “fase 1” (sin drops): solo consolidaciones y eliminación de duplicación lógica en código.

### Artefacto generado

- CSV: `docs/database/tenant-schema-audit.csv`
- Script reproducible: `apps/webapp-api/src/tools/tenant_schema_csv.py`

Regeneración:

```bash
python apps/webapp-api/src/tools/tenant_schema_csv.py
```
