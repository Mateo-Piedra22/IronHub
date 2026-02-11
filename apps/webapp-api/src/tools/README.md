# Excel Template Migration Tools

Herramientas completas para migrar plantillas de Excel existentes al nuevo sistema dinámico de plantillas.

## 🚀 Características

- **Análisis automático** de estructura de archivos Excel
- **Extracción inteligente** de ejercicios y configuración
- **Conversión completa** al formato de plantillas dinámicas
- **Validación** de plantillas migradas
- **API REST** para integración con el sistema
- **CLI** para procesamiento por lotes
- **Reportes detallados** de migración

## 📁 Estructura de Archivos

```
apps/webapp-api/src/tools/
├── excel_template_migrator.py    # Motor principal de migración
├── migrate_excel_templates.py    # CLI para migración
└── README.md                     # Este archivo

apps/webapp-api/src/routes/
└── migration.py                  # Endpoints API de migración

apps/webapp-api/
└── requirements-migration.txt    # Dependencias de migración
```

## 🛠️ Instalación

1. Instalar dependencias:
```bash
pip install -r requirements-migration.txt
```

2. Crear directorio para plantillas Excel:
```bash
mkdir -p excel_templates
```

## 📋 Uso CLI

### Migrar Todos los Archivos
```bash
python migrate_excel_templates.py
```

### Migrar Archivo Específico
```bash
python migrate_excel_templates.py --file mi_plantilla.xlsx
```

### Vista Previa sin Migrar
```bash
python migrate_excel_templates.py --preview-only --verbose
```

### Validar Plantillas Migradas
```bash
python migrate_excel_templates.py --validate
```

### Directorios Personalizados
```bash
python migrate_excel_templates.py --input-dir ./plantillas --output-dir ./migradas
```

## 🔧 Opciones CLI

| Opción | Descripción | Default |
|--------|-------------|---------|
| `--file, -f` | Archivo Excel específico | - |
| `--input-dir, -i` | Directorio de entrada | `excel_templates` |
| `--output-dir, -o` | Directorio de salida | `migrated_templates` |
| `--preview-only, -p` | Solo vista previa | `False` |
| `--validate, -v` | Validar después de migrar | `False` |
| `--force` | Sobreescribir existentes | `False` |
| `--verbose, -V` | Salida detallada | `False` |
| `--report-format` | Formato de reporte | `markdown` |

## 🌐 API REST

### Upload y Migrar
```http
POST /api/migration/upload
Content-Type: multipart/form-data

file: [archivo_excel]
template_name: "Mi Plantilla"
description: "Descripción de la plantilla"
category: "fuerza"
auto_save: true
```

### Vista Previa
```http
POST /api/migration/preview
Content-Type: multipart/form-data

file: [archivo_excel]
analyze_structure: true
extract_exercises: true
generate_config: true
```

### Migración por Lotes
```http
POST /api/migration/batch
Content-Type: multipart/form-data

files: [archivo1, archivo2, ...]
auto_save: true
category: "general"
```

### Estado de Migración
```http
GET /api/migration/status/{migration_id}
```

### Listar Plantillas Migradas
```http
GET /api/migration/templates?skip=0&limit=50
```

## 📊 Formatos de Excel Soportados

### Estructura Detectada Automáticamente:
- **Headers de ejercicios**: Ejercicio, Series, Repeticiones, Descanso
- **Configuración**: Nombre, Descripción, Categoría, Días
- **Estilos**: Fuentes, Colores, Bordes, Alineación
- **Layout**: Anchos de columna, Alturas de fila, Celdas combinadas

### Ejemplo de Formato Excel:
| Ejercicio | Series | Repeticiones | Descanso | Notas |
|-----------|---------|--------------|----------|-------|
| Press de Banca | 4 | 8-10 | 90s | En banco plano |
| Sentadillas | 4 | 12 | 120s | Profundidad completa |
| Remo con Barra | 3 | 10 | 60s | Espalda recta |

## 🎯 Mapeo de Campos

### Campos de Ejercicio:
- **Ejercicio/Exercise** → `name`
- **Series/Sets** → `sets`
- **Repeticiones/Reps** → `reps`
- **Descanso/Rest** → `rest`
- **Peso/Weight** → `weight`
- **Notas/Notes** → `notes`

### Metadatos de Plantilla:
- **Nombre/Name** → `template.name`
- **Descripción/Description** → `template.description`
- **Categoría/Category** → `template.category`
- **Días/Days** → `template.days_per_week`

## 📋 Salida de Migración

### Archivos Generados:
1. **`{nombre}_migrated.json`** - Configuración de plantilla
2. **`{nombre}_metadata.json`** - Metadatos de migración
3. **`migration_report.md`** - Reporte completo
4. **`migration_log.json`** - Log detallado

### Estructura de Plantilla:
```json
{
  "version": "1.0.0",
  "metadata": {
    "name": "Mi Plantilla",
    "description": "Migrada desde Excel",
    "tags": ["migrado", "excel", "fuerza"]
  },
  "layout": {
    "page_size": "A4",
    "orientation": "portrait",
    "margins": { "top": 20, "right": 20, "bottom": 20, "left": 20 }
  },
  "sections": [
    {
      "id": "header",
      "type": "header",
      "content": { "title": "{{gym_name}}", "subtitle": "Rutina" }
    },
    {
      "id": "day_1",
      "type": "exercise_table",
      "content": {
        "title": "Día 1",
        "exercises": [...]
      }
    }
  ],
  "variables": {
    "gym_name": { "type": "string", "default": "Gym" },
    "client_name": { "type": "string", "default": "Cliente" }
  },
  "styling": {
    "primary_color": "#000000",
    "font_family": "Arial",
    "font_size": 12
  }
}
```

## 🔍 Validación

### Checks Automáticos:
- ✅ Estructura JSON válida
- ✅ Campos requeridos presentes
- ✅ Tipos de datos correctos
- ✅ Configuración de secciones válida
- ✅ Variables definidas correctamente

### Niveles de Severidad:
- **Errors** - Bloquean la migración
- **Warnings** - Permiten migración con advertencias
- **Info** - Informativos solo

## 📈 Reportes

### Tipos de Reporte:
1. **Resumen** - Estadísticas generales
2. **Exitosos** - Lista de migraciones correctas
3. **Fallidos** - Detalles de errores
4. **Validación** - Resultados de validación

### Formatos:
- **Markdown** - Para documentación
- **JSON** - Para procesamiento
- **Texto** - Para logs

## 🚨 Manejo de Errores

### Errores Comunes:
- **Archivo no encontrado** - Verificar ruta
- **Formato inválido** - Solo .xlsx/.xls
- **Estructura no detectada** - Revisar headers
- **JSON inválido** - Error de conversión

### Soluciones:
1. **Modo verbose** para diagnóstico
2. **Vista previa** antes de migrar
3. **Validación** post-migración
4. **Logs detallados** para debugging

## 🎛️ Configuración Avanzada

### Personalización del Motor:
```python
migrator = ExcelTemplateMigrator()
migrator.default_config["layout"]["page_size"] = "A3"
migrator.default_config["styling"]["font_family"] = "Calibri"
```

### Mapeo Personalizado:
```python
def custom_column_detector(header: str) -> str:
    # Lógica personalizada para detectar columnas
    pass

migrator._detect_column_type = custom_column_detector
```

## 📝 Ejemplos de Uso

### Script de Migración Programática:
```python
from excel_template_migrator import ExcelTemplateMigrator

migrator = ExcelTemplateMigrator()
migrator.excel_templates_dir = Path("./my_templates")

# Migrar archivo específico
success, result = migrator.migrate_template(Path("routine.xlsx"))

if success:
    print(f"✅ Migrado: {result}")
else:
    print(f"❌ Error: {result}")
```

### Integración con API:
```python
import requests

# Subir y migrar
with open("template.xlsx", "rb") as f:
    files = {"file": f}
    data = {
        "template_name": "Mi Plantilla",
        "category": "fuerza",
        "auto_save": "true"
    }
    response = requests.post(
        "http://localhost:8000/api/migration/upload",
        files=files,
        data=data
    )

result = response.json()
print(f"Template ID: {result['template_id']}")
```

## 🔧 Troubleshooting

### Problemas Comunes:

**Q: No se detectan los ejercicios**
A: Verificar que los headers sean exactamente "Ejercicio", "Series", "Repeticiones"

**Q: El archivo Excel está corrupto**
A: Intentar abrir en Excel y guardar como nuevo archivo

**Q: Falla la migración con JSON inválido**
A: Revisar caracteres especiales en nombres de ejercicios

**Q: No se genera el preview**
A: Verificar permisos del directorio temporal

### Logs y Debugging:
```bash
# Modo verbose
python migrate_excel_templates.py --verbose

# Solo vista previa
python migrate_excel_templates.py --preview-only --verbose

# Validar después de migrar
python migrate_excel_templates.py --validate --verbose
```

## 📞 Soporte

Para problemas o preguntas:
1. Revisar logs de error
2. Usar modo verbose
3. Validar estructura del Excel
4. Consultar reportes generados

---

**Nota**: Esta herramienta está diseñada para migrar plantillas de Excel existentes al nuevo sistema dinámico, preservando la mayor cantidad de información posible del formato original.
