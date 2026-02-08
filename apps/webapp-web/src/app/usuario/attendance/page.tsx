'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Calendar, TrendingUp, Loader2 } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { api, type Asistencia } from '@/lib/api';
import { Button, Input } from '@/components/ui';

export default function AttendancePage() {
    const { user } = useAuth();
    const [attendance, setAttendance] = useState<Asistencia[]>([]);
    const [loading, setLoading] = useState(true);
    const [desde, setDesde] = useState('');
    const [hasta, setHasta] = useState('');
    const [page, setPage] = useState(1);
    const pageSize = 50;
    const [total, setTotal] = useState(0);
    const [monthCount, setMonthCount] = useState(0);
    const [lastMonthCount, setLastMonthCount] = useState(0);

    const loadAttendance = useCallback(async () => {
        if (!user?.id) return;
        setLoading(true);
        try {
            const res = await api.getAsistencias({ usuario_id: user.id, desde: desde || undefined, hasta: hasta || undefined, page, limit: pageSize });
            if (res.ok && res.data) {
                setAttendance(res.data.asistencias || []);
                setTotal(Number(res.data.total || 0));
            }
        } finally {
            setLoading(false);
        }
    }, [user?.id, desde, hasta, page]);

    useEffect(() => {
        loadAttendance();
    }, [loadAttendance]);

    useEffect(() => {
        if (!user?.id) return;
        (async () => {
            const now = new Date();
            const firstDay = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
            const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().slice(0, 10);
            const lastMonthFirst = new Date(now.getFullYear(), now.getMonth() - 1, 1).toISOString().slice(0, 10);
            const lastMonthLast = new Date(now.getFullYear(), now.getMonth(), 0).toISOString().slice(0, 10);
            const [r1, r2] = await Promise.all([
                api.getAsistencias({ usuario_id: user.id, desde: firstDay, hasta: lastDay, limit: 1 }),
                api.getAsistencias({ usuario_id: user.id, desde: lastMonthFirst, hasta: lastMonthLast, limit: 1 }),
            ]);
            if (r1.ok && r1.data) setMonthCount(Number(r1.data.total || 0));
            if (r2.ok && r2.data) setLastMonthCount(Number(r2.data.total || 0));
        })();
    }, [user?.id]);

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
                <h1 className="text-2xl font-display font-bold text-white">Mis Asistencias</h1>
                <p className="text-slate-400 mt-1">Registro de asistencias al gimnasio</p>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="stat-card"
                >
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-primary-500/20 flex items-center justify-center">
                            <Calendar className="w-5 h-5 text-primary-400" />
                        </div>
                        <div>
                            <div className="stat-value text-xl">{monthCount}</div>
                            <div className="stat-label text-xs">Este mes</div>
                        </div>
                    </div>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="stat-card"
                >
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-success-500/20 flex items-center justify-center">
                            <TrendingUp className="w-5 h-5 text-success-400" />
                        </div>
                        <div>
                            <div className="stat-value text-xl">
                                {monthCount >= lastMonthCount ? '+' : ''}
                                {monthCount - lastMonthCount}
                            </div>
                            <div className="stat-label text-xs">vs. mes anterior</div>
                        </div>
                    </div>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="stat-card"
                >
                    <div className="flex items-center gap-3">
                        <div>
                            <div className="stat-value text-xl">
                                {total}
                            </div>
                            <div className="stat-label text-xs">Total (filtro)</div>
                        </div>
                    </div>
                </motion.div>
            </div>

            <div className="card p-4">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                    <Input label="Desde" type="date" value={desde} onChange={(e) => { setPage(1); setDesde(e.target.value); }} />
                    <Input label="Hasta" type="date" value={hasta} onChange={(e) => { setPage(1); setHasta(e.target.value); }} />
                    <div className="flex items-end gap-2">
                        <Button variant="secondary" onClick={() => loadAttendance()} isLoading={loading}>
                            Refrescar
                        </Button>
                    </div>
                    <div className="flex items-end justify-end gap-2">
                        <Button variant="ghost" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
                            Anterior
                        </Button>
                        <div className="text-xs text-slate-500">Página {page}</div>
                        <Button variant="ghost" onClick={() => setPage((p) => p + 1)} disabled={page * pageSize >= total}>
                            Siguiente
                        </Button>
                    </div>
                </div>
            </div>

            {/* Attendance List */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="card overflow-hidden"
            >
                <div className="p-4 border-b border-slate-800/50">
                    <h2 className="font-semibold text-white">Historial de Asistencias</h2>
                </div>
                <div className="divide-y divide-neutral-800/50">
                    {attendance.length === 0 ? (
                        <div className="p-8 text-center text-slate-500">
                            No hay asistencias registradas
                        </div>
                    ) : (
                        attendance.map((a, index) => (
                            <motion.div
                                key={a.id}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: 0.4 + index * 0.03 }}
                                className="p-4 flex items-center justify-between hover:bg-slate-800/30 transition-colors"
                            >
                                <div className="flex items-center gap-4">
                                    <div className="w-14 h-14 rounded-xl bg-slate-800 flex flex-col items-center justify-center p-1 border border-slate-700">
                                        <span className="text-[10px] text-slate-500 uppercase tracking-tighter leading-none mb-0.5">
                                            {new Date(a.fecha).toLocaleDateString('es-AR', { month: 'short' }).replace('.', '')}
                                        </span>
                                        <span className="text-xl font-bold text-white leading-none">
                                            {new Date(a.fecha).getDate()}
                                        </span>
                                        <span className="text-[10px] text-slate-500 uppercase leading-none mt-0.5">
                                            {new Date(a.fecha).toLocaleDateString('es-AR', { weekday: 'short' }).replace('.', '')}
                                        </span>
                                    </div>
                                    <div>
                                        <div className="text-sm font-medium text-white capitalize">
                                            {new Date(a.fecha).toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' })}
                                        </div>
                                        <div className="text-xs text-slate-500">
                                            Check-in {a.hora ? `a las ${String(a.hora).slice(0, 8)}` : ''}
                                            {a.sucursal_nombre ? ` • ${a.sucursal_nombre}` : ''}
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        ))
                    )}
                </div>
            </motion.div>
        </div>
    );
}
