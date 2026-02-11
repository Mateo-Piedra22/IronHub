"""
PDF Engine Core

This module provides the core PDF generation engine for dynamic routine templates,
including variable resolution, exercise table building, QR code management, and preview generation.
"""

import io
import os
import base64
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime
import logging

# PDF generation libraries
from reportlab.lib.pagesizes import letter, A4, legal, landscape
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import black, grey, lightgrey, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
)
from reportlab.lib.utils import ImageReader

# Image processing
import qrcode

# Template processing
from jinja2 import BaseLoader, StrictUndefined, TemplateError
from jinja2.sandbox import SandboxedEnvironment

logger = logging.getLogger(__name__)

_ASSETS_ROOT = (Path(__file__).resolve().parents[2] / "assets").resolve()
_MAX_IMAGE_BYTES = int(os.environ.get("PDF_MAX_IMAGE_BYTES", "600000"))


class PDFEngine:
    """Core PDF generation engine for dynamic routine templates"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.custom_styles = self._create_custom_styles()
        self.jinja_env = SandboxedEnvironment(
            loader=BaseLoader(),
            undefined=StrictUndefined,
            autoescape=False,
        )
        self._compiled_templates: Dict[str, Any] = {}
        self._max_compiled_templates = int(os.environ.get("PDF_MAX_COMPILED_TEMPLATES", "500"))
        
    def generate_pdf(
        self,
        template_config: Dict[str, Any],
        data: Dict[str, Any],
        output_path: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Union[str, bytes]:
        """Generate PDF from template and data"""
        try:
            # Parse template configuration
            layout = template_config.get("layout", {})
            pages = template_config.get("pages", [])
            variables = template_config.get("variables", {})
            qr_config = template_config.get("qr_code", {})
            styling = template_config.get("styling", {})
            
            # Resolve variables
            resolved_data = self._resolve_variables(data, variables)

            page_size = self._get_page_size(layout.get("page_size", "A4"))
            if str(layout.get("orientation", "portrait")).strip().lower() == "landscape":
                page_size = landscape(page_size)

            margins = layout.get("margins", {}) or {}
            right_margin = self._to_points(margins.get("right", 20))
            left_margin = self._to_points(margins.get("left", 20))
            top_margin = self._to_points(margins.get("top", 20))
            bottom_margin = self._to_points(margins.get("bottom", 20))
            
            qr_position = str((qr_config or {}).get("position") or "inline").strip().lower()
            if qr_position in ("separate_sheet", "sheet"):
                qr_position = "separate"

            qr_overlay_reader: Optional[ImageReader] = None
            qr_overlay_w = 0.0
            qr_overlay_h = 0.0
            if (qr_config or {}).get("enabled", False) and qr_position in ("header", "footer"):
                qr_data = self._get_qr_code_data(resolved_data, qr_config or {})
                if qr_data:
                    try:
                        size_cfg = (qr_config or {}).get("size") or {}
                        if not isinstance(size_cfg, dict):
                            size_cfg = {}
                        qr_overlay_w = self._to_points(size_cfg.get("width", 40))
                        qr_overlay_h = self._to_points(size_cfg.get("height", 40))
                        qr_overlay_reader = self._build_qr_image_reader(qr_data)
                    except Exception:
                        qr_overlay_reader = None

            def _draw_qr_overlay(canvas, doc) -> None:
                try:
                    if qr_overlay_reader is None:
                        return
                    if qr_position not in ("header", "footer"):
                        return
                    if qr_overlay_w <= 0 or qr_overlay_h <= 0:
                        return
                    x = float(doc.pagesize[0]) - float(doc.rightMargin) - float(qr_overlay_w)
                    if qr_position == "header":
                        y = float(doc.height) + float(doc.bottomMargin) + max(
                            0.0, (float(doc.topMargin) - float(qr_overlay_h)) / 2.0
                        )
                    else:
                        y = max(0.0, (float(doc.bottomMargin) - float(qr_overlay_h)) / 2.0)
                    canvas.drawImage(
                        qr_overlay_reader,
                        x,
                        y,
                        width=qr_overlay_w,
                        height=qr_overlay_h,
                        preserveAspectRatio=True,
                        mask="auto",
                    )
                except Exception:
                    return

            # Create PDF document
            if output_path:
                # Save to file
                doc = SimpleDocTemplate(
                    output_path,
                    pagesize=page_size,
                    rightMargin=right_margin,
                    leftMargin=left_margin,
                    topMargin=top_margin,
                    bottomMargin=bottom_margin,
                )
                
                # Build document
                story = self._build_story(pages, resolved_data, qr_config, styling)
                if qr_overlay_reader is not None:
                    doc.build(story, onFirstPage=_draw_qr_overlay, onLaterPages=_draw_qr_overlay)
                else:
                    doc.build(story)
                
                return output_path
            else:
                # Return as bytes
                buffer = io.BytesIO()
                doc = SimpleDocTemplate(
                    buffer,
                    pagesize=page_size,
                    rightMargin=right_margin,
                    leftMargin=left_margin,
                    topMargin=top_margin,
                    bottomMargin=bottom_margin,
                )
                
                story = self._build_story(pages, resolved_data, qr_config, styling)
                if qr_overlay_reader is not None:
                    doc.build(story, onFirstPage=_draw_qr_overlay, onLaterPages=_draw_qr_overlay)
                else:
                    doc.build(story)
                
                buffer.seek(0)
                return buffer.getvalue()
                
        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            raise
    
    def generate_preview(
        self,
        template_config: Dict[str, Any],
        sample_data: Optional[Dict[str, Any]] = None,
        page_number: int = 1
    ) -> bytes:
        """Generate preview of specific page"""
        try:
            # Use sample data if not provided
            if not sample_data:
                sample_data = self._generate_sample_data(template_config)
            
            # Generate full PDF first
            pdf_bytes = self.generate_pdf(template_config, sample_data)
            
            # Extract specific page (simplified approach)
            # In production, you might want to use more sophisticated page extraction
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Error generating preview: {e}")
            raise
    
    def validate_template_structure(self, template_config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate template structure for PDF generation"""
        errors = []
        
        # Check required sections
        if "layout" not in template_config:
            errors.append("Missing 'layout' section")
        
        if "pages" not in template_config:
            errors.append("Missing 'pages' section")
        elif not template_config["pages"]:
            errors.append("Pages section cannot be empty")
        
        # Validate layout
        layout = template_config.get("layout", {})
        if layout:
            if "page_size" in layout and layout["page_size"] not in ["A4", "Letter", "Legal"]:
                errors.append(f"Invalid page size: {layout['page_size']}")
            
            if "orientation" in layout and layout["orientation"] not in ["portrait", "landscape"]:
                errors.append(f"Invalid orientation: {layout['orientation']}")
        
        # Validate pages
        pages = template_config.get("pages", [])
        for i, page in enumerate(pages):
            if "sections" not in page:
                errors.append(f"Page {i+1} missing 'sections'")
            elif not page["sections"]:
                errors.append(f"Page {i+1} sections cannot be empty")
        
        return len(errors) == 0, errors
    
    # === Private Methods ===
    
    def _create_custom_styles(self) -> Dict[str, ParagraphStyle]:
        """Create custom paragraph styles"""
        styles = {}
        
        # Title style
        styles["title"] = ParagraphStyle(
            "CustomTitle",
            parent=self.styles["Title"],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=black
        )
        
        # Subtitle style
        styles["subtitle"] = ParagraphStyle(
            "CustomSubtitle",
            parent=self.styles["Heading2"],
            fontSize=18,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=black
        )
        
        # Header style
        styles["header"] = ParagraphStyle(
            "CustomHeader",
            parent=self.styles["Heading3"],
            fontSize=14,
            spaceAfter=12,
            alignment=TA_LEFT,
            textColor=black
        )
        
        # Body style
        styles["body"] = ParagraphStyle(
            "CustomBody",
            parent=self.styles["Normal"],
            fontSize=11,
            spaceAfter=6,
            alignment=TA_JUSTIFY,
            textColor=black
        )
        
        # Small style
        styles["small"] = ParagraphStyle(
            "CustomSmall",
            parent=self.styles["Normal"],
            fontSize=9,
            spaceAfter=3,
            alignment=TA_LEFT,
            textColor=grey
        )
        
        return styles
    
    def _get_page_size(self, size_name: str) -> Tuple[float, float]:
        """Get page size by name"""
        sizes = {
            "A4": A4,
            "Letter": letter,
            "Legal": legal
        }
        return sizes.get(size_name, A4)

    def _to_points(self, v: Any) -> float:
        try:
            num = float(v)
        except Exception:
            return float(20 * mm)
        if 0 <= num <= 50:
            return float(num * mm)
        return float(num)
    
    def _resolve_variables(
        self,
        data: Dict[str, Any],
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve template variables with data"""
        resolved = data.copy()
        
        # Process each variable definition
        for var_name, var_config in variables.items():
            var_type = var_config.get("type", "string")
            
            if var_type == "calculated":
                # Handle calculated variables
                resolved[var_name] = self._calculate_variable(var_name, var_config, resolved)
            elif var_type == "user_data":
                # Handle user data variables
                resolved[var_name] = self._get_user_data(var_name, var_config, resolved)
            elif var_type == "gym_data":
                # Handle gym data variables
                resolved[var_name] = self._get_gym_data(var_name, var_config, resolved)
            elif var_name not in resolved:
                # Use default value if available
                resolved[var_name] = var_config.get("default", "")
        
        return resolved
    
    def _calculate_variable(
        self,
        var_name: str,
        var_config: Dict[str, Any],
        data: Dict[str, Any]
    ) -> Any:
        """Calculate variable value"""
        # This is a simplified implementation
        # In production, you'd want a more sophisticated expression parser
        
        calculation = var_config.get("calculation", "")
        
        # Handle common calculations
        if "total_exercises" in calculation.lower():
            if "dias" in data:
                total = sum(len(day.get("ejercicios", [])) for day in data["dias"])
                return total
        
        if "total_days" in calculation.lower():
            return len(data.get("dias", []))
        
        if "current_date" in calculation.lower():
            return datetime.now().strftime("%d/%m/%Y")
        
        return ""
    
    def _get_user_data(
        self,
        var_name: str,
        var_config: Dict[str, Any],
        data: Dict[str, Any]
    ) -> Any:
        """Get user data variable"""
        user_data = data.get("usuario", {})
        field_path = var_config.get("field", var_name)
        
        # Navigate nested fields (e.g., "perfil.nombre")
        parts = field_path.split(".")
        value = user_data
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                value = ""
                break
        
        return value
    
    def _get_gym_data(
        self,
        var_name: str,
        var_config: Dict[str, Any],
        data: Dict[str, Any]
    ) -> Any:
        """Get gym data variable"""
        gym_data = data.get("gimnasio", {})
        field_path = var_config.get("field", var_name)
        
        # Navigate nested fields
        parts = field_path.split(".")
        value = gym_data
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                value = ""
                break
        
        return value
    
    def _build_story(
        self,
        pages: List[Dict[str, Any]],
        data: Dict[str, Any],
        qr_config: Dict[str, Any],
        styling: Dict[str, Any]
    ) -> List[Any]:
        """Build story for PDF document"""
        story = []
        
        for i, page in enumerate(pages):
            # Add page content
            for section in page.get("sections", []):
                section_content = self._build_section(section, data, qr_config, styling)
                if section_content:
                    story.extend(section_content)
            
            # Add page break except for last page
            if i < len(pages) - 1:
                story.append(PageBreak())
        
        return story
    
    def _build_section(
        self,
        section: Dict[str, Any],
        data: Dict[str, Any],
        qr_config: Dict[str, Any],
        styling: Dict[str, Any]
    ) -> List[Any]:
        """Build section content"""
        section_type = section.get("type")
        content = section.get("content", {})
        
        # Check conditional rendering
        conditional = section.get("conditional")
        if conditional and not self._evaluate_condition(conditional, data):
            return []
        
        if section_type == "header":
            return self._build_header_section(content, data, styling)
        elif section_type == "text":
            return self._build_text_section(content, data, styling)
        elif section_type == "table":
            return self._build_table_section(content, data, styling)
        elif section_type == "exercise_table":
            return self._build_exercise_table_section(content, data, styling)
        elif section_type == "image":
            return self._build_image_section(content, data, styling)
        elif section_type == "qr_code":
            return self._build_qr_code_section(content, data, qr_config, styling)
        elif section_type == "spacing":
            return self._build_spacing_section(content)
        else:
            logger.warning(f"Unknown section type: {section_type}")
            return []
    
    def _evaluate_condition(self, conditional: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Evaluate conditional rendering"""
        condition = conditional.get("if", "")
        show = conditional.get("show", True)
        
        # Simple condition evaluation (can be enhanced)
        if "has_exercises" in condition.lower():
            return bool(data.get("dias") and any(day.get("ejercicios") for day in data["dias"]))
        
        if "user_assigned" in condition.lower():
            return bool(data.get("usuario"))
        
        return show
    
    def _build_header_section(
        self,
        content: Dict[str, Any],
        data: Dict[str, Any],
        styling: Dict[str, Any]
    ) -> List[Any]:
        """Build header section"""
        elements = []
        
        title = content.get("title", "{{nombre_rutina}}")
        subtitle = content.get("subtitle", "")
        
        # Process template variables
        title = self._process_template_string(title, data)
        subtitle = self._process_template_string(subtitle, data)
        
        # Add title
        if title:
            elements.append(Paragraph(title, self.custom_styles["title"]))
        
        # Add subtitle
        if subtitle:
            elements.append(Paragraph(subtitle, self.custom_styles["subtitle"]))
        
        # Add spacing
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _build_text_section(
        self,
        content: Dict[str, Any],
        data: Dict[str, Any],
        styling: Dict[str, Any]
    ) -> List[Any]:
        """Build text section"""
        elements = []
        
        text = content.get("text", "")
        style_name = content.get("style", "body")
        
        # Process template variables
        text = self._process_template_string(text, data)
        
        # Get style
        style = self.custom_styles.get(style_name, self.custom_styles["body"])
        
        # Add paragraph
        if text:
            elements.append(Paragraph(text, style))
        
        return elements
    
    def _build_table_section(
        self,
        content: Dict[str, Any],
        data: Dict[str, Any],
        styling: Dict[str, Any]
    ) -> List[Any]:
        """Build generic table section"""
        elements = []
        
        headers = content.get("headers", [])
        rows = content.get("rows", [])
        
        # Process template variables in headers and rows
        processed_headers = [self._process_template_string(str(h), data) for h in headers]
        processed_rows = []
        
        for row in rows:
            processed_row = [self._process_template_string(str(cell), data) for cell in row]
            processed_rows.append(processed_row)
        
        # Create table
        if processed_headers and processed_rows:
            table_data = [processed_headers] + processed_rows
            table = Table(table_data)
            
            # Add style
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), white),
                ('GRID', (0, 0), (-1, -1), 1, black)
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 12))
        
        return elements
    
    def _build_exercise_table_section(
        self,
        content: Dict[str, Any],
        data: Dict[str, Any],
        styling: Dict[str, Any]
    ) -> List[Any]:
        """Build exercise table section"""
        elements = []
        
        # Get exercise data
        dias = data.get("dias", [])
        current_week = data.get("current_week", 1)
        
        if not dias:
            return elements
        
        # Build exercise table
        for dia in dias:
            dia_num = dia.get("numero", 1)
            ejercicios = dia.get("ejercicios", [])
            
            if not ejercicios:
                continue
            
            # Day header
            elements.append(Paragraph(f"Día {dia_num}", self.custom_styles["header"]))
            
            # Exercise table headers
            headers = ["Ejercicio", "Series", "Repeticiones", "Descanso", "Notas"]
            
            # Exercise table rows
            rows = []
            for ejercicio in ejercicios:
                row = [
                    ejercicio.get("nombre", ""),
                    str(ejercicio.get("series", "")),
                    self._get_weekly_value(ejercicio.get("repeticiones", ""), current_week),
                    str(ejercicio.get("descanso", "")),
                    ejercicio.get("notas", "")
                ]
                rows.append(row)
            
            # Create table
            table_data = [headers] + rows
            table = Table(table_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1*inch, 2*inch])
            
            # Style table
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), white),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 20))
        
        return elements
    
    def _build_image_section(
        self,
        content: Dict[str, Any],
        data: Dict[str, Any],
        styling: Dict[str, Any]
    ) -> List[Any]:
        """Build image section"""
        elements = []
        
        image_path = content.get("path", "")
        width = content.get("width", 2*inch)
        height = content.get("height", 2*inch)
        
        # Process template variables in path
        image_path = self._process_template_string(image_path, data)
        
        if not image_path:
            return elements

        # data URI support (safer than filesystem access)
        if image_path.startswith("data:image/"):
            try:
                if "," not in image_path:
                    return elements
                header, b64 = image_path.split(",", 1)
                raw = base64.b64decode(b64, validate=True)
                if len(raw) > _MAX_IMAGE_BYTES:
                    return elements
                reader = ImageReader(io.BytesIO(raw))
                img = Image(reader, width=width, height=height)
                elements.append(img)
                elements.append(Spacer(1, 12))
                return elements
            except Exception:
                return elements

        # Restrict filesystem reads to assets directory only
        try:
            p = Path(image_path)
            if p.is_absolute():
                return elements
            candidate = (_ASSETS_ROOT / p).resolve()
            if _ASSETS_ROOT not in candidate.parents and candidate != _ASSETS_ROOT:
                return elements
            if not candidate.exists() or not candidate.is_file():
                return elements
            img = Image(str(candidate), width=width, height=height)
            elements.append(img)
            elements.append(Spacer(1, 12))
        except Exception as e:
            logger.warning(f"Could not load image {image_path}: {e}")
        
        return elements
    
    def _build_qr_code_section(
        self,
        content: Dict[str, Any],
        data: Dict[str, Any],
        qr_config: Dict[str, Any],
        styling: Dict[str, Any]
    ) -> List[Any]:
        """Build QR code section"""
        elements = []

        pos = str((qr_config or {}).get("position") or "inline").strip().lower()
        if pos in ("separate_sheet", "sheet"):
            pos = "separate"
        if pos == "none":
            return elements
        if pos in ("header", "footer"):
            return elements
        
        # Get QR code data
        qr_data = self._get_qr_code_data(data, qr_config)
        
        if not qr_data:
            return elements
        
        # QR code size
        size = content.get("size", 1.5*inch)
        
        # Add to document
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Convert to PIL image
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to ReportLab image
            buffer = io.BytesIO()
            qr_img.save(buffer, format="PNG")
            buffer.seek(0)
            
            # Add to document
            qr_image = Image(buffer, width=size, height=size)
            if pos == "separate":
                elements.append(PageBreak())
            elements.append(qr_image)
            elements.append(Spacer(1, 12))
            
        except Exception as e:
            logger.warning(f"Could not generate QR code: {e}")
        
        return elements

    def _build_qr_image_reader(self, qr_data: str) -> ImageReader:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        qr_img.save(buffer, format="PNG")
        buffer.seek(0)
        return ImageReader(buffer)
    
    def _build_spacing_section(self, content: Dict[str, Any]) -> List[Any]:
        """Build spacing section"""
        height = content.get("height", 20)
        return [Spacer(1, height)]
    
    def _process_template_string(self, template_str: str, data: Dict[str, Any]) -> str:
        """Process template string with variables"""
        if not template_str:
            return ""
        
        try:
            s = str(template_str)
            if "{%" in s or "{#" in s:
                raise TemplateError("Solo se permiten expresiones {{ ... }}")
            if "__" in s or "import" in s.lower():
                raise TemplateError("Expresión no permitida")
            template = self._compiled_templates.get(s)
            if template is None:
                if self._max_compiled_templates > 0 and len(self._compiled_templates) >= self._max_compiled_templates:
                    try:
                        self._compiled_templates.pop(next(iter(self._compiled_templates)))
                    except Exception:
                        self._compiled_templates = {}
                template = self.jinja_env.from_string(s)
                self._compiled_templates[s] = template
            return str(template.render(**data))
        except TemplateError:
            # Fallback to simple variable replacement
            result = template_str
            for key, value in data.items():
                result = result.replace(f"{{{{{key}}}}}", str(value))
            return result
    
    def _get_weekly_value(self, value_string: str, week: int) -> str:
        """Get value for specific week from weekly progression string"""
        if not value_string:
            return ""
        
        try:
            # Parse comma-separated values
            values = [v.strip() for v in value_string.split(",")]
            if week <= len(values):
                return values[week - 1]
            else:
                return values[-1] if values else ""
        except:
            return value_string
    
    def _get_qr_code_data(self, data: Dict[str, Any], qr_config: Dict[str, Any]) -> str:
        """Get QR code data"""
        if not qr_config.get("enabled", False):
            return ""
        
        data_source = qr_config.get("data_source", "routine_uuid")
        
        if data_source == "routine_uuid":
            return data.get("uuid_rutina", "")
        elif data_source == "custom_url":
            return qr_config.get("custom_data", "")
        elif data_source == "user_data":
            # Generate user-specific data
            user_id = data.get("usuario", {}).get("id", "")
            routine_id = data.get("rutina_id", "")
            return f"user:{user_id}:routine:{routine_id}"
        
        return ""
    
    def _generate_sample_data(self, template_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate sample data for preview"""
        return {
            "nombre_rutina": "Rutina de Ejemplo",
            "descripcion": "Esta es una rutina de ejemplo para previsualización",
            "dias_semana": 3,
            "current_week": 1,
            "uuid_rutina": "sample-uuid-12345",
            "usuario": {
                "id": 1,
                "nombre": "Usuario Ejemplo",
                "apellido": "Apellido",
                "email": "usuario@ejemplo.com"
            },
            "gimnasio": {
                "id": 1,
                "nombre": "Gimnasio Ejemplo",
                "direccion": "Calle Ejemplo 123",
                "telefono": "+54 11 1234-5678"
            },
            "dias": [
                {
                    "numero": 1,
                    "nombre": "Día 1",
                    "ejercicios": [
                        {
                            "nombre": "Sentadillas",
                            "series": 4,
                            "repeticiones": "12,10,8,6",
                            "descanso": "60s",
                            "notas": "Mantener la espalda recta"
                        },
                        {
                            "nombre": "Press de Banca",
                            "series": 3,
                            "repeticiones": "10,8,6",
                            "descanso": "90s",
                            "notas": "Controlar el descenso"
                        }
                    ]
                },
                {
                    "numero": 2,
                    "nombre": "Día 2",
                    "ejercicios": [
                        {
                            "nombre": "Dominadas",
                            "series": 3,
                            "repeticiones": "8,6,4",
                            "descanso": "120s",
                            "notas": "Completa el rango de movimiento"
                        }
                    ]
                }
            ]
        }


# Export main class
__all__ = ["PDFEngine"]
