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
                <div className="p-6 border-b border-slate-800/50">
                    <Link href="/dashboard" className="flex items-center gap-3">
                        <img
                            src="/images/logo-ironhub.png"
                            alt="IronHub"
                            className="w-10 h-10 rounded-xl shadow-sm"
                        />
                        <div>
                            <span className="text-lg font-display font-bold text-white">
                                Iron<span className="text-primary-400">Hub</span>
                            </span>
                            <span className="block text-xs text-slate-500">Admin Panel</span>
                        </div>
                    </Link>
                </div>

                {/* Navigation */}
                <nav className="flex-1 p-4 space-y-1">
                    {navigation.map((item) => {
                        // For /dashboard (parent), only exact match to prevent multi-selection
                        // For child routes, also match sub-paths
                        const isActive = item.href === '/dashboard'
                            ? pathname === item.href
                            : pathname === item.href || pathname?.startsWith(item.href + '/');
                        return (
                            <Link
                                key={item.name}
                                href={item.href}
                                className={`sidebar-item ${isActive ? 'active' : ''}`}
                            >
                                <item.icon className="w-5 h-5" />
                                <span>{item.name}</span>
                                {isActive && <ChevronRight className="w-4 h-4 ml-auto text-primary-400" />}
                            </Link>
                        );
                    })}
                </nav>

                {/* Footer */}
                <div className="p-4 border-t border-slate-800/50 space-y-3">
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

                    {/* MotionA Credit */}
                    <a
                        href="https://motiona.xyz"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center justify-center gap-2 py-2 text-slate-500 hover:text-slate-300 transition-colors text-xs"
                    >
                        <img
                            src="/images/logo-motiona.png"
                            alt="MotionA"
                            className="w-5 h-5 rounded"
                        />
                        <span>by MotionA</span>
                    </a>
                </div>
            </aside>

            {/* Main content */}
            <main className="main-content">
                {children}
            </main>
        </div>
    );
}

