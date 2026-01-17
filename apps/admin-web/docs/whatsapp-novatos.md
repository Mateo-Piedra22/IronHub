# WhatsApp (Admin) — Guía para novatos

## Qué es cada cosa (en simple)
- **Plantilla**: un mensaje pre-aprobado por Meta (WhatsApp).
- **Catálogo**: la lista “maestra” de plantillas que maneja IronHub.
- **Provisionar**: “crear” esas plantillas dentro de Meta para un gimnasio.
- **Binding/Acción**: “cuando pasa X (pago, bienvenida, etc.), qué plantilla uso”.

## Pasos recomendados (sin romper nada)
1) Entrá a Admin → WhatsApp → tocá **Sincronizar defaults**
2) Entrá al gimnasio → WhatsApp → tocá **Provisionar plantillas estándar**
3) Esperá que Meta apruebe (APPROVED) las nuevas
4) En el gimnasio → WhatsApp → “Acciones y versiones”
   - activá/desactivá acciones
   - elegí la versión de la plantilla

## Si querés cambiar un texto
No se puede “editar” una plantilla aprobada en Meta.
- Tocá **Bump** (crea `v2`)
- Editá `v2`
- Provisioná
- Cuando Meta la apruebe, cambiás la acción a `v2`

## Si algo falla al provisionar
Leé el error: suele ser por reglas de Meta (demasiadas variables, variables al final, etc.).
Solución típica: reducir variables o alargar el texto y volver a intentar con una versión nueva.
