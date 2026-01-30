# IronHub

Plataforma multi-tenant para gestión de gimnasios (SaaS). Cada gimnasio opera con su propia base de datos (tenant DB) y un panel superadmin administra el ciclo de vida (alta, estado, suscripción, mantenimiento).

## Documentación

La documentación completa vive en [docs/README.md](docs/README.md).

## Estructura del repositorio

```
IronHub/
├── apps/
│   ├── admin-api/        API superadmin (FastAPI)
│   ├── admin-web/        Panel superadmin (Next.js)
│   ├── webapp-api/       API tenant (FastAPI)
│   ├── webapp-web/       App tenant (Next.js)
│   └── landing/          Landing pública (Next.js)
├── docs/                 Documentación (enterprise)
└── deprecated/           Referencia histórica (no se deployea)
```

## Inicio rápido (desarrollo)

**Backend tenant (webapp-api)**

```bash
cd apps/webapp-api
python -m venv venv
venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

**Backend superadmin (admin-api)**

```bash
cd apps/admin-api
python -m venv venv
venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8002
```

**Frontends**

```bash
cd apps/admin-web
npm install
npm run dev
```

```bash
cd apps/webapp-web
npm install
npm run dev
```

## Migraciones

- Tenant DBs (todas las DBs de gimnasios): ver [docs/database/migrations.md](docs/database/migrations.md).
- Validación de schema e idempotencia: ver [docs/database/schema-audit.md](docs/database/schema-audit.md).
- Deploy sin pasos manuales: ver [docs/operations/auto-migrations.md](docs/operations/auto-migrations.md).
- Operación del panel superadmin: ver [docs/operations/admin-panel.md](docs/operations/admin-panel.md).

## Licencia

Proprietary - MotionA - Mateo Piedrabuena (2026)
