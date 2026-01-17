import type { MetadataRoute } from 'next';

export default function sitemap(): MetadataRoute.Sitemap {
    const base = 'https://ironhub.motiona.xyz';
    const now = new Date();
    return [
        { url: `${base}/`, lastModified: now, changeFrequency: 'weekly', priority: 1 },
        { url: `${base}/privacy`, lastModified: now, changeFrequency: 'monthly', priority: 0.3 },
        { url: `${base}/terms`, lastModified: now, changeFrequency: 'monthly', priority: 0.3 },
        { url: `${base}/data-deletion`, lastModified: now, changeFrequency: 'monthly', priority: 0.2 },
    ];
}

