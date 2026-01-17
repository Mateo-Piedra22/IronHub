import { ImageResponse } from 'next/og';

export const runtime = 'edge';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default function TwitterImage() {
    return new ImageResponse(
        (
            <div
                style={{
                    width: '100%',
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'center',
                    padding: 80,
                    background: 'linear-gradient(135deg, #0b1220 0%, #111827 50%, #0b1220 100%)',
                    color: '#fff',
                    fontFamily: 'Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial',
                }}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <div
                        style={{
                            width: 72,
                            height: 72,
                            borderRadius: 20,
                            background: 'linear-gradient(135deg, #7c3aed 0%, #2563eb 100%)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: 34,
                            fontWeight: 900,
                            letterSpacing: -2,
                        }}
                    >
                        IH
                    </div>
                    <div style={{ fontSize: 42, fontWeight: 900, letterSpacing: -1 }}>IronHub</div>
                </div>
                <div style={{ marginTop: 28, fontSize: 54, fontWeight: 900, letterSpacing: -2, lineHeight: 1.05 }}>
                    Plataforma de gestión
                    <br />
                    para gimnasios
                </div>
                <div style={{ marginTop: 18, fontSize: 26, color: 'rgba(226,232,240,0.85)', maxWidth: 900, lineHeight: 1.35 }}>
                    Operación diaria + reportes + WhatsApp.
                </div>
            </div>
        ),
        size
    );
}

