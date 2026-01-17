import { NextResponse } from 'next/server';
import { randomUUID } from 'crypto';

export async function POST(request: Request) {
    let signedRequest = '';
    try {
        const contentType = request.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            const body = await request.json().catch(() => ({}));
            signedRequest = String((body as any)?.signed_request || '');
        } else {
            const form = await request.formData().catch(() => null);
            if (form) {
                signedRequest = String(form.get('signed_request') || '');
            }
        }
    } catch {
        signedRequest = '';
    }

    const confirmationCode = randomUUID();
    const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://ironhub.motiona.xyz';
    const url = `${baseUrl.replace(/\/+$/, '')}/data-deletion/status?code=${encodeURIComponent(confirmationCode)}`;

    return NextResponse.json(
        {
            url,
            confirmation_code: confirmationCode,
            received_signed_request: Boolean(signedRequest),
        },
        { status: 200 }
    );
}
