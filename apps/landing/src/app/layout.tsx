import type { Metadata } from 'next';
import './globals.css';
import MarketingLayout from './(marketing)/layout';

export const metadata: Metadata = {
    title: 'IronHub | Premium Gym Management Platform',
    description: 'Plataforma profesional de gestión de gimnasios. Control total de socios, pagos, asistencias y más. Desarrollado por MotionA.',
    keywords: ['gym management', 'gestión gimnasio', 'IronHub', 'MotionA', 'fitness software'],
    authors: [{ name: 'MotionA' }],
    creator: 'MotionA',
    publisher: 'MotionA',
    metadataBase: new URL('https://ironhub.motiona.xyz'),
    alternates: {
        canonical: '/',
    },
    openGraph: {
        title: 'IronHub | Premium Gym Management Platform',
        description: 'Plataforma profesional de gestión de gimnasios desarrollada por MotionA.',
        url: 'https://ironhub.motiona.xyz',
        siteName: 'IronHub',
        locale: 'es_AR',
        type: 'website',
    },
    twitter: {
        card: 'summary_large_image',
        title: 'IronHub | Premium Gym Management',
        description: 'Plataforma profesional de gestión de gimnasios desarrollada por MotionA.',
    },
    robots: {
        index: true,
        follow: true,
    },
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="es">
            <head>
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
            </head>
            <body className="min-h-screen antialiased" data-brand="ironhub">
                <MarketingLayout>
                    {children}
                </MarketingLayout>
            </body>
        </html>
    );
}
