'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    Dumbbell, LayoutDashboard, CreditCard, Calendar,
    Clipboard, LogOut, User, Bell
} from 'lucide-react';

const navigation = [
    { name: 'Inicio', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Mis Pagos', href: '/dashboard/payments', icon: CreditCard },
    { name: 'Asistencias', href: '/dashboard/attendance', icon: Calendar },
    { name: 'Mi Rutina', href: '/dashboard/routines', icon: Clipboard },
    { name: 'Mi Perfil', href: '/dashboard/profile', icon: User },
];

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();

    return (
        <div className="min-h-screen">
            {/* Top navigation bar */}
            <header className="fixed top-0 left-0 right-0 z-50 glass border-b border-neutral-800/50">
                <div className="max-w-7xl mx-auto px-4 py-3">
                    <div className="flex items-center justify-between">
                        {/* Logo */}
                        <Link href="/dashboard" className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-iron-500 to-iron-700 flex items-center justify-center shadow-glow-sm">
                                <Dumbbell className="w-5 h-5 text-white" />
                            </div>
                            <span className="text-lg font-display font-bold text-white hidden sm:block">
                                Mi Gimnasio
                            </span>
                        </Link>

                        {/* Right side actions */}
                        <div className="flex items-center gap-3">
                            <button className="p-2 rounded-lg hover:bg-neutral-800/50 text-neutral-400 hover:text-white transition-colors relative">
                                <Bell className="w-5 h-5" />
                                <span className="absolute top-1 right-1 w-2 h-2 bg-iron-500 rounded-full" />
                            </button>
                            <button
                                onClick={() => window.location.href = '/'}
                                className="p-2 rounded-lg hover:bg-danger-500/20 text-neutral-400 hover:text-danger-400 transition-colors"
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
            <nav className="fixed bottom-0 left-0 right-0 z-50 glass border-t border-neutral-800/50 md:hidden">
                <div className="flex items-center justify-around py-2">
                    {navigation.slice(0, 4).map((item) => {
                        const isActive = pathname === item.href;
                        return (
                            <Link
                                key={item.name}
                                href={item.href}
                                className={`flex flex-col items-center gap-1 px-4 py-2 rounded-lg transition-colors ${isActive ? 'text-iron-400' : 'text-neutral-500'
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
            <aside className="hidden md:block fixed left-0 top-16 bottom-0 w-64 glass border-r border-neutral-800/50 p-4">
                <nav className="space-y-1">
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
