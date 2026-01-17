import type { Metadata } from 'next';
import { headers } from 'next/headers';
import './globals.css';
import { Providers } from './providers';

const TENANT_DOMAIN = process.env.NEXT_PUBLIC_TENANT_DOMAIN || 'ironhub.motiona.xyz';
const API_BASE = process.env.NEXT_PUBLIC_API_URL || `https://api.${TENANT_DOMAIN}`;

function getTenantFromHost(host: string): string {
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

export async function generateMetadata(): Promise<Metadata> {
    const h = await headers();
    const host = h.get('x-forwarded-host') || h.get('host') || TENANT_DOMAIN;
    const tenant = getTenantFromHost(host);
    let gymName = '';
    try {
        if (tenant) {
            const res = await fetch(`${API_BASE}/gym/data`, {
                headers: { 'X-Tenant': tenant },
                next: { revalidate: 300 },
            });
            const data = (await res.json().catch(() => null)) as any;
            gymName = String(data?.gym_name || data?.gym?.name || '').trim();
        }
    } catch {
        gymName = '';
    }

    const baseUrl = host.startsWith('http') ? host : `https://${host}`;
    const title = gymName ? `${gymName} | IronHub` : 'IronHub';

    return {
        title,
        description: 'Sistema de gestión de gimnasios',
        metadataBase: new URL(baseUrl),
        alternates: { canonical: '/' },
        openGraph: {
            title,
            description: 'Sistema de gestión de gimnasios',
            url: baseUrl,
            siteName: 'IronHub',
            locale: 'es_AR',
            type: 'website',
        },
        twitter: {
            card: 'summary',
            title,
            description: 'Sistema de gestión de gimnasios',
        },
        icons: {
            icon: '/favicon.ico',
            apple: '/apple-touch-icon.png',
        },
    };
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="es" className="dark">
            <head>
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
            </head>
            <body className="min-h-screen antialiased">
                <Providers>
                    {children}
                </Providers>
            </body>
        </html>
    );
}

