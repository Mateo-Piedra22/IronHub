'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { Users, CreditCard, Clipboard, ScanLine, Settings } from 'lucide-react';

export default function DashboardPage() {
    return (
        <div className="p-4 lg:p-6">
            <div className="max-w-6xl mx-auto space-y-4">
                <div className="card p-5">
                    <h1 className="text-xl font-display font-bold text-white">Dashboard</h1>
                    <p className="text-sm text-slate-400">
                        KPIs y accesos rápidos del dueño.
                    </p>
                </div>
                <DashboardKpis />
                <DashboardQuickLinks />
            </div>
        </div>
    );
}

function DashboardKpis() {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string>('');
    const [data, setData] = useState<{
        total_activos: number;
        total_inactivos: number;
        ingresos_mes: number;
        asistencias_hoy: number;
        nuevos_30_dias: number;
    } | null>(null);

    useEffect(() => {
        const run = async () => {
            setLoading(true);
            setError('');
            try {
                const res = await api.getKPIs();
                if (res.ok && res.data) {
                    setData(res.data);
                } else {
                    setData(null);
                    setError(res.error || 'No se pudieron cargar los KPIs');
                }
            } catch {
                setData(null);
                setError('No se pudieron cargar los KPIs');
            } finally {
                setLoading(false);
            }
        };
        run();
    }, []);

    const kpis = [
        { label: 'Activos', value: data?.total_activos ?? '-', accent: 'text-primary-300' },
        { label: 'Inactivos', value: data?.total_inactivos ?? '-', accent: 'text-slate-200' },
        { label: 'Ingresos del mes', value: data?.ingresos_mes ?? '-', accent: 'text-gold-300' },
        { label: 'Asistencias hoy', value: data?.asistencias_hoy ?? '-', accent: 'text-primary-300' },
        { label: 'Nuevos (30 días)', value: data?.nuevos_30_dias ?? '-', accent: 'text-slate-200' },
    ];

    return (
        <div className="card p-5">
            <div className="flex items-center justify-between gap-3 mb-4">
                <h2 className="text-base font-semibold text-white">KPIs</h2>
                {loading ? (
                    <span className="text-xs text-slate-500">Cargando…</span>
                ) : error ? (
                    <span className="text-xs text-danger-400">{error}</span>
                ) : null}
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                {kpis.map((k) => (
                    <div key={k.label} className="rounded-xl bg-slate-900/60 border border-slate-800/60 p-4">
                        <div className="text-xs text-slate-500">{k.label}</div>
                        <div className={`mt-1 text-lg font-bold ${k.accent}`}>{k.value}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function DashboardQuickLinks() {
    const links = [
        { href: '/gestion/usuarios', label: 'Usuarios', icon: Users },
        { href: '/gestion/pagos', label: 'Pagos', icon: CreditCard },
        { href: '/gestion/rutinas', label: 'Rutinas', icon: Clipboard },
        { href: '/gestion/asistencias', label: 'Asistencias', icon: ScanLine },
        { href: '/gestion/configuracion', label: 'Configuración', icon: Settings },
    ];
    return (
        <div className="card p-5">
            <h2 className="text-base font-semibold text-white mb-4">Accesos rápidos</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {links.map((l) => (
                    <Link
                        key={l.href}
                        href={l.href}
                        className="flex items-center gap-3 rounded-xl bg-slate-900/60 border border-slate-800/60 p-4 hover:border-primary-500/40 hover:bg-slate-900 transition-colors"
                    >
                        <div className="w-9 h-9 rounded-xl bg-slate-800/60 flex items-center justify-center">
                            <l.icon className="w-4 h-4 text-slate-300" />
                        </div>
                        <div className="text-sm font-semibold text-white">{l.label}</div>
                    </Link>
                ))}
            </div>
        </div>
    );
}
