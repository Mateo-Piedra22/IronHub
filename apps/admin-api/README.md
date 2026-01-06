# admin-api

Super-admin FastAPI backend for platform management.

## Overview

Centralized administration API for managing:
- Gym (tenant) registration and lifecycle
- Subscription and payment tracking
- System-wide maintenance
- Audit logging

## Project Structure

```
src/
├── main.py              # FastAPI application
├── services/
│   └── admin_service.py # Core admin logic (1800+ lines)
├── database/
│   └── raw_manager.py   # PostgreSQL operations
├── models/
│   └── orm_models.py    # SQLAlchemy models
├── security_utils.py    # Password hashing, API keys
└── secure_config.py     # Environment configuration
```

## Key Features

### Gym Management
- Create, update, delete gyms
- Subdomain validation and suggestions
- Database provisioning per tenant

### Subscription Management
- Payment tracking
- Plan upgrades/downgrades
- Expiration alerts

### Status Control
- Active / Suspended / Maintenance states
- Scheduled maintenance windows
- Hard suspend for non-payment

### Security
- Password hashing (bcrypt)
- API key generation
- Audit trail logging

## AdminService Functions (64 total)

| Category | Functions |
|----------|-----------|
| Gym CRUD | 8 |
| Payments | 4 |
| Suspensions | 5 |
| Maintenance | 4 |
| Audit | 3 |
| Security | 6 |

## Environment Variables

```env
# Admin Database
ADMIN_DB_HOST=
ADMIN_DB_NAME=ironhub_admin
ADMIN_DB_USER=
ADMIN_DB_PASSWORD=
ADMIN_DB_SSLMODE=require

# Security
ADMIN_PASSWORD=
SESSION_SECRET=
```

## Running Locally

```bash
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8001
```

## Database Schema

The admin database contains:
- `gyms`: Tenant registry
- `gym_payments`: Payment history
- `admin_audit_log`: Action history
- `admin_users`: Platform admins
