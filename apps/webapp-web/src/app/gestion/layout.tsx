'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';
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
    LayoutDashboard,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { ToastContainer } from '@/components/ui';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api';

// Navigation items matching legacy gestion.html tabs
const navigation = [
    { name: 'Dashboard', href: '/gestion/dashboard', icon: LayoutDashboard, description: 'Estadísticas y KPIs' },
    { name: 'Usuarios', href: '/gestion/usuarios', icon: Users, description: 'Gestionar socios' },
    { name: 'Pagos', href: '/gestion/pagos', icon: CreditCard, description: 'Registro de pagos' },
    { name: 'Profesores', href: '/gestion/profesores', icon: GraduationCap, description: 'Staff y sesiones' },
    { name: 'Rutinas', href: '/gestion/rutinas', icon: Clipboard, description: 'Plantillas y asignación' },
    { name: 'Ejercicios', href: '/gestion/ejercicios', icon: Dumbbell, description: 'Biblioteca de ejercicios' },
    { name: 'Clases', href: '/gestion/clases', icon: CalendarDays, description: 'Horarios grupales' },
    { name: 'Asistencias', href: '/gestion/asistencias', icon: ScanLine, description: 'Check-in y registro' },
    { name: 'WhatsApp', href: '/gestion/whatsapp', icon: MessageSquare, description: 'Mensajes y API' },
    { name: 'Configuración', href: '/gestion/configuracion', icon: Settings, description: 'Cuotas, métodos, tema' },
];

export default function GestionLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();
    const router = useRouter();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const [loggingOut, setLoggingOut] = useState(false);

    // Logout handler
    const handleLogout = async () => {
        setLoggingOut(true);
        try {
            await api.logout();
        } catch {
            // Ignore errors
        } finally {
            router.push('/gestion-login');
        }
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
                                <Dumbbell className="w-4 h-4 text-white" />
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
                            <div className="h-full flex flex-col">
                                {/* Header */}
                                <div className="h-16 flex items-center justify-between px-4 border-b border-slate-800">
                                    <div className="flex items-center gap-3">
                                        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
                                            <Dumbbell className="w-4 h-4 text-white" />
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
                                <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
                                    {navigation.map((item) => {
                                        // For dashboard parent, only exact match to prevent multi-selection
                                        const isActive = item.href === '/gestion/dashboard'
                                            ? pathname === item.href
                                            : pathname === item.href || pathname?.startsWith(item.href + '/');
                                        return (
                                            <Link
                                                key={item.name}
                                                href={item.href}
                                                onClick={() => setMobileMenuOpen(false)}
                                                className={cn(
                                                    'flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200',
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
                <nav className="p-4 space-y-1 overflow-y-auto h-full">
                    {navigation.map((item) => {
                        // For dashboard parent, only exact match to prevent multi-selection
                        const isActive = item.href === '/gestion/dashboard'
                            ? pathname === item.href
                            : pathname === item.href || pathname?.startsWith(item.href + '/');
                        return (
                            <Link
                                key={item.name}
                                href={item.href}
                                className={cn(
                                    'group flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200',
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
        </div>
    );
}

