'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Loader2, CreditCard, Plus, Edit2, Trash2, ToggleLeft, ToggleRight,
    Calendar, AlertTriangle, Send, Bell, X, Check, DollarSign, Clock
} from 'lucide-react';
import { api, Plan } from '@/lib/api';

interface Expiration {
    gym_id: number;
    nombre: string;
    subdominio: string;
    valid_until: string;
    days_remaining: number;
}

interface SubscriptionRow {
    gym_id: number;
    nombre: string;
    subdominio: string;
    plan_id?: number | null;
    next_due_date?: string | null;
    subscription_status?: string | null;
}

// ===== Plan Form Modal =====
function PlanFormModal({
    plan,
    onClose,
    onSaved,
}: {
    plan?: Plan;
    onClose: () => void;
    onSaved: () => void;
}) {
    const [loading, setLoading] = useState(false);
    const [form, setForm] = useState({
        name: plan?.name || '',
        amount: plan?.amount?.toString() || '',
        currency: plan?.currency || 'ARS',
        period_days: plan?.period_days?.toString() || '30',
    });
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        if (!form.name.trim()) {
            setError('El nombre es requerido');
            setLoading(false);
            return;
        }
        if (!form.amount || parseFloat(form.amount) <= 0) {
            setError('El monto debe ser mayor a 0');
            setLoading(false);
            return;
        }

        try {
            const data = {
                name: form.name.trim(),
                amount: parseFloat(form.amount),
                currency: form.currency,
                period_days: parseInt(form.period_days),
            };

            if (plan?.id) {
                await api.updatePlan(plan.id, data);
            } else {
                await api.createPlan(data);
            }
            onSaved();
            onClose();
        } catch {
            setError('Error al guardar el plan');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="card max-w-md w-full p-6"
            >
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-semibold text-white">
                        {plan ? 'Editar Plan' : 'Nuevo Plan'}
                    </h2>
                    <button onClick={onClose} className="p-2 rounded-lg hover:bg-slate-800">
                        <X className="w-5 h-5 text-slate-400" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="label">Nombre del Plan</label>
                        <input
                            type="text"
                            value={form.name}
                            onChange={(e) => setForm({ ...form, name: e.target.value })}
                            placeholder="Ej: Plan Mensual Premium"
                            className="input"
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="label">Monto</label>
                            <div className="relative">
                                <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                <input
                                    type="number"
                                    step="0.01"
                                    min="0"
                                    value={form.amount}
                                    onChange={(e) => setForm({ ...form, amount: e.target.value })}
                                    placeholder="0.00"
                                    className="input pl-10"
                                />
                            </div>
                        </div>
                        <div>
                            <label className="label">Moneda</label>
                            <select
                                value={form.currency}
                                onChange={(e) => setForm({ ...form, currency: e.target.value })}
                                className="input"
                            >
                                <option value="ARS">ARS (Peso)</option>
                                <option value="USD">USD (Dólar)</option>
                                <option value="EUR">EUR (Euro)</option>
                            </select>
                        </div>
                    </div>

                    <div>
                        <label className="label">Duración (días)</label>
                        <div className="relative">
                            <Clock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input
                                type="number"
                                min="1"
                                value={form.period_days}
                                onChange={(e) => setForm({ ...form, period_days: e.target.value })}
                                placeholder="30"
                                className="input pl-10"
                            />
                        </div>
                        <p className="text-xs text-slate-500 mt-1">
                            Períodos comunes: 30 (mensual), 90 (trimestral), 365 (anual)
                        </p>
                    </div>

                    {error && (
                        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                            {error}
                        </div>
                    )}

                    <div className="flex justify-end gap-3 pt-2">
                        <button type="button" onClick={onClose} className="btn-secondary">
                            Cancelar
                        </button>
                        <button type="submit" disabled={loading} className="btn-primary flex items-center gap-2">
                            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                            {plan ? 'Guardar' : 'Crear Plan'}
                        </button>
                    </div>
                </form>
            </motion.div>
        </div>
    );
}

// ===== Main Page =====
export default function SubscriptionsPage() {
    const [activeTab, setActiveTab] = useState<'plans' | 'expirations' | 'gyms'>('plans');

    // Plans state
    const [plans, setPlans] = useState<Plan[]>([]);
    const [plansLoading, setPlansLoading] = useState(true);
    const [showPlanModal, setShowPlanModal] = useState(false);
    const [editingPlan, setEditingPlan] = useState<Plan | undefined>();

    // Expirations state
    const [expirations, setExpirations] = useState<Expiration[]>([]);
    const [expirationsLoading, setExpirationsLoading] = useState(true);
    const [days, setDays] = useState(30);
    const [sending, setSending] = useState(false);

    // Subscriptions by gym state
    const [subsLoading, setSubsLoading] = useState(false);
    const [subsItems, setSubsItems] = useState<SubscriptionRow[]>([]);
    const [subsTotal, setSubsTotal] = useState(0);
    const [subsPage, setSubsPage] = useState(1);
    const subsPageSize = 50;
    const [subsQ, setSubsQ] = useState('');
    const [subsStatus, setSubsStatus] = useState('');
    const [subsDueBeforeDays, setSubsDueBeforeDays] = useState(30);
    const [planDraft, setPlanDraft] = useState<Record<number, string>>({});
    const [rowSaving, setRowSaving] = useState<Record<number, boolean>>({});

    // Load Plans
    const loadPlans = useCallback(async () => {
        setPlansLoading(true);
        try {
            const res = await api.getPlans();
            if (res.ok && res.data) {
                setPlans(res.data.plans || res.data || []);
            }
        } catch {
            setPlans([]);
        } finally {
            setPlansLoading(false);
        }
    }, []);

    // Load Expirations
    const loadExpirations = useCallback(async () => {
        setExpirationsLoading(true);
        try {
            const res = await api.getExpirations(days);
            if (res.ok && res.data) {
                setExpirations(res.data.expirations || []);
            }
        } catch {
            setExpirations([]);
        } finally {
            setExpirationsLoading(false);
        }
    }, [days]);

    const loadSubs = useCallback(async () => {
        setSubsLoading(true);
        try {
            const res = await api.listSubscriptions({
                q: subsQ || undefined,
                status: subsStatus || undefined,
                due_before_days: subsDueBeforeDays || undefined,
                page: subsPage,
                page_size: subsPageSize,
            });
            if (!res.ok || !res.data) return;
            const data = res.data;
            setSubsItems(Array.isArray(data.items) ? data.items : []);
            setSubsTotal(Number(data.total || 0));
        } finally {
            setSubsLoading(false);
        }
    }, [subsDueBeforeDays, subsPage, subsQ, subsStatus]);

    useEffect(() => {
        loadPlans();
    }, [loadPlans]);

    useEffect(() => {
        if (activeTab === 'expirations') loadExpirations();
        if (activeTab === 'gyms') loadSubs();
    }, [activeTab, loadExpirations, loadSubs]);

    const handleTogglePlan = async (plan: Plan) => {
        try {
            await api.togglePlan(plan.id, !plan.active);
            loadPlans();
        } catch {
            // Ignore
        }
    };

    const handleDeletePlan = async (plan: Plan) => {
        if (!confirm(`¿Eliminar el plan "${plan.name}"?`)) return;
        try {
            await api.deletePlan(plan.id);
            loadPlans();
        } catch {
            // Ignore
        }
    };

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

    const openEditPlan = (plan: Plan) => {
        setEditingPlan(plan);
        setShowPlanModal(true);
    };

    const openNewPlan = () => {
        setEditingPlan(undefined);
        setShowPlanModal(true);
    };

    const assignPlan = async (gymId: number) => {
        const planId = planDraft[gymId];
        if (!planId) return;
        setRowSaving((s) => ({ ...s, [gymId]: true }));
        try {
            await api.upsertGymSubscription(gymId, { plan_id: Number(planId), status: 'active' });
            loadSubs();
        } finally {
            setRowSaving((s) => ({ ...s, [gymId]: false }));
        }
    };

    const renew = async (gymId: number, periods = 1) => {
        setRowSaving((s) => ({ ...s, [gymId]: true }));
        try {
            await api.renewGymSubscription(gymId, periods);
            loadSubs();
        } finally {
            setRowSaving((s) => ({ ...s, [gymId]: false }));
        }
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                    <h1 className="page-title">Suscripciones</h1>
                    <p className="text-slate-400 mt-1">Gestión de planes y vencimientos</p>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex items-center gap-1 p-1 bg-slate-800/50 rounded-xl w-fit">
                <button
                    onClick={() => setActiveTab('plans')}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === 'plans'
                            ? 'bg-primary-600 text-white'
                            : 'text-slate-400 hover:text-white'
                        }`}
                >
                    <CreditCard className="w-4 h-4 inline-block mr-2" />
                    Planes
                </button>
                <button
                    onClick={() => setActiveTab('expirations')}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === 'expirations'
                            ? 'bg-primary-600 text-white'
                            : 'text-slate-400 hover:text-white'
                        }`}
                >
                    <Calendar className="w-4 h-4 inline-block mr-2" />
                    Vencimientos
                </button>
                <button
                    onClick={() => setActiveTab('gyms')}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === 'gyms'
                            ? 'bg-primary-600 text-white'
                            : 'text-slate-400 hover:text-white'
                        }`}
                >
                    <Bell className="w-4 h-4 inline-block mr-2" />
                    Gimnasios
                </button>
            </div>

            {/* Plans Tab */}
            {activeTab === 'plans' && (
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="space-y-4"
                >
                    <div className="flex justify-end">
                        <button onClick={openNewPlan} className="btn-primary flex items-center gap-2">
                            <Plus className="w-4 h-4" />
                            Nuevo Plan
                        </button>
                    </div>

                    <div className="card overflow-hidden">
                        {plansLoading ? (
                            <div className="flex items-center justify-center py-16">
                                <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
                            </div>
                        ) : plans.length === 0 ? (
                            <div className="p-12 text-center">
                                <CreditCard className="w-12 h-12 mx-auto text-slate-600 mb-4" />
                                <p className="text-slate-400">No hay planes configurados</p>
                                <button onClick={openNewPlan} className="btn-primary mt-4">
                                    Crear primer plan
                                </button>
                            </div>
                        ) : (
                            <table className="data-table">
                                <thead>
                                    <tr>
                                        <th>Plan</th>
                                        <th>Monto</th>
                                        <th>Duración</th>
                                        <th>Estado</th>
                                        <th>Acciones</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {plans.map((plan) => (
                                        <tr key={plan.id}>
                                            <td className="font-medium text-white">{plan.name}</td>
                                            <td className="text-slate-300">
                                                {plan.currency} {plan.amount?.toLocaleString()}
                                            </td>
                                            <td className="text-slate-400">
                                                {plan.period_days} días
                                            </td>
                                            <td>
                                                <span
                                                    className={`badge ${plan.active ? 'badge-success' : 'badge-secondary'
                                                        }`}
                                                >
                                                    {plan.active ? 'Activo' : 'Inactivo'}
                                                </span>
                                            </td>
                                            <td>
                                                <div className="flex items-center gap-2">
                                                    <button
                                                        onClick={() => handleTogglePlan(plan)}
                                                        className="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-white"
                                                        title={plan.active ? 'Desactivar' : 'Activar'}
                                                    >
                                                        {plan.active ? (
                                                            <ToggleRight className="w-4 h-4 text-success-400" />
                                                        ) : (
                                                            <ToggleLeft className="w-4 h-4" />
                                                        )}
                                                    </button>
                                                    <button
                                                        onClick={() => openEditPlan(plan)}
                                                        className="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-white"
                                                        title="Editar"
                                                    >
                                                        <Edit2 className="w-4 h-4" />
                                                    </button>
                                                    <button
                                                        onClick={() => handleDeletePlan(plan)}
                                                        className="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-red-400"
                                                        title="Eliminar"
                                                    >
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
                </motion.div>
            )}

            {/* Expirations Tab */}
            {activeTab === 'expirations' && (
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="space-y-4"
                >
                    <div className="flex items-center justify-end gap-3">
                        <label className="text-sm text-slate-400">Próximos días:</label>
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

                    <div className="card overflow-hidden">
                        {expirationsLoading ? (
                            <div className="flex items-center justify-center py-16">
                                <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
                            </div>
                        ) : expirations.length === 0 ? (
                            <div className="p-12 text-center">
                                <Calendar className="w-12 h-12 mx-auto text-slate-600 mb-4" />
                                <p className="text-slate-400">
                                    No hay vencimientos en los próximos {days} días
                                </p>
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
                                            <td className="text-slate-400">{exp.subdominio}</td>
                                            <td className="text-slate-400">{exp.valid_until}</td>
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
                                                    className="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-white"
                                                    title="Enviar recordatorio"
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
                </motion.div>
            )}

            {activeTab === 'gyms' && (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                    <div className="card p-4 flex flex-wrap items-center gap-3">
                        <input
                            value={subsQ}
                            onChange={(e) => { setSubsPage(1); setSubsQ(e.target.value); }}
                            className="input w-72"
                            placeholder="Buscar gimnasio/subdominio"
                        />
                        <select
                            value={subsStatus}
                            onChange={(e) => { setSubsPage(1); setSubsStatus(e.target.value); }}
                            className="input w-44"
                        >
                            <option value="">Todos</option>
                            <option value="active">active</option>
                            <option value="overdue">overdue</option>
                            <option value="canceled">canceled</option>
                        </select>
                        <div className="flex items-center gap-2 text-sm text-slate-400">
                            <Clock className="w-4 h-4" />
                            <span>Vence en</span>
                            <select
                                value={subsDueBeforeDays}
                                onChange={(e) => { setSubsPage(1); setSubsDueBeforeDays(Number(e.target.value)); }}
                                className="input w-24"
                            >
                                <option value={7}>7</option>
                                <option value={15}>15</option>
                                <option value={30}>30</option>
                                <option value={60}>60</option>
                                <option value={90}>90</option>
                            </select>
                            <span>días</span>
                        </div>
                        <div className="ml-auto flex items-center gap-2 text-sm text-slate-400">
                            <span>Total: {subsTotal}</span>
                            <button className="btn-secondary px-3 py-2" disabled={subsPage <= 1} onClick={() => setSubsPage((p) => Math.max(1, p - 1))}>
                                Anterior
                            </button>
                            <button className="btn-secondary px-3 py-2" disabled={subsPage * subsPageSize >= subsTotal} onClick={() => setSubsPage((p) => p + 1)}>
                                Siguiente
                            </button>
                        </div>
                    </div>

                    <div className="card overflow-hidden">
                        {subsLoading ? (
                            <div className="flex items-center justify-center py-16">
                                <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
                            </div>
                        ) : subsItems.length === 0 ? (
                            <div className="p-12 text-center">
                                <AlertTriangle className="w-12 h-12 mx-auto text-slate-600 mb-4" />
                                <p className="text-slate-400">No hay suscripciones para mostrar</p>
                            </div>
                        ) : (
                            <table className="data-table">
                                <thead>
                                    <tr>
                                        <th>Gimnasio</th>
                                        <th>Subdominio</th>
                                        <th>Plan</th>
                                        <th>Vence</th>
                                        <th>Estado</th>
                                        <th>Acciones</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {subsItems.map((row) => {
                                        const gid = Number(row.gym_id);
                                        const currentPlanId = row.plan_id ? String(row.plan_id) : '';
                                        const selectedPlanId = planDraft[gid] ?? currentPlanId;
                                        return (
                                            <tr key={gid}>
                                                <td className="font-medium text-white">{row.nombre}</td>
                                                <td className="text-slate-400">{row.subdominio}</td>
                                                <td>
                                                    <select
                                                        value={selectedPlanId}
                                                        onChange={(e) => setPlanDraft((s) => ({ ...s, [gid]: e.target.value }))}
                                                        className="input w-56"
                                                    >
                                                        <option value="">(Sin plan)</option>
                                                        {plans.filter((p) => p.active).map((p) => (
                                                            <option key={p.id} value={p.id}>
                                                                {p.name} ({p.currency} {p.amount?.toLocaleString()})
                                                            </option>
                                                        ))}
                                                    </select>
                                                </td>
                                                <td className="text-slate-400">{row.next_due_date ? String(row.next_due_date).slice(0, 10) : '—'}</td>
                                                <td>
                                                    <span className={`badge ${row.subscription_status === 'overdue' ? 'badge-danger' : row.subscription_status === 'active' ? 'badge-success' : 'badge-secondary'}`}>
                                                        {row.subscription_status || '—'}
                                                    </span>
                                                </td>
                                                <td>
                                                    <div className="flex items-center gap-2">
                                                        <button
                                                            onClick={() => assignPlan(gid)}
                                                            disabled={!selectedPlanId || Boolean(rowSaving[gid])}
                                                            className="btn-secondary px-3 py-2"
                                                        >
                                                            {rowSaving[gid] ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Asignar'}
                                                        </button>
                                                        <button
                                                            onClick={() => renew(gid, 1)}
                                                            disabled={Boolean(rowSaving[gid])}
                                                            className="btn-primary px-3 py-2"
                                                        >
                                                            Renovar +1
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        )}
                    </div>
                </motion.div>
            )}

            {/* Plan Modal */}
            <AnimatePresence>
                {showPlanModal && (
                    <PlanFormModal
                        plan={editingPlan}
                        onClose={() => setShowPlanModal(false)}
                        onSaved={loadPlans}
                    />
                )}
            </AnimatePresence>
        </div>
    );
}
