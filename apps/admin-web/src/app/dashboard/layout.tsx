'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    Dumbbell, LayoutDashboard, Building2, Users, CreditCard,
    MessageSquare, Settings, LogOut, ChevronRight
} from 'lucide-react';

const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Gimnasios', href: '/dashboard/gyms', icon: Building2 },
    { name: 'Suscripciones', href: '/dashboard/subscriptions', icon: CreditCard },
    { name: 'Pagos', href: '/dashboard/payments', icon: CreditCard },
    { name: 'WhatsApp', href: '/dashboard/whatsapp', icon: MessageSquare },
    { name: 'Configuración', href: '/dashboard/settings', icon: Settings },
];

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();

    return (
        <div className="min-h-screen">
            {/* Sidebar */}
            <aside className="sidebar">
                {/* Logo */}
                <div className="p-6 border-b border-neutral-800/50">
                    <Link href="/dashboard" className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-iron-500 to-iron-700 flex items-center justify-center shadow-glow-sm">
                            <Dumbbell className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <span className="text-lg font-display font-bold text-white">
                                Iron<span className="text-iron-400">Hub</span>
                            </span>
                            <span className="block text-xs text-neutral-500">Admin Panel</span>
                        </div>
                    </Link>
                </div>

                {/* Navigation */}
                <nav className="flex-1 p-4 space-y-1">
                    {navigation.map((item) => {
                        const isActive = pathname === item.href || pathname?.startsWith(item.href + '/');
                        return (
                            <Link
                                key={item.name}
                                href={item.href}
                                className={`sidebar-item ${isActive ? 'active' : ''}`}
                            >
                                <item.icon className="w-5 h-5" />
                                <span>{item.name}</span>
                                {isActive && <ChevronRight className="w-4 h-4 ml-auto text-iron-400" />}
                            </Link>
                        );
                    })}
                </nav>

                {/* Footer */}
                <div className="p-4 border-t border-neutral-800/50">
                    <button
                        onClick={() => {
                            // TODO: Implement logout
                            window.location.href = '/';
                        }}
                        className="sidebar-item w-full text-danger-400 hover:bg-danger-500/10 hover:text-danger-300"
                    >
                        <LogOut className="w-5 h-5" />
                        <span>Cerrar Sesión</span>
                    </button>
                </div>
            </aside>

            {/* Main content */}
            <main className="main-content">
                {children}
            </main>
        </div>
    );
}
