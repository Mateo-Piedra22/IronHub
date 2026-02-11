'use client';

import Image from 'next/image';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { useEffect, useMemo, useState } from 'react';
import {
    BarChart3,
    QrCode,
    User,
    Users,
    MessageCircle,
    Dumbbell,
} from 'lucide-react';

interface HomeSelectorProps {
    gymName: string;
    logoUrl: string;
    portalTagline?: string | null;
    footerText?: string | null;
    showPoweredBy?: boolean;
    supportWhatsAppEnabled?: boolean;
    supportWhatsApp?: string | null;
    portalEnableCheckin?: boolean;
    portalEnableMember?: boolean;
    portalEnableStaff?: boolean;
    portalEnableOwner?: boolean;
}

interface OptionCard {
    id: string;
    title: string;
    description: string;
    href: string;
    icon: React.ComponentType<{ className?: string }>;
    roleChip: string;
    buttonText: string;
    variant: 'primary' | 'default' | 'accent';
}

const options: OptionCard[] = [
    {
        id: 'dashboard',
        title: 'Dashboard',
        description: 'Ingresa al panel con KPIs, reportes y control del sistema.',
        href: '/login',
        icon: BarChart3,
        roleChip: 'Dueño',
        buttonText: 'Ir al login',
        variant: 'primary',
    },
    {
        id: 'checkin',
        title: 'Check-in',
        description: 'Valida tu asistencia escaneando un QR o ingresando el token.',
        href: '/checkin',
        icon: QrCode,
        roleChip: 'Socio',
        buttonText: 'Ir al check-in',
        variant: 'accent',
    },
    {
        id: 'usuarios',
        title: 'Usuarios',
        description: 'Accede a tu panel: vencimientos, pagos, rutinas y QR.',
        href: '/usuario-login',
        icon: User,
        roleChip: 'Socio',
        buttonText: 'Ir a Usuarios',
        variant: 'default',
    },
    {
        id: 'gestion',
        title: 'Gestión',
        description: 'Administra usuarios y pagos desde la web.',
        href: '/gestion-login',
        icon: Users,
        roleChip: 'Dueño/Profesor',
        buttonText: 'Ir a Gestión',
        variant: 'accent',
    },
];

export default function HomeSelector({
    gymName,
    logoUrl,
    portalTagline,
    footerText,
    showPoweredBy = true,
    supportWhatsAppEnabled = false,
    supportWhatsApp,
    portalEnableCheckin = true,
    portalEnableMember = true,
    portalEnableStaff = true,
    portalEnableOwner = true,
}: HomeSelectorProps) {
    const [logoBroken, setLogoBroken] = useState(false);
    const showLogo = !!logoUrl && !logoBroken;
    const tagline = portalTagline || 'Portal de acceso para clientes, dueño y profesores.';

    useEffect(() => {
        setLogoBroken(false);
    }, [logoUrl]);

    const memberOptions = options.filter((o) => {
        if (o.id === 'checkin') return portalEnableCheckin;
        if (o.id === 'usuarios') return portalEnableMember;
        return false;
    });
    const adminOptions = options.filter((o) => {
        if (o.id === 'gestion') return portalEnableStaff;
        if (o.id === 'dashboard') return portalEnableOwner;
        return false;
    });

    const sections = useMemo(() => {
        const out: { title: string; items: OptionCard[]; delayBase: number }[] = [];
        if (memberOptions.length) out.push({ title: 'Acceso', items: memberOptions, delayBase: 0.1 });
        if (adminOptions.length) out.push({ title: 'Administración', items: adminOptions, delayBase: 0.18 });
        return out;
    }, [memberOptions, adminOptions]);

    const footerLinks = useMemo(() => {
        const out = [...memberOptions, ...adminOptions];
        const seen = new Set<string>();
        return out.filter((x) => {
            if (seen.has(x.href)) return false;
            seen.add(x.href);
            return true;
        });
    }, [memberOptions, adminOptions]);

    const waNumber = String(supportWhatsApp || '').replace(/[^\d]/g, '');
    const waHref = waNumber
        ? `https://wa.me/${waNumber}?text=${encodeURIComponent(`Hola, necesito ayuda con ${gymName || 'mi gimnasio'}.`)}`
        : '';

    return (
        <div className="min-h-dvh flex items-start md:items-center justify-center p-6 py-10">
            {/* Background effects */}
            <div className="fixed inset-0 pointer-events-none">
                <div className="absolute -top-40 -right-40 h-[500px] w-[500px] rounded-full bg-primary-600/20 blur-[100px]" />
                <div className="absolute bottom-0 -left-40 h-[400px] w-[400px] rounded-full bg-gold-600/10 blur-[100px]" />
            </div>

            <div className="w-full max-w-3xl relative z-10 space-y-4">
                {/* Header Card */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="card p-5"
                >
                    {/* Brand */}
                    <div className="flex items-center gap-3 mb-4">
                        {showLogo ? (
                            <div className="relative w-12 h-12 md:w-16 md:h-16 rounded-xl bg-slate-900/40 border border-slate-700/60 overflow-hidden">
                                <Image
                                    src={logoUrl}
                                    alt={`Logo de ${gymName}`}
                                    fill
                                    sizes="(max-width: 768px) 48px, 64px"
                                    className="object-contain p-2"
                                    unoptimized
                                    onError={() => setLogoBroken(true)}
                                />
                            </div>
                        ) : (
                            <div className="w-12 h-12 md:w-16 md:h-16 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
                                <Dumbbell className="w-5 h-5 text-white" />
                            </div>
                        )}
                        <div>
                            <h1 className="text-xl font-display font-bold text-white">
                                {gymName || 'IronHub'}
                            </h1>
                            <p className="text-sm text-slate-400">
                                {tagline}
                            </p>
                        </div>
                    </div>

                    {/* Options Grid */}
                    <div className={`grid grid-cols-1 ${sections.length > 1 ? 'lg:grid-cols-2' : ''} gap-4`}>
                        {sections.map((sec) => (
                            <div key={sec.title} className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-4">
                                <div className="text-sm font-semibold text-white mb-3">{sec.title}</div>
                                <div className={`grid gap-3 ${sec.items.length >= 3 ? 'md:grid-cols-2' : 'grid-cols-1'}`}>
                                    {sec.items.map((option, index) => (
                                        <motion.div
                                            key={option.id}
                                            initial={{ opacity: 0, y: 12 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: sec.delayBase + index * 0.05 }}
                                        >
                                            <Link
                                                href={option.href}
                                                className="block p-4 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:border-primary-500/50 hover:bg-slate-800 transition-all duration-200 group h-full"
                                            >
                                                <div className="flex items-center gap-2 mb-2">
                                                    <div className="w-8 h-8 rounded-lg bg-slate-700/50 group-hover:bg-primary-500/20 flex items-center justify-center transition-colors">
                                                        <option.icon className="w-4 h-4 text-slate-400 group-hover:text-primary-400 transition-colors" />
                                                    </div>
                                                    <span className="font-semibold text-white">
                                                        {option.title}
                                                    </span>
                                                    <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full bg-slate-700/50 text-slate-400 border border-slate-600/50">
                                                        {option.roleChip}
                                                    </span>
                                                </div>
                                                <p className="text-sm text-slate-500 mb-3">
                                                    {option.description}
                                                </p>
                                                <span
                                                    className={`inline-flex items-center text-sm font-medium px-3 py-1.5 rounded-lg transition-colors ${
                                                        option.variant === 'primary'
                                                            ? 'bg-primary-500/20 text-primary-400 group-hover:bg-primary-500/30'
                                                            : option.variant === 'accent'
                                                            ? 'bg-gold-500/20 text-gold-400 group-hover:bg-gold-500/30'
                                                            : 'bg-slate-700/50 text-slate-300 group-hover:bg-slate-700'
                                                    }`}
                                                >
                                                    {option.buttonText}
                                                </span>
                                            </Link>
                                        </motion.div>
                                    ))}
                                </div>
                            </div>
                        ))}
                        {!sections.length ? (
                            <div className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-4">
                                <div className="text-sm text-slate-400">No hay accesos habilitados para este portal.</div>
                            </div>
                        ) : null}
                    </div>
                </motion.div>

                {/* Footer Card */}
                <motion.footer
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="card p-4 text-center"
                >
                    <div className="flex items-center justify-center gap-2 flex-wrap text-sm">
                        {footerLinks.map((l, idx) => (
                            <span key={l.href} className="flex items-center gap-2">
                                {idx > 0 ? <span className="text-slate-600">•</span> : null}
                                <Link href={l.href} className="text-slate-400 hover:text-white transition-colors">
                                    {l.title}
                                </Link>
                            </span>
                        ))}
                    </div>
                    <p className="text-xs text-slate-600 mt-3">
                        {footerText
                            ? footerText
                            : `© ${new Date().getFullYear()} ${gymName || 'IronHub'}. Todos los derechos reservados.`}
                        {showPoweredBy ? (
                            <span className="block mt-1">
                                IronHub - Powered by MotionA
                            </span>
                        ) : null}
                    </p>
                </motion.footer>
            </div>

            {/* WhatsApp Floating Button */}
            {supportWhatsAppEnabled && waHref ? (
                <a
                    href={waHref}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="fixed bottom-[calc(1.25rem+env(safe-area-inset-bottom))] right-[calc(1.25rem+env(safe-area-inset-right))] z-50 group"
                    aria-label="Contactar por WhatsApp"
                >
                    <div className="w-12 h-12 rounded-full bg-primary-500 hover:bg-primary-400 flex items-center justify-center shadow-lg hover:shadow-xl transition-all hover:scale-110">
                        <MessageCircle className="w-6 h-6 text-white" />
                    </div>
                    <span className="absolute right-14 top-1/2 -translate-y-1/2 px-3 py-1.5 rounded-lg bg-slate-800 text-white text-sm border border-slate-700 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                        Soporte
                    </span>
                </a>
            ) : null}
        </div>
    );
}
