"""
PDF Service - Handles PDF generation for templates and routines
Integrates with the dynamic template system to produce professional PDFs
"""

import logging
import io
import base64
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_pdf import PdfPages

logger = logging.getLogger(__name__)

class PDFService:
    """Service for generating PDFs from templates and routines"""
    
    def __init__(self):
        self.output_dir = Path("/tmp/pdf_generation")
        self.output_dir.mkdir(exist_ok=True)
        
        # Default PDF settings
        self.default_settings = {
            "page_size": "A4",
            "orientation": "portrait",
            "margin_top": 20,
            "margin_right": 20,
            "margin_bottom": 20,
            "margin_left": 20,
            "font_family": "Arial",
            "font_size": 12,
            "primary_color": "#000000",
            "secondary_color": "#666666"
        }
    
    def generate_template_preview(
        self,
        template_config: Dict[str, Any],
        request: Dict[str, Any]
    ) -> str:
        """Generate preview URL for template"""
        try:
            # Extract settings from template
            layout = template_config.get("layout", {})
            styling = template_config.get("styling", {})
            
            # Merge with request settings
            settings = {
                **self.default_settings,
                **layout,
                **styling,
                **request
            }
            
            # Generate PDF
            pdf_path = self._create_pdf_from_template(template_config, settings)
            
            # Convert to base64 for URL
            with open(pdf_path, "rb") as f:
                pdf_data = base64.b64encode(f.read()).decode()
            
            # Create data URL
            data_url = f"data:application/pdf;base64,{pdf_data}"
            
            # Clean up temporary file
            pdf_path.unlink()
            
            return data_url
        
        except Exception as e:
            logger.error(f"Error generating template preview: {e}")
            raise
    
    def generate_rutina_preview_with_template(
        self,
        rutina: Any,
        template_config: Dict[str, Any],
        request: Dict[str, Any]
    ) -> str:
        """Generate routine preview using template"""
        try:
            # Create enhanced template config with routine data
            enhanced_config = self._merge_rutina_with_template(rutina, template_config)
            
            # Generate preview
            return self.generate_template_preview(enhanced_config, request)
        
        except Exception as e:
            logger.error(f"Error generating routine preview with template: {e}")
            raise
    
    def export_rutina_with_template(
        self,
        rutina: Any,
        template_id: int,
        template_config: Dict[str, Any],
        request: Dict[str, Any]
    ) -> str:
        """Export routine with template (full quality)"""
        try:
            # Use high quality settings for export
            export_settings = {
                **request,
                "quality": "high",
                "multi_page": True,
                "show_metadata": True,
                "show_watermark": False
            }
            
            # Create enhanced config
            enhanced_config = self._merge_rutina_with_template(rutina, template_config)
            
            # Generate high-quality PDF
            pdf_path = self._create_pdf_from_template(enhanced_config, export_settings)
            
            # Return file path for download
            return str(pdf_path)
        
        except Exception as e:
            logger.error(f"Error exporting routine with template: {e}")
            raise
    
    def _create_pdf_from_template(
        self,
        template_config: Dict[str, Any],
        settings: Dict[str, Any]
    ) -> Path:
        """Create PDF from template configuration"""
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"template_preview_{timestamp}.pdf"
            pdf_path = self.output_dir / filename
            
            # Create PDF
            with PdfPages(pdf_path) as pdf:
                # Process each section
                sections = template_config.get("sections", [])
                
                for section in sections:
                    section_type = section.get("type")
                    
                    if section_type == "header":
                        self._render_header_section(pdf, section, settings)
                    elif section_type == "exercise_table":
                        self._render_exercise_table_section(pdf, section, settings)
                    elif section_type == "footer":
                        self._render_footer_section(pdf, section, settings)
                    elif section_type == "info_box":
                        self._render_info_box_section(pdf, section, settings)
                    elif section_type == "image":
                        self._render_image_section(pdf, section, settings)
                    elif section_type == "text":
                        self._render_text_section(pdf, section, settings)
            
            return pdf_path
        
        except Exception as e:
            logger.error(f"Error creating PDF from template: {e}")
            raise
    
    def _merge_rutina_with_template(self, rutina: Any, template_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge routine data with template configuration"""
        try:
            enhanced_config = template_config.copy()
            
            # Update metadata with routine info
            metadata = enhanced_config.get("metadata", {})
            metadata["rutina_name"] = getattr(rutina, "nombre", "Rutina")
            metadata["client_name"] = getattr(rutina, "usuario_nombre", "Cliente")
            metadata["creation_date"] = datetime.now().strftime("%d/%m/%Y")
            enhanced_config["metadata"] = metadata
            
            # Update sections with routine exercises
            sections = enhanced_config.get("sections", [])
            for section in sections:
                if section.get("type") == "exercise_table":
                    # Get exercises from routine
                    exercises = self._extract_exercises_from_rutina(rutina)
                    section["content"]["exercises"] = exercises
            
            return enhanced_config
        
        except Exception as e:
            logger.error(f"Error merging routine with template: {e}")
            return template_config
    
    def _extract_exercises_from_rutina(self, rutina: Any) -> List[Dict[str, Any]]:
        """Extract exercises from routine object"""
        exercises = []
        
        try:
            dias = getattr(rutina, "dias", [])
            for dia_idx, dia in enumerate(dias):
                ejercicios = getattr(dia, "ejercicios", [])
                for ejercicio in ejercicios:
                    exercise_data = {
                        "name": getattr(ejercicio, "ejercicio", {}).get("nombre", "Ejercicio"),
                        "sets": getattr(ejercicio, "series", 1),
                        "reps": getattr(ejercicio, "repeticiones", "10"),
                        "rest": getattr(ejercicio, "descanso", "60s"),
                        "notes": getattr(ejercicio, "notas", ""),
                        "day": dia_idx + 1
                    }
                    exercises.append(exercise_data)
        
        except Exception as e:
            logger.error(f"Error extracting exercises from routine: {e}")
        
        return exercises
    
    def _render_header_section(self, pdf: PdfPages, section: Dict[str, Any], settings: Dict[str, Any]):
        """Render header section"""
        try:
            fig, ax = plt.subplots(figsize=(8.27, 11.69) if settings.get("page_size") == "A4" else (11.69, 8.27))
            ax.axis('off')
            
            content = section.get("content", {})
            
            # Title
            title = content.get("title", "{{gym_name}}")
            title = self._resolve_variables(title, content)
            ax.text(0.5, 0.9, title, fontsize=16, fontweight='bold', 
                   ha='center', va='top', transform=ax.transAxes)
            
            # Subtitle
            subtitle = content.get("subtitle", "Rutina de Entrenamiento")
            ax.text(0.5, 0.85, subtitle, fontsize=12, 
                   ha='center', va='top', transform=ax.transAxes)
            
            # Client and trainer info
            if content.get("show_client_name"):
                client_name = content.get("client_name", "{{client_name}}")
                client_name = self._resolve_variables(client_name, content)
                ax.text(0.1, 0.75, f"Cliente: {client_name}", fontsize=10, 
                       ha='left', va='top', transform=ax.transAxes)
            
            if content.get("show_trainer_name"):
                trainer_name = content.get("trainer_name", "{{trainer_name}}")
                trainer_name = self._resolve_variables(trainer_name, content)
                ax.text(0.1, 0.70, f"Entrenador: {trainer_name}", fontsize=10, 
                       ha='left', va='top', transform=ax.transAxes)
            
            # Date
            if content.get("show_date"):
                date_str = datetime.now().strftime("%d/%m/%Y")
                ax.text(0.9, 0.75, f"Fecha: {date_str}", fontsize=10, 
                       ha='right', va='top', transform=ax.transAxes)
            
            # Logo placeholder
            if content.get("show_logo"):
                logo_rect = patches.Rectangle((0.8, 0.8), 0.15, 0.1, 
                                           linewidth=1, edgecolor='gray', 
                                           facecolor='lightgray', transform=ax.transAxes)
                ax.add_patch(logo_rect)
                ax.text(0.875, 0.85, "LOGO", fontsize=8, ha='center', va='center', transform=ax.transAxes)
            
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
        
        except Exception as e:
            logger.error(f"Error rendering header section: {e}")
    
    def _render_exercise_table_section(self, pdf: PdfPages, section: Dict[str, Any], settings: Dict[str, Any]):
        """Render exercise table section"""
        try:
            content = section.get("content", {})
            exercises = content.get("exercises", [])
            
            if not exercises:
                return
            
            # Create figure
            fig, ax = plt.subplots(figsize=(8.27, 11.69) if settings.get("page_size") == "A4" else (11.69, 8.27))
            ax.axis('off')
            
            # Section title
            title = content.get("title", "Ejercicios")
            ax.text(0.5, 0.95, title, fontsize=14, fontweight='bold', 
                   ha='center', va='top', transform=ax.transAxes)
            
            # Create table data
            table_data = []
            headers = content.get("columns", ["Ejercicio", "Series", "Repeticiones", "Descanso"])
            
            # Add header row
            table_data.append(headers)
            
            # Add exercise rows
            for exercise in exercises:
                row = [
                    exercise.get("name", ""),
                    str(exercise.get("sets", "")),
                    exercise.get("reps", ""),
                    exercise.get("rest", "")
                ]
                table_data.append(row)
            
            # Create table
            table = ax.table(cellText=table_data[1:], colLabels=table_data[0],
                           cellLoc='center', loc='center',
                           bbox=[0.1, 0.2, 0.8, 0.7])
            
            # Style table
            table.auto_set_font_size(False)
            table.set_fontsize(10)
            table.scale(1, 1.5)
            
            # Style header row
            for i in range(len(headers)):
                cell = table[(0, i)]
                cell.set_facecolor('#4472C4')
                cell.set_text_props(weight='bold', color='white')
            
            # Add notes if present
            notes = [ex.get("notes", "") for ex in exercises if ex.get("notes")]
            if notes and content.get("show_notes", True):
                ax.text(0.1, 0.1, "Notas:", fontsize=10, fontweight='bold', 
                       ha='left', va='top', transform=ax.transAxes)
                
                for i, note in enumerate(notes[:3]):  # Limit to 3 notes
                    ax.text(0.1, 0.05 - i*0.03, f"• {note}", fontsize=8, 
                           ha='left', va='top', transform=ax.transAxes)
            
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
        
        except Exception as e:
            logger.error(f"Error rendering exercise table section: {e}")
    
    def _render_footer_section(self, pdf: PdfPages, section: Dict[str, Any], settings: Dict[str, Any]):
        """Render footer section"""
        try:
            fig, ax = plt.subplots(figsize=(8.27, 11.69) if settings.get("page_size") == "A4" else (11.69, 8.27))
            ax.axis('off')
            
            content = section.get("content", {})
            
            # Signature line
            if content.get("show_signature"):
                ax.text(0.7, 0.3, "Firma:", fontsize=10, ha='left', va='top', transform=ax.transAxes)
                ax.plot([0.7, 0.9], [0.25, 0.25], color='black', linewidth=1, transform=ax.transAxes)
            
            # Date
            if content.get("show_date"):
                date_str = datetime.now().strftime("%d/%m/%Y")
                ax.text(0.7, 0.2, f"Fecha: {date_str}", fontsize=10, ha='left', va='top', transform=ax.transAxes)
            
            # Notes
            if content.get("notes"):
                notes = content.get("notes", "")
                ax.text(0.5, 0.1, notes, fontsize=8, ha='center', va='top', 
                       style='italic', transform=ax.transAxes)
            
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
        
        except Exception as e:
            logger.error(f"Error rendering footer section: {e}")
    
    def _render_info_box_section(self, pdf: PdfPages, section: Dict[str, Any], settings: Dict[str, Any]):
        """Render info box section"""
        try:
            fig, ax = plt.subplots(figsize=(8.27, 11.69) if settings.get("page_size") == "A4" else (11.69, 8.27))
            ax.axis('off')
            
            content = section.get("content", {})
            
            # Info box background
            info_rect = patches.Rectangle((0.1, 0.7), 0.8, 0.2, 
                                       linewidth=1, edgecolor='gray', 
                                       facecolor='lightgray', alpha=0.3, transform=ax.transAxes)
            ax.add_patch(info_rect)
            
            # Info text
            title = content.get("title", "Información")
            text = content.get("text", "")
            
            ax.text(0.5, 0.85, title, fontsize=12, fontweight='bold', 
                   ha='center', va='center', transform=ax.transAxes)
            ax.text(0.5, 0.75, text, fontsize=10, 
                   ha='center', va='center', transform=ax.transAxes)
            
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
        
        except Exception as e:
            logger.error(f"Error rendering info box section: {e}")
    
    def _render_image_section(self, pdf: PdfPages, section: Dict[str, Any], settings: Dict[str, Any]):
        """Render image section"""
        try:
            fig, ax = plt.subplots(figsize=(8.27, 11.69) if settings.get("page_size") == "A4" else (11.69, 8.27))
            ax.axis('off')
            
            content = section.get("content", {})
            image_path = content.get("image_path", "")
            
            if image_path and Path(image_path).exists():
                # Load and display image
                img = Image.open(image_path)
                ax.imshow(img, extent=[0.1, 0.9, 0.2, 0.8], aspect='auto')
            else:
                # Placeholder
                img_rect = patches.Rectangle((0.1, 0.2), 0.8, 0.6, 
                                           linewidth=1, edgecolor='gray', 
                                           facecolor='lightgray', transform=ax.transAxes)
                ax.add_patch(img_rect)
                ax.text(0.5, 0.5, "IMAGEN", fontsize=12, ha='center', va='center', transform=ax.transAxes)
            
            # Caption
            caption = content.get("caption", "")
            if caption:
                ax.text(0.5, 0.1, caption, fontsize=10, ha='center', va='top', transform=ax.transAxes)
            
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
        
        except Exception as e:
            logger.error(f"Error rendering image section: {e}")
    
    def _render_text_section(self, pdf: PdfPages, section: Dict[str, Any], settings: Dict[str, Any]):
        """Render text section"""
        try:
            fig, ax = plt.subplots(figsize=(8.27, 11.69) if settings.get("page_size") == "A4" else (11.69, 8.27))
            ax.axis('off')
            
            content = section.get("content", {})
            
            # Title
            title = content.get("title", "")
            if title:
                ax.text(0.5, 0.9, title, fontsize=14, fontweight='bold', 
                       ha='center', va='top', transform=ax.transAxes)
            
            # Text content
            text = content.get("text", "")
            if text:
                ax.text(0.5, 0.7, text, fontsize=11, ha='center', va='center', 
                       wrap=True, transform=ax.transAxes)
            
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
        
        except Exception as e:
            logger.error(f"Error rendering text section: {e}")
    
    def _resolve_variables(self, text: str, context: Dict[str, Any]) -> str:
        """Resolve template variables"""
        try:
            # Simple variable resolution
            variables = {
                "{{gym_name}}": context.get("gym_name", "Gym"),
                "{{client_name}}": context.get("client_name", "Cliente"),
                "{{trainer_name}}": context.get("trainer_name", "Entrenador"),
                "{{date}}": datetime.now().strftime("%d/%m/%Y"),
                "{{time}}": datetime.now().strftime("%H:%M")
            }
            
            resolved_text = text
            for var, value in variables.items():
                resolved_text = resolved_text.replace(var, str(value))
            
            return resolved_text
        
        except Exception as e:
            logger.error(f"Error resolving variables: {e}")
            return text
    
    def generate_qr_code(self, data: str, size: int = 100) -> str:
        """Generate QR code as base64 string"""
        try:
            import qrcode
            
            # Create QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data(data)
            qr.make(fit=True)
            
            # Create image
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffer = io.BytesIO()
            qr_img.save(buffer, format="PNG")
            qr_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{qr_base64}"
        
        except ImportError:
            logger.warning("qrcode library not available, using placeholder")
            return ""
        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            return ""
    
    def add_watermark(self, pdf_path: Path, watermark_text: str = "CONFIDENTIAL"):
        """Add watermark to PDF"""
        try:
            # This would require a more sophisticated PDF manipulation library
            # For now, we'll just log the request
            logger.info(f"Watermark requested: {watermark_text} for {pdf_path}")
        
        except Exception as e:
            logger.error(f"Error adding watermark: {e}")
    
    def get_pdf_metadata(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract metadata from PDF"""
        try:
            # This would require a PDF library like PyPDF2
            # For now, return basic file info
            stat = pdf_path.stat()
            return {
                "file_size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime),
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "pages": 1  # Placeholder
            }
        
        except Exception as e:
            logger.error(f"Error getting PDF metadata: {e}")
            return {}
