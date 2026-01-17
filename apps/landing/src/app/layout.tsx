import type { Metadata } from 'next';
import './globals.css';
import SiteHeader from './_components/SiteHeader';
import SiteFooter from './_components/SiteFooter';

export const metadata: Metadata = {
    title: 'IronHub | Premium Gym Management Platform',
    description: 'Plataforma profesional de gestión de gimnasios. Control total de socios, pagos, asistencias y más. Desarrollado por MotionA.',
    keywords: ['gym management', 'gestión gimnasio', 'IronHub', 'MotionA', 'fitness software'],
    authors: [{ name: 'MotionA' }],
    creator: 'MotionA',
    publisher: 'MotionA',
    metadataBase: new URL('https://ironhub.motiona.xyz'),
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
        <html lang="es" className="dark">
            <head>
                <link rel="icon" href="/favicon.ico" />
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
            </head>
            <body className="min-h-screen antialiased">
                <div className="relative">
                    {/* Gradient orbs for premium effect */}
                    <div className="pointer-events-none fixed inset-0 overflow-hidden">
                        <div className="absolute -top-40 -right-40 h-[500px] w-[500px] rounded-full bg-primary-600/20 blur-[100px]" />
                        <div className="absolute top-1/2 -left-40 h-[400px] w-[400px] rounded-full bg-gold-600/10 blur-[100px]" />
                        <div className="absolute bottom-0 right-1/3 h-[300px] w-[300px] rounded-full bg-primary-500/10 blur-[80px]" />
                    </div>

                    {/* Main content */}
                    <div className="relative z-10">
                        <SiteHeader />
                        {children}
                        <SiteFooter />
                    </div>
                </div>
            </body>
        </html>
    );
}
