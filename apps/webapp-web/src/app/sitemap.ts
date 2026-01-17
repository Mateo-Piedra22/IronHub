import type { MetadataRoute } from 'next';
import { headers } from 'next/headers';

export const runtime = 'edge';

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
    const h = await headers();
    const host = h.get('x-forwarded-host') || h.get('host') || 'ironhub.motiona.xyz';
    const base = host.startsWith('http') ? host : `https://${host}`;
    const now = new Date();
    return [
        { url: `${base}/`, lastModified: now, changeFrequency: 'weekly', priority: 0.8 },
        { url: `${base}/login`, lastModified: now, changeFrequency: 'monthly', priority: 0.4 },
        { url: `${base}/usuario-login`, lastModified: now, changeFrequency: 'monthly', priority: 0.3 },
        { url: `${base}/gestion-login`, lastModified: now, changeFrequency: 'monthly', priority: 0.3 },
    ];
}

