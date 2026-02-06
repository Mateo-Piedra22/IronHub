'use client';

import { useEffect, useMemo, useState } from 'react';

type ConnectResult =
    | { ok: true; code: string; waba_id: string; phone_number_id: string }
    | { ok: false; error: string };

function getOrigin(url: string): string {
    try {
        return new URL(url).origin;
    } catch {
        return '';
    }
}

export default function WhatsAppConnectPage() {
    const [loading, setLoading] = useState(false);
    const [status, setStatus] = useState<string>('');

    const appId = (process.env.NEXT_PUBLIC_META_APP_ID || '').trim();
    const configId = (process.env.NEXT_PUBLIC_META_WA_EMBEDDED_SIGNUP_CONFIG_ID || '').trim();
    const apiVersion = (process.env.NEXT_PUBLIC_META_GRAPH_API_VERSION || 'v19.0').trim();

    const returnOrigin = useMemo(() => {
        const sp = new URLSearchParams(typeof window !== 'undefined' ? window.location.search : '');
        const o = (sp.get('return_origin') || '').trim();
        return o ? getOrigin(o) : '';
    }, []);

    const postToOpener = (payload: ConnectResult) => {
        try {
            const msg = JSON.stringify({ type: 'IH_WA_CONNECT_RESULT', payload });
            if (window.opener && returnOrigin) {
                window.opener.postMessage(msg, returnOrigin);
            }
        } catch {}
    };

    type FacebookSdk = {
        init: (opts: { appId: string; cookie: boolean; xfbml: boolean; version: string }) => void;
        login: (
            cb: (response: { authResponse?: { code?: string } | null } | null) => void,
            opts: Record<string, unknown>
        ) => void;
    };

    const ensureFacebookSdk = async () => {
        const w = window as unknown as { FB?: FacebookSdk; fbAsyncInit?: () => void };
        if (w.FB) {
            try {
                w.FB.init({ appId, cookie: true, xfbml: false, version: apiVersion });
            } catch {}
            return;
        }
        await new Promise<void>((resolve, reject) => {
            w.fbAsyncInit = function () {
                try {
                    if (!w.FB) {
                        reject(new Error('El SDK de Meta no está disponible'));
                        return;
                    }
                    w.FB.init({ appId, cookie: true, xfbml: false, version: apiVersion });
                    resolve();
                } catch (e) {
                    reject(e);
                }
            };
            const id = 'facebook-jssdk';
            if (document.getElementById(id)) return;
            const js = document.createElement('script');
            js.id = id;
            js.src = 'https://connect.facebook.net/en_US/sdk.js';
            js.async = true;
            js.defer = true;
            js.onerror = () => reject(new Error('No se pudo cargar el SDK de Meta'));
            document.body.appendChild(js);
        });
    };

    const connect = async () => {
        if (!appId || !configId) {
            setStatus('Falta NEXT_PUBLIC_META_APP_ID o NEXT_PUBLIC_META_WA_EMBEDDED_SIGNUP_CONFIG_ID');
            return;
        }
        if (!returnOrigin) {
            setStatus('Falta return_origin');
            return;
        }
        setLoading(true);
        setStatus('');
        let listener: ((event: MessageEvent) => void) | null = null;
        try {
            await ensureFacebookSdk();
            const w = window as unknown as { FB?: FacebookSdk };

            let code: string | null = null;
            let wabaId: string | null = null;
            let phoneNumberId: string | null = null;
            let done = false;
            let finishResolve: (() => void) | null = null;
            const finishPromise = new Promise<void>((resolve) => (finishResolve = resolve));

            const maybeDone = (payload: ConnectResult) => {
                if (done) return;
                done = true;
                postToOpener(payload);
                try {
                    window.close();
                } catch {}
                finishResolve?.();
            };

            const maybeComplete = () => {
                if (!code || !wabaId || !phoneNumberId) return;
                maybeDone({ ok: true, code, waba_id: wabaId, phone_number_id: phoneNumberId });
            };

            listener = (event: MessageEvent) => {
                try {
                    if (event.origin !== 'https://www.facebook.com' && event.origin !== 'https://web.facebook.com') return;
                    const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
                    if (!data || data.type !== 'WA_EMBEDDED_SIGNUP') return;
                    if (data.event === 'FINISH') {
                        const d = data.data || {};
                        wabaId = String(d.waba_id || '');
                        phoneNumberId = String(d.phone_number_id || '');
                        maybeComplete();
                    }
                    if (data.event === 'CANCEL') {
                        maybeDone({ ok: false, error: 'Cancelado por el usuario' });
                    }
                } catch {}
            };

            window.addEventListener('message', listener);

            await new Promise<void>((resolve) => {
                w.FB?.login(
                    (response) => {
                        try {
                            code = response?.authResponse?.code ? String(response.authResponse.code) : null;
                        } catch {
                            code = null;
                        }
                        if (!code) {
                            maybeDone({ ok: false, error: 'No se recibió code de OAuth' });
                        } else {
                            maybeComplete();
                        }
                        resolve();
                    },
                    {
                        config_id: configId,
                        response_type: 'code',
                        override_default_response_type: true,
                        extras: { sessionInfoVersion: 2 },
                    }
                );
            });

            await Promise.race([
                finishPromise,
                new Promise<void>((_resolve, reject) => setTimeout(() => reject(new Error('Tiempo de espera agotado')), 120000)),
            ]);
        } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : 'Error iniciando conexión';
            postToOpener({ ok: false, error: msg });
            setStatus(msg);
        } finally {
            try {
                if (listener) window.removeEventListener('message', listener);
            } catch {}
            setLoading(false);
        }
    };

    useEffect(() => {
        setStatus('');
    }, []);

    return (
        <div style={{ maxWidth: 520, margin: '40px auto', padding: 16, fontFamily: 'system-ui' }}>
            <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Conectar WhatsApp</h1>
            <p style={{ color: '#64748b', marginBottom: 16 }}>
                Esta ventana guía el registro integrado de Meta y devuelve la conexión al panel del gimnasio.
            </p>
            <button
                onClick={connect}
                disabled={loading}
                style={{
                    background: '#1877f2',
                    border: 0,
                    borderRadius: 8,
                    color: '#fff',
                    cursor: loading ? 'not-allowed' : 'pointer',
                    padding: '10px 16px',
                    fontWeight: 700,
                    width: '100%',
                }}
            >
                {loading ? 'Conectando…' : 'Login con Meta (Embedded Signup)'}
            </button>
            {status ? (
                <div style={{ marginTop: 12, color: '#ef4444', fontSize: 13 }}>
                    {status}
                </div>
            ) : null}
        </div>
    );
}
