const TENANT_DOMAIN = process.env.NEXT_PUBLIC_TENANT_DOMAIN || 'ironhub.motiona.xyz';

const RESERVED = new Set(['www', 'api', 'admin', 'admin-api']);

export function getTenantFromHostname(hostname: string): string {
    const h = String(hostname || '').trim().toLowerCase();
    if (!h) return '';
    if (h === 'localhost' || h === '127.0.0.1') {
        return (process.env.NEXT_PUBLIC_DEV_SUBDOMAIN || 'demo').trim();
    }
    const parts = h.split('.');
    if (!parts.length) return '';
    if (RESERVED.has(parts[0])) return '';

    const tenantParts = TENANT_DOMAIN.split('.').filter(Boolean);
    if (parts.length > tenantParts.length) {
        return parts[0] || '';
    }
    const envTenant =
        (process.env.NEXT_PUBLIC_DEFAULT_TENANT || process.env.NEXT_PUBLIC_DEV_SUBDOMAIN || '').trim();
    return envTenant || '';
}

export function getCurrentTenant(): string {
    if (typeof window === 'undefined') return '';
    return getTenantFromHostname(window.location.hostname);
}

export function getCsrfTokenFromCookie(): string {
    if (typeof document === 'undefined') return '';
    const match = document.cookie.match(/(?:^|;\s*)ironhub_csrf=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
}

