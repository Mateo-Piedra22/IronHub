# landing

Public landing page for IronHub platform.

## Overview

Marketing landing page showcasing platform features:
- Hero section with CTAs
- Feature highlights
- Gym directory
- Contact information

## Project Structure

```
src/
├── app/
│   ├── layout.tsx       # Root layout with fonts
│   ├── page.tsx         # Landing page (523 lines)
│   └── globals.css      # Tailwind + custom styles
└── lib/
    └── utils.ts         # Utilities
```

## Page Sections

| Section | Description |
|---------|-------------|
| Header | Sticky navbar with navigation |
| Hero | Main headline with CTAs |
| Features | 6 feature cards with icons |
| Gyms | Directory of active gyms |
| About | Platform information |
| Contact | Contact details and form |
| Footer | Links and copyright |

## Design Features

- Framer Motion animations
- Gradient text effects
- Glass morphism cards
- Responsive design (mobile-first)
- Dark theme

## Environment Variables

```env
# No environment variables required for static site
```

## Development

```bash
pnpm install
pnpm dev
```

## Deployment

Deploys to Vercel at `ironhub.motiona.xyz`.
See root [DEPLOYMENT.md](../../DEPLOYMENT.md) for instructions.
