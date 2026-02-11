"""
Template Admin API Response Models

This module contains Pydantic models for template admin API responses,
ensuring proper data validation and serialization.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


class TemplateStatus(str, Enum):
    """Template status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    ARCHIVED = "archived"


class PreviewFormat(str, Enum):
    """Preview format enumeration"""
    PDF = "pdf"
    IMAGE = "image"
    THUMBNAIL = "thumbnail"
    HTML = "html"
    JSON = "json"


class PreviewQuality(str, Enum):
    """Preview quality enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


class ValidationError(BaseModel):
    """Validation error model"""
    field: str
    message: str
    code: str
    severity: str = "error"


class ValidationWarning(BaseModel):
    """Validation warning model"""
    field: str
    message: str
    code: str
    severity: str = "warning"


class TemplateValidationResponse(BaseModel):
    """Template validation response"""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationWarning]
    performance_score: float = Field(ge=0, le=100)
    security_score: float = Field(ge=0, le=100)
    best_practices_score: float = Field(ge=0, le=100)


class TemplateVersion(BaseModel):
    """Template version model"""
    id: int
    plantilla_id: int
    version: str
    configuracion: Dict[str, Any]
    creada_por: Optional[int]
    fecha_creacion: datetime
    es_actual: bool
    creador: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class TemplateAnalytics(BaseModel):
    """Template analytics model"""
    template_id: int
    total_uses: int
    preview_generations: int
    downloads: int
    avg_generation_time: float
    success_rate: float
    last_used: Optional[datetime]
    usage_by_day: Dict[str, int]
    popular_gyms: List[Dict[str, Any]]
    error_rate: float
    
    class Config:
        from_attributes = True


class GymAssignment(BaseModel):
    """Gym template assignment model"""
    id: int
    gimnasio_id: int
    plantilla_id: int
    activa: bool
    prioridad: int
    asignada_por: Optional[int]
    fecha_asignacion: datetime
    uso_count: int
    gimnasio: Optional[Dict[str, Any]] = None
    asignador: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class Template(BaseModel):
    """Template model"""
    id: int
    nombre: str
    descripcion: Optional[str]
    categoria: str
    dias_semana: Optional[int]
    activa: bool
    publica: bool
    creada_por: Optional[int]
    fecha_creacion: datetime
    version_actual: str
    tags: List[str]
    uso_count: int
    preview_url: Optional[str]
    creador: Optional[Dict[str, Any]] = None
    versions: Optional[List[TemplateVersion]] = None
    analytics: Optional[TemplateAnalytics] = None
    
    @validator('tags', pre=True)
    def parse_tags(cls, v):
        if isinstance(v, str):
            return [tag.strip() for tag in v.split(',') if tag.strip()]
        return v or []
    
    class Config:
        from_attributes = True


class TemplateCreateRequest(BaseModel):
    """Template creation request"""
    nombre: str = Field(..., min_length=1, max_length=255)
    configuracion: Dict[str, Any] = Field(...)
    descripcion: Optional[str] = Field(None, max_length=1000)
    categoria: str = Field("general", max_length=100)
    dias_semana: Optional[int] = Field(None, ge=1, le=7)
    tags: List[str] = Field(default_factory=list)
    publica: bool = False
    generate_preview: bool = True
    
    @validator('tags')
    def validate_tags(cls, v):
        if len(v) > 20:
            raise ValueError('Maximum 20 tags allowed')
        return [tag.strip() for tag in v if tag.strip()]


class TemplateUpdateRequest(BaseModel):
    """Template update request"""
    nombre: Optional[str] = Field(None, min_length=1, max_length=255)
    configuracion: Optional[Dict[str, Any]] = None
    descripcion: Optional[str] = Field(None, max_length=1000)
    categoria: Optional[str] = Field(None, max_length=100)
    dias_semana: Optional[int] = Field(None, ge=1, le=7)
    tags: Optional[List[str]] = None
    publica: Optional[bool] = None
    cambios_descripcion: Optional[str] = Field(None, max_length=500)
    generate_preview: bool = True
    create_version: bool = True
    
    @validator('tags')
    def validate_tags(cls, v):
        if v is not None and len(v) > 20:
            raise ValueError('Maximum 20 tags allowed')
        return [tag.strip() for tag in v] if v else None


class TemplateSearchRequest(BaseModel):
    """Template search request"""
    query: Optional[str] = Field(None, max_length=255)
    categoria: Optional[str] = Field(None, max_length=100)
    dias_semana: Optional[int] = Field(None, ge=1, le=7)
    publica: Optional[bool] = None
    creada_por: Optional[int] = None
    tags: Optional[List[str]] = None
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)
    sort_by: str = Field("fecha_creacion", regex="^(nombre|fecha_creacion|uso_count|categoria)$")
    sort_order: str = Field("desc", regex="^(asc|desc)$")


class TemplatePreviewRequest(BaseModel):
    """Template preview request"""
    format: PreviewFormat = PreviewFormat.PDF
    quality: PreviewQuality = PreviewQuality.MEDIUM
    page_number: int = Field(1, ge=1)
    sample_data: Optional[Dict[str, Any]] = None
    background: bool = False


class TemplateVersionRequest(BaseModel):
    """Template version creation request"""
    version: str = Field(..., min_length=1, max_length=50)
    configuracion: Dict[str, Any] = Field(...)
    descripcion: Optional[str] = Field(None, max_length=500)


class TemplateImportRequest(BaseModel):
    """Template import request"""
    validate_only: bool = False
    overwrite: bool = False


class TemplateExportRequest(BaseModel):
    """Template export request"""
    include_analytics: bool = False
    include_versions: bool = False


class GymAssignmentRequest(BaseModel):
    """Gym assignment request"""
    template_id: int
    prioridad: int = Field(0, ge=0, le=100)


class TemplateListResponse(BaseModel):
    """Template list response"""
    success: bool
    templates: List[Template]
    total: int
    limit: int
    offset: int
    has_more: bool


class TemplateResponse(BaseModel):
    """Single template response"""
    success: bool
    template: Template


class TemplateValidationResponse(BaseModel):
    """Template validation response"""
    success: bool
    validation: TemplateValidationResponse


class TemplatePreviewResponse(BaseModel):
    """Template preview response"""
    success: bool
    preview_url: Optional[str]
    format: PreviewFormat
    quality: PreviewQuality
    page_number: int
    generation_time: Optional[float] = None
    cache_hit: Optional[bool] = None


class TemplateVersionResponse(BaseModel):
    """Template version response"""
    success: bool
    versions: List[TemplateVersion]
    total: int


class TemplateAnalyticsResponse(BaseModel):
    """Template analytics response"""
    success: bool
    analytics: TemplateAnalytics
    period_days: int


class AnalyticsDashboardResponse(BaseModel):
    """Analytics dashboard response"""
    success: bool
    dashboard: Dict[str, Any]
    period_days: int
    gimnasio_id: Optional[int]


class TemplateImportResponse(BaseModel):
    """Template import response"""
    success: bool
    template: Optional[Template] = None
    validation: Optional[TemplateValidationResponse] = None
    message: str


class TemplateExportResponse(BaseModel):
    """Template export response"""
    success: bool
    export_data: Dict[str, Any]
    filename: str


class GymTemplatesResponse(BaseModel):
    """Gym templates response"""
    success: bool
    templates: List[Template]
    gimnasio_id: int


class GymAssignmentResponse(BaseModel):
    """Gym assignment response"""
    success: bool
    assignment: GymAssignment
    message: str


class CategoriesResponse(BaseModel):
    """Categories response"""
    success: bool
    categories: List[str]


class TagsResponse(BaseModel):
    """Tags response"""
    success: bool
    tags: List[str]


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# === Analytics Specific Models ===

class UsageStats(BaseModel):
    """Usage statistics model"""
    date: str
    uses: int
    previews: int
    downloads: int


class PopularTemplate(BaseModel):
    """Popular template model"""
    template_id: int
    nombre: str
    uses: int
    categoria: str
    crecimiento: float  # Percentage growth


class GymUsageStats(BaseModel):
    """Gym usage statistics model"""
    gimnasio_id: int
    gimnasio_nombre: str
    template_usos: int
    previews_generados: int
    templates_asignados: int


class PerformanceMetrics(BaseModel):
    """Performance metrics model"""
    avg_preview_generation_time: float
    cache_hit_rate: float
    error_rate: float
    total_requests: int
    successful_requests: int


class DashboardData(BaseModel):
    """Complete dashboard data model"""
    overview: Dict[str, Any]
    popular_templates: List[PopularTemplate]
    usage_stats: List[UsageStats]
    gym_usage: List[GymUsageStats]
    performance: PerformanceMetrics
    recent_activity: List[Dict[str, Any]]


# === WebSocket Message Models ===

class PreviewProgressMessage(BaseModel):
    """Preview progress message"""
    type: str = "preview_progress"
    template_id: int
    progress: float = Field(ge=0, le=100)
    status: str
    message: Optional[str] = None
    preview_url: Optional[str] = None


class TemplateUpdateMessage(BaseModel):
    """Template update message"""
    type: str = "template_update"
    template_id: int
    action: str  # created, updated, deleted, etc.
    template_data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AnalyticsUpdateMessage(BaseModel):
    """Analytics update message"""
    type: str = "analytics_update"
    template_id: Optional[int] = None
    gimnasio_id: Optional[int] = None
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
