import { NextResponse } from 'next/server';

const ADMIN_API_URL = process.env.ADMIN_API_URL || process.env.NEXT_PUBLIC_ADMIN_API_URL || 'https://admin-api.ironhub.motiona.xyz';

function isObject(value: unknown): value is Record<string, unknown> {
    return Boolean(value) && typeof value === 'object';
}

export async function GET() {
    try {
        const base = ADMIN_API_URL.replace(/\/+$/, '');
        const candidates = [`${base}/gyms/public`, `${base}/api/gyms/public`];
        let res: Response | null = null;
        console.log(`[GymsProxy] Using Admin Base: ${base}`);

        for (const url of candidates) {
            console.log(`[GymsProxy] Trying: ${url}`);
            try {
                const r = await fetch(url, { headers: { Accept: 'application/json' }, next: { revalidate: 60 } });
                console.log(`[GymsProxy] ${url} -> Status: ${r.status}`);
                if (r.ok) {
                    res = r;
                    break;
                }
            } catch (err) {
                console.error(`[GymsProxy] Error fetching ${url}:`, err);
            }
        }

        if (!res) {
            return NextResponse.json({ items: [], total: 0 }, { status: 200 });
        }

        const data: unknown = await res.json().catch(() => null);
        const itemsValue = isObject(data) ? data.items : null;
        const items = Array.isArray(itemsValue) ? itemsValue : [];
        const totalValue = isObject(data) ? data.total : null;
        const total = typeof totalValue === 'number' ? totalValue : items.length;

        return NextResponse.json({ items, total }, { status: 200 });
    } catch {
        return NextResponse.json({ items: [], total: 0 }, { status: 200 });
    }
}
