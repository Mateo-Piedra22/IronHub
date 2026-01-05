# IronHub - Multi-Tenant Gym Management System

## Monorepo Structure

```
apps/
├── admin-api/     → FastAPI | admin-api.ironhub.motiona.xyz
├── webapp-api/    → FastAPI | api.{gym}.ironhub.motiona.xyz
├── admin-web/     → Next.js | admin.ironhub.motiona.xyz
├── webapp-web/    → Next.js | {gym}.ironhub.motiona.xyz
└── landing/       → Next.js | ironhub.motiona.xyz
```

## Multi-Tenant Architecture

Each gym gets:
- **Dedicated Database** (Neon PostgreSQL)
- **Subdomain** ({gym}.ironhub.motiona.xyz)
- **B2 Storage Prefix** (assets/{gym}/)
- **54 Tables** (usuarios, pagos, clases, rutinas, etc.)

## Deploy to Vercel

Each app deploys independently. Link each folder as a separate Vercel project:

```bash
# From each app directory
vercel --prod
```

### Environment Variables

See `.env.example` in each app for required variables.

## Development

```bash
# Frontend apps
npm install
npm run dev

# Backend APIs
pip install -r requirements.txt
uvicorn src.main:app --reload
```

## Tech Stack

- **Frontend**: Next.js 15, React 19, Tailwind CSS
- **Backend**: FastAPI, SQLAlchemy, PostgreSQL
- **DB Hosting**: Neon.tech
- **Storage**: Backblaze B2
- **Deploy**: Vercel
