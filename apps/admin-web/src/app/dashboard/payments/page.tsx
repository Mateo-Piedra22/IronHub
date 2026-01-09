'use client';

import { useState, useEffect } from 'react';
import { Loader2, DollarSign, Plus, X, Pencil, Trash2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api, type Payment, type Gym } from '@/lib/api';

export default function PaymentsPage() {
    const [payments, setPayments] = useState<Payment[]>([]);
    const [gyms, setGyms] = useState<Gym[]>([]);
    const [loading, setLoading] = useState(true);
    const [createOpen, setCreateOpen] = useState(false);
    const [formData, setFormData] = useState({
        gym_id: '',
        amount: '',
        plan: '',
        valid_until: '',
        notes: '',
    });
    const [formLoading, setFormLoading] = useState(false);

    const loadData = async () => {
        setLoading(true);
        try {
            const [paymentsRes, gymsRes] = await Promise.all([
                api.getRecentPayments(100),
                api.getGyms({ page_size: 100 }),
            ]);
            if (paymentsRes.ok && paymentsRes.data) {
                setPayments(paymentsRes.data.payments || []);
            }
            if (gymsRes.ok && gymsRes.data) {
                setGyms(gymsRes.data.gyms || []);
            }
        } catch {
            // Ignore
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadData();
    }, []);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!formData.gym_id || !formData.amount) return;
        setFormLoading(true);
        try {
            const res = await api.registerPayment(Number(formData.gym_id), {
                amount: Number(formData.amount),
                plan: formData.plan || undefined,
                valid_until: formData.valid_until || undefined,
            });
            if (res.ok) {
                setCreateOpen(false);
                setFormData({ gym_id: '', amount: '', plan: '', valid_until: '', notes: '' });
                loadData();
            }
        } catch {
            // Ignore
        } finally {
            setFormLoading(false);
        }
    };

    const getGymName = (gymId: number): string => {
        const gym = gyms.find(g => g.id === gymId);
        return gym?.nombre || `Gym #${gymId}`;
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                    <h1 className="page-title">Pagos de Suscripciones</h1>
                    <p className="text-slate-400 mt-1">Pagos de gimnasios al sistema IronHub</p>
                </div>
                <button onClick={() => setCreateOpen(true)} className="btn-primary flex items-center gap-2">
                    <Plus className="w-4 h-4" />
                    Registrar Pago
                </button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="card p-4">
                    <div className="text-sm text-slate-500">Total Pagos</div>
                    <div className="text-2xl font-bold text-white">{payments.length}</div>
                </div>
                <div className="card p-4">
                    <div className="text-sm text-slate-500">Recaudado (ARS)</div>
                    <div className="text-2xl font-bold text-success-400">
                        ${payments.filter(p => p.currency === 'ARS').reduce((acc, p) => acc + p.amount, 0).toLocaleString()}
                    </div>
                </div>
                <div className="card p-4">
                    <div className="text-sm text-slate-500">Pagados</div>
                    <div className="text-2xl font-bold text-primary-400">
                        {payments.filter(p => p.status === 'paid').length}
                    </div>
                </div>
                <div className="card p-4">
                    <div className="text-sm text-slate-500">Pendientes</div>
                    <div className="text-2xl font-bold text-warning-400">
                        {payments.filter(p => p.status !== 'paid').length}
                    </div>
                </div>
            </div>

            {/* Payments Table */}
            <div className="card overflow-hidden">
                {loading ? (
                    <div className="flex items-center justify-center py-16">
                        <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
                    </div>
                ) : payments.length === 0 ? (
                    <div className="p-8 text-center text-slate-500">No hay pagos registrados</div>
                ) : (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Gimnasio</th>
                                <th>Monto</th>
                                <th>Moneda</th>
                                <th>Estado</th>
                                <th>Válido hasta</th>
                                <th>Fecha</th>
                            </tr>
                        </thead>
                        <tbody>
                            {payments.map((p) => (
                                <tr key={p.id}>
                                    <td className="text-slate-500">{p.id}</td>
                                    <td className="font-medium text-white">{getGymName(p.gym_id)}</td>
                                    <td className="text-success-400 font-medium">${p.amount.toLocaleString()}</td>
                                    <td className="text-slate-400">{p.currency}</td>
                                    <td>
                                        <span className={`badge ${p.status === 'paid' ? 'badge-success' : 'badge-warning'}`}>
                                            {p.status === 'paid' ? 'Pagado' : p.status}
                                        </span>
                                    </td>
                                    <td className="text-slate-400">{p.valid_until || '—'}</td>
                                    <td className="text-slate-400">{p.created_at?.slice(0, 10)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Create Modal */}
            <AnimatePresence>
                {createOpen && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60"
                        onClick={() => setCreateOpen(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            onClick={(e) => e.stopPropagation()}
                            className="card w-full max-w-md p-6"
                        >
                            <div className="flex items-center justify-between mb-4">
                                <h2 className="text-xl font-bold text-white">Registrar Pago</h2>
                                <button onClick={() => setCreateOpen(false)} className="text-slate-400 hover:text-white">
                                    <X className="w-5 h-5" />
                                </button>
                            </div>
                            <form onSubmit={handleCreate} className="space-y-4">
                                <div>
                                    <label className="label">Gimnasio *</label>
                                    <select
                                        value={formData.gym_id}
                                        onChange={(e) => setFormData({ ...formData, gym_id: e.target.value })}
                                        className="input"
                                        required
                                    >
                                        <option value="">Seleccionar gimnasio...</option>
                                        {gyms.map((g) => (
                                            <option key={g.id} value={g.id}>
                                                {g.nombre} ({g.subdominio})
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <label className="label">Monto *</label>
                                    <input
                                        type="number"
                                        step="0.01"
                                        value={formData.amount}
                                        onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                                        className="input"
                                        required
                                    />
                                </div>
                                <div>
                                    <label className="label">Plan</label>
                                    <input
                                        type="text"
                                        value={formData.plan}
                                        onChange={(e) => setFormData({ ...formData, plan: e.target.value })}
                                        className="input"
                                        placeholder="Mensual, Anual..."
                                    />
                                </div>
                                <div>
                                    <label className="label">Válido hasta</label>
                                    <input
                                        type="date"
                                        value={formData.valid_until}
                                        onChange={(e) => setFormData({ ...formData, valid_until: e.target.value })}
                                        className="input"
                                    />
                                </div>
                                <div className="flex justify-end gap-3 pt-2">
                                    <button type="button" onClick={() => setCreateOpen(false)} className="btn-secondary">
                                        Cancelar
                                    </button>
                                    <button type="submit" disabled={formLoading} className="btn-primary">
                                        {formLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Registrar'}
                                    </button>
                                </div>
                            </form>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
