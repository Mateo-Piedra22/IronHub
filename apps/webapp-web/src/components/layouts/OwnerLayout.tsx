'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { BarChart3, Building2, Home, LogOut, Menu, Settings, Users, X, ChevronRight, MessageSquare, ShieldCheck, UsersRound } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import { ToastContainer } from '@/components/ui';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api';

const navigation = [
    { key: 'overview', name: 'Overview', href: '/dashboard', icon: BarChart3, description: 'KPIs y reportes' },
    { key: 'sucursales', name: 'Sucursales', href: '/dashboard/sucursales', icon: Building2, description: 'Datos, WhatsApp, estado' },
    { key: 'equipo', name: 'Equipo', href: '/dashboard/equipo', icon: UsersRound, description: 'Profesores y staff' },
    { key: 'whatsapp', name: 'WhatsApp', href: '/dashboard/whatsapp', icon: MessageSquare, description: 'Admin, salud, cola' },
    { key: 'configuracion', name: 'Configuración', href: '/dashboard/configuracion', icon: Settings, description: 'Flags, ajustes, control' },
    { key: 'meta_review', name: 'Meta Review', href: '/dashboard/meta-review', icon: ShieldCheck, description: 'Acceso puntual' },
    { key: 'gestion', name: 'Gestión', href: '/gestion/usuarios', icon: Users, description: 'Panel operativo' },
];

export default function OwnerLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const router = useRouter();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const [loggingOut, setLoggingOut] = useState(false);
    const [gymLogoUrl, setGymLogoUrl] = useState<string>('');
    const [sucursales, setSucursales] = useState<Array<{ id: number; nombre: string }>>([]);
    const [sucursalActualId, setSucursalActualId] = useState<number | null>(null);
    const [switchingSucursal, setSwitchingSucursal] = useState(false);
    const [moduleFlags, setModuleFlags] = useState<Record<string, boolean> | null>(null);

    useEffect(() => {
        const loadBranding = async () => {
            try {
                const res = await api.getBootstrap('auto');
                const logo = res.ok ? (res.data?.gym?.logo_url || '') : '';
                if (logo) setGymLogoUrl(logo);
                const items = (res.ok ? (res.data?.sucursales || []) : []) as Array<{ id: number; nombre: string }>;
                setSucursales(items);
                const currentId = res.ok ? (res.data?.sucursal_actual_id ?? null) : null;
                setSucursalActualId(typeof currentId === 'number' ? currentId : null);
                if (res.ok && (res.data as any)?.flags?.modules) {
                    setModuleFlags(((res.data as any).flags.modules || null) as any);
                } else {
                    setModuleFlags(null);
                }
            } catch {
                setGymLogoUrl('');
                setSucursales([]);
                setSucursalActualId(null);
                setModuleFlags(null);
            }
        };
        loadBranding();
    }, []);

    const navItems = navigation.filter((item) => {
        if (item.key === 'overview' || item.key === 'gestion' || item.key === 'meta_review') return true;
        if (item.key === 'configuracion') return true;
        if (item.key === 'equipo') {
            if (!moduleFlags) return true;
            const emp = moduleFlags['empleados'];
            const prof = moduleFlags['profesores'];
            return emp !== false || prof !== false;
        }
        if (!moduleFlags) return true;
        if (Object.prototype.hasOwnProperty.call(moduleFlags, item.key)) {
            return moduleFlags[item.key] !== false;
        }
        return true;
    });

    const handleLogout = async () => {
        setLoggingOut(true);
        try {
            await api.logout();
        } catch {
        } finally {
            router.push('/login');
        }
    };

    const currentSection = navigation.find((item) => pathname === item.href || pathname?.startsWith(item.href + '/'));

    return (
        <div className="min-h-screen bg-slate-950">
            <ToastContainer />

            <header className="fixed top-0 left-0 right-0 z-40 h-16 bg-slate-900 border-b border-slate-800/50">
                <div className="h-full flex items-center justify-between px-4 lg:px-6">
                    <div className="flex items-center gap-4">
                        <button
                            onClick={() => setMobileMenuOpen(true)}
                            className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/50 transition-colors"
                            aria-label="Abrir menú"
                        >
                            <Menu className="w-5 h-5" />
                        </button>

                        <Link href="/dashboard" className="flex items-center gap-3">
                            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-sm">
                                {gymLogoUrl ? (
                                    <img
                                        src={gymLogoUrl}
                                        alt="Logo"
                                        className="w-6 h-6 object-contain bg-white/90 rounded-md p-1"
                                        onError={() => setGymLogoUrl('')}
                                    />
                                ) : (
                                    <BarChart3 className="w-4 h-4 text-white" />
                                )}
                            </div>
                            <div className="hidden sm:block">
                                <h1 className="text-base font-display font-bold text-white leading-none">Dueño</h1>
                                <p className="text-xs text-slate-500">Dashboard ejecutivo</p>
                            </div>
                        </Link>

                        {currentSection ? (
                            <div className="hidden md:flex items-center gap-2 text-slate-400">
                                <ChevronRight className="w-4 h-4" />
                                <span className="text-sm font-medium text-white">{currentSection.name}</span>
                            </div>
                        ) : null}
                    </div>

                    <div className="flex items-center gap-2">
                        {sucursales.length > 1 ? (
                            <select
                                className="h-9 rounded-lg bg-slate-800/60 border border-slate-700/60 text-slate-200 text-sm px-3 outline-none focus:ring-2 focus:ring-primary-500/40 disabled:opacity-60"
                                value={sucursalActualId ?? ''}
                                disabled={switchingSucursal}
                                onChange={async (e) => {
                                    const nextId = Number(e.target.value);
                                    if (!nextId || nextId === sucursalActualId) return;
                                    setSwitchingSucursal(true);
                                    try {
                                        const r = await api.seleccionarSucursal(nextId);
                                        if (r.ok) {
                                            setSucursalActualId(nextId);
                                            router.refresh();
                                        }
                                    } finally {
                                        setSwitchingSucursal(false);
                                    }
                                }}
                            >
                                <option value="" disabled>
                                    Seleccionar sucursal
                                </option>
                                {sucursales.map((s) => (
                                    <option key={s.id} value={s.id}>
                                        {s.nombre}
                                    </option>
                                ))}
                            </select>
                        ) : null}
                        <Link
                            href="/"
                            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/50 transition-colors"
                            title="Ir al inicio"
                        >
                            <Home className="w-5 h-5" />
                        </Link>
                        <button
                            onClick={handleLogout}
                            disabled={loggingOut}
                            className="p-2 rounded-lg text-slate-400 hover:text-danger-400 hover:bg-danger-500/10 transition-colors disabled:opacity-50"
                            title="Cerrar sesión"
                        >
                            <LogOut className="w-5 h-5" />
                        </button>
                    </div>
                </div>
            </header>

            <AnimatePresence>
                {mobileMenuOpen ? (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setMobileMenuOpen(false)}
                            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm lg:hidden"
                        />
                        <motion.aside
                            initial={{ x: -280 }}
                            animate={{ x: 0 }}
                            exit={{ x: -280 }}
                            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                            className="fixed top-0 left-0 bottom-0 z-50 w-72 bg-slate-900 border-r border-slate-800 lg:hidden"
                        >
                            <div className="h-full flex flex-col min-h-0">
                                <div className="h-16 flex items-center justify-between px-4 border-b border-slate-800">
                                    <div className="flex items-center gap-3">
                                        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
                                            {gymLogoUrl ? (
                                                <img src={gymLogoUrl} alt="Logo" className="w-6 h-6 object-contain bg-white/90 rounded-md p-1" />
                                            ) : (
                                                <BarChart3 className="w-4 h-4 text-white" />
                                            )}
                                        </div>
                                        <span className="text-base font-display font-bold text-white">Dueño</span>
                                    </div>
                                    <button
                                        onClick={() => setMobileMenuOpen(false)}
                                        className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/50 transition-colors"
                                    >
                                        <X className="w-5 h-5" />
                                    </button>
                                </div>
                                <nav className="flex-1 min-h-0 p-4 space-y-1 overflow-y-auto overflow-x-auto">
                                    {navItems.map((item) => {
                                        const isActive = pathname === item.href || pathname?.startsWith(item.href + '/');
                                        const isHash = item.href.startsWith('/dashboard#');
                                        return (
                                            <Link
                                                key={item.name}
                                                href={item.href}
                                                onClick={() => setMobileMenuOpen(false)}
                                                className={cn(
                                                    'flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 whitespace-nowrap min-w-max',
                                                    isActive && !isHash
                                                        ? 'bg-primary-500/20 text-primary-300'
                                                        : 'text-slate-400 hover:bg-slate-800/50 hover:text-white'
                                                )}
                                            >
                                                <item.icon className="w-5 h-5 flex-shrink-0" />
                                                <div>
                                                    <div className="font-medium">{item.name}</div>
                                                    <div className="text-xs text-slate-500">{item.description}</div>
                                                </div>
                                            </Link>
                                        );
                                    })}
                                </nav>
                            </div>
                        </motion.aside>
                    </>
                ) : null}
            </AnimatePresence>

            <aside className="hidden lg:block fixed top-16 left-0 bottom-0 w-64 border-r border-slate-800/50 bg-slate-900/50 backdrop-blur-lg">
                <nav className="p-4 space-y-1 overflow-y-auto overflow-x-auto h-full">
                    {navItems.map((item) => {
                        const isActive = pathname === item.href || pathname?.startsWith(item.href + '/');
                        const isHash = item.href.startsWith('/dashboard#');
                        return (
                            <Link
                                key={item.name}
                                href={item.href}
                                className={cn(
                                    'flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 whitespace-nowrap min-w-max',
                                    isActive && !isHash ? 'bg-primary-500/20 text-primary-300' : 'text-slate-400 hover:bg-slate-800/50 hover:text-white'
                                )}
                            >
                                <item.icon className="w-5 h-5 flex-shrink-0" />
                                <div>
                                    <div className="font-medium">{item.name}</div>
                                    <div className="text-xs text-slate-500">{item.description}</div>
                                </div>
                            </Link>
                        );
                    })}
                </nav>
            </aside>

            <main className="pt-16 lg:pl-64">{children}</main>
        </div>
    );
}
