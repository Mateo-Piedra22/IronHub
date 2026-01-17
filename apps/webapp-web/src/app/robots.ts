import type { MetadataRoute } from 'next';
import { headers } from 'next/headers';

export const runtime = 'edge';

export default async function robots(): Promise<MetadataRoute.Robots> {
    const h = await headers();
    const host = h.get('x-forwarded-host') || h.get('host') || 'ironhub.motiona.xyz';
    const base = host.startsWith('http') ? host : `https://${host}`;
    return {
        rules: [
            {
                userAgent: '*',
                allow: ['/', '/login', '/usuario-login', '/gestion-login'],
                disallow: ['/dashboard', '/gestion', '/api', '/_next'],
            },
        ],
        sitemap: `${base}/sitemap.xml`,
    };
}

