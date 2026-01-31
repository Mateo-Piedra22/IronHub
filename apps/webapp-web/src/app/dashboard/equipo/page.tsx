'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { UsersRound } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api';
import ProfesoresPage from '@/app/gestion/profesores/page';
import EmpleadosPage from '@/app/gestion/empleados/page';

export default function EquipoPage() {
    const [tab, setTab] = useState<'profesores' | 'staff'>('profesores');
    const [sucursalActualId, setSucursalActualId] = useState<number | null>(null);
    const [loadingSucursal, setLoadingSucursal] = useState(false);
    const [loadingGeneral, setLoadingGeneral] = useState(false);
    const [errorGeneral, setErrorGeneral] = useState('');
    const [search, setSearch] = useState('');
    const [profesores, setProfesores] = useState<any[]>([]);
    const [staff, setStaff] = useState<any[]>([]);

    const tabs = useMemo(
        () => [
            { key: 'profesores' as const, label: 'Profesores' },
            { key: 'staff' as const, label: 'Staff' },
        ],
        []
    );

    const loadSucursalActual = useCallback(async () => {
        setLoadingSucursal(true);
        try {
            const r = await api.getSucursales();
            if (r.ok && r.data?.ok) {
                setSucursalActualId((r.data.sucursal_actual_id ?? null) as any);
            } else {
                setSucursalActualId(null);
            }
        } finally {
            setLoadingSucursal(false);
        }
    }, []);

    const loadGeneral = useCallback(async () => {
        if (sucursalActualId) return;
        setLoadingGeneral(true);
        setErrorGeneral('');
        try {
            if (tab === 'profesores') {
                const r = await api.getOwnerDashboardProfesores({ search: search || undefined });
                if (r.ok && r.data?.ok) setProfesores((r.data.items || []) as any[]);
                else setErrorGeneral(r.error || 'No se pudieron cargar profesores');
            } else {
                const r = await api.getOwnerDashboardStaff({ search: search || undefined });
                if (r.ok && r.data?.ok) setStaff((r.data.items || []) as any[]);
                else setErrorGeneral(r.error || 'No se pudo cargar staff');
            }
        } catch (e) {
            setErrorGeneral(String(e) || 'No se pudieron cargar datos');
        } finally {
            setLoadingGeneral(false);
        }
    }, [sucursalActualId, tab, search]);

    useEffect(() => {
        loadSucursalActual();
    }, [loadSucursalActual]);

    useEffect(() => {
        loadGeneral();
    }, [loadGeneral]);

    useEffect(() => {
        const handler = () => loadSucursalActual();
        window.addEventListener('ironhub:sucursal-changed', handler as any);
        return () => window.removeEventListener('ironhub:sucursal-changed', handler as any);
    }, [loadSucursalActual]);

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-primary-500/20 text-primary-300 flex items-center justify-center">
                    <UsersRound className="w-5 h-5" />
                </div>
                <div>
                    <h1 className="text-xl font-semibold text-white">Equipo</h1>
                    <p className="text-sm text-slate-400">
                        {sucursalActualId ? 'Gestión completa por sucursal seleccionada.' : 'Vista general (todas las sucursales).'}
                    </p>
                </div>
            </div>

            <div className="flex flex-col gap-3">
                <div className="flex flex-wrap items-center gap-2">
                    {tabs.map((t) => (
                        <button
                            key={t.key}
                            onClick={() => setTab(t.key)}
                            className={cn(
                                'h-9 px-4 rounded-xl text-sm font-medium transition-colors border',
                                tab === t.key
                                    ? 'bg-primary-500/20 text-primary-200 border-primary-500/30'
                                    : 'bg-slate-900/30 text-slate-300 border-slate-800/60 hover:bg-slate-900/50'
                            )}
                        >
                            {t.label}
                        </button>
                    ))}
                    {!sucursalActualId ? (
                        <input
                            className="input h-9 w-64"
                            placeholder="Buscar por nombre/DNI..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                    ) : (
                        <Link href={tab === 'profesores' ? '/gestion/profesores' : '/gestion/empleados'} className="btn-secondary h-9">
                            Abrir gestión
                        </Link>
                    )}
                </div>
                {loadingSucursal ? <div className="text-xs text-slate-500">Cargando sucursal…</div> : null}
                {errorGeneral ? <div className="text-xs text-danger-400">{errorGeneral}</div> : null}
                {loadingGeneral ? <div className="text-xs text-slate-500">Cargando…</div> : null}
            </div>

            <div className="rounded-2xl border border-slate-800/60 bg-slate-900/20">
                {sucursalActualId ? (
                    tab === 'profesores' ? (
                        <ProfesoresPage />
                    ) : (
                        <EmpleadosPage />
                    )
                ) : (
                    tab === 'profesores' ? (
                        <div className="p-4 overflow-x-auto">
                            <table className="min-w-full text-sm">
                                <thead>
                                    <tr className="text-slate-500">
                                        <th className="text-left font-medium py-2 pr-4">Nombre</th>
                                        <th className="text-left font-medium py-2 pr-4">Teléfono</th>
                                        <th className="text-left font-medium py-2 pr-4">Tipo</th>
                                        <th className="text-left font-medium py-2 pr-4">Estado</th>
                                        <th className="text-left font-medium py-2 pr-4">Sucursales</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {profesores.map((p) => (
                                        <tr key={String(p.id)} className="border-t border-slate-800/60">
                                            <td className="py-2 pr-4 text-slate-200">{p.nombre || `#${p.id}`}</td>
                                            <td className="py-2 pr-4 text-slate-400">{p.telefono || '-'}</td>
                                            <td className="py-2 pr-4 text-slate-400">{p.tipo || '-'}</td>
                                            <td className="py-2 pr-4 text-slate-400">{p.estado || '-'}</td>
                                            <td className="py-2 pr-4 text-slate-400">
                                                {(p.sucursales || []).length
                                                    ? (p.sucursales || []).map((s: any) => s?.nombre).filter(Boolean).join(', ')
                                                    : 'Sin sucursal'}
                                            </td>
                                        </tr>
                                    ))}
                                    {!profesores.length ? (
                                        <tr>
                                            <td className="py-3 text-slate-400" colSpan={5}>
                                                Sin resultados
                                            </td>
                                        </tr>
                                    ) : null}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <div className="p-4 overflow-x-auto">
                            <table className="min-w-full text-sm">
                                <thead>
                                    <tr className="text-slate-500">
                                        <th className="text-left font-medium py-2 pr-4">Nombre</th>
                                        <th className="text-left font-medium py-2 pr-4">Rol</th>
                                        <th className="text-left font-medium py-2 pr-4">Sucursales</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {staff.map((s) => (
                                        <tr key={String(s.id)} className="border-t border-slate-800/60">
                                            <td className="py-2 pr-4 text-slate-200">{s.nombre || `#${s.id}`}</td>
                                            <td className="py-2 pr-4 text-slate-400">{s.rol || '-'}</td>
                                            <td className="py-2 pr-4 text-slate-400">
                                                {(s.sucursales_info || []).length
                                                    ? (s.sucursales_info || []).map((x: any) => x?.nombre).filter(Boolean).join(', ')
                                                    : 'Sin sucursal'}
                                            </td>
                                        </tr>
                                    ))}
                                    {!staff.length ? (
                                        <tr>
                                            <td className="py-3 text-slate-400" colSpan={3}>
                                                Sin resultados
                                            </td>
                                        </tr>
                                    ) : null}
                                </tbody>
                            </table>
                        </div>
                    )
                )}
            </div>
        </div>
    );
}
