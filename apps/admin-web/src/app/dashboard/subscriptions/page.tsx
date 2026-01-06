'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Loader2, Calendar, AlertTriangle, Send, Bell } from 'lucide-react';
import { api } from '@/lib/api';

interface Expiration {
    gym_id: number;
    nombre: string;
    subdominio: string;
    valid_until: string;
    days_remaining: number;
}

export default function SubscriptionsPage() {
    const [expirations, setExpirations] = useState<Expiration[]>([]);
    const [loading, setLoading] = useState(true);
    const [days, setDays] = useState(30);
    const [sending, setSending] = useState(false);

    const loadExpirations = async () => {
        setLoading(true);
        try {
            const res = await api.getExpirations(days);
            if (res.ok && res.data) {
                setExpirations(res.data.expirations || []);
            }
        } catch {
            // Ignore
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadExpirations();
    }, [days]);

    const handleRemindAll = async () => {
        setSending(true);
        try {
            const ids = expirations.map((e) => e.gym_id);
            await api.sendReminder(ids, 'Su suscripción está próxima a vencer');
        } catch {
            // Ignore
        } finally {
            setSending(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                    <h1 className="page-title">Suscripciones</h1>
                    <p className="text-neutral-400 mt-1">Dashboard de vencimientos próximos</p>
                </div>
                <div className="flex items-center gap-3">
                    <label className="text-sm text-neutral-400">Próximos días:</label>
                    <select
                        value={days}
                        onChange={(e) => setDays(Number(e.target.value))}
                        className="input w-24"
                    >
                        <option value={7}>7</option>
                        <option value={15}>15</option>
                        <option value={30}>30</option>
                        <option value={60}>60</option>
                        <option value={90}>90</option>
                    </select>
                    <button
                        onClick={handleRemindAll}
                        disabled={sending || expirations.length === 0}
                        className="btn-primary flex items-center gap-2"
                    >
                        {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Bell className="w-4 h-4" />}
                        Recordar a todos
                    </button>
                </div>
            </div>

            <div className="glass-card overflow-hidden">
                {loading ? (
                    <div className="flex items-center justify-center py-16">
                        <Loader2 className="w-8 h-8 animate-spin text-iron-400" />
                    </div>
                ) : expirations.length === 0 ? (
                    <div className="p-8 text-center text-neutral-500">
                        No hay vencimientos en los próximos {days} días
                    </div>
                ) : (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Gimnasio</th>
                                <th>Subdominio</th>
                                <th>Vence</th>
                                <th>Días restantes</th>
                                <th>Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            {expirations.map((exp) => (
                                <tr key={exp.gym_id}>
                                    <td className="font-medium text-white">{exp.nombre}</td>
                                    <td className="text-neutral-400">{exp.subdominio}</td>
                                    <td className="text-neutral-400">{exp.valid_until}</td>
                                    <td>
                                        <span
                                            className={`badge ${exp.days_remaining <= 7
                                                    ? 'badge-danger'
                                                    : exp.days_remaining <= 15
                                                        ? 'badge-warning'
                                                        : 'badge-success'
                                                }`}
                                        >
                                            {exp.days_remaining} días
                                        </span>
                                    </td>
                                    <td>
                                        <button
                                            onClick={async () => {
                                                await api.sendReminder(
                                                    [exp.gym_id],
                                                    `Recordatorio: su suscripción vence el ${exp.valid_until}`
                                                );
                                            }}
                                            className="p-2 rounded-lg bg-neutral-800 text-neutral-400 hover:text-white"
                                        >
                                            <Send className="w-4 h-4" />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}
