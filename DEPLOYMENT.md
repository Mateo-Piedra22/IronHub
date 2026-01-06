# IronHub Deployment Guide

This document describes how to deploy each application to Vercel.

## Prerequisites

- Vercel CLI installed: `npm i -g vercel`
- Vercel account connected: `vercel login`
- PostgreSQL database provisioned (Neon, Supabase, or similar)
- Backblaze B2 bucket configured
- Cloudflare CDN configured

## Applications Overview

| App | Type | Domain |
|-----|------|--------|
| landing | Next.js | ironhub.motiona.xyz |
| admin-web | Next.js | admin.ironhub.motiona.xyz |
| admin-api | Python/FastAPI | api-admin.ironhub.motiona.xyz |
| webapp-web | Next.js | *.ironhub.motiona.xyz |
| webapp-api | Python/FastAPI | api.ironhub.motiona.xyz |

---

## 1. Landing Page

```bash
cd apps/landing
vercel --prod
```

### Environment Variables
None required for static landing page.

### Domain Configuration
- Add custom domain: `ironhub.motiona.xyz`

---

## 2. Admin Web Dashboard

```bash
cd apps/admin-web
vercel --prod
```

### Environment Variables
```
NEXT_PUBLIC_API_URL=https://api-admin.ironhub.motiona.xyz
```

### Domain Configuration
- Add custom domain: `admin.ironhub.motiona.xyz`

---

## 3. Admin API

```bash
cd apps/admin-api
vercel --prod
```

### Environment Variables
```
ADMIN_DB_HOST=your-db-host
ADMIN_DB_PORT=5432
ADMIN_DB_NAME=ironhub_admin
ADMIN_DB_USER=your-user
ADMIN_DB_PASSWORD=your-password
ADMIN_DB_SSLMODE=require
SESSION_SECRET=generate-secure-secret
```

### Domain Configuration
- Add custom domain: `api-admin.ironhub.motiona.xyz`

---

## 4. Webapp Web (Tenant Dashboard)

```bash
cd apps/webapp-web
vercel --prod
```

### Environment Variables
```
NEXT_PUBLIC_API_URL=https://api.ironhub.motiona.xyz
```

### Domain Configuration
- Add wildcard domain: `*.ironhub.motiona.xyz`
- This enables subdomain routing per tenant

---

## 5. Webapp API (Tenant Backend)

```bash
cd apps/webapp-api
vercel --prod
```

### Environment Variables
```
DB_HOST=your-db-host
DB_PORT=5432
DB_USER=your-user
DB_PASSWORD=your-password
DB_SSLMODE=require

ADMIN_DB_HOST=your-admin-db-host
ADMIN_DB_NAME=ironhub_admin
ADMIN_DB_USER=your-user
ADMIN_DB_PASSWORD=your-password

B2_KEY_ID=your-b2-key
B2_APP_KEY=your-b2-app-key
B2_BUCKET_NAME=your-bucket
B2_BUCKET_ID=your-bucket-id
CLOUDFLARE_CDN_URL=https://cdn.ironhub.motiona.xyz

SESSION_SECRET=generate-secure-secret
```

### Domain Configuration
- Add custom domain: `api.ironhub.motiona.xyz`

---

## Database Setup

### Admin Database
Create the admin database schema:
```sql
CREATE DATABASE ironhub_admin;
```
The admin-api will auto-create tables on first run.

### Tenant Databases
New tenant databases are created automatically when gyms are registered.
Each gym gets its own database: `{subdomain}_db`

---

## Cloudflare CDN Configuration

1. Create a B2 bucket (public)
2. Configure Cloudflare:
   - CNAME: `cdn.ironhub.motiona.xyz` -> B2 bucket URL
   - Page Rules: Cache everything
   - SSL: Full (strict)

---

## DNS Configuration

Add these records to your domain:

| Type | Name | Value |
|------|------|-------|
| CNAME | @ | cname.vercel-dns.com |
| CNAME | admin | cname.vercel-dns.com |
| CNAME | api | cname.vercel-dns.com |
| CNAME | api-admin | cname.vercel-dns.com |
| CNAME | *.ironhub | cname.vercel-dns.com |
| CNAME | cdn | f000.backblazeb2.com |

---

## Post-Deployment Checklist

1. Verify all endpoints respond
2. Test tenant subdomain routing
3. Verify CDN file uploads
4. Test WhatsApp webhooks
5. Verify admin login
6. Create first gym tenant

---

## Troubleshooting

### 500 errors on API
- Check database connection strings
- Verify environment variables are set

### CDN files not loading
- Verify B2 bucket is public
- Check Cloudflare CNAME configuration

### Subdomain routing not working
- Verify wildcard domain is configured
- Check middleware tenant extraction
