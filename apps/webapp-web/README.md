# IronHub Webapp Frontend

Next.js frontend for gym tenant applications (`{tenant}.ironhub.motiona.xyz`).

## Tech Stack

- **Framework**: Next.js 15 with App Router
- **State**: TanStack Query + Zustand
- **Styling**: Tailwind CSS (IronHub design system)
- **Animations**: Framer Motion
- **Icons**: Lucide React

## Features

- 🔐 **Login**: DNI + PIN authentication
- 📊 **Dashboard**: Membership status, quick stats
- 💳 **Payments**: Payment history with receipts
- 🏃 **Attendance**: Check-in/out history with stats
- 🏋️ **Routines**: View assigned workout plans
- 👤 **Profile**: Personal information

## Pages

| Route | Description |
|-------|-------------|
| `/` | Login page |
| `/dashboard` | Member dashboard home |
| `/dashboard/payments` | Payment history |
| `/dashboard/attendance` | Attendance history |
| `/dashboard/routines` | Assigned workout routine |
| `/dashboard/profile` | Member profile |

## Getting Started

```bash
# Install dependencies
pnpm install

# Run development server
pnpm dev   # Runs on port 3002
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Webapp API URL (api.ironhub.motiona.xyz) |
| `NEXT_PUBLIC_TENANT_DOMAIN` | Base domain for tenants |

## Structure

```
apps/webapp-web/
├── src/
│   └── app/
│       ├── globals.css
│       ├── layout.tsx
│       ├── providers.tsx
│       ├── page.tsx                    # Login
│       └── dashboard/
│           ├── layout.tsx              # Navigation layout
│           ├── page.tsx                # Dashboard home
│           ├── payments/page.tsx       # Payment history
│           ├── attendance/page.tsx     # Attendance history
│           ├── routines/page.tsx       # Workout routines
│           └── profile/page.tsx        # Member profile
├── tailwind.config.js
└── package.json
```

## Multi-Tenancy

The app supports multi-tenancy via subdomain routing:
- `ironfitness.ironhub.motiona.xyz` → Iron Fitness gym
- `powergym.ironhub.motiona.xyz` → PowerGym

Tenant is extracted from hostname and sent to API.

## Deployment

Deploy to Vercel with wildcard domain:

1. Create Vercel project
2. Set root directory: `apps/webapp-web`
3. Configure domain: `*.ironhub.motiona.xyz`
4. Add environment variables

---

Developed by **MotionA** © 2026
