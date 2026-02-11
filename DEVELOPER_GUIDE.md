# IronHub Template System - Developer Guide

## 📋 Table of Contents

1. [Development Setup](#development-setup)
2. [Project Structure](#project-structure)
3. [API Development](#api-development)
4. [Frontend Development](#frontend-development)
5. [Database Schema](#database-schema)
6. [Testing](#testing)
7. [Deployment](#deployment)
8. [Contributing](#contributing)

---

## 🛠️ Development Setup

### Prerequisites

- **Python 3.9+**
- **Node.js 16+**
- **PostgreSQL 13+**
- **Redis 6+**
- **Git**

### Local Development Setup

#### 1. Clone Repository

```bash
git clone https://github.com/your-org/ironhub-templates.git
cd ironhub-templates
```

#### 2. Backend Setup

```bash
cd apps/webapp-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# Setup environment
cp .env.example .env
# Edit .env with your local settings

# Database setup
createdb ironhub_dev
alembic upgrade head

# Start development server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### 3. Frontend Setup

```bash
cd apps/admin-web  # or cd apps/webapp-web

# Install dependencies
npm install

# Setup environment
cp .env.example .env.local
# Edit .env.local with your local settings

# Start development server
npm run dev
```

#### 4. Database Setup

```bash
# Create databases
createdb ironhub_dev
createdb ironhub_test

# Run migrations
alembic upgrade head

# Create test data (optional)
python scripts/create_test_data.py
```

### Development Tools

#### IDE Configuration

**VSCode Settings** (.vscode/settings.json):
```json
{
  "python.defaultInterpreterPath": "./apps/webapp-api/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

**Recommended Extensions**:
- Python
- Pylance
- Black Formatter
- ESLint
- Prettier
- GitLens

#### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## 📁 Project Structure

### Repository Layout

```
ironhub-templates/
├── apps/
│   ├── webapp-api/                 # Backend API
│   │   ├── src/
│   │   │   ├── api/               # API endpoints
│   │   │   ├── models/            # Database models
│   │   │   ├── services/          # Business logic
│   │   │   ├── repositories/      # Data access layer
│   │   │   ├── utils/             # Utility functions
│   │   │   └── main.py            # FastAPI app entry
│   │   ├── tests/                 # Test files
│   │   ├── alembic/               # Database migrations
│   │   ├── requirements.txt       # Dependencies
│   │   └── run_tests.py          # Test runner
│   ├── admin-web/                 # Admin frontend
│   │   ├── src/
│   │   │   ├── components/        # React components
│   │   │   ├── pages/             # Page components
│   │   │   ├── hooks/             # Custom hooks
│   │   │   ├── services/          # API services
│   │   │   ├── utils/             # Utility functions
│   │   │   └── App.tsx            # App entry
│   │   ├── public/                # Static assets
│   │   └── package.json           # Dependencies
│   └── webapp-web/                # User frontend
│       └── ...                    # Similar structure to admin-web
├── docs/                          # Documentation
├── scripts/                       # Utility scripts
├── docker/                        # Docker configurations
└── README.md                      # Project overview
```

### Backend Architecture

#### Layer Architecture

```
┌─────────────────┐
│   API Layer     │  (FastAPI routes)
├─────────────────┤
│ Service Layer   │  (Business logic)
├─────────────────┤
│Repository Layer │  (Data access)
├─────────────────┤
│   Database      │  (PostgreSQL)
└─────────────────┘
```

#### Key Components

**API Routes** (`src/api/`):
- Define HTTP endpoints
- Handle request/response validation
- Call service layer

**Services** (`src/services/`):
- Implement business logic
- Coordinate between repositories
- Handle complex operations

**Repositories** (`src/repositories/`):
- Database operations
- Query optimization
- Data transformation

**Models** (`src/models/`):
- SQLAlchemy ORM models
- Pydantic schemas
- Database relationships

### Frontend Architecture

#### Component Structure

```
src/
├── components/
│   ├── ui/                     # Reusable UI components
│   ├── forms/                  # Form components
│   ├── layout/                 # Layout components
│   └── features/               # Feature-specific components
├── pages/
│   ├── templates/              # Template pages
│   ├── analytics/              # Analytics pages
│   └── settings/               # Settings pages
├── hooks/                      # Custom React hooks
├── services/                   # API client services
├── store/                      # State management
├── utils/                      # Utility functions
└── types/                      # TypeScript definitions
```

---

## 🔌 API Development

### FastAPI Best Practices

#### Route Organization

```python
# src/api/templates.py
from fastapi import APIRouter, Depends, HTTPException
from ..services.template_service import TemplateService
from ..database import get_db

router = APIRouter(prefix="/api/templates", tags=["templates"])

@router.get("/")
async def get_templates(
    query: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get templates with filtering"""
    service = TemplateService(db)
    return await service.get_templates(query=query, category=category)
```

#### Request/Response Models

```python
# src/models/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class TemplateCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)
    configuracion: Dict[str, Any] = Field(...)
    categoria: str = Field(..., regex="^(strength|cardio|flexibility)$")
    tags: List[str] = Field(default_factory=list)

class TemplateResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str]
    categoria: str
    fecha_creacion: datetime
    uso_count: int
    rating_promedio: Optional[float]
    
    class Config:
        from_attributes = True
```

#### Error Handling

```python
# src/utils/exceptions.py
from fastapi import HTTPException

class TemplateNotFoundError(HTTPException):
    def __init__(self, template_id: int):
        super().__init__(
            status_code=404,
            detail=f"Template with id {template_id} not found"
        )

class ValidationError(HTTPException):
    def __init__(self, message: str):
        super().__init__(
            status_code=400,
            detail=f"Validation error: {message}"
        )
```

#### Dependency Injection

```python
# src/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from ..services.auth_service import AuthService

security = HTTPBearer()

async def get_current_user(
    token: str = Depends(security),
    auth_service: AuthService = Depends()
):
    """Get current authenticated user"""
    user = await auth_service.verify_token(token.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return user
```

### Service Layer Development

#### Service Pattern

```python
# src/services/template_service.py
from typing import List, Optional, Dict, Any
from ..repositories.template_repository import TemplateRepository
from ..models.orm_models import PlantillaRutina
from ..utils.exceptions import TemplateNotFoundError

class TemplateService:
    def __init__(self, db_session):
        self.db = db_session
        self.repository = TemplateRepository(db_session)
    
    async def get_template_by_id(self, template_id: int) -> Optional[PlantillaRutina]:
        """Get template by ID with error handling"""
        template = await self.repository.get_by_id(template_id)
        if not template:
            raise TemplateNotFoundError(template_id)
        return template
    
    async def create_template(self, template_data: TemplateCreate) -> PlantillaRutina:
        """Create new template with validation"""
        # Validate configuration
        validation_result = self.validate_template_config(template_data.configuracion)
        if not validation_result["valid"]:
            raise ValidationError(f"Invalid template configuration: {validation_result['errors']}")
        
        # Create template
        template = await self.repository.create(template_data.dict())
        return template
```

#### Repository Pattern

```python
# src/repositories/template_repository.py
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from ..models.orm_models import PlantillaRutina

class TemplateRepository:
    def __init__(self, db: Session):
        self.db = db
    
    async def get_by_id(self, template_id: int) -> Optional[PlantillaRutina]:
        """Get template by ID"""
        return self.db.query(PlantillaRutina).filter(
            PlantillaRutina.id == template_id
        ).first()
    
    async def get_with_filters(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[PlantillaRutina]:
        """Get templates with filters"""
        db_query = self.db.query(PlantillaRutina)
        
        # Apply filters
        if query:
            db_query = db_query.filter(
                or_(
                    PlantillaRutina.nombre.ilike(f"%{query}%"),
                    PlantillaRutina.descripcion.ilike(f"%{query}%")
                )
            )
        
        if category:
            db_query = db_query.filter(PlantillaRutina.categoria == category)
        
        # Apply pagination
        return db_query.offset(offset).limit(limit).all()
```

### Database Development

#### Model Definition

```python
# src/models/orm_models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class PlantillaRutina(Base):
    __tablename__ = "plantillas_rutina"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False, index=True)
    descripcion = Column(Text)
    configuracion = Column(Text, nullable=False)  # JSON string
    categoria = Column(String(50), nullable=False, index=True)
    dias_semana = Column(Integer)
    activa = Column(Boolean, default=True, index=True)
    publica = Column(Boolean, default=False)
    creada_por = Column(Integer, index=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    version_actual = Column(String(20), default="1.0.0")
    tags = Column(Text)  # JSON array string
    uso_count = Column(Integer, default=0)
    rating_promedio = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    
    # Relationships
    versiones = relationship("PlantillaRutinaVersion", back_populates="plantilla")
    analitica = relationship("PlantillaAnalitica", back_populates="plantilla")
```

#### Migration Management

```python
# alembic/versions/001_initial_tables.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Create templates table
    op.create_table(
        'plantillas_rutina',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('configuracion', sa.Text(), nullable=False),
        sa.Column('categoria', sa.String(length=50), nullable=False),
        sa.Column('dias_semana', sa.Integer(), nullable=True),
        sa.Column('activa', sa.Boolean(), nullable=True),
        sa.Column('publica', sa.Boolean(), nullable=True),
        sa.Column('creada_por', sa.Integer(), nullable=True),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=True),
        sa.Column('fecha_actualizacion', sa.DateTime(), nullable=True),
        sa.Column('version_actual', sa.String(length=20), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('uso_count', sa.Integer(), nullable=True),
        sa.Column('rating_promedio', sa.Float(), nullable=True),
        sa.Column('rating_count', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_plantillas_rutina_id', 'plantillas_rutina', ['id'], unique=False)
    op.create_index('ix_plantillas_rutina_nombre', 'plantillas_rutina', ['nombre'], unique=False)
```

---

## ⚛️ Frontend Development

### React Component Development

#### Component Structure

```typescript
// src/components/templates/TemplateCard.tsx
import React, { useState } from 'react';
import { Card, Badge, Button, Star } from '@/components/ui';
import { Template, TemplateAnalytics } from '@/types';
import { useToast } from '@/hooks/useToast';
import { formatDistanceToNow } from 'date-fns';

interface TemplateCardProps {
  template: Template;
  analytics?: TemplateAnalytics;
  isFavorite: boolean;
  onSelect: () => void;
  onPreview: () => void;
  onFavorite: () => void;
  onRate: (rating: number) => void;
}

export const TemplateCard: React.FC<TemplateCardProps> = ({
  template,
  analytics,
  isFavorite,
  onSelect,
  onPreview,
  onFavorite,
  onRate
}) => {
  const [rating, setRating] = useState(0);
  const { success, error } = useToast();

  const handleRate = (newRating: number) => {
    setRating(newRating);
    onRate(newRating);
    success('Template rated successfully');
  };

  return (
    <Card className="template-card hover:shadow-lg transition-shadow">
      <div className="p-6">
        {/* Header */}
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              {template.nombre}
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              {template.descripcion}
            </p>
          </div>
          <Badge variant={template.activa ? 'success' : 'secondary'}>
            {template.activa ? 'Active' : 'Inactive'}
          </Badge>
        </div>

        {/* Metadata */}
        <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
          <span className="flex items-center gap-1">
            <span className="font-medium">{template.categoria}</span>
          </span>
          {template.dias_semana && (
            <span>{template.dias_semana} days/week</span>
          )}
          <span>
            Created {formatDistanceToNow(new Date(template.fecha_creacion))} ago
          </span>
        </div>

        {/* Tags */}
        {template.tags && template.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {template.tags.map((tag, index) => (
              <Badge key={index} variant="outline" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        )}

        {/* Analytics */}
        {analytics && (
          <div className="flex items-center justify-between mb-4 p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-4 text-sm">
              <span className="flex items-center gap-1">
                <span className="font-medium">{analytics.usos_totales}</span>
                <span className="text-gray-500">uses</span>
              </span>
              <span className="flex items-center gap-1">
                <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                <span className="font-medium">{analytics.rating_promedio.toFixed(1)}</span>
                <span className="text-gray-500">({analytics.rating_count})</span>
              </span>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          <Button onClick={onSelect} className="flex-1">
            Use Template
          </Button>
          <Button variant="outline" onClick={onPreview}>
            Preview
          </Button>
          <Button variant="ghost" size="sm" onClick={onFavorite}>
            <Heart className={`w-4 h-4 ${isFavorite ? 'fill-red-500 text-red-500' : ''}`} />
          </Button>
        </div>

        {/* Rating */}
        <div className="mt-4 pt-4 border-t">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">Rate this template:</span>
            <div className="flex gap-1">
              {[1, 2, 3, 4, 5].map((star) => (
                <Star
                  key={star}
                  className={`w-4 h-4 cursor-pointer transition-colors ${
                    star <= rating
                      ? 'fill-yellow-400 text-yellow-400'
                      : 'text-gray-300 hover:text-yellow-400'
                  }`}
                  onClick={() => handleRate(star)}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
};
```

#### Custom Hooks

```typescript
// src/hooks/useTemplates.ts
import { useState, useEffect, useCallback } from 'react';
import { Template, TemplateFilters, TemplatesResponse } from '@/types';
import { templateAPI } from '@/services/api';
import { useToast } from '@/hooks/useToast';

export const useTemplates = () => {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const { success, error: showError } = useToast();

  const loadTemplates = useCallback(async (
    filters: TemplateFilters = {},
    append: boolean = false
  ) => {
    setLoading(true);
    setError(null);

    try {
      const response: TemplatesResponse = await templateAPI.getTemplates(filters);
      
      if (response.success) {
        setTemplates(prev => 
          append ? [...prev, ...response.templates] : response.templates
        );
        setHasMore(response.has_more);
      } else {
        throw new Error('Failed to load templates');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      showError('Error loading templates');
    } finally {
      setLoading(false);
    }
  }, [showError]);

  const createTemplate = useCallback(async (templateData: Partial<Template>) => {
    setLoading(true);
    try {
      const response = await templateAPI.createTemplate(templateData);
      if (response.success) {
        setTemplates(prev => [response.template, ...prev]);
        success('Template created successfully');
        return response.template;
      }
    } catch (err) {
      showError('Error creating template');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [success, showError]);

  const updateTemplate = useCallback(async (id: number, updates: Partial<Template>) => {
    setLoading(true);
    try {
      const response = await templateAPI.updateTemplate(id, updates);
      if (response.success) {
        setTemplates(prev => 
          prev.map(template => 
            template.id === id ? { ...template, ...response.template } : template
          )
        );
        success('Template updated successfully');
        return response.template;
      }
    } catch (err) {
      showError('Error updating template');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [success, showError]);

  const deleteTemplate = useCallback(async (id: number) => {
    setLoading(true);
    try {
      await templateAPI.deleteTemplate(id);
      setTemplates(prev => prev.filter(template => template.id !== id));
      success('Template deleted successfully');
    } catch (err) {
      showError('Error deleting template');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [success, showError]);

  return {
    templates,
    loading,
    error,
    hasMore,
    loadTemplates,
    createTemplate,
    updateTemplate,
    deleteTemplate
  };
};
```

#### API Service

```typescript
// src/services/api.ts
import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { Template, TemplateFilters, CreateTemplateRequest } from '@/types';

class APIClient {
  private client: AxiosInstance;

  constructor(baseURL: string, apiKey: string) {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        console.log(`Making ${config.method?.toUpperCase()} request to ${config.url}`);
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        return response;
      },
      (error) => {
        if (error.response?.status === 401) {
          // Handle unauthorized
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  async getTemplates(filters: TemplateFilters = {}): Promise<TemplatesResponse> {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, String(value));
      }
    });

    const response: AxiosResponse<TemplatesResponse> = await this.client.get(
      `/api/templates?${params.toString()}`
    );
    return response.data;
  }

  async createTemplate(data: CreateTemplateRequest): Promise<TemplateResponse> {
    const response: AxiosResponse<TemplateResponse> = await this.client.post(
      '/api/templates',
      data
    );
    return response.data;
  }

  async updateTemplate(id: number, data: Partial<Template>): Promise<TemplateResponse> {
    const response: AxiosResponse<TemplateResponse> = await this.client.put(
      `/api/templates/${id}`,
      data
    );
    return response.data;
  }

  async deleteTemplate(id: number): Promise<void> {
    await this.client.delete(`/api/templates/${id}`);
  }

  async generatePreview(id: number, options: PreviewOptions): Promise<PreviewResponse> {
    const response: AxiosResponse<PreviewResponse> = await this.client.post(
      `/api/templates/${id}/preview`,
      options
    );
    return response.data;
  }
}

export const templateAPI = new APIClient(
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  process.env.NEXT_PUBLIC_JWT_KEY || ''
);
```

---

## 🗄️ Database Schema

### Core Tables

#### Templates Table

```sql
CREATE TABLE plantillas_rutina (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    configuracion TEXT NOT NULL, -- JSON configuration
    categoria VARCHAR(50) NOT NULL,
    dias_semana INTEGER,
    activa BOOLEAN DEFAULT TRUE,
    publica BOOLEAN DEFAULT FALSE,
    creada_por INTEGER REFERENCES usuarios(id),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version_actual VARCHAR(20) DEFAULT '1.0.0',
    tags TEXT, -- JSON array
    uso_count INTEGER DEFAULT 0,
    rating_promedio DECIMAL(3,2) DEFAULT 0.0,
    rating_count INTEGER DEFAULT 0
);

-- Indexes
CREATE INDEX idx_plantillas_rutina_nombre ON plantillas_rutina(nombre);
CREATE INDEX idx_plantillas_rutina_categoria ON plantillas_rutina(categoria);
CREATE INDEX idx_plantillas_rutina_activa ON plantillas_rutina(activa);
CREATE INDEX idx_plantillas_rutina_publica ON plantillas_rutina(publica);
CREATE INDEX idx_plantillas_rutina_creada_por ON plantillas_rutina(creada_por);
```

#### Template Versions Table

```sql
CREATE TABLE plantillas_rutina_version (
    id SERIAL PRIMARY KEY,
    plantilla_id INTEGER REFERENCES plantillas_rutina(id) ON DELETE CASCADE,
    version VARCHAR(20) NOT NULL,
    configuracion TEXT NOT NULL,
    creado_por INTEGER REFERENCES usuarios(id),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notas TEXT
);

CREATE INDEX idx_plantillas_rutina_version_plantilla_id ON plantillas_rutina_version(plantilla_id);
CREATE UNIQUE INDEX idx_plantillas_rutina_version_unique ON plantillas_rutina_version(plantilla_id, version);
```

#### Template Analytics Table

```sql
CREATE TABLE plantillas_analitica (
    id SERIAL PRIMARY KEY,
    plantilla_id INTEGER REFERENCES plantillas_rutina(id) ON DELETE CASCADE,
    fecha DATE NOT NULL,
    usos_diarios INTEGER DEFAULT 0,
    usuarios_unicos INTEGER DEFAULT 0,
    rating_promedio DECIMAL(3,2),
    evaluaciones INTEGER DEFAULT 0,
    creado_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_plantillas_analitica_plantilla_id ON plantillas_analitica(plantilla_id);
CREATE INDEX idx_plantillas_analitica_fecha ON plantillas_analitica(fecha);
```

#### User Favorites Table

```sql
CREATE TABLE usuario_favoritos (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
    plantilla_id INTEGER REFERENCES plantillas_rutina(id) ON DELETE CASCADE,
    fecha_agregado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(usuario_id, plantilla_id)
);

CREATE INDEX idx_usuario_favoritos_usuario_id ON usuario_favoritos(usuario_id);
CREATE INDEX idx_usuario_favoritos_plantilla_id ON usuario_favoritos(plantilla_id);
```

### Database Functions

#### Update Usage Count

```sql
CREATE OR REPLACE FUNCTION incrementar_uso_plantilla(plantilla_id_param INTEGER)
RETURNS VOID AS $$
BEGIN
    UPDATE plantillas_rutina 
    SET uso_count = uso_count + 1,
        fecha_actualizacion = CURRENT_TIMESTAMP
    WHERE id = plantilla_id_param;
    
    -- Update analytics
    INSERT INTO plantillas_analitica (plantilla_id, fecha, usos_diarios)
    VALUES (plantilla_id_param, CURRENT_DATE, 1)
    ON CONFLICT (plantilla_id, fecha) 
    DO UPDATE SET 
        usos_diarios = plantillas_analitica.usos_diarios + 1;
END;
$$ LANGUAGE plpgsql;
```

#### Update Rating

```sql
CREATE OR REPLACE FUNCTION actualizar_rating_plantilla(
    plantilla_id_param INTEGER,
    nuevo_rating INTEGER
)
RETURNS VOID AS $$
DECLARE
    total_evaluaciones INTEGER;
    suma_ratings INTEGER;
BEGIN
    -- Get current ratings
    SELECT rating_count, COALESCE(rating_promedio * rating_count, 0)
    INTO total_evaluaciones, suma_ratings
    FROM plantillas_rutina
    WHERE id = plantilla_id_param;
    
    -- Update with new rating
    total_evaluaciones := total_evaluaciones + 1;
    suma_ratings := suma_ratings + nuevo_rating;
    
    UPDATE plantillas_rutina 
    SET 
        rating_count = total_evaluaciones,
        rating_promedio = ROUND(suma_ratings::DECIMAL / total_evaluaciones, 2),
        fecha_actualizacion = CURRENT_TIMESTAMP
    WHERE id = plantilla_id_param;
END;
$$ LANGUAGE plpgsql;
```

---

## 🧪 Testing

### Backend Testing

#### Unit Tests

```python
# tests/test_template_service.py
import pytest
from unittest.mock import Mock, patch
from src.services.template_service import TemplateService
from src.models.orm_models import PlantillaRutina

class TestTemplateService:
    @pytest.fixture
    def mock_db(self):
        return Mock()
    
    @pytest.fixture
    def template_service(self, mock_db):
        return TemplateService(mock_db)
    
    def test_create_template_success(self, template_service, mock_db):
        # Arrange
        template_data = {
            "nombre": "Test Template",
            "configuracion": {"version": "1.0.0"},
            "categoria": "test"
        }
        
        mock_template = Mock(spec=PlantillaRutina)
        mock_template.id = 1
        template_service.repository.create = Mock(return_value=mock_template)
        
        # Act
        result = template_service.create_template(template_data)
        
        # Assert
        assert result.id == 1
        template_service.repository.create.assert_called_once()
    
    def test_get_template_not_found(self, template_service):
        # Arrange
        template_service.repository.get_by_id = Mock(return_value=None)
        
        # Act & Assert
        with pytest.raises(TemplateNotFoundError):
            template_service.get_template_by_id(999)
```

#### Integration Tests

```python
# tests/test_api_integration.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

class TestTemplateAPIIntegration:
    def test_full_template_lifecycle(self):
        # Create template
        create_response = client.post(
            "/api/templates",
            json={
                "nombre": "Integration Test Template",
                "configuracion": {"version": "1.0.0"},
                "categoria": "test"
            }
        )
        assert create_response.status_code == 200
        template_id = create_response.json()["template"]["id"]
        
        # Get template
        get_response = client.get(f"/api/templates/{template_id}")
        assert get_response.status_code == 200
        assert get_response.json()["template"]["nombre"] == "Integration Test Template"
        
        # Update template
        update_response = client.put(
            f"/api/templates/{template_id}",
            json={"nombre": "Updated Template"}
        )
        assert update_response.status_code == 200
        
        # Delete template
        delete_response = client.delete(f"/api/templates/{template_id}")
        assert delete_response.status_code == 200
```

### Frontend Testing

#### Component Tests

```typescript
// src/components/__tests__/TemplateCard.test.tsx
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { TemplateCard } from '../TemplateCard';
import { Template } from '@/types';

const mockTemplate: Template = {
  id: 1,
  nombre: 'Test Template',
  descripcion: 'Test Description',
  categoria: 'test',
  activa: true,
  publica: false,
  fecha_creacion: '2023-01-01T00:00:00Z',
  uso_count: 10,
  rating_promedio: 4.5,
  rating_count: 5,
  tags: ['test', 'template']
};

describe('TemplateCard', () => {
  it('renders template information correctly', () => {
    render(
      <TemplateCard
        template={mockTemplate}
        isFavorite={false}
        onSelect={jest.fn()}
        onPreview={jest.fn()}
        onFavorite={jest.fn()}
        onRate={jest.fn()}
      />
    );

    expect(screen.getByText('Test Template')).toBeInTheDocument();
    expect(screen.getByText('Test Description')).toBeInTheDocument();
    expect(screen.getByText('test')).toBeInTheDocument();
  });

  it('calls onSelect when Use Template button is clicked', () => {
    const mockOnSelect = jest.fn();
    render(
      <TemplateCard
        template={mockTemplate}
        isFavorite={false}
        onSelect={mockOnSelect}
        onPreview={jest.fn()}
        onFavorite={jest.fn()}
        onRate={jest.fn()}
      />
    );

    fireEvent.click(screen.getByText('Use Template'));
    expect(mockOnSelect).toHaveBeenCalledTimes(1);
  });

  it('displays rating correctly', () => {
    render(
      <TemplateCard
        template={mockTemplate}
        analytics={{ rating_promedio: 4.5, rating_count: 5 }}
        isFavorite={false}
        onSelect={jest.fn()}
        onPreview={jest.fn()}
        onFavorite={jest.fn()}
        onRate={jest.fn()}
      />
    );

    expect(screen.getByText('4.5')).toBeInTheDocument();
    expect(screen.getByText('(5)')).toBeInTheDocument();
  });
});
```

#### Hook Tests

```typescript
// src/hooks/__tests__/useTemplates.test.ts
import { renderHook, act } from '@testing-library/react';
import { useTemplates } from '../useTemplates';
import { templateAPI } from '@/services/api';

jest.mock('@/services/api');

const mockTemplateAPI = templateAPI as jest.Mocked<typeof templateAPI>;

describe('useTemplates', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('loads templates successfully', async () => {
    const mockTemplates = [
      { id: 1, nombre: 'Template 1' },
      { id: 2, nombre: 'Template 2' }
    ];

    mockTemplateAPI.getTemplates.mockResolvedValue({
      success: true,
      templates: mockTemplates,
      total: 2,
      has_more: false
    });

    const { result } = renderHook(() => useTemplates());

    await act(async () => {
      await result.current.loadTemplates();
    });

    expect(result.current.templates).toEqual(mockTemplates);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('handles loading errors', async () => {
    mockTemplateAPI.getTemplates.mockRejectedValue(new Error('API Error'));

    const { result } = renderHook(() => useTemplates());

    await act(async () => {
      await result.current.loadTemplates();
    });

    expect(result.current.error).toBe('API Error');
    expect(result.current.loading).toBe(false);
  });
});
```

---

## 🚀 Deployment

### Docker Configuration

#### Dockerfile

```dockerfile
# apps/webapp-api/Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: ./apps/webapp-api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/ironhub
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      - db
      - redis
    volumes:
      - ./uploads:/app/uploads
    restart: unless-stopped

  admin-web:
    build: ./apps/admin-web
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - api
    restart: unless-stopped

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=ironhub
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    restart: unless-stopped

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - api
      - admin-web
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### Kubernetes Deployment

#### Deployment Manifest

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ironhub-api
  labels:
    app: ironhub-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ironhub-api
  template:
    metadata:
      labels:
        app: ironhub-api
    spec:
      containers:
      - name: api
        image: ironhub/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: ironhub-secrets
              key: database-url
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: ironhub-secrets
              key: jwt-secret
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: ironhub-api-service
spec:
  selector:
    app: ironhub-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
```

### CI/CD Pipeline

#### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        pip install -r apps/webapp-api/requirements.txt
        pip install -r apps/webapp-api/requirements-test.txt
    
    - name: Run tests
      run: |
        cd apps/webapp-api
        python run_tests.py --coverage
    
    - name: Upload coverage
      uses: codecov/codecov-action@v1

  build-and-deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Build Docker image
      run: |
        docker build -t ironhub/api:${{ github.sha }} ./apps/webapp-api
        docker tag ironhub/api:${{ github.sha }} ironhub/api:latest
    
    - name: Push to registry
      run: |
        echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
        docker push ironhub/api:${{ github.sha }}
        docker push ironhub/api:latest
    
    - name: Deploy to Kubernetes
      run: |
        echo ${{ secrets.KUBECONFIG }} | base64 -d > kubeconfig
        export KUBECONFIG=kubeconfig
        kubectl set image deployment/ironhub-api api=ironhub/api:${{ github.sha }}
        kubectl rollout status deployment/ironhub-api
```

---

## 🤝 Contributing

### Development Workflow

#### 1. Setup Development Environment

```bash
# Clone repository
git clone https://github.com/your-org/ironhub-templates.git
cd ironhub-templates

# Setup development environment
./scripts/setup-dev.sh

# Install pre-commit hooks
pre-commit install
```

#### 2. Create Feature Branch

```bash
# Create feature branch
git checkout -b feature/template-analytics

# Make your changes
# ... (work on your feature)

# Commit changes
git add .
git commit -m "feat: add template analytics dashboard"
```

#### 3. Testing

```bash
# Run all tests
python run_tests.py

# Run linting
python run_tests.py --lint

# Run specific tests
python run_tests.py --specific tests/test_analytics.py
```

#### 4. Submit Pull Request

```bash
# Push to your fork
git push origin feature/template-analytics

# Create pull request on GitHub
# Include description, tests run, and screenshots if applicable
```

### Code Standards

#### Python Standards

- Follow PEP 8 style guide
- Use type hints for all functions
- Write comprehensive docstrings
- Keep functions small and focused
- Use meaningful variable names

```python
# Good example
def create_template(
    db: Session,
    template_data: TemplateCreate,
    user_id: int
) -> Template:
    """
    Create a new workout template.
    
    Args:
        db: Database session
        template_data: Template creation data
        user_id: ID of the creating user
        
    Returns:
        Created template object
        
    Raises:
        ValidationError: If template data is invalid
    """
    # Implementation
```

#### TypeScript Standards

- Use TypeScript for all new code
- Define interfaces for all data structures
- Use functional components with hooks
- Follow React best practices

```typescript
// Good example
interface TemplateCardProps {
  template: Template;
  analytics?: TemplateAnalytics;
  onSelect: () => void;
}

export const TemplateCard: React.FC<TemplateCardProps> = ({
  template,
  analytics,
  onSelect
}) => {
  // Implementation
};
```

#### Testing Standards

- Write tests for all new features
- Maintain 80% code coverage
- Use descriptive test names
- Test both happy path and error cases

```python
# Good example
class TestTemplateService:
    def test_create_template_with_valid_data_should_return_template(self):
        """Test creating template with valid data returns template."""
        # Arrange
        template_data = {"nombre": "Test", "categoria": "strength"}
        
        # Act
        result = self.service.create_template(template_data)
        
        # Assert
        assert result.nombre == "Test"
        assert result.categoria == "strength"
```

### Documentation Standards

- Update documentation for all API changes
- Include examples in docstrings
- Keep README files current
- Document complex business logic

### Release Process

#### Version Management

- Use semantic versioning (MAJOR.MINOR.PATCH)
- Update version numbers in all relevant files
- Create release notes for each version
- Tag releases in Git

#### Release Checklist

1. **Code Quality**
   - [ ] All tests passing
   - [ ] Code coverage ≥ 80%
   - [ ] No linting errors
   - [ ] Security scan passed

2. **Documentation**
   - [ ] API docs updated
   - [ ] User guide updated
   - [ ] Changelog updated
   - [ ] Migration notes added

3. **Testing**
   - [ ] Unit tests pass
   - [ ] Integration tests pass
   - [ ] Manual testing completed
   - [ ] Performance tests pass

4. **Deployment**
   - [ ] Staging deployment successful
   - [ ] Database migrations tested
   - [ ] Rollback plan ready
   - [ ] Monitoring configured

---

## 📞 Getting Help

### Development Resources

- **API Documentation**: http://localhost:8000/docs
- **Database Schema**: docs/database-schema.md
- **Component Library**: Storybook at http://localhost:6006
- **Development Guide**: docs/development.md

### Support Channels

- **Slack**: #ironhub-developers
- **Email**: dev-support@ironhub.com
- **GitHub Issues**: Create issue for bugs/features
- **Office Hours**: Weekly on Tuesdays at 2 PM EST

### Code Review Guidelines

- Review for code quality and standards
- Check for security vulnerabilities
- Verify test coverage
- Ensure documentation is updated
- Provide constructive feedback

---

*This developer guide is updated regularly. Check for new versions monthly.*

**Last Updated**: January 2024
**Version**: 1.0

For the most current information, visit our developer portal at dev.ironhub.com
