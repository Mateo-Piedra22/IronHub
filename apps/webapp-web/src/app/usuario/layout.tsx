'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import {
    Dumbbell, LayoutDashboard, CreditCard, Calendar,
    Clipboard, LogOut, User, Bell, Shield
} from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { api } from '@/lib/api';

const navigation = [
    { name: 'Inicio', href: '/usuario', icon: LayoutDashboard },
    { name: 'Mis Pagos', href: '/usuario/payments', icon: CreditCard },
    { name: 'Asistencias', href: '/usuario/attendance', icon: Calendar },
    { name: 'Mi Rutina', href: '/usuario/routines', icon: Clipboard },
    { name: 'Mi Perfil', href: '/usuario/profile', icon: User },
    { name: 'Mis Accesos', href: '/usuario/accesos', icon: Shield },
];

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();
    const { logout } = useAuth();
    const [gymLogoUrl, setGymLogoUrl] = useState<string>('');

    useEffect(() => {
        const loadBranding = async () => {
            try {
                const res = await api.getBootstrap('usuario');
                const logo = res.ok ? (res.data?.gym?.logo_url || '') : '';
                if (logo) setGymLogoUrl(logo);
            } catch {
                // ignore
            }
        };
        loadBranding();
    }, []);

    return (
        <div className="min-h-screen">
            {/* Top navigation bar */}
            <header className="fixed top-0 left-0 right-0 z-50 bg-slate-900 border-b border-slate-800/50">
                <div className="max-w-7xl mx-auto px-4 py-3">
                    <div className="flex items-center justify-between">
                        {/* Logo */}
                        <Link href="/usuario" className="flex items-center gap-3">
                            <div
                                className={`w-10 h-10 rounded-xl shadow-sm overflow-hidden flex items-center justify-center ${
                                    gymLogoUrl ? 'bg-transparent' : 'bg-gradient-to-br from-primary-500 to-primary-700'
                                }`}
                            >
                                {gymLogoUrl ? (
                                    <img
                                        src={gymLogoUrl}
                                        alt="Logo"
                                        className="w-full h-full object-contain"
                                        onError={() => setGymLogoUrl('')}
                                    />
                                ) : (
                                    <Dumbbell className="w-5 h-5 text-white" />
                                )}
                            </div>
                            <span className="text-lg font-display font-bold text-white hidden sm:block">
                                Mi Gimnasio
                            </span>
                        </Link>

                        {/* Right side actions */}
                        <div className="flex items-center gap-3">
                            <button className="p-2 rounded-lg hover:bg-slate-800/50 text-slate-400 hover:text-white transition-colors relative">
                                <Bell className="w-5 h-5" />
                                <span className="absolute top-1 right-1 w-2 h-2 bg-primary-500 rounded-full" />
                            </button>
                            <button
                                onClick={() => logout()}
                                className="p-2 rounded-lg hover:bg-danger-500/20 text-slate-400 hover:text-danger-400 transition-colors"
                            >
                                <LogOut className="w-5 h-5" />
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main content with padding for header */}
            <main className="pt-20 pb-24">
                <div className="max-w-7xl mx-auto px-4">
                    {children}
                </div>
            </main>

            {/* Bottom navigation for mobile */}
            <nav className="fixed bottom-0 left-0 right-0 z-50 bg-slate-900 border-t border-slate-800/50 md:hidden">
                <div className="flex items-center justify-around py-2">
                    {navigation.slice(0, 4).map((item) => {
                        const isActive = pathname === item.href;
                        return (
                            <Link
                                key={item.name}
                                href={item.href}
                                className={`flex flex-col items-center gap-1 px-4 py-2 rounded-lg transition-colors ${isActive ? 'text-primary-400' : 'text-slate-500'
                                    }`}
                            >
                                <item.icon className="w-5 h-5" />
                                <span className="text-xs">{item.name}</span>
                            </Link>
                        );
                    })}
                </div>
            </nav>

            {/* Desktop sidebar */}
            <aside className="hidden md:block fixed left-0 top-16 bottom-0 w-64 bg-slate-900 border-r border-slate-800/50 p-4 flex flex-col min-h-0">
                <nav className="space-y-1 flex-1 min-h-0 overflow-y-auto overflow-x-auto">
                    {navigation.map((item) => {
                        const isActive = pathname === item.href || pathname?.startsWith(item.href + '/');
                        return (
                            <Link
                                key={item.name}
                                href={item.href}
                                className={`nav-item ${isActive ? 'active' : ''}`}
                            >
                                <item.icon className="w-5 h-5" />
                                <span>{item.name}</span>
                            </Link>
                        );
                    })}
                </nav>
            </aside>

            {/* Content offset for desktop sidebar */}
            <style jsx global>{`
        @media (min-width: 768px) {
          main {
            margin-left: 16rem;
          }
        }
      `}</style>
        </div>
    );
}

