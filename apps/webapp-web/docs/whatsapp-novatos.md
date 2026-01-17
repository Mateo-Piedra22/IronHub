# WhatsApp (WebApp) — Explicación a prueba de tontos

## Qué pasa cuando “IronHub manda un WhatsApp”
IronHub no inventa mensajes: usa **plantillas** que Meta aprueba.

Cada gimnasio tiene:
- una “llave” que dice si una acción está activa (ej. enviar bienvenida)
- un nombre de plantilla a usar para esa acción (ej. `ih_welcome_v1`)

Cuando ocurre un evento (ej. pago):
1) IronHub mira si la acción está habilitada para ese gimnasio
2) Busca el nombre de la plantilla asignada
3) Envía el mensaje por la API de WhatsApp Cloud

## Qué hacer si querés cambiar el texto
No podés cambiar un template ya aprobado en Meta.
Hay que crear una nueva versión:
- `ih_welcome_v1` → `ih_welcome_v2`

Después, el Admin decide que la acción “welcome” use `v2`.

## Meta Review: lo borro después?
No lo borres: sirve para probar y para soporte.
Cuando tengas `config_id`, el “conectar con Meta” será el flujo normal, pero Meta Review queda como herramienta interna.
