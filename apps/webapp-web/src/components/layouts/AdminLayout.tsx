'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import {
    Users,
    CreditCard,
    GraduationCap,
    Clipboard,
    Dumbbell,
    CalendarDays,
    ScanLine,
    Settings,
    LogOut,
    Menu,
    X,
    ChevronRight,
    Home,
    MessageSquare,
    Clock,
    Briefcase
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { ToastContainer, Modal, Button } from '@/components/ui';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api';
import { MiJornadaWidget } from '@/components/MiJornadaWidget';

// Navigation items
const navigation = [
    { key: 'usuarios', name: 'Usuarios', href: '/gestion/usuarios', icon: Users, description: 'Gestionar socios' },
    { key: 'pagos', name: 'Pagos', href: '/gestion/pagos', icon: CreditCard, description: 'Registro de pagos' },
    { key: 'rutinas', name: 'Rutinas', href: '/gestion/rutinas', icon: Clipboard, description: 'Plantillas y asignación' },
    { key: 'ejercicios', name: 'Ejercicios', href: '/gestion/ejercicios', icon: Dumbbell, description: 'Biblioteca de ejercicios' },
    { key: 'clases', name: 'Clases', href: '/gestion/clases', icon: CalendarDays, description: 'Horarios grupales' },
    { key: 'asistencias', name: 'Asistencias', href: '/gestion/asistencias', icon: ScanLine, description: 'Check-in y registro' },
    { key: 'whatsapp', name: 'WhatsApp', href: '/gestion/whatsapp', icon: MessageSquare, description: 'Mensajes y API' },
];

export default function AdminLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();
    const router = useRouter();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const [loggingOut, setLoggingOut] = useState(false);
    const [gymLogoUrl, setGymLogoUrl] = useState<string>('');
    const [sucursales, setSucursales] = useState<Array<{ id: number; nombre: string; codigo: string; activa: boolean }>>([]);
    const [sucursalActualId, setSucursalActualId] = useState<number | null>(null);
    const [switchingSucursal, setSwitchingSucursal] = useState(false);
    const [moduleFlags, setModuleFlags] = useState<Record<string, boolean> | null>(null);
    const [userScopes, setUserScopes] = useState<string[]>([]);
    const [userName, setUserName] = useState('');
    const [userRole, setUserRole] = useState('');
    const [sessionStartTime, setSessionStartTime] = useState<Date | null>(null);
    const [sessionTimer, setSessionTimer] = useState<string | null>(null);

    useEffect(() => {
        const loadBranding = async () => {
            try {
                const res = await api.getBootstrap('gestion');
                const logo = res.ok ? (res.data?.gym?.logo_url || '') : '';
                if (logo) setGymLogoUrl(logo);
                if (res.ok && res.data?.sucursales) {
                    setSucursales(res.data.sucursales.filter((s) => s.activa));
                    setSucursalActualId((res.data.sucursal_actual_id ?? null) as any);
                }
                if (res.ok && (res.data as any)?.flags?.modules) {
                    setModuleFlags(((res.data as any).flags.modules || null) as any);
                } else {
                    setModuleFlags(null);
                }
            } catch {
                // ignore
            }
        };
        loadBranding();
    }, []);

    const hasScopeFor = (key: string, scopes: string[]) => {
        const k = String(key || '').trim().toLowerCase();
        if (!k) return true;
        if (k === 'whatsapp') {
            return scopes.includes('whatsapp:read') || scopes.includes('whatsapp:send') || scopes.includes('whatsapp:config');
        }
        return scopes.includes(`${k}:read`) || scopes.includes(`${k}:write`);
    };

    const navItems = navigation.filter((item) => {
        if (moduleFlags && Object.prototype.hasOwnProperty.call(moduleFlags, item.key) && moduleFlags[item.key] === false) {
            return false;
        }
        if (!userRole) return true;
        const roleNorm = String(userRole || '').toLowerCase();
        if (roleNorm === 'owner' || roleNorm === 'admin') return true;
        return hasScopeFor(item.key, userScopes || []);
    });

    useEffect(() => {
        const current = navigation.find((n) => pathname.startsWith(n.href));
        if (!current) return;
        const enabledByModule = !moduleFlags || moduleFlags[current.key] !== false;
        const roleNorm = String(userRole || '').toLowerCase();
        const enabledByScope =
            !userRole || roleNorm === 'owner' || roleNorm === 'admin' || hasScopeFor(current.key, userScopes || []);
        const enabled = enabledByModule && enabledByScope;
        if (enabled) return;
        const first = navItems[0] || navigation[0];
        if (first) router.push(first.href);
    }, [moduleFlags, pathname, router, userRole, userScopes, navItems]);

    const [logoutWarningOpen, setLogoutWarningOpen] = useState(false);
    const [activeSession, setActiveSession] = useState<any>(null);

    // Load User & Session Data
    useEffect(() => {
        const loadHeaderData = async () => {
            try {
                const res = await api.getSession('gestion');
                if (res.ok && res.data?.user) {
                    setUserName(res.data.user.nombre);
                    setUserRole(res.data.user.rol);
                    setUserScopes((res.data.user.scopes || []) as any);

                    // If profesor, check active session
                    if (res.data.user.rol === 'profesor' && res.data.user.gestion_profesor_id) {
                        const activeRes = await api.getSesionActiva(res.data.user.gestion_profesor_id);
                        if (activeRes.ok && activeRes.data?.sesion) {
                            const s = activeRes.data.sesion;
                            // Calculate start time
                            let start: Date | null = null;
                            if (s.inicio) start = new Date(s.inicio);
                            else if (s.fecha && s.hora_inicio) start = new Date(`${s.fecha}T${s.hora_inicio}`);

                            if (start && !isNaN(start.getTime())) {
                                setSessionStartTime(start);
                            } else {
                                setSessionStartTime(null);
                            }
                        } else {
                            setSessionStartTime(null);
                        }
                    }
                }
            } catch { }
        };

        loadHeaderData();
        const poll = setInterval(loadHeaderData, 15000); // Poll every 15s to keep sync
        return () => clearInterval(poll);
    }, []);

    // Timer Tick
    useEffect(() => {
        if (!sessionStartTime) {
            setSessionTimer(null);
            return;
        }

        const tick = () => {
            const now = new Date();
            const diff = Math.floor((now.getTime() - sessionStartTime.getTime()) / 1000);
            if (diff < 0) {
                setSessionTimer('00:00:00');
                return;
            }
            const h = Math.floor(diff / 3600);
            const m = Math.floor((diff % 3600) / 60);
            const s = diff % 60;
            setSessionTimer(`${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`);
        };

        tick();
        const interval = setInterval(tick, 1000);
        return () => clearInterval(interval);
    }, [sessionStartTime]);

    const proceedLogout = async () => {
        setLoggingOut(true);
        try {
            await api.logoutGestion();
        } catch {
            // Ignore errors
        } finally {
            router.push('/gestion-login');
        }
    };

    const handleLogout = async () => {
        setLoggingOut(true);
        try {
            // Check current user
            const sessionRes = await api.getSession('gestion');
            if (sessionRes.ok && sessionRes.data?.user?.rol === 'profesor' && sessionRes.data.user.gestion_profesor_id) {
                const pid = sessionRes.data.user.gestion_profesor_id;
                const activeRes = await api.getSesionActiva(pid);
                if (activeRes.ok && activeRes.data?.sesion) {
                    setActiveSession({ ...activeRes.data.sesion, profesorId: pid });
                    setLogoutWarningOpen(true);
                    setLoggingOut(false);
                    return;
                }
            }
        } catch (e) {
            // Ignore errors and proceed
        }
        proceedLogout();
    };

    const handleCloseSessionAndLogout = async () => {
        if (activeSession) {
            try {
                // api.endSesion requires sessionId. getSesionActiva returns sesion object with id
                await api.endSesion(activeSession.profesorId, activeSession.id);
            } catch { }
        }
        proceedLogout();
    };

    // Get current section title
    const currentSection = navigation.find(
        (item) => pathname === item.href || pathname?.startsWith(item.href + '/')
    );

    return (
        <div className="min-h-screen bg-slate-950">
            {/* Toast Container */}
            <ToastContainer />

            {/* Header - Fixed top bar */}
            <header className="fixed top-0 left-0 right-0 z-40 h-16 bg-slate-900 border-b border-slate-800/50">
                <div className="h-full flex items-center justify-between px-4 lg:px-6">
                    {/* Left: Logo + current section */}
                    <div className="flex items-center gap-4">
                        {/* Mobile menu button */}
                        <button
                            onClick={() => setMobileMenuOpen(true)}
                            className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/50 transition-colors"
                            aria-label="Abrir menú"
                        >
                            <Menu className="w-5 h-5" />
                        </button>

                        {/* Logo */}
                        <Link href="/gestion/usuarios" className="flex items-center gap-3">
                            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-sm">
                                {gymLogoUrl ? (
                                    <img
                                        src={gymLogoUrl}
                                        alt="Logo"
                                        className="w-6 h-6 object-contain bg-white/90 rounded-md p-1"
                                        onError={() => setGymLogoUrl('')}
                                    />
                                ) : (
                                    <Dumbbell className="w-4 h-4 text-white" />
                                )}
                            </div>
                            <div className="hidden sm:block">
                                <h1 className="text-base font-display font-bold text-white leading-none">
                                    Gestión
                                </h1>
                                <p className="text-xs text-slate-500">Panel de administración</p>
                            </div>
                        </Link>

                        {/* Current section badge */}
                        {currentSection && (
                            <div className="hidden md:flex items-center gap-2 text-slate-400">
                                <ChevronRight className="w-4 h-4" />
                                <span className="text-sm font-medium text-white">
                                    {currentSection.name}
                                </span>
                            </div>
                        )}
                    </div>

                    {/* Right: Actions */}
                    <div className="flex items-center gap-4">
                        {/* User Info & Timer */}
                        <div className="hidden md:flex flex-col items-end">
                            <div className="text-sm font-medium text-white flex items-center gap-2">
                                {userName}
                                {userRole === 'owner' && <span className="text-[10px] bg-purple-500/20 text-purple-300 px-1.5 py-0.5 rounded font-bold uppercase tracking-wider">Admin</span>}
                                {userRole === 'profesor' && <span className="text-[10px] bg-blue-500/20 text-blue-300 px-1.5 py-0.5 rounded font-bold uppercase tracking-wider">Profe</span>}
                            </div>
                        </div>

                        <MiJornadaWidget className="hidden md:flex" />

                        <div className="flex items-center gap-2">
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
                </div>
            </header>

            {/* Mobile sidebar overlay */}
            <AnimatePresence>
                {mobileMenuOpen && (
                    <>
                        {/* Backdrop */}
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setMobileMenuOpen(false)}
                            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm lg:hidden"
                        />

                        {/* Sidebar */}
                        <motion.aside
                            initial={{ x: -280 }}
                            animate={{ x: 0 }}
                            exit={{ x: -280 }}
                            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                            className="fixed top-0 left-0 bottom-0 z-50 w-72 bg-slate-900 border-r border-slate-800 lg:hidden"
                        >
                            <div className="h-full flex flex-col min-h-0">
                                {/* Header */}
                                <div className="h-16 flex items-center justify-between px-4 border-b border-slate-800">
                                    <div className="flex items-center gap-3">
                                        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
                                            {gymLogoUrl ? (
                                                <img src={gymLogoUrl} alt="Logo" className="w-6 h-6 object-contain bg-white/90 rounded-md p-1" />
                                            ) : (
                                                <Dumbbell className="w-4 h-4 text-white" />
                                            )}
                                        </div>
                                        <span className="text-base font-display font-bold text-white">
                                            Gestión
                                        </span>
                                    </div>
                                    <button
                                        onClick={() => setMobileMenuOpen(false)}
                                        className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/50 transition-colors"
                                    >
                                        <X className="w-5 h-5" />
                                    </button>
                                </div>

                                {/* Nav */}
                                <nav className="flex-1 min-h-0 p-4 space-y-1 overflow-y-auto overflow-x-auto">
                                    {navItems.map((item) => {
                                        const isActive = pathname === item.href || pathname?.startsWith(item.href + '/');
                                        return (
                                            <Link
                                                key={item.name}
                                                href={item.href}
                                                onClick={() => setMobileMenuOpen(false)}
                                                className={cn(
                                                    'flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 whitespace-nowrap min-w-max',
                                                    isActive
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
                )}
            </AnimatePresence>

            {/* Desktop sidebar */}
            <aside className="hidden lg:block fixed top-16 left-0 bottom-0 w-64 border-r border-slate-800/50 bg-slate-900/50 backdrop-blur-lg">
                <nav className="p-4 space-y-1 overflow-y-auto overflow-x-auto h-full">
                    {navItems.map((item) => {
                        const isActive = pathname === item.href || pathname?.startsWith(item.href + '/');
                        return (
                            <Link
                                key={item.name}
                                href={item.href}
                                className={cn(
                                    'group flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 whitespace-nowrap min-w-max',
                                    isActive
                                        ? 'bg-primary-500/20 text-primary-300 shadow-sm'
                                        : 'text-slate-400 hover:bg-slate-800/50 hover:text-white'
                                )}
                            >
                                <item.icon className={cn(
                                    'w-5 h-5 flex-shrink-0 transition-transform duration-200',
                                    !isActive && 'group-hover:scale-110'
                                )} />
                                <span className="font-medium">{item.name}</span>
                            </Link>
                        );
                    })}
                </nav>
            </aside>

            {/* Main content */}
            <main className="pt-16 lg:pl-64 min-h-screen">
                <div className="p-4 lg:p-6">
                    {children}
                </div>
            </main>
            {/* Logout Warning Modal */}
            <Modal
                isOpen={logoutWarningOpen}
                onClose={() => setLogoutWarningOpen(false)}
                title="Sesión Activa Detectada"
                size="md"
            >
                <div className="space-y-4">
                    <div className="p-4 bg-warning-500/10 rounded-lg flex gap-3">
                        <div className="p-2 bg-warning-500/20 rounded-full h-fit">
                            <Clock className="w-5 h-5 text-warning-400" />
                        </div>
                        <div>
                            <h4 className="font-medium text-warning-100 mb-1">Tu jornada laboral sigue activa</h4>
                            <p className="text-sm text-warning-200/80">
                                Tienes una sesión iniciada. ¿Deseas finalizarla antes de salir?
                            </p>
                        </div>
                    </div>

                    <div className="flex flex-col gap-2 sm:flex-row sm:justify-end pt-2">
                        <Button
                            variant="ghost"
                            onClick={() => setLogoutWarningOpen(false)}
                            disabled={loggingOut}
                        >
                            Cancelar
                        </Button>
                        <Button
                            variant="secondary"
                            onClick={proceedLogout}
                            disabled={loggingOut}
                        >
                            Mantener Activa y Salir
                        </Button>
                        <Button
                            variant="primary"
                            onClick={handleCloseSessionAndLogout}
                            isLoading={loggingOut}
                        >
                            Finalizar y Salir
                        </Button>
                    </div>
                </div>
            </Modal>
        </div>
    );
}
