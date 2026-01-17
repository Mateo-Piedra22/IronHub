import { ImageResponse } from 'next/og';

export const runtime = 'edge';

export const size = {
    width: 32,
    height: 32,
};

export const contentType = 'image/png';

export default function Icon() {
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
                    borderRadius: 8,
                    color: '#fff',
                    fontSize: 18,
                    fontWeight: 800,
                    fontFamily: 'Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial',
                    letterSpacing: -1,
                }}
            >
                IH
            </div>
        ),
        size
    );
}

