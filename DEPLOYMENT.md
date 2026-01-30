# Deploy (runbook)

Este archivo es un índice. La guía enterprise y los runbooks viven en:

- [Deploy y operaciones](docs/operations/deployment.md)
- [Migraciones (Alembic)](docs/database/migrations.md)

## Paso obligatorio: migraciones tenant

En cada deploy que afecte a `webapp-api`, ejecutar:

```bash
cd apps/webapp-api
python -m src.cli.migrate
```

Si falla, el deploy debe detenerse.
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
