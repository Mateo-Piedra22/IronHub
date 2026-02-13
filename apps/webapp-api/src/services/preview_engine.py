"""
Preview Engine

This module provides real-time preview generation for dynamic routine templates,
including sample data generation, caching, and performance optimization.
"""

import io
import hashlib
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time

from .pdf_engine import PDFEngine
from .variable_resolver import VariableResolver, VariableContext
from .exercise_table_builder import ExerciseTableBuilder
from .qr_code_manager import QRCodeManager

logger = logging.getLogger(__name__)


class PreviewFormat(Enum):
    """Preview output formats"""
    PDF = "pdf"
    IMAGE = "image"
    THUMBNAIL = "thumbnail"
    HTML = "html"
    JSON = "json"


class PreviewQuality(Enum):
    """Preview quality levels"""
    LOW = "low"      # Fast, lower quality
    MEDIUM = "medium"  # Balanced
    HIGH = "high"    # High quality, slower
    ULTRA = "ultra"  # Maximum quality


@dataclass
class PreviewConfig:
    """Configuration for preview generation"""
    format: PreviewFormat = PreviewFormat.PDF
    quality: PreviewQuality = PreviewQuality.MEDIUM
    page_number: int = 1
    width: Optional[int] = None
    height: Optional[int] = None
    dpi: int = 150
    use_cache: bool = True
    cache_ttl: int = 3600  # 1 hour
    generate_sample_data: bool = True
    include_analytics: bool = False
    optimize_for_speed: bool = False
    max_render_time: float = 30.0  # seconds


@dataclass
class PreviewResult:
    """Result of preview generation"""
    success: bool
    data: Union[bytes, str, Dict[str, Any]]
    format: PreviewFormat
    size_bytes: int
    generation_time: float
    cache_hit: bool
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PreviewEngine:
    """Advanced preview generation engine"""

    # ---- Cache size limits (prevent unbounded memory growth) ----
    _MAX_PREVIEW_CACHE = 200
    _MAX_SAMPLE_DATA_CACHE = 100

    def __init__(self):
        self.pdf_engine = PDFEngine()
        self.variable_resolver = VariableResolver()
        self.exercise_builder = ExerciseTableBuilder()
        self.qr_manager = QRCodeManager()
        
        # Bounded LRU caches
        self.preview_cache: OrderedDict = OrderedDict()
        self.sample_data_cache: OrderedDict = OrderedDict()
        
        # Performance
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.generation_stats = {
            "total_previews": 0,
            "cache_hits": 0,
            "avg_generation_time": 0.0,
            "errors": 0
        }
        
        # Quality settings
        self.quality_settings = self._initialize_quality_settings()
    
    def generate_preview(
        self,
        template_config: Dict[str, Any],
        config: PreviewConfig,
        custom_data: Optional[Dict[str, Any]] = None
    ) -> PreviewResult:
        """Generate template preview"""
        start_time = time.time()
        cache_hit = False
        
        try:
            # Check cache first
            if config.use_cache:
                cached_result = self._get_cached_preview(template_config, config, custom_data)
                if cached_result:
                    cache_hit = True
                    self.generation_stats["cache_hits"] += 1
                    return cached_result
            
            # Generate sample data if needed
            if not custom_data and config.generate_sample_data:
                custom_data = self._generate_sample_data(template_config)
            
            # Validate template
            is_valid, errors = self.pdf_engine.validate_template_structure(template_config)
            if not is_valid:
                return PreviewResult(
                    success=False,
                    data="",
                    format=config.format,
                    size_bytes=0,
                    generation_time=time.time() - start_time,
                    cache_hit=cache_hit,
                    error_message=f"Template validation failed: {'; '.join(errors)}"
                )
            
            # Generate preview based on format
            if config.format == PreviewFormat.PDF:
                result = self._generate_pdf_preview(template_config, config, custom_data)
            elif config.format == PreviewFormat.IMAGE:
                result = self._generate_image_preview(template_config, config, custom_data)
            elif config.format == PreviewFormat.THUMBNAIL:
                result = self._generate_thumbnail_preview(template_config, config, custom_data)
            elif config.format == PreviewFormat.HTML:
                result = self._generate_html_preview(template_config, config, custom_data)
            elif config.format == PreviewFormat.JSON:
                result = self._generate_json_preview(template_config, config, custom_data)
            else:
                result = PreviewResult(
                    success=False,
                    data="",
                    format=config.format,
                    size_bytes=0,
                    generation_time=time.time() - start_time,
                    cache_hit=cache_hit,
                    error_message=f"Unsupported preview format: {config.format}"
                )
            
            # Update generation time
            result.generation_time = time.time() - start_time
            result.cache_hit = cache_hit
            
            # Cache result if successful
            if result.success and config.use_cache:
                self._cache_preview(template_config, config, custom_data, result)
            
            # Update statistics
            self._update_stats(result, cache_hit)
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating preview: {e}")
            
            error_result = PreviewResult(
                success=False,
                data="",
                format=config.format,
                size_bytes=0,
                generation_time=time.time() - start_time,
                cache_hit=cache_hit,
                error_message=f"Preview generation error: {str(e)}"
            )
            
            self._update_stats(error_result, cache_hit)
            return error_result
    
    def generate_preview_async(
        self,
        template_config: Dict[str, Any],
        config: PreviewConfig,
        custom_data: Optional[Dict[str, Any]] = None
    ) -> asyncio.Future:
        """Generate preview asynchronously"""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(
            self.executor,
            self.generate_preview,
            template_config,
            config,
            custom_data
        )
    
    def generate_batch_previews(
        self,
        templates: List[Dict[str, Any]],
        config: PreviewConfig,
        custom_data_list: Optional[List[Dict[str, Any]]] = None
    ) -> List[PreviewResult]:
        """Generate multiple previews in batch"""
        results = []
        
        # Use custom data for each template if provided
        for i, template in enumerate(templates):
            custom_data = custom_data_list[i] if custom_data_list and i < len(custom_data_list) else None
            result = self.generate_preview(template, config, custom_data)
            results.append(result)
        
        return results
    
    def get_preview_analytics(self) -> Dict[str, Any]:
        """Get preview generation analytics"""
        return {
            **self.generation_stats,
            "cache_size": len(self.preview_cache),
            "sample_data_cache_size": len(self.sample_data_cache),
            "cache_hit_rate": (
                self.generation_stats["cache_hits"] / max(1, self.generation_stats["total_previews"]) * 100
            )
        }
    
    def clear_cache(self, template_id: Optional[str] = None):
        """Clear preview cache"""
        if template_id:
            # Clear specific template cache
            keys_to_remove = [k for k in self.preview_cache.keys() if k.startswith(f"{template_id}:")]
            for key in keys_to_remove:
                del self.preview_cache[key]
        else:
            # Clear all cache
            self.preview_cache.clear()
            self.sample_data_cache.clear()
    
    # === Preview Generation Methods ===
    
    def _generate_pdf_preview(
        self,
        template_config: Dict[str, Any],
        config: PreviewConfig,
        custom_data: Optional[Dict[str, Any]]
    ) -> PreviewResult:
        """Generate PDF preview"""
        try:
            # Apply quality settings
            pdf_options = self._get_pdf_options(config.quality)
            
            # Generate PDF
            pdf_bytes = self.pdf_engine.generate_pdf(
                template_config=template_config,
                data=custom_data,
                output_path=None,
                options=pdf_options
            )
            
            # Extract specific page if requested
            if config.page_number > 1:
                pdf_bytes = self._extract_pdf_page(pdf_bytes, config.page_number)
            
            return PreviewResult(
                success=True,
                data=pdf_bytes,
                format=PreviewFormat.PDF,
                size_bytes=len(pdf_bytes),
                generation_time=0.0,  # Will be set by caller
                cache_hit=False,
                metadata={
                    "page_count": self._get_pdf_page_count(pdf_bytes),
                    "quality": config.quality.value
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating PDF preview: {e}")
            return PreviewResult(
                success=False,
                data="",
                format=PreviewFormat.PDF,
                size_bytes=0,
                generation_time=0.0,
                cache_hit=False,
                error_message=str(e)
            )
    
    def _generate_image_preview(
        self,
        template_config: Dict[str, Any],
        config: PreviewConfig,
        custom_data: Optional[Dict[str, Any]]
    ) -> PreviewResult:
        """Generate image preview"""
        try:
            # Generate PDF first
            pdf_result = self._generate_pdf_preview(template_config, config, custom_data)
            if not pdf_result.success:
                return pdf_result
            
            # Convert PDF to image
            image_bytes = self._convert_pdf_to_image(
                pdf_result.data,
                config.page_number,
                config.dpi,
                config.width,
                config.height
            )
            
            return PreviewResult(
                success=True,
                data=image_bytes,
                format=PreviewFormat.IMAGE,
                size_bytes=len(image_bytes),
                generation_time=0.0,
                cache_hit=False,
                metadata={
                    "width": config.width,
                    "height": config.height,
                    "dpi": config.dpi
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating image preview: {e}")
            return PreviewResult(
                success=False,
                data="",
                format=PreviewFormat.IMAGE,
                size_bytes=0,
                generation_time=0.0,
                cache_hit=False,
                error_message=str(e)
            )
    
    def _generate_thumbnail_preview(
        self,
        template_config: Dict[str, Any],
        config: PreviewConfig,
        custom_data: Optional[Dict[str, Any]]
    ) -> PreviewResult:
        """Generate thumbnail preview"""
        try:
            # Use thumbnail-specific settings
            thumb_config = PreviewConfig(
                format=PreviewFormat.IMAGE,
                quality=PreviewQuality.LOW,
                page_number=config.page_number,
                width=config.width or 300,
                height=config.height or 200,
                dpi=72,
                use_cache=config.use_cache,
                cache_ttl=config.cache_ttl,
                generate_sample_data=config.generate_sample_data,
                optimize_for_speed=True
            )
            
            return self._generate_image_preview(template_config, thumb_config, custom_data)
            
        except Exception as e:
            logger.error(f"Error generating thumbnail preview: {e}")
            return PreviewResult(
                success=False,
                data="",
                format=PreviewFormat.THUMBNAIL,
                size_bytes=0,
                generation_time=0.0,
                cache_hit=False,
                error_message=str(e)
            )
    
    def _generate_html_preview(
        self,
        template_config: Dict[str, Any],
        config: PreviewConfig,
        custom_data: Optional[Dict[str, Any]]
    ) -> PreviewResult:
        """Generate HTML preview"""
        try:
            # Create HTML representation
            html_content = self._create_html_representation(template_config, custom_data)
            
            return PreviewResult(
                success=True,
                data=html_content,
                format=PreviewFormat.HTML,
                size_bytes=len(html_content.encode()),
                generation_time=0.0,
                cache_hit=False,
                metadata={
                    "css_included": True,
                    "responsive": True
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating HTML preview: {e}")
            return PreviewResult(
                success=False,
                data="",
                format=PreviewFormat.HTML,
                size_bytes=0,
                generation_time=0.0,
                cache_hit=False,
                error_message=str(e)
            )
    
    def _generate_json_preview(
        self,
        template_config: Dict[str, Any],
        config: PreviewConfig,
        custom_data: Optional[Dict[str, Any]]
    ) -> PreviewResult:
        """Generate JSON preview (template data and resolved variables)"""
        try:
            # Resolve variables
            context = VariableContext(
                template_data=custom_data or {},
                user_data=custom_data.get("usuario") if custom_data else None,
                gym_data=custom_data.get("gimnasio") if custom_data else None,
                routine_data=custom_data.get("rutina") if custom_data else None,
                exercise_data=custom_data.get("dias") if custom_data else None
            )
            
            resolved_data = self.variable_resolver.resolve_variables(template_config, context)
            
            # Create preview data
            preview_data = {
                "template_config": template_config,
                "resolved_variables": resolved_data,
                "sample_data": custom_data,
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "quality": config.quality.value,
                    "page_number": config.page_number
                }
            }
            
            json_content = json.dumps(preview_data, indent=2, default=str)
            
            return PreviewResult(
                success=True,
                data=json_content,
                format=PreviewFormat.JSON,
                size_bytes=len(json_content.encode()),
                generation_time=0.0,
                cache_hit=False,
                metadata={
                    "variable_count": len(resolved_data),
                    "data_size": len(json_content)
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating JSON preview: {e}")
            return PreviewResult(
                success=False,
                data="",
                format=PreviewFormat.JSON,
                size_bytes=0,
                generation_time=0.0,
                cache_hit=False,
                error_message=str(e)
            )
    
    # === Sample Data Generation ===
    
    def _generate_sample_data(self, template_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate realistic sample data for preview"""
        # Check cache first
        template_hash = self._get_template_hash(template_config)
        if template_hash in self.sample_data_cache:
            return self.sample_data_cache[template_hash]
        
        # Generate sample data based on template requirements
        variables = template_config.get("variables", {})
        
        sample_data = {
            "nombre_rutina": "Rutina de Ejemplo Premium",
            "descripcion": "Esta es una rutina de ejemplo generada automáticamente para previsualización",
            "dias_semana": 4,
            "current_week": 1,
            "uuid_rutina": "preview-" + hashlib.sha256(template_hash.encode()).hexdigest()[:12],
            "fecha_creacion": datetime.now(),
            "categoria": template_config.get("metadata", {}).get("category", "general"),
        }
        total_weeks = template_config.get("total_weeks") or template_config.get("metadata", {}).get("total_weeks") or 4
        try:
            total_weeks = int(total_weeks)
        except Exception:
            total_weeks = 4
        sample_data["total_weeks"] = total_weeks
        sample_data["fecha"] = datetime.now().strftime("%d/%m/%Y")
        sample_data["current_year"] = datetime.now().strftime("%Y")
        sample_data["gym_logo_base64"] = ""
        
        # Add user data if required
        if any(var.get("type") == "user_data" for var in variables.values()):
            sample_data["usuario"] = {
                "id": 123,
                "nombre": "Juan",
                "apellido": "Pérez",
                "email": "juan.perez@ejemplo.com",
                "telefono": "+54 11 1234-5678",
                "fecha_nacimiento": "1990-01-01",
                "objetivo": "Hipertrofia",
                "nivel": "Intermedio"
            }
        
        # Add gym data if required
        if any(var.get("type") == "gym_data" for var in variables.values()):
            sample_data["gimnasio"] = {
                "id": 1,
                "nombre": "IronHub Gym",
                "direccion": "Av. Corrientes 1000, Buenos Aires",
                "telefono": "+54 11 5555-1234",
                "email": "info@ironhub.com",
                "logo_url": "/static/images/gym-logo.png"
            }
        
        # Add exercise data based on template structure
        sample_data["dias"] = self._generate_sample_exercises(template_config)
        
        # Add calculated variables
        for var_name, var_config in variables.items():
            if var_config.get("type") == "calculated":
                calculation = var_config.get("calculation", "")
                if "total_exercises" in calculation:
                    total_exercises = sum(len(day.get("ejercicios", [])) for day in sample_data["dias"])
                    sample_data[var_name] = total_exercises
                elif "total_days" in calculation:
                    sample_data[var_name] = len(sample_data["dias"])
                elif "current_date" in calculation:
                    sample_data[var_name] = datetime.now().strftime("%d/%m/%Y")
        
        # Cache result (bounded)
        self.sample_data_cache[template_hash] = sample_data
        while len(self.sample_data_cache) > self._MAX_SAMPLE_DATA_CACHE:
            self.sample_data_cache.popitem(last=False)
        
        return sample_data
    
    def _generate_sample_exercises(self, template_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate sample exercise data"""
        # Determine number of days from template
        dias_semana = template_config.get("dias_semana", 4)
        
        # Sample exercises by day
        exercise_database = [
            {
                "nombre": "Sentadillas con barra",
                "series": 4,
                "repeticiones": "12,10,8,6",
                "descanso": "90s",
                "peso_kg": "60,65,70,75",
                "notas": "Mantener la espalda recta",
                "grupo_muscular": "Piernas",
                "equipamiento": "Barra"
            },
            {
                "nombre": "Press de banca plano",
                "series": 3,
                "repeticiones": "10,8,6",
                "descanso": "120s",
                "peso_kg": "50,55,60",
                "notas": "Controlar el descenso",
                "grupo_muscular": "Pecho",
                "equipamiento": "Barra"
            },
            {
                "nombre": "Dominadas",
                "series": 3,
                "repeticiones": "8,6,4",
                "descanso": "120s",
                "notas": "Completa el rango de movimiento",
                "grupo_muscular": "Espalda",
                "equipamiento": "Barra fija"
            },
            {
                "nombre": "Curl de bíceps con mancuernas",
                "series": 3,
                "repeticiones": "12,10,8",
                "descanso": "60s",
                "peso_kg": "10,12,15",
                "notas": "Sin balanceo",
                "grupo_muscular": "Brazos",
                "equipamiento": "Mancuernas"
            },
            {
                "nombre": "Zancadas",
                "series": 3,
                "repeticiones": "10,10,10",
                "descanso": "60s",
                "peso_kg": "10,10,10",
                "notas": "Mantener el equilibrio",
                "grupo_muscular": "Piernas",
                "equipamiento": "Mancuernas"
            },
            {
                "nombre": "Remo con mancuernas",
                "series": 3,
                "repeticiones": "12,10,8",
                "descanso": "90s",
                "peso_kg": "15,17.5,20",
                "notas": "Contraer la espalda",
                "grupo_muscular": "Espalda",
                "equipamiento": "Mancuernas"
            }
        ]
        
        # Generate days
        dias = []
        for day_num in range(1, dias_semana + 1):
            # Select 2-3 exercises for this day
            exercises_per_day = min(3, len(exercise_database))
            day_exercises = []
            
            for i in range(exercises_per_day):
                exercise_idx = (day_num - 1 + i) % len(exercise_database)
                exercise = exercise_database[exercise_idx].copy()
                exercise["orden"] = i + 1
                exercise["dia_semana"] = day_num
                day_exercises.append(exercise)
            
            dias.append({
                "numero": day_num,
                "nombre": f"Día {day_num}",
                "ejercicios": day_exercises
            })
        
        return dias
    
    # === Caching Methods ===
    
    def _get_cached_preview(
        self,
        template_config: Dict[str, Any],
        config: PreviewConfig,
        custom_data: Optional[Dict[str, Any]]
    ) -> Optional[PreviewResult]:
        """Get cached preview"""
        cache_key = self._get_cache_key(template_config, config, custom_data)
        
        if cache_key in self.preview_cache:
            cached_item = self.preview_cache[cache_key]
            
            # Check TTL
            if datetime.now() - cached_item["timestamp"] < timedelta(seconds=config.cache_ttl):
                return cached_item["result"]
            else:
                # Remove expired cache
                del self.preview_cache[cache_key]
        
        return None
    
    def _cache_preview(
        self,
        template_config: Dict[str, Any],
        config: PreviewConfig,
        custom_data: Optional[Dict[str, Any]],
        result: PreviewResult
    ):
        """Cache preview result (bounded LRU)"""
        cache_key = self._get_cache_key(template_config, config, custom_data)
        
        self.preview_cache[cache_key] = {
            "result": result,
            "timestamp": datetime.now()
        }
        # Move to end (most recently used)
        self.preview_cache.move_to_end(cache_key)
        
        # Evict oldest entries beyond limit
        while len(self.preview_cache) > self._MAX_PREVIEW_CACHE:
            self.preview_cache.popitem(last=False)
    
    def _get_cache_key(
        self,
        template_config: Dict[str, Any],
        config: PreviewConfig,
        custom_data: Optional[Dict[str, Any]]
    ) -> str:
        """Generate cache key"""
        template_hash = self._get_template_hash(template_config)
        config_hash = hashlib.sha256(
            f"{config.format.value}{config.quality.value}{config.page_number}{config.dpi}".encode()
        ).hexdigest()
        
        if custom_data:
            data_hash = hashlib.sha256(
                json.dumps(custom_data, sort_keys=True, default=str).encode()
            ).hexdigest()
            return f"{template_hash}:{config_hash}:{data_hash}"
        else:
            return f"{template_hash}:{config_hash}"
    
    def _get_template_hash(self, template_config: Dict[str, Any]) -> str:
        """Get template hash for caching"""
        template_str = json.dumps(template_config, sort_keys=True, default=str)
        return hashlib.sha256(template_str.encode()).hexdigest()
    
    # === Utility Methods ===
    
    def _initialize_quality_settings(self) -> Dict[PreviewQuality, Dict[str, Any]]:
        """Initialize quality settings"""
        return {
            PreviewQuality.LOW: {
                "dpi": 72,
                "compression": 6,
                "optimize": True
            },
            PreviewQuality.MEDIUM: {
                "dpi": 150,
                "compression": 4,
                "optimize": True
            },
            PreviewQuality.HIGH: {
                "dpi": 300,
                "compression": 2,
                "optimize": False
            },
            PreviewQuality.ULTRA: {
                "dpi": 600,
                "compression": 0,
                "optimize": False
            }
        }
    
    def _get_pdf_options(self, quality: PreviewQuality) -> Dict[str, Any]:
        """Get PDF generation options based on quality"""
        settings = self.quality_settings[quality]
        return {
            "compress": settings["compression"] > 0,
            "compression_level": settings["compression"],
            "optimize": settings["optimize"]
        }
    
    def _extract_pdf_page(self, pdf_bytes: bytes, page_number: int) -> bytes:
        """Extract specific page from PDF"""
        # This is a simplified implementation
        # In production, you'd use a proper PDF library like PyPDF2
        return pdf_bytes
    
    def _get_pdf_page_count(self, pdf_bytes: bytes) -> int:
        """Get number of pages in PDF"""
        # This is a simplified implementation
        # In production, you'd use a proper PDF library
        return 1
    
    def _convert_pdf_to_image(
        self,
        pdf_bytes: bytes,
        page_number: int,
        dpi: int,
        width: Optional[int],
        height: Optional[int]
    ) -> bytes:
        """Convert PDF page to image"""
        try:
            import pypdfium2 as pdfium
        except Exception as e:
            raise RuntimeError("pypdfium2 no está disponible para convertir PDF a imagen") from e

        if not isinstance(pdf_bytes, (bytes, bytearray)):
            raise TypeError("pdf_bytes debe ser bytes")

        page_idx = max(0, int(page_number) - 1)
        pdf = pdfium.PdfDocument(pdf_bytes)
        if page_idx >= len(pdf):
            page_idx = 0

        page = pdf.get_page(page_idx)
        try:
            scale = max(0.5, float(dpi) / 72.0)
        except Exception:
            scale = 2.0
        bitmap = page.render(scale=scale)
        pil_image = bitmap.to_pil()

        if width and height:
            try:
                pil_image = pil_image.resize((int(width), int(height)))
            except Exception:
                pass

        out = io.BytesIO()
        pil_image.save(out, format="PNG")
        return out.getvalue()
    
    def _create_html_representation(
        self,
        template_config: Dict[str, Any],
        custom_data: Optional[Dict[str, Any]]
    ) -> str:
        """Create HTML representation of template"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Template Preview</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { text-align: center; border-bottom: 2px solid #333; padding: 20px; }
                .content { margin: 20px 0; }
                .exercise-table { width: 100%; border-collapse: collapse; }
                .exercise-table th, .exercise-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                .exercise-table th { background-color: #f2f2f2; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{nombre_rutina}</h1>
                <p>{descripcion}</p>
            </div>
            <div class="content">
                <h2>Ejercicios</h2>
                {exercise_tables}
            </div>
        </body>
        </html>
        """
        
        # Replace variables
        if custom_data:
            html = html.format(
                nombre_rutina=custom_data.get("nombre_rutina", "Rutina"),
                descripcion=custom_data.get("descripcion", ""),
                exercise_tables=self._generate_html_exercise_tables(custom_data.get("dias", []))
            )
        
        return html
    
    def _generate_html_exercise_tables(self, dias: List[Dict[str, Any]]) -> str:
        """Generate HTML exercise tables"""
        html = ""
        
        for dia in dias:
            dia_nombre = dia.get('nombre', f'Día {dia.get("numero", "")}')
            html += f"<h3>{dia_nombre}</h3>"
            html += "<table class='exercise-table'>"
            html += "<tr><th>Ejercicio</th><th>Series</th><th>Repeticiones</th><th>Descanso</th><th>Notas</th></tr>"
            
            for ejercicio in dia.get("ejercicios", []):
                html += f"""
                <tr>
                    <td>{ejercicio.get('nombre', '')}</td>
                    <td>{ejercicio.get('series', '')}</td>
                    <td>{ejercicio.get('repeticiones', '')}</td>
                    <td>{ejercicio.get('descanso', '')}</td>
                    <td>{ejercicio.get('notas', '')}</td>
                </tr>
                """
            
            html += "</table>"
        
        return html
    
    def _update_stats(self, result: PreviewResult, cache_hit: bool):
        """Update generation statistics"""
        self.generation_stats["total_previews"] += 1
        
        if not result.success:
            self.generation_stats["errors"] += 1
        
        # Update average generation time
        current_avg = self.generation_stats["avg_generation_time"]
        total = self.generation_stats["total_previews"]
        self.generation_stats["avg_generation_time"] = (
            (current_avg * (total - 1) + result.generation_time) / total
        )


# Export main classes
__all__ = [
    "PreviewEngine",
    "PreviewConfig",
    "PreviewResult",
    "PreviewFormat",
    "PreviewQuality"
]
