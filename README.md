# IronHub - Gym Management Platform

A multi-tenant SaaS platform for gym management built with modern technologies.

## Architecture

```
IronHub/
├── apps/
│   ├── admin-api/       # Super-admin backend (FastAPI)
│   ├── admin-web/       # Super-admin dashboard (Next.js)
│   ├── landing/         # Public landing page (Next.js)
│   ├── webapp-api/      # Tenant backend API (FastAPI)
│   └── webapp-web/      # Tenant management dashboard (Next.js)
├── core/                # Shared Python modules
└── deprecated/          # Legacy system (reference only)
```

## Technology Stack

### Backend
- Python 3.11+
- FastAPI
- SQLAlchemy + PostgreSQL
- Backblaze B2 + Cloudflare CDN

### Frontend
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Framer Motion

## Multi-Tenant Architecture

Each gym (tenant) operates with:
- Isolated database per tenant
- Subdomain-based routing (e.g., `mygym.ironhub.xyz`)
- Centralized admin database for subscription management

### Tenant Resolution
1. Request arrives at subdomain
2. Middleware extracts tenant from Host header
3. Tenant status verified against admin database
4. Tenant-specific database connection established
5. Request processed with isolated data

## Environment Variables

### Required for All Apps

```env
# Database
DB_HOST=
DB_PORT=5432
DB_USER=
DB_PASSWORD=
DB_SSLMODE=require

# Admin Database
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

# Security
SESSION_SECRET=
```

## Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- pnpm (recommended)

### Backend Setup

```bash
cd apps/webapp-api
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd apps/webapp-web
pnpm install
pnpm dev
```

## Project Structure

See individual app README files for detailed documentation:
- [webapp-api/README.md](apps/webapp-api/README.md)
- [webapp-web/README.md](apps/webapp-web/README.md)
- [admin-api/README.md](apps/admin-api/README.md)
- [admin-web/README.md](apps/admin-web/README.md)
- [landing/README.md](apps/landing/README.md)

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

## License

Proprietary - MotionA - Mateo Piedrabuena 2026
