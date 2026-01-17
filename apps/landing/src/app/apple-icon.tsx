import { ImageResponse } from 'next/og';

export const runtime = 'edge';

export const size = {
    width: 180,
    height: 180,
};

export const contentType = 'image/png';

export default function AppleIcon() {
    return new ImageResponse(
        (
            <div
                style={{
                    width: '100%',
                    height: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: 'linear-gradient(135deg, #7c3aed 0%, #2563eb 100%)',
                    borderRadius: 36,
                    color: '#fff',
                    fontSize: 86,
                    fontWeight: 900,
                    fontFamily: 'Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial',
                    letterSpacing: -4,
                }}
            >
                IH
            </div>
        ),
        size
    );
}

