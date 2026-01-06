# admin-web

Next.js super-admin dashboard for platform management.

## Overview

Platform administration dashboard for:
- Managing gym tenants
- Tracking subscriptions
- Viewing system metrics
- Handling support requests

## Project Structure

```
src/
├── app/
│   ├── layout.tsx
│   ├── page.tsx          # Dashboard
│   ├── gyms/             # Gym management
│   ├── payments/         # Payment tracking
│   ├── settings/         # Platform settings
│   └── audit/            # Audit logs
├── components/
│   └── ui/               # Shared components
└── lib/
    ├── api.ts            # API client
    └── utils.ts          # Utilities
```

## Key Pages

| Route | Description |
|-------|-------------|
| / | Platform dashboard |
| /gyms | Gym listing and management |
| /gyms/[id] | Individual gym details |
| /payments | Payment history |
| /audit | Audit log viewer |
| /settings | Platform configuration |

## Environment Variables

```env
NEXT_PUBLIC_API_URL=http://localhost:8001
```

## Development

```bash
pnpm install
pnpm dev
```

## Deployment

Deploys to Vercel at `admin.ironhub.motiona.xyz`.
See root [DEPLOYMENT.md](../../DEPLOYMENT.md) for instructions.
