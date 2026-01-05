# IronHub Webapp API

FastAPI backend for gym tenant applications (`{tenant}.ironhub.motiona.xyz`).

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL + SQLAlchemy (per-tenant)
- **Multi-Tenancy**: Database per tenant

## Features

- 👤 User authentication (gym members)
- 📋 User management
- 💳 Payment tracking
- 🏃 Attendance logging
- 🏋️ Routines & exercises
- 📱 WhatsApp notifications

## Getting Started

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn src.main:app --reload --port 8001
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ADMIN_DB_*` | Admin database for tenant lookup |
| `TENANT_BASE_DOMAIN` | Base domain (ironhub.motiona.xyz) |

## Deployment

**Domain**: `api.ironhub.motiona.xyz`

---

Developed by **MotionA** © 2026
