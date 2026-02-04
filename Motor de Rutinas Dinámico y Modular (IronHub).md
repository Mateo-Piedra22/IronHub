```markdown

\# Especificación Técnica: Motor de Rutinas Dinámico y Modular (IronHub)



\## 1. Resumen Ejecutivo

El objetivo es reemplazar el sistema actual de generación de PDFs (basado en plantillas estáticas `.xlsx` y código imperativo) por un \*\*Motor de Renderizado Declarativo\*\*. 



En este nuevo sistema, el diseño de la rutina no está en el código Python, sino en la Base de Datos (JSON). El backend actúa como un "intérprete" que lee instrucciones de diseño y dibuja el PDF dinámicamente. Esto permite que cada gimnasio tenga diseños únicos sin cambiar el código fuente.



---



\## 2. Arquitectura de Datos



\### 2.1. Nuevo Modelo de Base de Datos

Se requiere una nueva tabla para almacenar las definiciones visuales.



\*\*Archivo:\*\* `apps/webapp-api/src/models/orm\_models.py`



```python

class PlantillaRutina(Base):

&nbsp;   \_\_tablename\_\_ = 'plantillas\_rutina'

&nbsp;   

&nbsp;   id: Mapped\[int] = mapped\_column(Integer, primary\_key=True)

&nbsp;   nombre: Mapped\[str] = mapped\_column(String(100), nullable=False) # Ej: "Modern Dark - 3 Días"

&nbsp;   descripcion: Mapped\[Optional\[str]] = mapped\_column(Text)

&nbsp;   

&nbsp;   # Si gym\_id es NULL, es una plantilla del sistema (disponible para todos)

&nbsp;   gym\_id: Mapped\[Optional\[int]] = mapped\_column(ForeignKey('gyms.id', ondelete='CASCADE'))

&nbsp;   

&nbsp;   # JSONB que contiene TODA la estructura visual (márgenes, colores, posiciones)

&nbsp;   configuracion: Mapped\[dict] = mapped\_column(JSONB, nullable=False)

&nbsp;   

&nbsp;   activo: Mapped\[bool] = mapped\_column(Boolean, server\_default='true')

&nbsp;   created\_at: Mapped\[datetime] = mapped\_column(DateTime, server\_default=func.current\_timestamp())



&nbsp;   \_\_table\_args\_\_ = (

&nbsp;       Index('idx\_plantillas\_gym', 'gym\_id'),

&nbsp;   )



```



\### 2.2. El "Contrato" JSON (Schema de `configuracion`)



Este JSON define cómo se ve el PDF. El motor leerá esto para saber qué dibujar.



\*\*Ejemplo de estructura JSON:\*\*



```json

{

&nbsp; "document": {

&nbsp;   "page\_size": "A4",

&nbsp;   "orientation": "portrait", // o "landscape"

&nbsp;   "margins": { "top": 30, "bottom": 30, "left": 30, "right": 30 },

&nbsp;   "background\_color": "#FFFFFF"

&nbsp; },

&nbsp; "styles": {

&nbsp;   "h1": { "font": "Helvetica-Bold", "size": 18, "color": "#111827" },

&nbsp;   "body": { "font": "Helvetica", "size": 10, "color": "#374151" },

&nbsp;   "accent\_color": "{{ brand.primary\_color }}" // Variable dinámica del Gym

&nbsp; },

&nbsp; "layout": \[

&nbsp;   {

&nbsp;     "type": "header",

&nbsp;     "height": 80,

&nbsp;     "columns": \[

&nbsp;       { "width": "20%", "element": { "type": "image", "src": "{{ gym.logo\_url }}", "fit": "contain" } },

&nbsp;       { "width": "60%", "element": { "type": "text", "content": "{{ gym.name }}", "style": "h1", "align": "center" } },

&nbsp;       { "width": "20%", "element": { "type": "qr\_code", "data": "\[https://ironhub.ar/v/](https://ironhub.ar/v/){{ routine.uuid }}", "size": 50 } }

&nbsp;     ]

&nbsp;   },

&nbsp;   {

&nbsp;     "type": "spacer",

&nbsp;     "height": 20

&nbsp;   },

&nbsp;   {

&nbsp;     "type": "info\_block",

&nbsp;     "fields": \[

&nbsp;       { "label": "Alumno:", "value": "{{ user.full\_name }}" },

&nbsp;       { "label": "Fecha:", "value": "{{ routine.created\_at }}" },

&nbsp;       { "label": "Objetivo:", "value": "{{ routine.goal }}" }

&nbsp;     ]

&nbsp;   },

&nbsp;   {

&nbsp;     "type": "routine\_grid",

&nbsp;     "config": {

&nbsp;       "cols\_per\_row": 2, // 1, 2 o 3 días por fila

&nbsp;       "show\_borders": true,

&nbsp;       "header\_bg": "{{ styles.accent\_color }}",

&nbsp;       "header\_text\_color": "#FFFFFF",

&nbsp;       "include\_warmup": true

&nbsp;     }

&nbsp;   },

&nbsp;   {

&nbsp;     "type": "footer",

&nbsp;     "text": "Generado por IronHub - {{ current\_page }} / {{ total\_pages }}"

&nbsp;   }

&nbsp; ]

}



```



---



\## 3. Lógica del Backend (El Motor)



El motor debe ser una clase capaz de interpretar los tipos de bloques (`header`, `routine\_grid`, `image`, etc.).



\*\*Archivo:\*\* `apps/webapp-api/src/services/pdf\_engine.py`



\### Principios de Implementación:



1\. \*\*Contexto de Datos:\*\* El motor recibe un diccionario `context` con todos los datos reales (`gym`, `user`, `routine`, `exercises`).

2\. \*\*Resolución de Variables:\*\* Una función auxiliar debe buscar cadenas como `{{ user.nombre }}` y reemplazarlas por el valor real.

3\. \*\*Fábrica de Componentes:\*\* Un método `build\_element(json\_def)` que retorna objetos de ReportLab (`Table`, `Paragraph`, `Image`, `Spacer`).



\### Estructura sugerida del código:



```python

from reportlab.platypus import SimpleDocTemplate, Table, Paragraph, Spacer, Image

from reportlab.lib.styles import ParagraphStyle

from reportlab.lib import colors

import io



class PDFEngine:

&nbsp;   def \_\_init\_\_(self, template\_config: dict, context\_data: dict):

&nbsp;       self.config = template\_config

&nbsp;       self.context = context\_data

&nbsp;       self.styles = self.\_build\_styles(template\_config.get('styles', {}))



&nbsp;   def \_resolve\_var(self, value):

&nbsp;       """Reemplaza {{ variable }} con datos del context"""

&nbsp;       if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):

&nbsp;           key = value\[2:-2].strip()

&nbsp;           # Lógica simple para acceder a dict anidados (ej: user.name)

&nbsp;           keys = key.split('.')

&nbsp;           val = self.context

&nbsp;           for k in keys:

&nbsp;               val = val.get(k, {})

&nbsp;           return str(val) if val else ""

&nbsp;       return value



&nbsp;   def \_create\_routine\_grid(self, config):

&nbsp;       """

&nbsp;       La parte más compleja: Itera sobre los días de la rutina

&nbsp;       y crea tablas anidadas para los ejercicios.

&nbsp;       """

&nbsp;       # Aquí va la lógica para transformar self.context\['routine\_days'] 

&nbsp;       # en una lista de Tablas de ReportLab según 'cols\_per\_row'.

&nbsp;       pass



&nbsp;   def render(self) -> str:

&nbsp;       buffer = io.BytesIO()

&nbsp;       doc = SimpleDocTemplate(

&nbsp;           buffer,

&nbsp;           pagesize=self.\_get\_pagesize(),

&nbsp;           leftMargin=self.config\['document']\['margins']\['left'],

&nbsp;           # ... otros márgenes

&nbsp;       )

&nbsp;       

&nbsp;       story = \[]

&nbsp;       

&nbsp;       for section in self.config\['layout']:

&nbsp;           if section\['type'] == 'header':

&nbsp;               story.append(self.\_create\_header(section))

&nbsp;           elif section\['type'] == 'routine\_grid':

&nbsp;               story.append(self.\_create\_routine\_grid(section\['config']))

&nbsp;           elif section\['type'] == 'spacer':

&nbsp;               story.append(Spacer(1, section\['height']))

&nbsp;           # ... otros tipos

&nbsp;           

&nbsp;       doc.build(story)

&nbsp;       

&nbsp;       # En Serverless guardar en /tmp o devolver bytes directamente

&nbsp;       # Retornar path o buffer

&nbsp;       return buffer



```



---



\## 4. Frontend (Gestión y Uso)



\### 4.1. Fase 1: Selección (El MVP)



En `webapp-web` (Panel del Gimnasio), al momento de crear o editar una rutina:



\* Añadir un campo `plantilla\_id` (Dropdown).

\* El endpoint `GET /api/templates` devuelve las plantillas disponibles (Sistema + Propias del Gym).

\* Al darle a "Imprimir/PDF", se envía el ID de la plantilla seleccionada al backend.



\### 4.2. Fase 2: Configuración Simple (Admin Web)



En `admin-web` (Tu panel):



\* Un editor de código (usando `Monaco Editor` o similar) para editar el JSON crudo de la plantilla.

\* Un botón "Previsualizar" que envía el JSON + datos dummy al backend y devuelve el PDF en una pestaña nueva.



\### 4.3. Fase 3: Editor Visual (Futuro)



\* Interfaz Drag \& Drop donde el usuario arrastra "Bloque de Logo", "Bloque de Rutina".

\* Esto genera el JSON automáticamente.

\* Librería recomendada para React: `@dnd-kit/core`.



---



\## 5. Consideraciones para Vercel Serverless



El entorno serverless tiene límites de tiempo (normalmente 10s o 60s en Pro) y memoria.



1\. \*\*Imágenes:\*\* \* No descargar el logo del gimnasio en cada petición.

\* Pasar el logo como Base64 si es pequeño, o asegurarse de que el servidor donde está alojado (S3/R2) sea muy rápido.

\* Usar `requests` con timeout agresivo (ej: 2s) para no colgar la generación del PDF.





2\. \*\*QR Codes:\*\*

\* Generarlos en memoria (`io.BytesIO`) usando la librería `qrcode` de Python. No guardarlos en disco.





3\. \*\*Fuentes:\*\*

\* Limitarse a fuentes estándar (Helvetica, Times, Courier) inicialmente para evitar cargar archivos `.ttf` pesados. Si necesitas fuentes custom, alójalas en el proyecto y cárgalas al inicio, pero cuidado con el peso del deploy.





4\. \*\*Sistema de Archivos:\*\*

\* \*\*NUNCA\*\* asumas que las carpetas existen.

\* Usa siempre `tempfile.gettempdir()` para cualquier archivo temporal.

\* Borra los archivos temporales inmediatamente después de usarlos (o usa `with tempfile.NamedTemporaryFile...`).







---



\## 6. Plan de Migración Completo único:



1\. \*\*Base de Datos:\*\*

\* Crear migración Alembic para la tabla `plantillas\_rutina`.

\* Insertar 1 registro con el JSON equivalente a tu diseño actual ("Plantilla Clásica").





2\. \*\*Backend:\*\*

\* Implementar `PDFEngine`.

\* Refactorizar el endpoint de exportación de rutinas para aceptar `template\_id` (opcional, default a la Clásica).





3\. \*\*Testing:\*\*

\* Verificar que la "Plantilla Clásica" generada por el nuevo motor sea visualmente idéntica (o mejor) que la actual.





4\. \*\*Frontend:\*\*

\* Añadir el selector de plantillas en el UI.





