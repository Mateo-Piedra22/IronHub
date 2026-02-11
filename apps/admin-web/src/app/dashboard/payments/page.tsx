'use client';

import { useState, useEffect, useCallback } from 'react';
import { Loader2, Plus, X, Pencil, Trash2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api, type Payment, type Gym } from '@/lib/api';

interface AdminPlan {
    id: number;
    name: string;
    amount: number;
    currency?: string;
    period_days?: number;
}

export default function PaymentsPage() {
    const [payments, setPayments] = useState<Payment[]>([]);
    const [gyms, setGyms] = useState<Gym[]>([]);
    const [plans, setPlans] = useState<AdminPlan[]>([]);
    const [loading, setLoading] = useState(true);
    const [createOpen, setCreateOpen] = useState(false);
    const [editOpen, setEditOpen] = useState(false);
    const [editing, setEditing] = useState<Payment | null>(null);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const pageSize = 50;
    const [filters, setFilters] = useState<{ gym_id: string; status: string; q: string }>({ gym_id: '', status: '', q: '' });
    const [formData, setFormData] = useState({
        gym_id: '',
        amount: '',
        plan: '',
        plan_id: '',
        valid_until: '',
        notes: '',
        currency: 'ARS',
        status: 'paid',
    });
    const [formLoading, setFormLoading] = useState(false);

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const gymId = filters.gym_id ? Number(filters.gym_id) : undefined;
            const [paymentsRes, gymsRes, plansRes] = await Promise.all([
                api.listPayments({
                    gym_id: gymId,
                    status: filters.status || undefined,
                    q: filters.q || undefined,
                    page,
                    page_size: pageSize,
                }),
                api.getGyms({ page_size: 100 }),
                api.getAdminPlans(),
            ]);
            if (paymentsRes.ok && paymentsRes.data) {
                setPayments(paymentsRes.data.items || []);
                setTotal(Number(paymentsRes.data.total || 0));
            }
            if (gymsRes.ok && gymsRes.data) {
                setGyms(gymsRes.data.gyms || []);
            }
            if (plansRes.ok && plansRes.data?.plans) {
                setPlans(plansRes.data.plans as AdminPlan[]);
            }
        } catch {
            setPayments([]);
            setTotal(0);
        } finally {
            setLoading(false);
        }
    }, [filters.gym_id, filters.q, filters.status, page]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!formData.gym_id || !formData.amount) return;
        setFormLoading(true);
        try {
            const res = await api.registerPayment(Number(formData.gym_id), {
                amount: Number(formData.amount),
                plan: formData.plan || undefined,
                plan_id: formData.plan_id ? Number(formData.plan_id) : undefined,
                valid_until: formData.valid_until || undefined,
                notes: formData.notes || undefined,
                currency: formData.currency || 'ARS',
                status: formData.status || 'paid',
            });
            if (res.ok) {
                setCreateOpen(false);
                setFormData({ gym_id: '', amount: '', plan: '', plan_id: '', valid_until: '', notes: '', currency: 'ARS', status: 'paid' });
                loadData();
            }
        } catch {
            // Ignore
        } finally {
            setFormLoading(false);
        }
    };

    const handleUpdate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editing) return;
        setFormLoading(true);
        try {
            const res = await api.updateGymPayment(Number(formData.gym_id), editing.id, {
                plan: formData.plan || undefined,
                amount: Number(formData.amount),
                currency: formData.currency || 'ARS',
                status: formData.status || 'paid',
                valid_until: formData.valid_until || undefined,
                notes: formData.notes || undefined,
            });
            if (res.ok) {
                setEditOpen(false);
                setEditing(null);
                loadData();
            }
        } finally {
            setFormLoading(false);
        }
    };

    const openEdit = (p: Payment) => {
        setEditing(p);
        setFormData({
            gym_id: String(p.gym_id),
            amount: String(p.amount ?? ''),
            plan: String(p.plan || ''),
            plan_id: '',
            valid_until: p.valid_until ? String(p.valid_until).slice(0, 10) : '',
            notes: String(p.notes || ''),
            currency: String(p.currency || 'ARS'),
            status: String(p.status || 'paid'),
        });
        setEditOpen(true);
    };

    const handleDelete = async (p: Payment) => {
        if (!confirm(`Eliminar pago #${p.id}?`)) return;
        await api.deleteGymPayment(p.gym_id, p.id);
        loadData();
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
                <div className="p-4 border-b border-slate-800 flex flex-wrap items-center gap-3">
                    <select
                        value={filters.gym_id}
                        onChange={(e) => { setPage(1); setFilters({ ...filters, gym_id: e.target.value }); }}
                        className="input w-56"
                    >
                        <option value="">Todos los gimnasios</option>
                        {gyms.map((g) => (
                            <option key={g.id} value={g.id}>
                                {g.nombre} ({g.subdominio})
                            </option>
                        ))}
                    </select>
                    <select
                        value={filters.status}
                        onChange={(e) => { setPage(1); setFilters({ ...filters, status: e.target.value }); }}
                        className="input w-44"
                    >
                        <option value="">Todos los estados</option>
                        <option value="paid">paid</option>
                        <option value="pending">pending</option>
                        <option value="failed">failed</option>
                    </select>
                    <input
                        value={filters.q}
                        onChange={(e) => { setPage(1); setFilters({ ...filters, q: e.target.value }); }}
                        className="input w-64"
                        placeholder="Buscar (gym/subdominio/plan)"
                    />
                    <div className="ml-auto flex items-center gap-2 text-sm text-slate-400">
                        <span>Total: {total}</span>
                        <button
                            className="btn-secondary px-3 py-2"
                            disabled={page <= 1}
                            onClick={() => setPage((p) => Math.max(1, p - 1))}
                        >
                            Anterior
                        </button>
                        <button
                            className="btn-secondary px-3 py-2"
                            disabled={page * pageSize >= total}
                            onClick={() => setPage((p) => p + 1)}
                        >
                            Siguiente
                        </button>
                    </div>
                </div>
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
                                <th>Notas</th>
                                <th>Válido hasta</th>
                                <th>Fecha</th>
                                <th></th>
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
                                    <td className="text-slate-400 max-w-xs truncate">{p.notes || '—'}</td>
                                    <td className="text-slate-400">{p.valid_until || '—'}</td>
                                    <td className="text-slate-400">{p.created_at?.slice(0, 10)}</td>
                                    <td>
                                        <div className="flex items-center justify-end gap-2">
                                            <button onClick={() => openEdit(p)} className="p-2 rounded-lg bg-slate-800 text-slate-300 hover:text-white" title="Editar">
                                                <Pencil className="w-4 h-4" />
                                            </button>
                                            <button onClick={() => handleDelete(p)} className="p-2 rounded-lg bg-slate-800 text-slate-300 hover:text-white" title="Eliminar">
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </td>
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
                                        onChange={(e) => {
                                            const newGymId = e.target.value;
                                            let newPlanId = formData.plan_id;
                                            let newAmount = formData.amount;
                                            let newValidUntil = formData.valid_until;
                                            let newCurrency = formData.currency;
                                            let newPlanName = formData.plan;

                                            // Auto-select plan if gym has one assigned
                                            if (newGymId) {
                                                const g = gyms.find(x => x.id === Number(newGymId));
                                                if (g && g.subscription_plan_id) {
                                                    const pid = g.subscription_plan_id;
                                                    const p = plans.find(x => x.id === pid);
                                                    if (p) {
                                                        newPlanId = String(pid);
                                                        newPlanName = p.name;
                                                        newAmount = String(p.amount);
                                                        newCurrency = p.currency || newCurrency;
                                                        // Calculate valid until
                                                        const d = new Date();
                                                        d.setDate(d.getDate() + (p.period_days || 30));
                                                        newValidUntil = d.toISOString().slice(0, 10);
                                                    }
                                                }
                                            }

                                            setFormData({
                                                ...formData,
                                                gym_id: newGymId,
                                                plan_id: newPlanId,
                                                plan: newPlanName,
                                                amount: newAmount,
                                                valid_until: newValidUntil,
                                                currency: newCurrency
                                            });
                                        }}
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
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="label">Plan</label>
                                        <select
                                            value={formData.plan_id}
                                            onChange={(e) => {
                                                const val = e.target.value;
                                                let newAmount = formData.amount;
                                                let newValidUntil = formData.valid_until;
                                                let newCurrency = formData.currency;
                                                let newPlanName = '';

                                                if (val) {
                                                    const p = plans.find(x => x.id === Number(val));
                                                    if (p) {
                                                        newPlanName = p.name;
                                                        newAmount = String(p.amount);
                                                        newCurrency = p.currency || newCurrency;
                                                        const d = new Date();
                                                        d.setDate(d.getDate() + (p.period_days || 30));
                                                        newValidUntil = d.toISOString().slice(0, 10);
                                                    }
                                                }
                                                setFormData({ ...formData, plan_id: val, plan: newPlanName, amount: newAmount, valid_until: newValidUntil, currency: newCurrency });
                                            }}
                                            className="input"
                                        >
                                            <option value="">-- Sin plan --</option>
                                            {plans.map(p => (
                                                <option key={p.id} value={p.id}>{p.name}</option>
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
                                </div>
                                <div>
                                    <label className="label">Válido hasta</label>
                                    <input
                                        type="date"
                                        value={formData.valid_until}
                                        onChange={(e) => setFormData({ ...formData, valid_until: e.target.value })}
                                        className="input"
                                        title="Fecha de vencimiento calculada o manual"
                                    />
                                    <p className="text-[10px] text-slate-500 mt-1">* Se calcula automáticamente al elegir plan.</p>
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="label">Moneda</label>
                                        <input
                                            type="text"
                                            value={formData.currency}
                                            onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
                                            className="input"
                                        />
                                    </div>
                                    <div>
                                        <label className="label">Estado</label>
                                        <select
                                            value={formData.status}
                                            onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                                            className="input"
                                        >
                                            <option value="paid">paid</option>
                                            <option value="pending">pending</option>
                                            <option value="failed">failed</option>
                                        </select>
                                    </div>
                                </div>
                                <div>
                                    <label className="label">Notas</label>
                                    <input
                                        type="text"
                                        value={formData.notes}
                                        onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                                        className="input"
                                        placeholder="Referencia / observaciones"
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

            <AnimatePresence>
                {editOpen && editing && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60"
                        onClick={() => { setEditOpen(false); setEditing(null); }}
                    >
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            onClick={(e) => e.stopPropagation()}
                            className="card w-full max-w-md p-6"
                        >
                            <div className="flex items-center justify-between mb-4">
                                <h2 className="text-xl font-bold text-white">Editar Pago #{editing.id}</h2>
                                <button onClick={() => { setEditOpen(false); setEditing(null); }} className="text-slate-400 hover:text-white">
                                    <X className="w-5 h-5" />
                                </button>
                            </div>
                            <form onSubmit={handleUpdate} className="space-y-4">
                                <div>
                                    <label className="label">Monto</label>
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
                                    />
                                </div>
                                <div>
                                    <label className="label">Notas</label>
                                    <input
                                        type="text"
                                        value={formData.notes}
                                        onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                                        className="input"
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
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="label">Moneda</label>
                                        <input
                                            type="text"
                                            value={formData.currency}
                                            onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
                                            className="input"
                                        />
                                    </div>
                                    <div>
                                        <label className="label">Estado</label>
                                        <select
                                            value={formData.status}
                                            onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                                            className="input"
                                        >
                                            <option value="paid">paid</option>
                                            <option value="pending">pending</option>
                                            <option value="failed">failed</option>
                                        </select>
                                    </div>
                                </div>
                                <div className="flex justify-end gap-3 pt-2">
                                    <button type="button" onClick={() => { setEditOpen(false); setEditing(null); }} className="btn-secondary">
                                        Cancelar
                                    </button>
                                    <button type="submit" disabled={formLoading} className="btn-primary">
                                        {formLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Guardar'}
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
