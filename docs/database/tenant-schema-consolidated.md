# Esquema tenant consolidado (estructura DB por gimnasio)

Este documento describe la **estructura del schema tenant** (por gimnasio) luego de la consolidación de fuentes de verdad en backend y frontend.

> Nota: El esquema físico (tablas/columnas) no se reduce “a ciegas”. Primero se consolida el acceso por código y se audita uso/filas por tenant; luego se programa la deprecación y, recién ahí, el drop definitivo.

## Fuentes de verdad (decisiones)

### 1) Sucursales permitidas (branch access)

**Objetivo**: evitar que distintas rutas calculen “allowed branches” con criterios distintos.

- Punto de verdad en backend: `BranchAccessService.get_allowed_sucursal_ids(request)`
  - Staff/Profesor: `usuario_sucursales`
  - Socios: `EntitlementsService.get_effective_branch_access()` (cuando está habilitado) y fallback a `MembershipService` (hasta completar migración)

Archivos:
- Servicio: `apps/webapp-api/src/services/branch_access_service.py`
- Router de sucursales: `apps/webapp-api/src/routers/branches.py`

Tablas involucradas:
- `sucursales`
- `usuario_sucursales`
- `usuario_accesos_sucursales` (overrides / entitlements v2)
- `membership_sucursales`
- `tipo_cuota_sucursales`

### 2) Config del gimnasio: `gym_config` + `configuracion`

**Objetivo**: definir precedencia clara y evitar “doble fuente” ambigua.

Regla:
- `configuracion` (KV) se carga como base
- `gym_config` (columnas estructuradas) **overridea** claves solapadas

Archivo:
- `apps/webapp-api/src/services/gym_config_service.py`

Tablas:
- `gym_config` (perfil estructurado del gimnasio)
- `configuracion` (KV legacy / flags / settings genéricos)

Recomendación operativa (para la siguiente iteración):
- Mantener `configuracion` para claves no estructuradas y compatibilidad
- Migrar progresivamente settings “core” a columnas de `gym_config`
- Definir lista blanca de claves permitidas en `configuracion` para evitar crecimiento infinito

### 3) Tema/branding (estático por gimnasio, enterprise)

**Objetivo**: tema estático por gimnasio administrado centralmente (admin DB), sin scheduling.

- Fuente de verdad: **admin DB** `gym_branding` (por `gym_id`)
- Edición: admin-web (Branding)
- Consumo: `webapp-api` lo inyecta en `GET /api/bootstrap` y `webapp-web` aplica el tema vía CSS variables.

### 4) Equipo (Usuario + extensiones)

Modelo:
- Identidad base: `usuarios`
- Extensión Staff: `staff_profiles` + `staff_permissions`
- Extensión Profesor: `profesores` (y satélites)

Endpoints unificados:
- `GET /api/team` (listado único)
- `POST /api/team/promote` (promover a staff/profesor)

## Mapa de dominios (tablas principales)

> Para inventario completo y trazabilidad de uso por código: `docs/database/tenant-schema-audit.csv`

### Usuarios y relaciones
- `usuarios`
- `usuario_sucursales`
- `usuario_accesos_sucursales`
- `usuario_permisos_clases`
- `etiquetas`, `usuario_etiquetas`
- `usuario_notas`
- `usuario_estados`, `historial_estados`

### Membresías / cuotas / entitlements
- `memberships`, `membership_sucursales`
- `tipos_cuota`, `tipo_cuota_sucursales`
- `tipo_cuota_clases_permisos`

### Pagos
- `pagos`, `pago_detalles`
- `metodos_pago`, `conceptos_pago`
- `numeracion_comprobantes`, `comprobantes_pago`
- `pagos_idempotency`

### Asistencias / check-in
- `asistencias`
- `checkin_pending`
- `checkin_station_tokens`

### Clases e inscripciones
- `clases`, `tipos_clases`, `clases_horarios`
- `clase_usuarios`, `clase_lista_espera`
- `notificaciones_cupos`
- `clase_bloques`, `clase_bloque_items`
- `clase_ejercicios`, `clase_asistencia_historial`
- `clase_profesor_asignaciones`

### Rutinas y ejercicios
- `ejercicios`
- `rutinas`, `rutina_ejercicios`
- `ejercicio_grupos`, `ejercicio_grupo_items`

### Profesores (extensión)
- `profesores`
- `horarios_profesores`
- `profesores_horarios_disponibilidad`
- `profesor_disponibilidad`
- `profesor_clase_asignaciones`
- `profesor_suplencias`, `profesor_suplencias_generales`
- `especialidades`, `profesor_especialidades`
- `profesor_certificaciones`, `profesor_evaluaciones`
- `profesor_horas_trabajadas`, `profesor_notificaciones`

### Staff (extensión) y sesiones
- `staff_profiles`, `staff_permissions`, `staff_sessions`
- `work_session_pauses`

### WhatsApp
- `whatsapp_config`, `whatsapp_messages`, `whatsapp_templates`

### Config / flags / temas / mantenimiento
- `gym_config`
- `configuracion`
- `feature_flags`, `feature_flags_overrides`
- `audit_logs`

## Tablas legacy removidas (tenant)

En installs desde cero, estas tablas se eliminan por migración porque el producto ya no las usa:
- `custom_themes`, `theme_schedules`, `theme_scheduling_config` (temas programados)
- `system_diagnostics`, `maintenance_tasks`
- `acciones_masivas_pendientes`

## Artefactos de auditoría y regeneración

- CSV de auditoría: `docs/database/tenant-schema-audit.csv`
- Script: `apps/webapp-api/src/tools/tenant_schema_csv.py`

Regenerar:

```bash
python apps/webapp-api/src/tools/tenant_schema_csv.py
```

## Etapa pesada (medición + drops opcionales)

### Medición por tenant (rowcount/size)

- CLI: `apps/webapp-api/src/cli/tenant_table_stats.py`

Ejemplos:

```bash
python -m src.cli.tenant_table_stats --tenant <subdominio>
python -m src.cli.tenant_table_stats --db-url "<postgres-url>" --out docs/database/tenant-table-stats.csv
```

### Plan de cleanup por tenant (cruza uso + “tabla vacía”)

- CLI: `apps/webapp-api/src/cli/tenant_cleanup_plan.py`

```bash
python -m src.cli.tenant_cleanup_plan --tenant <subdominio>
```

### Migración de drop (segura y definitiva)

Se agregó una migración que dropea tablas legacy **solo si están vacías**. Si una tabla tiene filas, la migración falla para evitar pérdida de datos.

- `apps/webapp-api/alembic/versions/0007_optional_drop_legacy_tables.py`
