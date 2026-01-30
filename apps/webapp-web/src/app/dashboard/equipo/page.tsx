'use client';

import { useMemo, useState } from 'react';
import { UsersRound } from 'lucide-react';
import { cn } from '@/lib/utils';
import ProfesoresPage from '@/app/gestion/profesores/page';
import EmpleadosPage from '@/app/gestion/empleados/page';

export default function EquipoPage() {
    const [tab, setTab] = useState<'profesores' | 'staff'>('profesores');

    const tabs = useMemo(
        () => [
            { key: 'profesores' as const, label: 'Profesores' },
            { key: 'staff' as const, label: 'Staff' },
        ],
        []
    );

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-primary-500/20 text-primary-300 flex items-center justify-center">
                    <UsersRound className="w-5 h-5" />
                </div>
                <div>
                    <h1 className="text-xl font-semibold text-white">Equipo</h1>
                    <p className="text-sm text-slate-400">Administración completa de profesores y staff.</p>
                </div>
            </div>

            <div className="flex flex-wrap gap-2">
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
            </div>

            <div className="rounded-2xl border border-slate-800/60 bg-slate-900/20">
                {tab === 'profesores' ? <ProfesoresPage /> : <EmpleadosPage />}
            </div>
        </div>
    );
}

