'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Calendar, Clock, TrendingUp, CheckCircle, Loader2 } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { api, type Asistencia } from '@/lib/api';

export default function AttendancePage() {
    const { user } = useAuth();
    const [attendance, setAttendance] = useState<Asistencia[]>([]);
    const [loading, setLoading] = useState(true);

    const loadAttendance = useCallback(async () => {
        if (!user?.id) return;
        setLoading(true);
        try {
            const res = await api.getAsistencias({ usuario_id: user.id, limit: 50 });
            if (res.ok && res.data) {
                setAttendance(res.data.asistencias || []);
            }
        } catch (error) {
            console.error('Error loading attendance:', error);
        } finally {
            setLoading(false);
        }
    }, [user?.id]);

    useEffect(() => {
        loadAttendance();
    }, [loadAttendance]);

    // Calculate stats
    const now = new Date();
    const thisMonthAttendance = attendance.filter(a => {
        const date = new Date(a.fecha);
        return date.getMonth() === now.getMonth() && date.getFullYear() === now.getFullYear();
    });

    const lastMonth = new Date(now);
    lastMonth.setMonth(lastMonth.getMonth() - 1);
    const lastMonthAttendance = attendance.filter(a => {
        const date = new Date(a.fecha);
        return date.getMonth() === lastMonth.getMonth() && date.getFullYear() === lastMonth.getFullYear();
    });

    const avgDuration = attendance.length > 0
        ? Math.round(attendance.reduce((sum, a) => sum + (a.duracion_minutos || 60), 0) / attendance.length)
        : 0;

    const stats = {
        thisMonth: thisMonthAttendance.length,
        lastMonth: lastMonthAttendance.length,
        avgDuration,
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-iron-400" />
            </div>
        );
    }

    return (
        <div className="space-y-6 py-6">
            <div>
                <h1 className="text-2xl font-display font-bold text-white">Mis Asistencias</h1>
                <p className="text-neutral-400 mt-1">Registro de asistencias al gimnasio</p>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="stat-card"
                >
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-iron-500/20 flex items-center justify-center">
                            <Calendar className="w-5 h-5 text-iron-400" />
                        </div>
                        <div>
                            <div className="stat-value text-xl">{stats.thisMonth}</div>
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
                                {stats.thisMonth >= stats.lastMonth ? '+' : ''}
                                {stats.thisMonth - stats.lastMonth}
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
                        <div className="w-10 h-10 rounded-xl bg-gold-500/20 flex items-center justify-center">
                            <Clock className="w-5 h-5 text-gold-400" />
                        </div>
                        <div>
                            <div className="stat-value text-xl">
                                {stats.avgDuration > 0 ? `${Math.floor(stats.avgDuration / 60)}h ${stats.avgDuration % 60}m` : '-'}
                            </div>
                            <div className="stat-label text-xs">Promedio</div>
                        </div>
                    </div>
                </motion.div>
            </div>

            {/* Attendance List */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="glass-card overflow-hidden"
            >
                <div className="p-4 border-b border-neutral-800/50">
                    <h2 className="font-semibold text-white">Historial de Asistencias</h2>
                </div>
                <div className="divide-y divide-neutral-800/50">
                    {attendance.length === 0 ? (
                        <div className="p-8 text-center text-neutral-500">
                            No hay asistencias registradas
                        </div>
                    ) : (
                        attendance.map((a, index) => (
                            <motion.div
                                key={a.id}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: 0.4 + index * 0.03 }}
                                className="p-4 flex items-center justify-between hover:bg-neutral-800/30 transition-colors"
                            >
                                <div className="flex items-center gap-4">
                                    <div className="w-12 h-12 rounded-xl bg-neutral-800 flex flex-col items-center justify-center">
                                        <span className="text-xs text-neutral-500">
                                            {new Date(a.fecha).toLocaleDateString('es-AR', { weekday: 'short' }).toUpperCase()}
                                        </span>
                                        <span className="text-lg font-bold text-white">
                                            {new Date(a.fecha).getDate()}
                                        </span>
                                    </div>
                                    <div>
                                        <div className="text-sm font-medium text-white">
                                            {new Date(a.fecha).toLocaleDateString('es-AR', { month: 'long', year: 'numeric' })}
                                        </div>
                                        <div className="text-xs text-neutral-500">
                                            Entrada: {a.hora_entrada || '-'}
                                            {a.hora_salida && ` • Salida: ${a.hora_salida}`}
                                        </div>
                                    </div>
                                </div>
                                <div className="text-right">
                                    {a.duracion_minutos && (
                                        <span className="badge badge-success">
                                            {Math.floor(a.duracion_minutos / 60)}h {a.duracion_minutos % 60}m
                                        </span>
                                    )}
                                </div>
                            </motion.div>
                        ))
                    )}
                </div>
            </motion.div>
        </div>
    );
}
