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
                    background: '#f4f4f0',
                    border: '2px solid #000',
                    color: '#000',
                    fontSize: 18,
                    fontWeight: 800,
                    fontFamily: 'Helvetica Neue, Arial, system-ui',
                    letterSpacing: -1,
                }}
            >
                IH
            </div>
        ),
        size
    );
}
