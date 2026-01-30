'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Building2, Loader2, Lock, ShieldCheck } from 'lucide-react';
import { api, type UsuarioEntitlements } from '@/lib/api';

export default function AccesosPage() {
    const [data, setData] = useState<UsuarioEntitlements | null>(null);
    const [loading, setLoading] = useState(true);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.getUsuarioEntitlements();
            if (res.ok && res.data) {
                setData(res.data);
            } else {
                setData(null);
            }
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        void load();
    }, [load]);

    const allowedSucursales = useMemo(() => {
        const items = data?.allowed_sucursales || [];
        return items.filter((s) => !!s.activa);
    }, [data]);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
            </div>
        );
    }

    return (
        <div className="space-y-6 py-6">
            <div>
                <h1 className="text-2xl font-display font-bold text-white">Mis Accesos</h1>
                <p className="text-slate-400 mt-1">Sucursales y clases habilitadas por tu plan.</p>
            </div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="card p-4">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-primary-500/20 text-primary-300 flex items-center justify-center">
                        <ShieldCheck className="w-5 h-5" />
                    </div>
                    <div className="min-w-0">
                        <div className="text-sm font-semibold text-white">Estado</div>
                        <div className="text-xs text-slate-400">
                            {data?.enabled ? 'Reglas de acceso activas' : 'Acceso por plan sin reglas avanzadas'}
                        </div>
                    </div>
                </div>
            </motion.div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05 }}
                className="card overflow-hidden"
            >
                <div className="p-4 border-b border-slate-800/50 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Building2 className="w-4 h-4 text-slate-400" />
                        <h2 className="font-semibold text-white">Sucursales habilitadas</h2>
                    </div>
                    <div className="text-xs text-slate-500">
                        {allowedSucursales.length} / {data?.allowed_sucursales?.length || 0}
                    </div>
                </div>
                <div className="divide-y divide-neutral-800/50">
                    {allowedSucursales.length === 0 ? (
                        <div className="p-6 text-center text-slate-500">No hay sucursales habilitadas</div>
                    ) : (
                        allowedSucursales.map((s) => (
                            <div key={s.id} className="p-4 flex items-center justify-between">
                                <div className="min-w-0">
                                    <div className="text-sm font-medium text-white truncate">{s.nombre}</div>
                                    <div className="text-xs text-slate-500">{s.codigo}</div>
                                </div>
                                <div className="text-xs text-success-400">Permitido</div>
                            </div>
                        ))
                    )}
                </div>
            </motion.div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="card overflow-hidden"
            >
                <div className="p-4 border-b border-slate-800/50 flex items-center gap-2">
                    <Lock className="w-4 h-4 text-slate-400" />
                    <h2 className="font-semibold text-white">Clases habilitadas</h2>
                </div>
                {!data?.class_allowlist_enabled ? (
                    <div className="p-6 text-sm text-slate-400">
                        Tu acceso a clases no está limitado por listas (depende de disponibilidad y recepción).
                    </div>
                ) : (
                    <div className="p-4 space-y-4">
                        <div>
                            <div className="text-xs text-slate-500 mb-2">Tipos de clase</div>
                            {data.allowed_tipo_clases.length === 0 ? (
                                <div className="text-sm text-slate-400">Sin tipos configurados</div>
                            ) : (
                                <div className="flex flex-wrap gap-2">
                                    {data.allowed_tipo_clases.map((t) => (
                                        <span key={t.id} className="badge badge-success">
                                            {t.nombre}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>

                        <div>
                            <div className="text-xs text-slate-500 mb-2">Clases específicas</div>
                            {data.allowed_clases.length === 0 ? (
                                <div className="text-sm text-slate-400">Sin clases específicas configuradas</div>
                            ) : (
                                <div className="space-y-2">
                                    {data.allowed_clases.map((c) => (
                                        <div key={c.id} className="flex items-center justify-between p-3 rounded-xl border border-slate-800/60 bg-slate-950/20">
                                            <div className="min-w-0">
                                                <div className="text-sm text-white truncate">{c.nombre}</div>
                                                {c.sucursal_id ? (
                                                    <div className="text-xs text-slate-500">Sucursal #{c.sucursal_id}</div>
                                                ) : (
                                                    <div className="text-xs text-slate-500">Cualquier sucursal</div>
                                                )}
                                            </div>
                                            <div className="text-xs text-success-400">Permitido</div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </motion.div>
        </div>
    );
}

