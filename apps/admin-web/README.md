# IronHub Admin Panel

Modern admin dashboard for managing the IronHub gym management platform.

## Tech Stack

- **Framework**: Next.js 15 with App Router
- **State**: TanStack Query + Zustand
- **Styling**: Tailwind CSS (same design system as landing)
- **Forms**: React Hook Form + Zod
- **Animations**: Framer Motion
- **Charts**: Recharts
- **Icons**: Lucide React

## Features

- 📊 **Dashboard**: Real-time metrics and stats
- 🏢 **Gym Management**: Create, edit, delete gyms
- 💳 **Subscriptions**: Manage gym subscriptions
- 📱 **WhatsApp**: Configure WhatsApp integration per gym
- ⚙️ **Settings**: System configuration

## Getting Started

```bash
# Install dependencies
pnpm install

# Run development server
pnpm dev

# Build for production
pnpm build
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Admin API backend URL |
| `NEXT_PUBLIC_SITE_URL` | This admin panel URL |
| `NEXT_PUBLIC_LANDING_URL` | Landing page URL |

## Structure

```
apps/admin-web/
├── src/
│   └── app/
│       ├── globals.css
│       ├── layout.tsx
│       ├── providers.tsx
│       ├── page.tsx                 # Login page
│       └── dashboard/
│           ├── layout.tsx           # Sidebar layout
│           ├── page.tsx             # Dashboard home
│           ├── gyms/
│           │   └── page.tsx         # Gym management
│           ├── subscriptions/
│           ├── payments/
│           ├── whatsapp/
│           └── settings/
├── tailwind.config.js
└── package.json
```

## Deployment

Deploy to Vercel:

1. Create new Vercel project
2. Set root directory to `apps/admin-web`
3. Add environment variables
4. Deploy

**Domain**: `admin.ironhub.motiona.xyz`

---

Developed by **MotionA** © 2026
