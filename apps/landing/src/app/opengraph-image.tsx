import { ImageResponse } from 'next/og';

export const runtime = 'edge';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default function OpenGraphImage() {
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
                    background: '#f4f4f0',
                    color: '#000',
                    fontFamily: 'Helvetica Neue, Arial, system-ui',
                    border: '2px solid #000',
                }}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <div
                        style={{
                            width: 72,
                            height: 72,
                            background: '#ff4d00',
                            border: '2px solid #000',
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
                    Gestión premium
                    <br />
                    para gimnasios
                </div>
                <div style={{ marginTop: 18, fontSize: 26, color: '#333', maxWidth: 900, lineHeight: 1.35 }}>
                    Usuarios, pagos, asistencias, WhatsApp y reportes en un solo lugar.
                </div>
                <div style={{ marginTop: 40, fontSize: 22, color: '#5a5a5a' }}>motiona.xyz</div>
            </div>
        ),
        size
    );
}
