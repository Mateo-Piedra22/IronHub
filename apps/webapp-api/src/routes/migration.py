"""
Excel Template Migration API Endpoints
REST API endpoints for migrating Excel templates to the dynamic template system.
All endpoints require owner-level authentication.
"""

import logging
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from datetime import datetime

from sqlalchemy.orm import Session

from src.dependencies import get_db_session as get_db, require_owner

# Try importing the migrator — it may not be installed in all environments
try:
    from excel_template_migrator import ExcelTemplateMigrator
except ImportError:
    ExcelTemplateMigrator = None  # type: ignore

# Try importing ORM model and service
try:
    from src.database.orm_models import PlantillaRutina
except ImportError:
    PlantillaRutina = None  # type: ignore

try:
    from src.services.template_service import TemplateService
except ImportError:
    TemplateService = None  # type: ignore

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/migration", tags=["migration"])


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _require_session_user_id(request: Request) -> int:
    """Extract user_id from the session or raise 401."""
    uid = request.session.get("user_id")
    if uid is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        return int(uid)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _require_migrator():
    """Ensure ExcelTemplateMigrator is available."""
    if ExcelTemplateMigrator is None:
        raise HTTPException(
            status_code=501,
            detail="Migration functionality is not available in this environment",
        )


# ---------------------------------------------------------------------------
#  Pydantic models
# ---------------------------------------------------------------------------

class MigrationRequest(BaseModel):
    """Request model for template migration"""
    template_name: str = Field(..., description="Name for the migrated template")
    description: Optional[str] = Field(None, description="Description for the migrated template")
    category: str = Field("general", description="Category for the migrated template")
    days_per_week: Optional[int] = Field(None, description="Number of days per week")
    tags: List[str] = Field(default_factory=list, description="Tags for the migrated template")
    is_public: bool = Field(False, description="Whether the template should be public")
    auto_save: bool = Field(True, description="Whether to automatically save the migrated template")


class MigrationResponse(BaseModel):
    """Response model for template migration"""
    success: bool
    message: str
    template_id: Optional[int] = None
    template_config: Optional[Dict[str, Any]] = None
    exercises_count: Optional[int] = None
    sections_count: Optional[int] = None
    preview_url: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class MigrationPreviewRequest(BaseModel):
    """Request model for migration preview"""
    analyze_structure: bool = Field(True, description="Whether to analyze Excel structure")
    extract_exercises: bool = Field(True, description="Whether to extract exercises")
    generate_config: bool = Field(True, description="Whether to generate template configuration")


class MigrationPreviewResponse(BaseModel):
    """Response model for migration preview"""
    success: bool
    file_info: Dict[str, Any]
    structure: Optional[Dict[str, Any]] = None
    exercises: Optional[List[Dict[str, Any]]] = None
    template_config: Optional[Dict[str, Any]] = None
    estimated_sections: Optional[int] = None
    estimated_exercises: Optional[int] = None
    migration_complexity: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class MigrationStatusResponse(BaseModel):
    """Response model for migration status"""
    migration_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: Optional[int] = None
    message: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# In-memory storage for migration status (bounded to 100 entries)
_MAX_STATUS_ENTRIES = 100
migration_status_store: Dict[str, MigrationStatusResponse] = {}


def _store_status(migration_id: str, status: MigrationStatusResponse):
    """Store migration status with bounded size."""
    if len(migration_status_store) >= _MAX_STATUS_ENTRIES:
        # Remove oldest entry
        oldest_key = min(migration_status_store, key=lambda k: migration_status_store[k].created_at)
        del migration_status_store[oldest_key]
    migration_status_store[migration_id] = status


# ========== ENDPOINTS ==========

@router.post("/upload", response_model=MigrationResponse)
async def upload_and_migrate_excel(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    migration_request: MigrationRequest = Form(...),
    auto_save: bool = Form(True),
    db: Session = Depends(get_db),
    _=Depends(require_owner),
):
    """
    Upload Excel file and migrate to dynamic template.
    Requires owner-level authentication.
    """
    try:
        _require_migrator()
        user_id = _require_session_user_id(request)

        # Validate file type
        if not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail="Only Excel files (.xlsx, .xls) are supported",
            )

        # Validate file size (max 10MB)
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")
        await file.seek(0)

        # Create temporary directory for migration
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Save uploaded file
            file_path = temp_path / file.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Initialize migrator
            migrator = ExcelTemplateMigrator()
            migrator.excel_templates_dir = temp_path
            migrator.output_dir = temp_path / "output"
            migrator.output_dir.mkdir(exist_ok=True)

            # Perform migration
            logger.info(f"Starting migration for file: {file.filename} by user {user_id}")
            success, result = migrator.migrate_template(file_path)

            if not success:
                raise HTTPException(status_code=400, detail="Migration failed")

            # Load migrated template configuration
            template_config_path = Path(result)
            if not template_config_path.exists():
                raise HTTPException(status_code=500, detail="Migrated template file not found")

            with open(template_config_path, 'r', encoding='utf-8') as f:
                template_config = json.load(f)

            # Update template configuration with user input
            template_config["metadata"]["name"] = migration_request.template_name
            template_config["metadata"]["description"] = migration_request.description or f"Migrated from {file.filename}"
            template_config["metadata"]["tags"] = ["migrated", "excel"] + migration_request.tags

            # Count exercises and sections
            exercises_count = 0
            for section in template_config.get("sections", []):
                if section.get("type") == "exercise_table":
                    exercises = section.get("content", {}).get("exercises", [])
                    exercises_count += len(exercises)

            sections_count = len(template_config.get("sections", []))

            # Save template to database if requested
            template_id = None
            if migration_request.auto_save and PlantillaRutina is not None:
                template_record = PlantillaRutina(
                    nombre=migration_request.template_name,
                    descripcion=migration_request.description,
                    configuracion=template_config,
                    categoria=migration_request.category,
                    dias_semana=migration_request.days_per_week,
                    activa=True,
                    publica=migration_request.is_public,
                    creada_por=user_id,
                    version_actual="1.0.0",
                    tags=migration_request.tags + ["migrated", "excel"],
                )

                db.add(template_record)
                db.commit()
                db.refresh(template_record)

                template_id = template_record.id
                logger.info(f"Saved migrated template to database with ID: {template_id}")

            # Generate preview URL
            preview_url = f"/api/templates/{template_id}/preview" if template_id else None

            return MigrationResponse(
                success=True,
                message="Template migrated successfully",
                template_id=template_id,
                template_config=template_config,
                exercises_count=exercises_count,
                sections_count=sections_count,
                preview_url=preview_url,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upload_and_migrate_excel: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/preview", response_model=MigrationPreviewResponse)
async def preview_migration(
    request: Request,
    file: UploadFile = File(...),
    preview_request: MigrationPreviewRequest = Form(...),
    _=Depends(require_owner),
):
    """
    Preview migration without actually creating the template.
    Requires owner-level authentication.
    """
    try:
        _require_migrator()

        # Validate file type
        if not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail="Only Excel files (.xlsx, .xls) are supported",
            )

        # Validate file size
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")
        await file.seek(0)

        # Create temporary directory for preview
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Save uploaded file
            file_path = temp_path / file.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Initialize migrator
            migrator = ExcelTemplateMigrator()
            migrator.excel_templates_dir = temp_path
            migrator.output_dir = temp_path / "output"
            migrator.output_dir.mkdir(exist_ok=True)

            # File info
            file_info = {
                "name": file.filename,
                "size": file_path.stat().st_size,
                "type": file.content_type,
            }

            response = MigrationPreviewResponse(
                success=True,
                file_info=file_info,
                warnings=[],
            )

            # Analyze structure
            if preview_request.analyze_structure:
                structure = migrator.analyze_excel_structure(file_path)
                response.structure = structure

                # Estimate complexity
                if structure:
                    total_rows = structure.get("total_rows", 0)
                    total_cols = structure.get("total_cols", 0)
                    sheets_count = len(structure.get("sheets", []))

                    if total_rows > 100 or total_cols > 20 or sheets_count > 3:
                        response.migration_complexity = "high"
                    elif total_rows > 50 or total_cols > 10 or sheets_count > 1:
                        response.migration_complexity = "medium"
                    else:
                        response.migration_complexity = "low"

            # Extract configuration
            config = migrator.extract_template_config(file_path, response.structure or {})

            # Extract exercises
            if preview_request.extract_exercises:
                exercises = migrator.extract_exercises(file_path, config)
                response.exercises = [
                    {
                        "name": ex.name,
                        "sets": ex.sets,
                        "reps": ex.reps,
                        "rest": ex.rest,
                        "notes": ex.notes,
                    }
                    for ex in exercises
                ]
                response.estimated_exercises = len(exercises)

            # Generate template configuration
            if preview_request.generate_config:
                template_config = migrator.convert_to_dynamic_template(config, response.exercises or [])
                response.template_config = template_config
                response.estimated_sections = len(template_config.get("sections", []))

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in preview_migration: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/batch", response_model=Dict[str, Any])
async def batch_migrate_excel(
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    auto_save: bool = Form(True),
    category: str = Form("general"),
    db: Session = Depends(get_db),
    _=Depends(require_owner),
):
    """
    Batch migrate multiple Excel files.
    Requires owner-level authentication.
    """
    try:
        _require_migrator()
        user_id = _require_session_user_id(request)

        if len(files) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 files allowed per batch")

        # Create migration ID
        migration_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Initialize status
        _store_status(migration_id, MigrationStatusResponse(
            migration_id=migration_id,
            status="pending",
            progress=0,
            message="Batch migration queued",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ))

        # Add background task
        background_tasks.add_task(
            process_batch_migration,
            migration_id,
            files,
            auto_save,
            category,
            user_id,
            db,
        )

        return {
            "migration_id": migration_id,
            "status": "queued",
            "files_count": len(files),
            "message": "Batch migration started",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch_migrate_excel: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/status/{migration_id}", response_model=MigrationStatusResponse)
async def get_migration_status(
    migration_id: str,
    _=Depends(require_owner),
):
    """
    Get status of a migration process.
    Requires owner-level authentication.
    """
    if migration_id not in migration_status_store:
        raise HTTPException(status_code=404, detail="Migration not found")

    return migration_status_store[migration_id]


@router.get("/templates", response_model=List[Dict[str, Any]])
async def list_migrated_templates(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _=Depends(require_owner),
):
    """
    List migrated templates.
    Requires owner-level authentication.
    """
    try:
        if PlantillaRutina is None:
            return []

        # Bound the limit
        limit = min(limit, 100)

        templates = db.query(PlantillaRutina).filter(
            PlantillaRutina.tags.contains(["migrated"])
        ).offset(skip).limit(limit).all()

        return [
            {
                "id": template.id,
                "nombre": template.nombre,
                "descripcion": template.descripcion,
                "categoria": template.categoria,
                "dias_semana": template.dias_semana,
                "activa": template.activa,
                "publica": template.publica,
                "fecha_creacion": template.fecha_creacion.isoformat() if template.fecha_creacion else None,
                "version_actual": template.version_actual,
                "uso_count": template.uso_count,
                "rating_promedio": float(template.rating_promedio) if template.rating_promedio else None,
                "tags": template.tags or [],
            }
            for template in templates
        ]

    except Exception as e:
        logger.error(f"Error in list_migrated_templates: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/download/{template_id}")
async def download_migrated_template(
    template_id: int,
    format: str = "json",
    db: Session = Depends(get_db),
    _=Depends(require_owner),
):
    """
    Download migrated template configuration.
    Requires owner-level authentication.
    """
    try:
        if PlantillaRutina is None:
            raise HTTPException(status_code=501, detail="Template model not available")

        template = db.query(PlantillaRutina).filter(
            PlantillaRutina.id == template_id
        ).first()

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        if format == "json":
            # Create JSON file
            template_data = {
                "id": template.id,
                "nombre": template.nombre,
                "descripcion": template.descripcion,
                "configuracion": template.configuracion,
                "categoria": template.categoria,
                "dias_semana": template.dias_semana,
                "tags": template.tags,
                "fecha_creacion": template.fecha_creacion.isoformat() if template.fecha_creacion else None,
                "version_actual": template.version_actual,
            }

            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
                json.dump(template_data, tmp_file, indent=2, ensure_ascii=False)
                tmp_file_path = tmp_file.name

            return FileResponse(
                tmp_file_path,
                media_type="application/json",
                filename=f"{template.nombre}_template.json",
            )

        else:
            raise HTTPException(status_code=400, detail="Only JSON format is supported")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in download_migrated_template: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/templates/{template_id}")
async def delete_migrated_template(
    template_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_owner),
):
    """
    Delete a migrated template.
    Requires owner-level authentication.
    """
    try:
        if PlantillaRutina is None:
            raise HTTPException(status_code=501, detail="Template model not available")

        template = db.query(PlantillaRutina).filter(
            PlantillaRutina.id == template_id
        ).first()

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Check if it's a migrated template
        if not template.tags or "migrated" not in template.tags:
            raise HTTPException(
                status_code=400,
                detail="Only migrated templates can be deleted through this endpoint",
            )

        db.delete(template)
        db.commit()

        return {"success": True, "message": "Template deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_migrated_template: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------------------------------------------------------
#  Background task for batch migration
# ---------------------------------------------------------------------------

async def process_batch_migration(
    migration_id: str,
    files: List[UploadFile],
    auto_save: bool,
    category: str,
    user_id: int,
    db: Session,
):
    """Process batch migration in background."""
    try:
        if ExcelTemplateMigrator is None or PlantillaRutina is None:
            migration_status_store[migration_id].status = "failed"
            migration_status_store[migration_id].error = "Migration dependencies not available"
            migration_status_store[migration_id].updated_at = datetime.now()
            return

        # Update status
        migration_status_store[migration_id].status = "processing"
        migration_status_store[migration_id].message = "Processing batch migration"
        migration_status_store[migration_id].updated_at = datetime.now()

        results = []
        total_files = len(files)

        for i, file in enumerate(files):
            try:
                # Update progress
                progress = int((i / total_files) * 100)
                migration_status_store[migration_id].progress = progress
                migration_status_store[migration_id].message = f"Processing file {i+1}/{total_files}: {file.filename}"
                migration_status_store[migration_id].updated_at = datetime.now()

                # Create temporary directory for this file
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)

                    # Save file
                    file_path = temp_path / file.filename
                    with open(file_path, "wb") as buffer:
                        shutil.copyfileobj(file.file, buffer)

                    # Migrate file
                    migrator = ExcelTemplateMigrator()
                    migrator.excel_templates_dir = temp_path
                    migrator.output_dir = temp_path / "output"
                    migrator.output_dir.mkdir(exist_ok=True)

                    success, result = migrator.migrate_template(file_path)

                    if success and auto_save:
                        # Load and save to database
                        template_config_path = Path(result)
                        with open(template_config_path, 'r', encoding='utf-8') as f:
                            template_config = json.load(f)

                        template_record = PlantillaRutina(
                            nombre=template_config["metadata"]["name"],
                            descripcion=template_config["metadata"].get("description"),
                            configuracion=template_config,
                            categoria=category,
                            activa=True,
                            publica=False,
                            creada_por=user_id,
                            version_actual="1.0.0",
                            tags=["migrated", "excel", "batch"],
                        )

                        db.add(template_record)
                        db.commit()
                        db.refresh(template_record)

                        results.append({
                            "filename": file.filename,
                            "success": True,
                            "template_id": template_record.id,
                        })
                    else:
                        results.append({
                            "filename": file.filename,
                            "success": False,
                            "error": "Migration extraction failed",
                        })

            except Exception as e:
                logger.error(f"Error processing file {file.filename}: {e}")
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": "Processing failed",
                })

        # Update final status
        successful_count = len([r for r in results if r["success"]])
        migration_status_store[migration_id].status = "completed"
        migration_status_store[migration_id].progress = 100
        migration_status_store[migration_id].message = f"Batch migration completed: {successful_count}/{total_files} successful"
        migration_status_store[migration_id].updated_at = datetime.now()
        migration_status_store[migration_id].result = {
            "total_files": total_files,
            "successful": successful_count,
            "failed": total_files - successful_count,
            "results": results,
        }

    except Exception as e:
        logger.error(f"Error in batch migration {migration_id}: {e}")
        migration_status_store[migration_id].status = "failed"
        migration_status_store[migration_id].error = "Batch migration failed"
        migration_status_store[migration_id].updated_at = datetime.now()
