# IronHub Template System - Complete Documentation

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [API Documentation](#api-documentation)
6. [Frontend Integration](#frontend-integration)
7. [Excel Migration](#excel-migration)
8. [Testing](#testing)
9. [Deployment](#deployment)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

The IronHub Template System is a comprehensive solution for creating, managing, and using dynamic workout templates. It provides:

- **Dynamic Template Engine**: Create customizable workout templates with variables and sections
- **Excel Migration Tools**: Convert existing Excel-based templates to the new system
- **PDF Generation**: Generate professional PDFs from templates and routines
- **Analytics & Tracking**: Monitor template usage and performance
- **Multi-tenant Support**: Support for multiple gyms and users
- **REST API**: Complete API for integration with frontend applications

### Key Features

- 🎨 **Visual Template Builder**: Create templates with drag-and-drop interface
- 📊 **Real-time Analytics**: Track usage, ratings, and performance
- 🔄 **Version Control**: Maintain template versions and history
- 📱 **Mobile Responsive**: Works seamlessly on all devices
- 🔐 **Role-based Access**: Different permissions for admins, trainers, and users
- 📤 **Import/Export**: Migrate templates from Excel and other formats

---

## 🏗️ Architecture

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Admin Web    │    │   User Webapp   │    │   Mobile App    │
│                 │    │                 │    │                 │
│ • Template Mgmt │    │ • Template Use  │    │ • Routine View  │
│ • Analytics     │    │ • Routine Mgmt  │    │ • QR Scanning   │
│ • User Mgmt     │    │ • Progress      │    │ • Notifications │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Backend API   │
                    │                 │
                    │ • Template CRUD │
                    │ • PDF Generation│
                    │ • Analytics     │
                    │ • Migration     │
                    │ • Auth & AuthZ  │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Database      │
                    │                 │
                    │ • Templates     │
                    │ • Users         │
                    │ • Analytics     │
                    │ • Gyms          │
                    └─────────────────┘
```

### Technology Stack

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL
- **Frontend**: React, TypeScript, Tailwind CSS
- **PDF Generation**: Matplotlib, ReportLab
- **Excel Processing**: openpyxl, pandas
- **Testing**: pytest, coverage
- **Deployment**: Docker, Kubernetes

---

## 🚀 Installation

### Prerequisites

- Python 3.9+
- PostgreSQL 13+
- Node.js 16+
- Redis 6+

### Backend Installation

1. **Clone the repository**
```bash
git clone https://github.com/your-org/ironhub-templates.git
cd ironhub-templates/apps/webapp-api
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
pip install -r requirements-test.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Run database migrations**
```bash
alembic upgrade head
```

6. **Start the server**
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Installation

1. **Navigate to frontend directory**
```bash
cd apps/admin-web  # or apps/webapp-web
```

2. **Install dependencies**
```bash
npm install
```

3. **Configure environment**
```bash
cp .env.example .env.local
# Edit .env.local with your configuration
```

4. **Start development server**
```bash
npm run dev
```

---

## ⚙️ Configuration

### Environment Variables

#### Backend (.env)
```env
# Database
DATABASE_URL=postgresql://user:password@localhost/ironhub
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# File Storage
UPLOAD_DIR=/app/uploads
MAX_FILE_SIZE=10485760  # 10MB

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# External Services
PDF_GENERATION_TIMEOUT=30
MIGRATION_TIMEOUT=300
```

#### Frontend (.env.local)
```env
# API
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Authentication
NEXT_PUBLIC_JWT_KEY=your-jwt-key

# Features
NEXT_PUBLIC_ENABLE_ANALYTICS=true
NEXT_PUBLIC_ENABLE_MIGRATION=true
NEXT_PUBLIC_ENABLE_QR_SCANNING=true

# UI
NEXT_PUBLIC_THEME=light
NEXT_PUBLIC_LANGUAGE=es
```

---

## 📚 API Documentation

### Authentication

All API endpoints require JWT authentication:

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     https://api.ironhub.com/api/templates
```

### Template Endpoints

#### Get Templates
```http
GET /api/templates?query=strength&category=fuerza&limit=20&offset=0
```

#### Create Template
```http
POST /api/templates
Content-Type: application/json

{
  "nombre": "New Template",
  "configuracion": {
    "version": "1.0.0",
    "metadata": {
      "name": "New Template",
      "description": "A new workout template"
    },
    "sections": [...],
    "variables": {...},
    "styling": {...}
  },
  "descripcion": "Template description",
  "categoria": "general",
  "dias_semana": 3,
  "activa": true,
  "publica": false,
  "tags": ["new", "template"]
}
```

#### Generate Preview
```http
POST /api/templates/{id}/preview
Content-Type: application/json

{
  "format": "pdf",
  "quality": "high",
  "show_watermark": false,
  "show_metadata": true,
  "multi_page": true
}
```

### Migration Endpoints

#### Upload and Migrate Excel
```http
POST /api/migration/upload
Content-Type: multipart/form-data

file: [excel file]
template_name: "Migrated Template"
description: "Template migrated from Excel"
category: "strength"
auto_save: true
```

---

## 🧪 Testing

### Running Tests

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
python run_tests.py

# Run with coverage
python run_tests.py --coverage

# Run specific test type
python run_tests.py --unit
python run_tests.py --integration
python run_tests.py --api
```

### Test Structure

```
tests/
├── test_template_service.py     # Template service tests
├── test_pdf_service.py          # PDF service tests
├── test_migration_api.py        # Migration API tests
├── conftest.py                  # Test configuration
└── fixtures/                    # Test data fixtures
```

---

## 🚀 Deployment

### Docker Deployment

1. **Build Docker Image**
```bash
docker build -t ironhub-templates:latest .
```

2. **Run with Docker Compose**
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/ironhub
    depends_on:
      - db
  
  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=ironhub
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

---

## 🔧 Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check database connection
python -c "
from sqlalchemy import create_engine
engine = create_engine('postgresql://user:pass@localhost/db')
print('Connection successful')
"
```

#### PDF Generation Issues
```bash
# Check matplotlib backend
python -c "
import matplotlib
print('Backend:', matplotlib.get_backend())
matplotlib.use('Agg')  # Use non-interactive backend
"
```

---

## 📝 Contributing

### Development Setup

1. **Fork the repository**
2. **Create feature branch**
```bash
git checkout -b feature/new-feature
```

3. **Make changes and test**
```bash
python run_tests.py
python run_tests.py --lint
```

4. **Submit pull request**

---

## 📄 License

This project is licensed under the MIT License.

---

*Last updated: January 2024*
