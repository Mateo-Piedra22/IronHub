# CDN Migration Guide

From: gymms-motiona.xyz (old)
To: cdn.ironhub.motiona.xyz (confirmed)


## Overview

The CDN URL is configured via environment variables, not hardcoded in the codebase.
This makes migration straightforward.

---

## Step 1: Cloudflare Dashboard

### A. Create New CNAME Record

1. Log in to Cloudflare dashboard
2. Select your domain (motiona.xyz)
3. Go to DNS section
4. Add new record:
   - Type: CNAME
   - Name: cdn (or cdn.ironhub)
   - Target: f000.backblazeb2.com (your B2 region endpoint)
   - Proxy status: Proxied (orange cloud)

### B. Configure Page Rules (Optional)

1. Go to Rules > Page Rules
2. Create rule for cdn.ironhub.motiona.xyz/*
3. Settings:
   - Cache Level: Cache Everything
   - Edge Cache TTL: 1 month
   - Browser Cache TTL: 1 year

### C. SSL Configuration

1. Go to SSL/TLS
2. Ensure mode is "Full (strict)"
3. Always Use HTTPS: On

---

## Step 2: Update Environment Variables

### Vercel Dashboard

For each deployed app (webapp-api):

1. Go to Vercel project settings
2. Navigate to Environment Variables
3. Update or add:

```
CLOUDFLARE_CDN_URL=https://cdn.ironhub.motiona.xyz
```

Alternative variable name also supported:
```
CDN_URL=https://cdn.ironhub.motiona.xyz
```

### Local Development

Update your local .env files:

```bash
# apps/webapp-api/.env
CLOUDFLARE_CDN_URL=https://cdn.ironhub.motiona.xyz
```

---

## Step 3: Verify B2 Bucket Configuration

### Backblaze B2 Dashboard

1. Log in to Backblaze
2. Go to Buckets
3. Verify bucket settings:
   - File visibility: Public
   - CORS rules allow your new domain

### CORS Configuration (if needed)

Add to bucket CORS rules:
```json
[
  {
    "corsRuleName": "ironhub-cors",
    "allowedOrigins": [
      "https://ironhub.motiona.xyz",
      "https://*.ironhub.motiona.xyz"
    ],
    "allowedOperations": ["s3_get"],
    "allowedHeaders": ["*"],
    "maxAgeSeconds": 3600
  }
]
```

---

## Step 4: Redeploy Applications

After updating environment variables, redeploy webapp-api:

```bash
cd apps/webapp-api
vercel --prod
```

---

## Step 5: Verify Migration

### Test File Upload

1. Upload a test image via the gym logo feature
2. Check the returned URL uses new domain
3. Verify the file loads correctly

### Check Existing Files

Existing files in B2 will continue to work.
The CDN URL is just the base domain prefix.

---

## Rollback Plan

If issues occur:

1. Revert CLOUDFLARE_CDN_URL to old domain
2. Redeploy webapp-api
3. Keep old Cloudflare CNAME active as backup

---

## Code Reference

The CDN URL is used in:

`apps/webapp-api/src/services/storage_service.py`:

```python
def __init__(self):
    self.cdn_domain = os.getenv("CLOUDFLARE_CDN_URL") or os.getenv("CDN_URL")

def get_file_url(self, file_path: str) -> str:
    if self.cdn_domain and self.bucket_name:
        base = self.cdn_domain.rstrip("/")
        return f"{base}/file/{self.bucket_name}/{path}"
```

No hardcoded domains exist in the codebase.
