# IronHub Admin API

FastAPI backend for the IronHub admin panel.

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL + SQLAlchemy
- **Cache**: Redis (optional)
- **Auth**: Session-based

## Features

- 🔐 Admin authentication
- 🏢 Gym CRUD operations
- 💾 Database provisioning (Neon)
- 📊 Analytics endpoints
- 📱 WhatsApp configuration

## Getting Started

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn src.main:app --reload --port 8000
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Description |
|----------|-------------|
| `ADMIN_DB_HOST` | Admin database host |
| `ADMIN_DB_PORT` | Admin database port |
| `ADMIN_DB_NAME` | Admin database name |
| `ADMIN_DB_USER` | Admin database user |
| `ADMIN_DB_PASSWORD` | Admin database password |
| `ADMIN_SECRET` | Admin panel secret key |
| `NEON_API_TOKEN` | Neon API token for DB provisioning |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/login` | Admin login |
| POST | `/logout` | Admin logout |
| GET | `/gyms` | List all gyms |
| POST | `/gyms` | Create new gym |
| GET | `/gyms/{id}` | Get gym details |
| PUT | `/gyms/{id}` | Update gym |
| DELETE | `/gyms/{id}` | Delete gym |
| GET | `/metrics` | Dashboard metrics |

## Deployment

Deploy to Vercel as a Python serverless function:

1. Create new Vercel project
2. Set root directory to `apps/admin-api`
3. Add environment variables
4. Deploy

**Domain**: `api-admin.ironhub.motiona.xyz`

---

Developed by **MotionA** © 2026
