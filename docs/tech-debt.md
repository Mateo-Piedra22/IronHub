# Deuda técnica

## WhatsApp templates: Meta reclasifica UTILITY → MARKETING
### Contexto
Se observaron plantillas operativas (p. ej. `ih_welcome_v2`, `ih_membership_overdue_v2`, `ih_membership_due_today_v2`, `ih_membership_due_soon_v2`, `ih_membership_deactivated_v2`, `ih_waitlist_spot_available_v2`) que fueron aprobadas pero Meta las reclasificó a categoría `MARKETING`.

### Impacto
- El envío no se rompe (el envío usa `name + language`), pero puede cambiar pricing/política de conversaciones.
- Puede requerir cuidados adicionales de opt-in/consent y compliance.

### Propuesta futura
- Crear versiones `*_v3` con redacción estrictamente transaccional para maximizar probabilidad de clasificación `UTILITY`.
- Revisar reglas internas de copy para evitar wording promocional/marketing en plantillas transaccionales.
- Definir criterio de aceptación: si Meta insiste en `MARKETING`, aceptar y documentar costos/políticas por categoría.

### Estado actual (mitigación implementada)
- El provisionamiento evita recrear versiones viejas (`*_v1`) si ya existe una versión superior (`*_v2+`) en la WABA, incluso si Meta cambió la categoría.
- Si Meta bloquea nombres por eliminación de idioma/categoría, se auto-crea una versión superior y se usa un alias para mapear `v1 → v2/v3`.
- Se ajustó el copy de las `*_v1` transaccionales para maximizar clasificación `UTILITY` (Meta puede overridear igualmente).
