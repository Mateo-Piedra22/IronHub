# webapp-api

Multi-tenant FastAPI backend for gym management.

## Overview

This API serves as the backend for individual gym tenants. It handles:
- User management (socios, profesores)
- Payment processing and receipts
- Attendance tracking with QR check-in
- Routine and exercise management
- WhatsApp integration
- Class scheduling

## Project Structure

```
src/
├── main.py              # FastAPI application entry point
├── dependencies.py      # Dependency injection
├── utils.py             # Utility functions
├── models.py            # Pydantic/SQLAlchemy models
├── database/
│   ├── connection.py        # Global database connection
│   ├── tenant_connection.py # Multi-tenant connection manager
│   └── raw_manager.py       # Raw PostgreSQL operations
├── routers/
│   ├── admin.py         # Administrative operations
│   ├── attendance.py    # Check-in and attendance
│   ├── auth.py          # Authentication
│   ├── exercises.py     # Exercise CRUD
│   ├── gym.py           # Gym config, classes, routines
│   ├── inscripciones.py # Enrollments and waitlist
│   ├── payments.py      # Payments and receipts
│   ├── profesores.py    # Professor management
│   ├── public.py        # Public endpoints
│   ├── reports.py       # KPIs and reports
│   ├── users.py         # User management
│   └── whatsapp.py      # WhatsApp messaging
└── services/
    ├── storage_service.py  # B2 + Cloudflare CDN
    ├── user_service.py     # User business logic
    └── teacher_service.py  # Professor business logic
```

## Key Routers

| Router | Endpoints | Description |
|--------|-----------|-------------|
| payments.py | 24 | Payment CRUD, receipts, quota types |
| gym.py | 53 | Config, classes, blocks, routines |
| whatsapp.py | 22 | Messaging, webhooks, history |
| users.py | 18 | User CRUD, states, tags |
| profesores.py | 24 | Professor sessions, schedules |

## Authentication

Uses session-based authentication with role hierarchy:
- `dueno/owner`: Full access
- `profesor`: Limited management access
- `socio`: User panel only

### Security Dependencies

```python
require_gestion_access  # Owner or profesor
require_owner           # Owner only
require_profesor        # Profesor or higher
require_user_auth       # Authenticated user
```

## Multi-Tenant Database

Tenant connections are managed via `tenant_connection.py`:
- Tenant resolved from subdomain
- Status verified (active, suspended, maintenance)
- Connection pooled with LRU eviction (max 50 tenants)
- SSL required for all connections

## Environment Variables

```env
# Database
DB_HOST=
DB_PORT=5432
DB_USER=
DB_PASSWORD=
DB_SSLMODE=require

# Tenant suffix
TENANT_DB_SUFFIX=_db

# Admin DB for tenant resolution
ADMIN_DB_HOST=
ADMIN_DB_NAME=ironhub_admin
ADMIN_DB_USER=
ADMIN_DB_PASSWORD=

# Storage
B2_KEY_ID=
B2_APP_KEY=
B2_BUCKET_NAME=
B2_BUCKET_ID=
CLOUDFLARE_CDN_URL=

# Session
SESSION_SECRET=
```

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn src.main:app --reload --port 8000

# Run with specific host
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## API Documentation

When running, access:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Deployment

Uses Vercel Edge Functions with Python runtime.
See root [DEPLOYMENT.md](../../DEPLOYMENT.md) for instructions.
