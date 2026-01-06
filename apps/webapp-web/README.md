# webapp-web

Next.js 14 frontend for gym management dashboard.

## Overview

Management dashboard for gym owners and professors to:
- Manage users (socios)
- Process payments and generate receipts
- Track attendance
- Create and assign routines
- Send WhatsApp notifications
- View analytics and KPIs

## Project Structure

```
src/
├── app/
│   ├── gestion/
│   │   ├── layout.tsx       # Sidebar layout
│   │   ├── asistencias/     # Attendance tracking
│   │   ├── clases/          # Class management
│   │   ├── configuracion/   # Settings
│   │   ├── dashboard/       # KPIs and charts
│   │   ├── ejercicios/      # Exercise catalog
│   │   ├── pagos/           # Payment management
│   │   ├── profesores/      # Professor management
│   │   ├── rutinas/         # Routine builder
│   │   ├── usuarios/        # User management
│   │   └── whatsapp/        # Messaging center
│   ├── usuario/             # User self-service panel
│   └── checkin/             # QR check-in interface
├── components/
│   ├── ui/                  # Base UI components
│   │   ├── Button.tsx
│   │   ├── Modal.tsx
│   │   ├── Input.tsx
│   │   ├── Select.tsx
│   │   ├── DataTable.tsx
│   │   └── ...
│   ├── ReciboPreviewModal.tsx
│   ├── RutinaExportModal.tsx
│   ├── QRCheckInModal.tsx
│   ├── WhatsAppUserHistory.tsx
│   ├── SesionEditModal.tsx
│   └── ...
└── lib/
    ├── api.ts               # API client
    └── utils.ts             # Utility functions
```

## Key Pages

| Route | Description |
|-------|-------------|
| /gestion/dashboard | KPIs, charts, alerts |
| /gestion/usuarios | User CRUD with filters |
| /gestion/pagos | Payment processing |
| /gestion/asistencias | Daily attendance |
| /gestion/rutinas | Routine builder |
| /gestion/profesores | Professor sessions |
| /gestion/configuracion | Gym settings |
| /gestion/whatsapp | Message center |

## Key Components

| Component | Purpose |
|-----------|---------|
| DataTable | Sortable, filterable data tables |
| Modal | Overlay dialogs |
| ReciboPreviewModal | Receipt preview and print |
| RutinaExportModal | Excel export options |
| QRCheckInModal | QR code with countdown |
| SesionEditModal | Professor session editor |

## Environment Variables

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Development

```bash
# Install dependencies
pnpm install

# Run development server
pnpm dev

# Build for production
pnpm build

# Type check
pnpm tsc --noEmit

# Lint
pnpm lint
```

## Styling

Uses Tailwind CSS with custom design tokens:
- Primary colors: iron-* (blue/steel)
- Neutral scale: neutral-*
- Semantic: success-*, warning-*, danger-*

Custom utilities:
- `glass-card`: Frosted glass effect
- `gradient-text`: Gradient text
- `btn-glow`: Glowing button

## Deployment

Deploys to Vercel as Next.js application.
See root [DEPLOYMENT.md](../../DEPLOYMENT.md) for instructions.
