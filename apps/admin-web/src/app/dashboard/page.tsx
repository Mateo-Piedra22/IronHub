'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
    Building2, Users, CreditCard,
    ArrowUpRight, ArrowDownRight, Clock, AlertCircle, Loader2
} from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api';

interface Stats {
    label: string;
    value: string;
    change: string;
    trend: 'up' | 'down';
    icon: React.ComponentType<{ className?: string }>;
}

interface Gym {
    id: number;
    nombre: string;
    subdominio: string;
    status: string;
    created_at?: string;
}

interface Expiration {
    gym: string;
    days: number;
    type: string;
}

export default function DashboardPage() {
    const [loading, setLoading] = useState(true);
    const [stats, setStats] = useState<Stats[]>([]);
    const [recentGyms, setRecentGyms] = useState<Gym[]>([]);
    const [expirations, setExpirations] = useState<Expiration[]>([]);

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            // Fetch metrics
            const metricsRes = await api.getMetrics();
            if (metricsRes.ok && metricsRes.data) {
                const m = metricsRes.data;
                setStats([
                    {
                        label: 'Gimnasios Activos',
                        value: String(m.active_gyms || 0),
                        change: `${m.total_gyms || 0} total`,
                        trend: 'up',
                        icon: Building2
                    },
                    {
                        label: 'Socios Totales',
                        value: String(m.total_members || 0),
                        change: '-',
                        trend: 'up',
                        icon: Users
                    },
                    {
                        label: 'Suspendidos',
                        value: String(m.suspended_gyms || 0),
                        change: '-',
                        trend: m.suspended_gyms ? 'down' : 'up',
                        icon: AlertCircle
                    },
                    {
                        label: 'Ingresos (30d)',
                        value: m.total_revenue ? `$${m.total_revenue.toLocaleString()}` : '-',
                        change: '-',
                        trend: 'up',
                        icon: CreditCard
                    },
                ]);
            }

            // Fetch recent gyms
            const gymsRes = await api.getGyms({ page_size: 5 });
            if (gymsRes.ok && gymsRes.data) {
                setRecentGyms(gymsRes.data.gyms || []);
            }

            // Fetch expirations
            const expRes = await api.getExpirations(30);
            if (expRes.ok && expRes.data) {
                setExpirations(
                    (Array.isArray(expRes.data.expirations) ? expRes.data.expirations : [])
                        .slice(0, 5)
                        .map((e: unknown) => {
                            const obj = (typeof e === 'object' && e !== null ? (e as Record<string, unknown>) : {}) as Record<string, unknown>;
                            const gym = String(obj.gym_name ?? obj.nombre ?? 'Gym');
                            const days = Number(obj.days_remaining ?? obj.days_until ?? 0) || 0;
                            return { gym, days, type: 'subscription' };
                        })
                );
            }
        } catch (error) {
            console.error('Error loading dashboard:', error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadData();
    }, [loadData]);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
            </div>
        );
    }

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="page-header">
                <h1 className="page-title">Dashboard</h1>
                <p className="text-slate-400 mt-1">
                    Resumen general de IronHub
                </p>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {stats.map((stat, index) => (
                    <motion.div
                        key={stat.label}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="stat-card"
                    >
                        <div className="flex items-start justify-between">
                            <div>
                                <p className="stat-label">{stat.label}</p>
                                <p className="stat-value mt-2">{stat.value}</p>
                            </div>
                            <div className="w-10 h-10 rounded-xl bg-primary-500/20 flex items-center justify-center">
                                <stat.icon className="w-5 h-5 text-primary-400" />
                            </div>
                        </div>
                        <div className="mt-4 flex items-center gap-1.5">
                            {stat.trend === 'up' ? (
                                <ArrowUpRight className="w-4 h-4 text-success-400" />
                            ) : (
                                <ArrowDownRight className="w-4 h-4 text-danger-400" />
                            )}
                            <span className={stat.trend === 'up' ? 'text-success-400' : 'text-danger-400'}>
                                {stat.change}
                            </span>
                        </div>
                    </motion.div>
                ))}
            </div>

            {/* Content Grid */}
            <div className="grid lg:grid-cols-3 gap-6">
                {/* Recent Gyms */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 }}
                    className="lg:col-span-2 card"
                >
                    <div className="p-6 border-b border-slate-800/50 flex items-center justify-between">
                        <h2 className="text-lg font-semibold text-white">Gimnasios Recientes</h2>
                        <Link href="/dashboard/gyms" className="text-sm text-primary-400 hover:text-primary-300">
                            Ver todos →
                        </Link>
                    </div>
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Nombre</th>
                                <th>Subdominio</th>
                                <th>Estado</th>
                            </tr>
                        </thead>
                        <tbody>
                            {recentGyms.length === 0 ? (
                                <tr>
                                    <td colSpan={3} className="text-center text-slate-500 py-8">
                                        No hay gimnasios registrados
                                    </td>
                                </tr>
                            ) : (
                                recentGyms.map((gym) => (
                                    <tr key={gym.id} className="cursor-pointer">
                                        <td className="font-medium text-white">{gym.nombre}</td>
                                        <td className="text-slate-400">{gym.subdominio}.ironhub.xyz</td>
                                        <td>
                                            <span className={`badge ${gym.status === 'active' ? 'badge-success' :
                                                    gym.status === 'maintenance' ? 'badge-warning' : 'badge-danger'
                                                }`}>
                                                {gym.status === 'active' ? 'Activo' :
                                                    gym.status === 'maintenance' ? 'Mantenimiento' : 'Suspendido'}
                                            </span>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </motion.div>

                {/* Upcoming Expirations */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 }}
                    className="card"
                >
                    <div className="p-6 border-b border-slate-800/50">
                        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                            <AlertCircle className="w-5 h-5 text-warning-400" />
                            Próximos Vencimientos
                        </h2>
                    </div>
                    <div className="p-4 space-y-3">
                        {expirations.length === 0 ? (
                            <p className="text-slate-500 text-center py-4">Sin vencimientos próximos</p>
                        ) : (
                            expirations.map((item, index) => (
                                <div
                                    key={index}
                                    className="flex items-center justify-between p-3 rounded-xl bg-slate-800/30 border border-slate-800/50"
                                >
                                    <div>
                                        <p className="font-medium text-white">{item.gym}</p>
                                        <p className="text-xs text-slate-500">Suscripción</p>
                                    </div>
                                    <div className="flex items-center gap-2 text-warning-400">
                                        <Clock className="w-4 h-4" />
                                        <span className="text-sm font-medium">{item.days} días</span>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </motion.div>
            </div>
        </div>
    );
}

