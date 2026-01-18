import { NextResponse } from 'next/server';

const ADMIN_API_URL = process.env.ADMIN_API_URL || process.env.NEXT_PUBLIC_ADMIN_API_URL || 'https://admin-api.ironhub.motiona.xyz';
const WEBAPP_API_URL = process.env.WEBAPP_API_URL || process.env.NEXT_PUBLIC_WEBAPP_API_URL || 'https://api.ironhub.motiona.xyz';

function isObject(value: unknown): value is Record<string, unknown> {
    return Boolean(value) && typeof value === 'object';
}

export async function GET(request: Request) {
    const { searchParams } = new URL(request.url);
    const ttlSeconds = searchParams.get('ttl_seconds');
    const qs = ttlSeconds ? `?ttl_seconds=${encodeURIComponent(ttlSeconds)}` : '';

    try {
        const base = ADMIN_API_URL.replace(/\/+$/, '');
        const webappBase = WEBAPP_API_URL.replace(/\/+$/, '');
        const candidates = [
            `${base}/gyms/public/metrics${qs}`,
            `${base}/api/gyms/public/metrics${qs}`,
        ];
        let res: Response | null = null;
        console.log(`[MetricsProxy] Using Admin Base: ${base}`);

        for (const url of candidates) {
            console.log(`[MetricsProxy] Trying: ${url}`);
            try {
                const r = await fetch(url, { headers: { Accept: 'application/json' }, next: { revalidate: 60 } });
                console.log(`[MetricsProxy] ${url} -> Status: ${r.status}`);
                if (r.ok) {
                    res = r;
                    break;
                }
            } catch (err) {
                console.error(`[MetricsProxy] Error fetching ${url}:`, err);
            }
        }

        if (!res) {
            return NextResponse.json({ ok: false }, { status: 200 });
        }

        const data: unknown = await res.json().catch(() => null);
        if (!isObject(data) || data.ok === false) return NextResponse.json({ ok: false }, { status: 200 });

        return NextResponse.json(data, { status: 200 });
    } catch {
        return NextResponse.json({ ok: false }, { status: 200 });
    }
}
