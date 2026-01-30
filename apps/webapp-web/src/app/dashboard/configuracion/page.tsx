'use client';

import { Settings } from 'lucide-react';
import ConfiguracionPage from '@/app/gestion/configuracion/page';

export default function DashboardConfiguracionPage() {
    return (
        <div className="space-y-6">
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-primary-500/20 text-primary-300 flex items-center justify-center">
                    <Settings className="w-5 h-5" />
                </div>
                <div>
                    <h1 className="text-xl font-semibold text-white">Configuración</h1>
                    <p className="text-sm text-slate-400">Flags, ajustes y control del sistema.</p>
                </div>
            </div>

            <div className="rounded-2xl border border-slate-800/60 bg-slate-900/20">
                <ConfiguracionPage />
            </div>
        </div>
    );
}

