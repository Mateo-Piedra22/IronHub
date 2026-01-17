import { headers } from 'next/headers';
import { ImageResponse } from 'next/og';
import { createElement } from 'react';

export const runtime = 'edge';

const TENANT_DOMAIN = process.env.NEXT_PUBLIC_TENANT_DOMAIN || 'ironhub.motiona.xyz';
const API_BASE = process.env.NEXT_PUBLIC_API_URL || `https://api.${TENANT_DOMAIN}`;

function getTenantFromHost(host: string | null): string {
    const raw = String(host || '').toLowerCase().split(':')[0];
    if (!raw || raw === 'localhost' || raw === '127.0.0.1') {
        return (process.env.NEXT_PUBLIC_DEV_SUBDOMAIN || process.env.NEXT_PUBLIC_DEFAULT_TENANT || 'demo').trim();
    }
    if (raw.startsWith('api.')) return '';
    const parts = raw.split('.');
    const tenantParts = TENANT_DOMAIN.split('.');
    if (parts.length > tenantParts.length) return parts[0] || '';
    return (process.env.NEXT_PUBLIC_DEFAULT_TENANT || '').trim();
}

async function getBranding(tenant: string) {
    if (!tenant) return null;
    const res = await fetch(`${API_BASE}/gym/data`, {
        headers: { 'X-Tenant': tenant },
        next: { revalidate: 300 },
    }).catch(() => null);
    if (!res || !res.ok) return null;
    const data = (await res.json().catch(() => null)) as any;
    return data || null;
}

async function fetchImage(url: string) {
    const res = await fetch(url, { next: { revalidate: 3600 } }).catch(() => null);
    if (!res || !res.ok) return null;
    const buf = await res.arrayBuffer();
    const ct = res.headers.get('content-type') || 'image/png';
    return { buf, ct };
}

export async function GET() {
    const h = await headers();
    const host = h.get('x-forwarded-host') || h.get('host');
    const tenant = getTenantFromHost(host);
    const branding = await getBranding(tenant);
    const logoUrl = String(branding?.logo_url || '').trim();

    if (logoUrl) {
        const img = await fetchImage(logoUrl);
        if (img) {
            return new Response(img.buf, {
                headers: {
                    'Content-Type': img.ct,
                    'Cache-Control': 'public, max-age=60, s-maxage=300, stale-while-revalidate=600',
                },
            });
        }
    }

    const gymName = String(branding?.gym_name || branding?.gym?.name || '').trim();
    const letters = gymName
        ? gymName
              .split(/\s+/)
              .filter(Boolean)
              .slice(0, 2)
              .map((w) => w[0]?.toUpperCase())
              .join('')
        : 'IH';

    return new ImageResponse(
        createElement(
            'div',
            {
                style: {
                    width: '100%',
                    height: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: 'linear-gradient(135deg, #7c3aed 0%, #2563eb 100%)',
                    borderRadius: 40,
                    color: '#fff',
                    fontSize: 96,
                    fontWeight: 900,
                    fontFamily: 'Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial',
                    letterSpacing: -4,
                },
            },
            letters || 'IH'
        ),
        { width: 180, height: 180 }
    );
}
