import type { Metadata } from 'next';
import './globals.css';
import MarketingLayout from './(marketing)/layout';

export const metadata: Metadata = {
    title: {
        default: 'IronHub - Plataforma de Gestión de Gimnasios y Fitness Centers',
        template: '%s | IronHub'
    },
    description: 'Software profesional de gestión para gimnasios. Control de socios, pagos con Mercado Pago, asistencias con QR, clases grupales, planes de entrenamiento, reportes en tiempo real y app móvil. Solución completa para fitness centers, box de CrossFit y estudios. Desarrollado por MotionA.',
    keywords: [
        'software gimnasio',
        'gestión gimnasio',
        'gym management software',
        'sistema gimnasio argentina',
        'software fitness center',
        'control asistencias gimnasio',
        'pagos gimnasio',
        'mercado pago gimnasio',
        'gestión socios gym',
        'software crossfit',
        'app gimnasio',
        'clases grupales software',
        'reportes gimnasio',
        'crm gimnasio',
        'sistema cuotas gym',
        'gestión instructores',
        'software box crossfit',
        'gym saas argentina'
    ],
    applicationName: 'IronHub',
    creator: 'Mateo Piedrabuena',
    publisher: 'MotionA',
    authors: [{ name: 'MotionA', url: 'https://motiona.xyz' }],
    category: 'business',
    icons: {
        icon: [{ url: '/images/logo-ironhub.png', type: 'image/png' }],
        apple: [{ url: '/images/logo-ironhub.png', sizes: '180x180', type: 'image/png' }]
    },
    appleWebApp: {
        capable: true,
        statusBarStyle: 'default',
        title: 'IronHub'
    },
    metadataBase: new URL('https://ironhub.motiona.xyz'),
    openGraph: {
        type: 'website',
        locale: 'es_AR',
        siteName: 'IronHub',
        title: 'IronHub - Plataforma de Gestión de Gimnasios',
        description: 'Software profesional para gestión de gimnasios con control de socios, pagos, asistencias y reportes en tiempo real.',
        url: 'https://ironhub.motiona.xyz',
        images: [{
            url: '/og-image.png',
            width: 1200,
            height: 630,
            alt: 'IronHub - Gestión de Gimnasios'
        }]
    },
    twitter: {
        card: 'summary_large_image',
        title: 'IronHub - Gestión de Gimnasios',
        description: 'Software profesional para gimnasios con control de socios, pagos y asistencias.',
        images: ['/og-image.png']
    },
    robots: {
        index: true,
        follow: true
    }
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
