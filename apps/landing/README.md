# IronHub Landing Page

Premium landing page for the IronHub gym management platform.

## Tech Stack

- **Framework**: Next.js 15 with App Router
- **Styling**: Tailwind CSS with custom design system
- **Animations**: Framer Motion
- **Icons**: Lucide React
- **Language**: TypeScript

## Design System

The landing page uses a premium, disruptive color palette:

- **Primary**: Deep Electric Violet (`#8b5cf6` - `#4c1d95`)
- **Accent**: Warm Gold (`#f59e0b` - `#78350f`)
- **Neutral**: Sophisticated slate-zinc blend

Features include:
- Glassmorphism effects
- Gradient backgrounds and orbs
- Micro-animations and hover effects
- Dark mode only

## Getting Started

```bash
# Install dependencies
pnpm install

# Run development server
pnpm dev

# Build for production
pnpm build

# Start production server
pnpm start
```

## Environment Variables

Copy `.env.example` to `.env.local` and configure:

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend API URL |
| `NEXT_PUBLIC_ADMIN_URL` | Admin panel URL |
| `NEXT_PUBLIC_SITE_URL` | This site's URL |

## Deployment

Deploy to Vercel:

1. Create new Vercel project
2. Set root directory to `apps/landing`
3. Add environment variables
4. Deploy

**Domain**: `ironhub.motiona.xyz`

## Structure

```
apps/landing/
├── src/
│   └── app/
│       ├── globals.css      # Global styles & design tokens
│       ├── layout.tsx       # Root layout with metadata
│       └── page.tsx         # Landing page sections
├── tailwind.config.js       # Tailwind configuration
├── next.config.js           # Next.js configuration
└── package.json
```

## Sections

1. **Header**: Fixed navigation with scroll effects
2. **Hero**: Main headline with animated stats
3. **Features**: 6 feature cards with icons
4. **Gyms**: Showcase of connected gyms (fetched from API)
5. **About**: MotionA company information
6. **Contact**: Contact details and CTA
7. **Footer**: Copyright and links

---

Developed by **MotionA** © 2026
