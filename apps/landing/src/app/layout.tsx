import type { Metadata } from 'next';
import './globals.css';
import Link from 'next/link';
import { Twitter, Mail, HelpCircle } from "lucide-react";
import { UnifiedShell } from '@/components/layout/UnifiedShell';

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

const primaryLinks = [
    { href: "/#features", label: "Características" },
    { href: "/#gyms", label: "Gimnasios" },
    { href: "/#about", label: "Sobre Nosotros" },
];

const legalLinks = [
    { href: "/terms", label: "Términos de Servicio" },
    { href: "/privacy", label: "Política de Privacidad" },
];

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const leftPanelContent = (
        <div className="flex flex-col flex-1 pb-safe">
            <div className="hidden lg:block">
                <span className="font-mono text-[10px] uppercase tracking-widest opacity-60 mb-4 block before:content-['['] before:mr-1 after:content-[']'] after:ml-1">Sistema</span>
                <div className="mb-10 flex items-center gap-3">
                    <img
                        src="/images/logo-ironhub.png"
                        alt="IronHub"
                        className="w-12 h-12 object-contain border border-black bg-white rounded-md"
                    />
                    <div className="flex flex-col justify-center">
                        <span className="font-bold text-2xl tracking-tighter leading-none uppercase text-black">IronHub</span>
                        <span className="font-mono text-[10px] tracking-widest opacity-60 text-black">GYM MANAGEMENT</span>
                    </div>
                </div>

                <div className="w-full border-t border-[var(--line-color,#000)] my-4" />
            </div>

            <nav className="flex flex-col gap-3 flex-1 mt-4 lg:mt-0 text-black">
                {primaryLinks.map((item, index) => (
                    <Link key={item.label} href={item.href} className="group flex items-center gap-2 text-sm">
                        <span className="w-2 h-2 bg-black opacity-0 group-hover:opacity-100 transition-opacity"></span>
                        <span className="group-hover:translate-x-1 transition-transform font-bold text-black uppercase">
                            0{index}. {item.label}
                        </span>
                    </Link>
                ))}
            </nav>

            <div className="hidden lg:block">
                <div className="w-full border-t border-[var(--line-color,#000)] my-4" />

                <div className="flex flex-col gap-3">
                    <Link
                        href="https://admin.ironhub.motiona.xyz"
                        className="group flex items-center gap-2 text-sm"
                    >
                        <span className="w-2 h-2 bg-black opacity-0 group-hover:opacity-100 transition-opacity"></span>
                        <span className="group-hover:translate-x-1 transition-transform font-bold text-black uppercase">Panel Admin</span>
                    </Link>
                </div>
            </div>

            <div className="pt-8 border-t border-[var(--line-color,#000)] mt-8">
                <span className="font-mono text-[10px] uppercase tracking-widest opacity-60 mb-4 block before:content-['['] before:mr-1 after:content-[']'] after:ml-1">Powered By</span>
                <a
                    href="https://motiona.xyz"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 group opacity-70 hover:opacity-100 transition-opacity"
                >
                    <img src="/motiona-logo.png" alt="MotionA" className="w-8 h-8 object-contain rounded-md" />
                    <span className="font-bold uppercase tracking-wider text-sm group-hover:underline text-black">MotionA</span>
                </a>
            </div>
        </div>
    );

    const rightPanelContent = (
        <div className="flex flex-col h-full text-black">
            <span className="font-mono text-[10px] uppercase tracking-widest opacity-60 mb-4 block before:content-['['] before:mr-1 after:content-[']'] after:ml-1">Legal</span>
            <ul className="space-y-3 text-sm">
                {legalLinks.map((item) => (
                    <li key={item.label}>
                        <Link href={item.href} className="hover:opacity-70 font-semibold font-mono text-xs uppercase tracking-wider">
                            {item.label}
                        </Link>
                    </li>
                ))}
            </ul>

            <div className="w-full border-t border-[var(--line-color,#000)] my-4" />

            <span className="font-mono text-[10px] uppercase tracking-widest opacity-60 mb-4 block before:content-['['] before:mr-1 after:content-[']'] after:ml-1">Contacto</span>
            <div className="flex gap-4 opacity-80">
                <a
                    href="https://twitter.com"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:opacity-100 transition-opacity"
                >
                    <Twitter className="h-5 w-5" />
                </a>
                <Link
                    href="/#contact"
                    className="hover:opacity-100 transition-opacity"
                >
                    <Mail className="h-5 w-5" />
                </Link>
                <Link
                    href="https://help.ironhub.motiona.xyz"
                    className="hover:opacity-100 transition-opacity"
                >
                    <HelpCircle className="h-5 w-5" />
                </Link>
            </div>

            <div className="w-full border-t border-[var(--line-color,#000)] my-4" />

            <div className="space-y-4 text-xs font-mono uppercase opacity-70">
                <p>Plataforma profesional de gestión de gimnasios.</p>
                <div className="space-y-1">
                    <p>Desarrollado por <strong>Mateo Piedrabuena</strong></p>
                    <p>© {new Date().getFullYear()} MotionA.</p>
                </div>
            </div>
        </div>
    );

    return (
        <html lang="es">
            <head>
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
            </head>
            <body className="min-h-screen antialiased bg-white" data-brand="ironhub">
                <UnifiedShell
                    brandName="IronHub"
                    brandLogo="/images/logo-ironhub.png"
                    leftPanelContent={leftPanelContent}
                    rightPanelContent={rightPanelContent}
                >
                    {children}
                </UnifiedShell>
            </body>
        </html>
    );
}
