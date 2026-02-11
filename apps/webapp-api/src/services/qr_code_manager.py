"""
QR Code Manager

This module provides advanced QR code generation and management for dynamic routine templates,
including multiple data sources, positioning options, and custom styling.
"""

import io
import os
import hashlib
from typing import Dict, Any, Optional, Union, Tuple, List
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

from reportlab.lib.units import inch
from reportlab.platypus import Image, Table, TableStyle
from reportlab.lib.colors import Color
from reportlab.graphics.shapes import Drawing

import qrcode
from PIL import Image as PILImage

logger = logging.getLogger(__name__)


class QRPosition(Enum):
    """QR code positioning options"""
    HEADER = "header"
    FOOTER = "footer"
    INLINE = "inline"
    SEPARATE = "separate"
    SHEET = "sheet"
    OVERLAY = "overlay"
    WATERMARK = "watermark"
    NONE = "none"


class QRDataSource(Enum):
    """QR code data sources"""
    ROUTINE_UUID = "routine_uuid"
    CUSTOM_URL = "custom_url"
    USER_DATA = "user_data"
    GYM_DATA = "gym_data"
    TEMPLATE_DATA = "template_data"
    COMPOSITE = "composite"
    DYNAMIC = "dynamic"


class QRErrorCorrection(Enum):
    """QR code error correction levels"""
    LOW = "L"  # ~7% correction
    MEDIUM = "M"  # ~15% correction
    QUARTILE = "Q"  # ~25% correction
    HIGH = "H"  # ~30% correction


@dataclass
class QRConfig:
    """Configuration for QR code generation"""
    enabled: bool = True
    position: QRPosition = QRPosition.FOOTER
    data_source: QRDataSource = QRDataSource.ROUTINE_UUID
    custom_data: Optional[str] = None
    size: Dict[str, float] = None
    error_correction: QRErrorCorrection = QRErrorCorrection.MEDIUM
    border_size: int = 4
    foreground_color: str = "#000000"
    background_color: str = "#FFFFFF"
    logo_path: Optional[str] = None
    logo_size: float = 0.2  # 20% of QR code size
    text_label: Optional[str] = None
    url_shorten: bool = False
    cache_enabled: bool = True
    analytics_enabled: bool = False
    
    def __post_init__(self):
        if self.size is None:
            self.size = {"width": 1.5*inch, "height": 1.5*inch}


@dataclass
class QRContext:
    """Context for QR code generation"""
    routine_data: Dict[str, Any]
    user_data: Optional[Dict[str, Any]] = None
    gym_data: Optional[Dict[str, Any]] = None
    template_data: Optional[Dict[str, Any]] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None


class QRCodeManager:
    """Advanced QR code generation and management"""

    _MAX_CACHE_SIZE = 500
    _MAX_ANALYTICS_SIZE = 1000

    def __init__(self):
        self.cache: dict = {}
        self.analytics_tracker: dict = {}
        self.default_config = QRConfig()
    
    def generate_qr_code(
        self,
        config: QRConfig,
        context: QRContext,
        position_info: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[Union[Image, Drawing, Table]], Optional[str]]:
        """Generate QR code with specified configuration"""
        try:
            if not config.enabled:
                return None, None
            
            # Get QR code data
            qr_data = self._get_qr_data(config, context)
            if not qr_data:
                return None, "No data available for QR code"
            
            # Generate QR code image
            qr_image = self._create_qr_image(qr_data, config)
            
            # Position QR code based on configuration
            if config.position == QRPosition.INLINE:
                return self._create_inline_qr(qr_image, config), None
            elif config.position in (QRPosition.SEPARATE, QRPosition.SHEET):
                return self._create_separate_qr(qr_image, config), None
            elif config.position == QRPosition.HEADER:
                return self._create_header_qr(qr_image, config, context), None
            elif config.position == QRPosition.FOOTER:
                return self._create_footer_qr(qr_image, config, context), None
            elif config.position == QRPosition.OVERLAY:
                return self._create_overlay_qr(qr_image, config, position_info), None
            elif config.position == QRPosition.WATERMARK:
                return self._create_watermark_qr(qr_image, config, position_info), None
            else:
                return qr_image, None
                
        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            return None, f"QR generation error: {str(e)}"
    
    def generate_qr_for_routine(
        self,
        routine_uuid: str,
        config: Optional[QRConfig] = None,
        context: Optional[QRContext] = None
    ) -> bytes:
        """Generate QR code for routine (returns bytes)"""
        try:
            if config is None:
                config = self.default_config
            
            if context is None:
                context = QRContext(routine_data={"uuid_rutina": routine_uuid})
            
            # Get QR data
            qr_data = self._get_qr_data(config, context)
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=self._get_error_correction_level(config.error_correction),
                box_size=10,
                border=config.border_size,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Create image
            qr_img = qr.make_image(
                fill_color=config.foreground_color,
                back_color=config.background_color
            )
            
            # Add logo if specified
            if config.logo_path and os.path.exists(config.logo_path):
                qr_img = self._add_logo_to_qr(qr_img, config.logo_path, config.logo_size)
            
            # Convert to bytes
            buffer = io.BytesIO()
            qr_img.save(buffer, format="PNG")
            buffer.seek(0)
            
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating QR for routine: {e}")
            return b""
    
    def validate_qr_config(self, config: QRConfig) -> Tuple[bool, List[str]]:
        """Validate QR code configuration"""
        errors = []
        
        if config.enabled:
            # Check data source
            if config.data_source == QRDataSource.CUSTOM_URL and not config.custom_data:
                errors.append("Custom URL data source requires custom_data")
            
            # Check size
            if config.size["width"] <= 0 or config.size["height"] <= 0:
                errors.append("QR code size must be positive")
            
            # Check colors
            if not self._is_valid_color(config.foreground_color):
                errors.append(f"Invalid foreground color: {config.foreground_color}")
            
            if not self._is_valid_color(config.background_color):
                errors.append(f"Invalid background color: {config.background_color}")
            
            # Check logo
            if config.logo_path and not os.path.exists(config.logo_path):
                errors.append(f"Logo file not found: {config.logo_path}")
        
        return len(errors) == 0, errors
    
    def get_qr_analytics(self, qr_id: str) -> Dict[str, Any]:
        """Get analytics for QR code"""
        return self.analytics_tracker.get(qr_id, {
            "scans": 0,
            "first_scan": None,
            "last_scan": None,
            "locations": [],
            "devices": []
        })
    
    # === QR Data Generation ===
    
    def _get_qr_data(self, config: QRConfig, context: QRContext) -> str:
        """Get QR code data based on configuration"""
        if config.data_source == QRDataSource.ROUTINE_UUID:
            return context.routine_data.get("uuid_rutina", "")
        
        elif config.data_source == QRDataSource.CUSTOM_URL:
            return config.custom_data or ""
        
        elif config.data_source == QRDataSource.USER_DATA:
            return self._generate_user_qr_data(context)
        
        elif config.data_source == QRDataSource.GYM_DATA:
            return self._generate_gym_qr_data(context)
        
        elif config.data_source == QRDataSource.TEMPLATE_DATA:
            return self._generate_template_qr_data(context)
        
        elif config.data_source == QRDataSource.COMPOSITE:
            return self._generate_composite_qr_data(config, context)
        
        elif config.data_source == QRDataSource.DYNAMIC:
            return self._generate_dynamic_qr_data(config, context)
        
        return ""
    
    def _generate_user_qr_data(self, context: QRContext) -> str:
        """Generate user-specific QR data"""
        if not context.user_data:
            return ""
        
        user_id = context.user_data.get("id", "")
        routine_id = context.routine_data.get("id", "")
        
        if context.base_url:
            return f"{context.base_url}/user/{user_id}/routine/{routine_id}"
        else:
            return f"user:{user_id}:routine:{routine_id}"
    
    def _generate_gym_qr_data(self, context: QRContext) -> str:
        """Generate gym-specific QR data"""
        if not context.gym_data:
            return ""
        
        gym_id = context.gym_data.get("id", "")
        routine_id = context.routine_data.get("id", "")
        
        if context.base_url:
            return f"{context.base_url}/gym/{gym_id}/routine/{routine_id}"
        else:
            return f"gym:{gym_id}:routine:{routine_id}"
    
    def _generate_template_qr_data(self, context: QRContext) -> str:
        """Generate template-specific QR data"""
        if not context.template_data:
            return ""
        
        template_id = context.template_data.get("id", "")
        version = context.template_data.get("version", "latest")
        
        if context.base_url:
            return f"{context.base_url}/template/{template_id}/version/{version}"
        else:
            return f"template:{template_id}:version:{version}"
    
    def _generate_composite_qr_data(self, config: QRConfig, context: QRContext) -> str:
        """Generate composite QR data"""
        data_parts = []
        
        # Add routine UUID
        routine_uuid = context.routine_data.get("uuid_rutina", "")
        if routine_uuid:
            data_parts.append(f"r:{routine_uuid}")
        
        # Add user ID if available
        if context.user_data:
            user_id = context.user_data.get("id", "")
            if user_id:
                data_parts.append(f"u:{user_id}")
        
        # Add gym ID if available
        if context.gym_data:
            gym_id = context.gym_data.get("id", "")
            if gym_id:
                data_parts.append(f"g:{gym_id}")
        
        # Add timestamp
        timestamp = datetime.now().isoformat()
        data_parts.append(f"t:{timestamp}")
        
        return "|".join(data_parts)
    
    def _generate_dynamic_qr_data(self, config: QRConfig, context: QRContext) -> str:
        """Generate dynamic QR data with analytics"""
        # Generate unique QR ID
        qr_id = self._generate_qr_id(context)
        
        # Track QR code for analytics
        if config.analytics_enabled:
            self.analytics_tracker[qr_id] = {
                "scans": 0,
                "first_scan": None,
                "last_scan": None,
                "created_at": datetime.now(),
                "routine_id": context.routine_data.get("id"),
                "user_id": context.user_data.get("id") if context.user_data else None
            }
        
        if context.base_url:
            return f"{context.base_url}/qr/{qr_id}"
        else:
            return f"qr:{qr_id}"
    
    # === QR Image Creation ===
    
    def _create_qr_image(self, data: str, config: QRConfig) -> PILImage.Image:
        """Create QR code image"""
        # Check cache first
        if config.cache_enabled:
            cache_key = self._get_cache_key(data, config)
            if cache_key in self.cache:
                return self.cache[cache_key]
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=self._get_error_correction_level(config.error_correction),
            box_size=10,
            border=config.border_size,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # Create image with custom colors
        qr_img = qr.make_image(
            fill_color=config.foreground_color,
            back_color=config.background_color
        )
        
        # Add logo if specified
        if config.logo_path and os.path.exists(config.logo_path):
            qr_img = self._add_logo_to_qr(qr_img, config.logo_path, config.logo_size)
        
        # Cache result (bounded)
        if config.cache_enabled:
            self.cache[cache_key] = qr_img
            # Evict oldest entries if over limit
            while len(self.cache) > self._MAX_CACHE_SIZE:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
        
        return qr_img
    
    def _add_logo_to_qr(self, qr_img: PILImage.Image, logo_path: str, logo_size: float) -> PILImage.Image:
        """Add logo to QR code"""
        try:
            # Open logo image
            logo = PILImage.open(logo_path)
            
            # Calculate logo size
            qr_width, qr_height = qr_img.size
            logo_width = int(qr_width * logo_size)
            logo_height = int(qr_height * logo_size)
            
            # Resize logo
            logo = logo.resize((logo_width, logo_height), PILImage.Resampling.LANCZOS)
            
            # Calculate position (center)
            logo_x = (qr_width - logo_width) // 2
            logo_y = (qr_height - logo_height) // 2
            
            # Paste logo onto QR code
            qr_img.paste(logo, (logo_x, logo_y), logo if logo.mode == "RGBA" else None)
            
            return qr_img
            
        except Exception as e:
            logger.warning(f"Could not add logo to QR code: {e}")
            return qr_img
    
    # === QR Positioning ===
    
    def _create_inline_qr(self, qr_img: PILImage.Image, config: QRConfig) -> Image:
        """Create inline QR code"""
        # Convert PIL image to ReportLab image
        buffer = io.BytesIO()
        qr_img.save(buffer, format="PNG")
        buffer.seek(0)
        
        return Image(buffer, width=config.size["width"], height=config.size["height"])
    
    def _create_separate_qr(self, qr_img: PILImage.Image, config: QRConfig) -> Table:
        """Create separate QR code with optional label"""
        # Convert PIL image to ReportLab image
        buffer = io.BytesIO()
        qr_img.save(buffer, format="PNG")
        buffer.seek(0)
        
        qr_image = Image(buffer, width=config.size["width"], height=config.size["height"])
        
        # Create table with QR and optional label
        if config.text_label:
            from reportlab.platypus import Paragraph
            from reportlab.lib.styles import getSampleStyleSheet
            
            styles = getSampleStyleSheet()
            label = Paragraph(config.text_label, styles["Normal"])
            
            table_data = [[qr_image], [label]]
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            return table
        else:
            return qr_image
    
    def _create_header_qr(self, qr_img: PILImage.Image, config: QRConfig, context: QRContext) -> Table:
        """Create header QR code with routine info"""
        # Convert PIL image to ReportLab image
        buffer = io.BytesIO()
        qr_img.save(buffer, format="PNG")
        buffer.seek(0)
        
        qr_image = Image(buffer, width=config.size["width"], height=config.size["height"])
        
        # Get routine info
        routine_name = context.routine_data.get("nombre_rutina", "Rutina")
        user_name = context.user_data.get("nombre", "") if context.user_data else ""
        
        # Create header table
        from reportlab.platypus import Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        
        styles = getSampleStyleSheet()
        
        # Routine info
        routine_text = f"<b>{routine_name}</b>"
        if user_name:
            routine_text += f"<br/>{user_name}"
        
        routine_para = Paragraph(routine_text, styles["Normal"])
        
        table_data = [
            [routine_para, qr_image]
        ]
        
        table = Table(table_data, colWidths=[4*inch, config.size["width"]])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        return table
    
    def _create_footer_qr(self, qr_img: PILImage.Image, config: QRConfig, context: QRContext) -> Table:
        """Create footer QR code with additional info"""
        # Convert PIL image to ReportLab image
        buffer = io.BytesIO()
        qr_img.save(buffer, format="PNG")
        buffer.seek(0)
        
        qr_image = Image(buffer, width=config.size["width"], height=config.size["height"])
        
        # Get footer info
        gym_name = context.gym_data.get("nombre", "") if context.gym_data else ""
        date_text = datetime.now().strftime("%d/%m/%Y")
        
        # Create footer table
        from reportlab.platypus import Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        
        styles = getSampleStyleSheet()
        
        # Footer info
        footer_text = f"{gym_name}<br/>{date_text}"
        if config.text_label:
            footer_text += f"<br/>{config.text_label}"
        
        footer_para = Paragraph(footer_text, styles["Normal"])
        
        table_data = [
            [footer_para, qr_image]
        ]
        
        table = Table(table_data, colWidths=[4*inch, config.size["width"]])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 0), (0, 0), 8),
            ('TEXTCOLOR', (0, 0), (0, 0), Color(0.5, 0.5, 0.5)),
        ]))
        
        return table
    
    def _create_overlay_qr(self, qr_img: PILImage.Image, config: QRConfig, position_info: Optional[Dict[str, Any]]) -> Drawing:
        """Create overlay QR code"""
        # This would create a drawing that can be overlaid on other content
        # Implementation depends on specific overlay requirements
        buffer = io.BytesIO()
        qr_img.save(buffer, format="PNG")
        buffer.seek(0)
        
        width = config.size["width"]
        height = config.size["height"]
        
        drawing = Drawing(width, height)
        
        # Add QR code to drawing
        qr_image = Image(buffer, width=width, height=height)
        drawing.add(qr_image)
        
        return drawing
    
    def _create_watermark_qr(self, qr_img: PILImage.Image, config: QRConfig, position_info: Optional[Dict[str, Any]]) -> Drawing:
        """Create watermark QR code (transparent)"""
        # Convert to transparent PNG
        qr_img = qr_img.convert("RGBA")
        
        # Apply transparency
        datas = qr_img.getdata()
        new_data = []
        for item in datas:
            # Make white background transparent
            if item[:3] == (255, 255, 255):
                new_data.append((255, 255, 255, 0))  # Transparent
            else:
                new_data.append(item + (128,))  # Semi-transparent
        
        qr_img.putdata(new_data)
        
        buffer = io.BytesIO()
        qr_img.save(buffer, format="PNG")
        buffer.seek(0)
        
        width = config.size["width"]
        height = config.size["height"]
        
        drawing = Drawing(width, height)
        qr_image = Image(buffer, width=width, height=height)
        drawing.add(qr_image)
        
        return drawing
    
    # === Utility Methods ===
    
    def _get_error_correction_level(self, level: QRErrorCorrection) -> int:
        """Get qrcode error correction level"""
        mapping = {
            QRErrorCorrection.LOW: qrcode.constants.ERROR_CORRECT_L,
            QRErrorCorrection.MEDIUM: qrcode.constants.ERROR_CORRECT_M,
            QRErrorCorrection.QUARTILE: qrcode.constants.ERROR_CORRECT_Q,
            QRErrorCorrection.HIGH: qrcode.constants.ERROR_CORRECT_H
        }
        return mapping.get(level, qrcode.constants.ERROR_CORRECT_M)
    
    def _is_valid_color(self, color: str) -> bool:
        """Check if color is valid hex color"""
        try:
            if color.startswith("#"):
                int(color[1:], 16)
                return True
            return False
        except:
            return False
    
    def _generate_qr_id(self, context: QRContext) -> str:
        """Generate unique QR ID"""
        data = f"{context.routine_data.get('id', '')}{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _get_cache_key(self, data: str, config: QRConfig) -> str:
        """Generate cache key for QR code"""
        config_str = f"{config.size}{config.error_correction}{config.foreground_color}{config.background_color}"
        return hashlib.sha256(f"{data}{config_str}".encode()).hexdigest()
    
    def clear_cache(self):
        """Clear QR code cache"""
        self.cache.clear()


# Export main classes
__all__ = [
    "QRCodeManager",
    "QRConfig",
    "QRContext",
    "QRPosition",
    "QRDataSource",
    "QRErrorCorrection"
]
