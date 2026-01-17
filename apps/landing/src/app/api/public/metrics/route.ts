import { NextResponse } from 'next/server';

const ADMIN_API_URL = process.env.ADMIN_API_URL || 'https://api-admin.ironhub.motiona.xyz';

function isObject(value: unknown): value is Record<string, unknown> {
    return Boolean(value) && typeof value === 'object';
}

export async function GET(request: Request) {
    const { searchParams } = new URL(request.url);
    const ttlSeconds = searchParams.get('ttl_seconds');
    const qs = ttlSeconds ? `?ttl_seconds=${encodeURIComponent(ttlSeconds)}` : '';

    try {
        const base = ADMIN_API_URL.replace(/\/+$/, '');
        const candidates = [`${base}/gyms/public/metrics${qs}`, `${base}/api/gyms/public/metrics${qs}`];
        let res: Response | null = null;
        for (const url of candidates) {
            const r = await fetch(url, { headers: { Accept: 'application/json' }, next: { revalidate: 60 } });
            if (r.ok) {
                res = r;
                break;
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
