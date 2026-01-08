'use client';

import { useState, useEffect, Fragment } from 'react';
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
        } catch (err) {
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
    const [activeTab, setActiveTab] = useState<'plans' | 'expirations'>('plans');

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

    // Load Plans
    const loadPlans = async () => {
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
    };

    // Load Expirations
    const loadExpirations = async () => {
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
    };

    useEffect(() => {
        loadPlans();
    }, []);

    useEffect(() => {
        if (activeTab === 'expirations') {
            loadExpirations();
        }
    }, [activeTab, days]);

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
