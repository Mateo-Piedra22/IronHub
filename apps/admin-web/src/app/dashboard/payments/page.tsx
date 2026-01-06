'use client';

import { useState, useEffect } from 'react';
import { Loader2, DollarSign, Plus, X, CreditCard, Calendar, BarChart3, Pencil, Trash2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api, type Payment, type MetodoPago, type TipoCuota, type EstadisticasPagos } from '@/lib/api';

type TabType = 'historial' | 'metodos' | 'planes' | 'estadisticas';

export default function PaymentsPage() {
    const [activeTab, setActiveTab] = useState<TabType>('historial');

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                    <h1 className="page-title">Pagos</h1>
                    <p className="text-neutral-400 mt-1">Gestión completa de pagos, métodos y planes</p>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-2 border-b border-neutral-800 pb-2">
                {[
                    { id: 'historial', label: 'Historial', icon: DollarSign },
                    { id: 'metodos', label: 'Métodos de Pago', icon: CreditCard },
                    { id: 'planes', label: 'Planes/Cuotas', icon: Calendar },
                    { id: 'estadisticas', label: 'Estadísticas', icon: BarChart3 },
                ].map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id as TabType)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-all ${activeTab === tab.id
                            ? 'bg-iron-500/20 text-iron-400 border-b-2 border-iron-500'
                            : 'text-neutral-400 hover:text-white hover:bg-neutral-800/50'
                            }`}
                    >
                        <tab.icon className="w-4 h-4" />
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Tab Content */}
            <AnimatePresence mode="wait">
                {activeTab === 'historial' && <HistorialTab key="historial" />}
                {activeTab === 'metodos' && <MetodosTab key="metodos" />}
                {activeTab === 'planes' && <PlanesTab key="planes" />}
                {activeTab === 'estadisticas' && <EstadisticasTab key="estadisticas" />}
            </AnimatePresence>
        </div>
    );
}

// ========== HISTORIAL TAB ==========
function HistorialTab() {
    const [payments, setPayments] = useState<Payment[]>([]);
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

    const loadPayments = async () => {
        setLoading(true);
        try {
            const res = await api.getRecentPayments(50);
            if (res.ok && res.data) {
                setPayments(res.data.payments || []);
            }
        } catch {
            // Ignore
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadPayments();
    }, []);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!formData.gym_id || !formData.amount) return;
        setFormLoading(true);
        try {
            await api.registerPayment(Number(formData.gym_id), {
                amount: Number(formData.amount),
                plan: formData.plan || undefined,
                valid_until: formData.valid_until || undefined,
            });
            setCreateOpen(false);
            setFormData({ gym_id: '', amount: '', plan: '', valid_until: '', notes: '' });
            loadPayments();
        } catch {
            // Ignore
        } finally {
            setFormLoading(false);
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
        >
            <div className="flex justify-end mb-4">
                <button onClick={() => setCreateOpen(true)} className="btn-primary flex items-center gap-2">
                    <Plus className="w-4 h-4" />
                    Registrar Pago
                </button>
            </div>

            <div className="glass-card overflow-hidden">
                {loading ? (
                    <div className="flex items-center justify-center py-16">
                        <Loader2 className="w-8 h-8 animate-spin text-iron-400" />
                    </div>
                ) : payments.length === 0 ? (
                    <div className="p-8 text-center text-neutral-500">No hay pagos registrados</div>
                ) : (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Gimnasio ID</th>
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
                                    <td className="text-neutral-500">{p.id}</td>
                                    <td className="font-medium text-white">{p.gym_id}</td>
                                    <td className="text-success-400 font-medium">${p.amount}</td>
                                    <td className="text-neutral-400">{p.currency}</td>
                                    <td>
                                        <span className={`badge ${p.status === 'paid' ? 'badge-success' : 'badge-warning'}`}>
                                            {p.status}
                                        </span>
                                    </td>
                                    <td className="text-neutral-400">{p.valid_until || '—'}</td>
                                    <td className="text-neutral-400">{p.created_at?.slice(0, 10)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Create Modal */}
            <AnimatePresence>
                {createOpen && (
                    <Modal title="Registrar Pago" onClose={() => setCreateOpen(false)}>
                        <form onSubmit={handleCreate} className="space-y-4">
                            <div>
                                <label className="label">Gimnasio ID *</label>
                                <input
                                    type="number"
                                    value={formData.gym_id}
                                    onChange={(e) => setFormData({ ...formData, gym_id: e.target.value })}
                                    className="input"
                                    required
                                />
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
                    </Modal>
                )}
            </AnimatePresence>
        </motion.div>
    );
}

// ========== MÉTODOS DE PAGO TAB ==========
function MetodosTab() {
    const [metodos, setMetodos] = useState<MetodoPago[]>([]);
    const [loading, setLoading] = useState(true);
    const [createOpen, setCreateOpen] = useState(false);
    const [editItem, setEditItem] = useState<MetodoPago | null>(null);
    const [formLoading, setFormLoading] = useState(false);

    const loadMetodos = async () => {
        setLoading(true);
        try {
            const res = await api.getMetodosPago(false);
            if (res.ok && res.data) {
                setMetodos(Array.isArray(res.data) ? res.data : []);
            }
        } catch {
            // Ignore
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadMetodos();
    }, []);

    const handleCreate = async (data: Partial<MetodoPago>) => {
        setFormLoading(true);
        try {
            const res = await api.createMetodoPago(data);
            if (res.ok) {
                setCreateOpen(false);
                loadMetodos();
            }
        } finally {
            setFormLoading(false);
        }
    };

    const handleUpdate = async (id: number, data: Partial<MetodoPago>) => {
        setFormLoading(true);
        try {
            const res = await api.updateMetodoPago(id, data);
            if (res.ok) {
                setEditItem(null);
                loadMetodos();
            }
        } finally {
            setFormLoading(false);
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm('¿Eliminar este método de pago?')) return;
        try {
            const res = await api.deleteMetodoPago(id);
            if (res.ok) loadMetodos();
        } catch {
            // Ignore
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
        >
            <div className="flex justify-end mb-4">
                <button onClick={() => setCreateOpen(true)} className="btn-primary flex items-center gap-2">
                    <Plus className="w-4 h-4" />
                    Nuevo Método
                </button>
            </div>

            <div className="glass-card overflow-hidden">
                {loading ? (
                    <div className="flex items-center justify-center py-16">
                        <Loader2 className="w-8 h-8 animate-spin text-iron-400" />
                    </div>
                ) : metodos.length === 0 ? (
                    <div className="p-8 text-center text-neutral-500">No hay métodos de pago configurados</div>
                ) : (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Icono</th>
                                <th>Nombre</th>
                                <th>Color</th>
                                <th>Comisión %</th>
                                <th>Estado</th>
                                <th>Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            {metodos.map((m) => (
                                <tr key={m.id}>
                                    <td className="text-2xl">{m.icono || '💳'}</td>
                                    <td className="font-medium text-white">{m.nombre}</td>
                                    <td>
                                        <div className="flex items-center gap-2">
                                            <div
                                                className="w-4 h-4 rounded-full"
                                                style={{ backgroundColor: m.color || '#3498db' }}
                                            />
                                            <span className="text-neutral-400 text-sm">{m.color}</span>
                                        </div>
                                    </td>
                                    <td className="text-neutral-400">{m.comision || 0}%</td>
                                    <td>
                                        <span className={`badge ${m.activo ? 'badge-success' : 'badge-neutral'}`}>
                                            {m.activo ? 'Activo' : 'Inactivo'}
                                        </span>
                                    </td>
                                    <td>
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => setEditItem(m)}
                                                className="p-1.5 rounded hover:bg-neutral-700 text-neutral-400 hover:text-white"
                                            >
                                                <Pencil className="w-4 h-4" />
                                            </button>
                                            <button
                                                onClick={() => handleDelete(m.id)}
                                                className="p-1.5 rounded hover:bg-red-500/20 text-neutral-400 hover:text-red-400"
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

            {/* Create Modal */}
            <AnimatePresence>
                {createOpen && (
                    <MetodoForm
                        title="Nuevo Método de Pago"
                        onClose={() => setCreateOpen(false)}
                        onSubmit={handleCreate}
                        loading={formLoading}
                    />
                )}
                {editItem && (
                    <MetodoForm
                        title="Editar Método de Pago"
                        onClose={() => setEditItem(null)}
                        onSubmit={(data) => handleUpdate(editItem.id, data)}
                        loading={formLoading}
                        initialData={editItem}
                    />
                )}
            </AnimatePresence>
        </motion.div>
    );
}

// ========== PLANES TAB ==========
function PlanesTab() {
    const [planes, setPlanes] = useState<TipoCuota[]>([]);
    const [loading, setLoading] = useState(true);
    const [createOpen, setCreateOpen] = useState(false);
    const [editItem, setEditItem] = useState<TipoCuota | null>(null);
    const [formLoading, setFormLoading] = useState(false);

    const loadPlanes = async () => {
        setLoading(true);
        try {
            const res = await api.getTiposCuota(false);
            if (res.ok && res.data) {
                setPlanes(Array.isArray(res.data) ? res.data : []);
            }
        } catch {
            // Ignore
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadPlanes();
    }, []);

    const handleCreate = async (data: Partial<TipoCuota>) => {
        setFormLoading(true);
        try {
            const res = await api.createTipoCuota(data);
            if (res.ok) {
                setCreateOpen(false);
                loadPlanes();
            }
        } finally {
            setFormLoading(false);
        }
    };

    const handleUpdate = async (id: number, data: Partial<TipoCuota>) => {
        setFormLoading(true);
        try {
            const res = await api.updateTipoCuota(id, data);
            if (res.ok) {
                setEditItem(null);
                loadPlanes();
            }
        } finally {
            setFormLoading(false);
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm('¿Eliminar este plan/tipo de cuota?')) return;
        try {
            const res = await api.deleteTipoCuota(id);
            if (res.ok) loadPlanes();
        } catch {
            // Ignore
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
        >
            <div className="flex justify-end mb-4">
                <button onClick={() => setCreateOpen(true)} className="btn-primary flex items-center gap-2">
                    <Plus className="w-4 h-4" />
                    Nuevo Plan
                </button>
            </div>

            <div className="glass-card overflow-hidden">
                {loading ? (
                    <div className="flex items-center justify-center py-16">
                        <Loader2 className="w-8 h-8 animate-spin text-iron-400" />
                    </div>
                ) : planes.length === 0 ? (
                    <div className="p-8 text-center text-neutral-500">No hay planes configurados</div>
                ) : (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Nombre</th>
                                <th>Precio</th>
                                <th>Duración</th>
                                <th>Estado</th>
                                <th>Descripción</th>
                                <th>Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            {planes.map((p) => (
                                <tr key={p.id}>
                                    <td className="font-medium text-white">{p.nombre}</td>
                                    <td className="text-success-400 font-medium">${p.precio}</td>
                                    <td className="text-neutral-400">{p.duracion_dias} días</td>
                                    <td>
                                        <span className={`badge ${p.activo ? 'badge-success' : 'badge-neutral'}`}>
                                            {p.activo ? 'Activo' : 'Inactivo'}
                                        </span>
                                    </td>
                                    <td className="text-neutral-400 max-w-xs truncate">{p.descripcion || '—'}</td>
                                    <td>
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => setEditItem(p)}
                                                className="p-1.5 rounded hover:bg-neutral-700 text-neutral-400 hover:text-white"
                                            >
                                                <Pencil className="w-4 h-4" />
                                            </button>
                                            <button
                                                onClick={() => handleDelete(p.id)}
                                                className="p-1.5 rounded hover:bg-red-500/20 text-neutral-400 hover:text-red-400"
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

            {/* Create Modal */}
            <AnimatePresence>
                {createOpen && (
                    <PlanForm
                        title="Nuevo Plan"
                        onClose={() => setCreateOpen(false)}
                        onSubmit={handleCreate}
                        loading={formLoading}
                    />
                )}
                {editItem && (
                    <PlanForm
                        title="Editar Plan"
                        onClose={() => setEditItem(null)}
                        onSubmit={(data) => handleUpdate(editItem.id, data)}
                        loading={formLoading}
                        initialData={editItem}
                    />
                )}
            </AnimatePresence>
        </motion.div>
    );
}

// ========== ESTADÍSTICAS TAB ==========
function EstadisticasTab() {
    const [stats, setStats] = useState<EstadisticasPagos | null>(null);
    const [loading, setLoading] = useState(true);
    const [year, setYear] = useState(new Date().getFullYear());

    const loadStats = async () => {
        setLoading(true);
        try {
            const res = await api.getEstadisticasPagos(year);
            if (res.ok && res.data) {
                setStats(res.data);
            }
        } catch {
            // Ignore
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadStats();
    }, [year]);

    const months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-6"
        >
            <div className="flex items-center gap-4">
                <label className="text-neutral-400">Año:</label>
                <select
                    value={year}
                    onChange={(e) => setYear(Number(e.target.value))}
                    className="input w-32"
                >
                    {[2024, 2025, 2026, 2027].map((y) => (
                        <option key={y} value={y}>{y}</option>
                    ))}
                </select>
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-16">
                    <Loader2 className="w-8 h-8 animate-spin text-iron-400" />
                </div>
            ) : !stats ? (
                <div className="p-8 text-center text-neutral-500">No hay estadísticas disponibles</div>
            ) : (
                <>
                    {/* Summary Cards */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <StatCard label="Total Pagos" value={stats.total_pagos} />
                        <StatCard label="Recaudado" value={`$${stats.total_recaudado.toLocaleString()}`} highlight />
                        <StatCard label="Promedio" value={`$${stats.promedio_pago.toFixed(2)}`} />
                        <StatCard label="Máximo" value={`$${stats.pago_maximo.toLocaleString()}`} />
                    </div>

                    {/* Monthly Chart (Simple) */}
                    <div className="glass-card p-6">
                        <h3 className="text-lg font-semibold text-white mb-4">Recaudación Mensual</h3>
                        <div className="grid grid-cols-12 gap-2 h-48">
                            {months.map((month, idx) => {
                                const monthData = stats.por_mes[idx + 1];
                                const total = monthData?.total || 0;
                                const maxTotal = Math.max(...Object.values(stats.por_mes).map(m => m.total || 0), 1);
                                const height = (total / maxTotal) * 100;

                                return (
                                    <div key={month} className="flex flex-col items-center justify-end h-full">
                                        <div
                                            className="w-full bg-gradient-to-t from-iron-500 to-iron-400 rounded-t transition-all hover:from-iron-400 hover:to-iron-300"
                                            style={{ height: `${Math.max(height, 2)}%` }}
                                            title={`$${total.toLocaleString()}`}
                                        />
                                        <span className="text-xs text-neutral-400 mt-2">{month}</span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* By Payment Method */}
                    {stats.por_metodo && stats.por_metodo.length > 0 && (
                        <div className="glass-card p-6">
                            <h3 className="text-lg font-semibold text-white mb-4">Por Método de Pago</h3>
                            <div className="space-y-3">
                                {stats.por_metodo.map((m, idx) => (
                                    <div key={idx} className="flex items-center justify-between">
                                        <span className="text-neutral-300">{m.metodo}</span>
                                        <div className="flex items-center gap-4">
                                            <span className="text-neutral-400">{m.cantidad} pagos</span>
                                            <span className="text-success-400 font-medium">${m.total.toLocaleString()}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </>
            )}
        </motion.div>
    );
}

// ========== SHARED COMPONENTS ==========

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60"
            onClick={onClose}
        >
            <motion.div
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.95, opacity: 0 }}
                onClick={(e) => e.stopPropagation()}
                className="glass-card w-full max-w-md p-6"
            >
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-bold text-white">{title}</h2>
                    <button onClick={onClose} className="text-neutral-400 hover:text-white">
                        <X className="w-5 h-5" />
                    </button>
                </div>
                {children}
            </motion.div>
        </motion.div>
    );
}

function StatCard({ label, value, highlight }: { label: string; value: string | number; highlight?: boolean }) {
    return (
        <div className="glass-card p-4">
            <div className="text-neutral-400 text-sm">{label}</div>
            <div className={`text-2xl font-bold mt-1 ${highlight ? 'text-success-400' : 'text-white'}`}>
                {value}
            </div>
        </div>
    );
}

function MetodoForm({
    title,
    onClose,
    onSubmit,
    loading,
    initialData,
}: {
    title: string;
    onClose: () => void;
    onSubmit: (data: Partial<MetodoPago>) => void;
    loading: boolean;
    initialData?: MetodoPago;
}) {
    const [formData, setFormData] = useState({
        nombre: initialData?.nombre || '',
        icono: initialData?.icono || '💳',
        color: initialData?.color || '#3498db',
        comision: initialData?.comision?.toString() || '0',
        activo: initialData?.activo ?? true,
        descripcion: initialData?.descripcion || '',
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSubmit({
            nombre: formData.nombre,
            icono: formData.icono,
            color: formData.color,
            comision: parseFloat(formData.comision) || 0,
            activo: formData.activo,
            descripcion: formData.descripcion || undefined,
        });
    };

    return (
        <Modal title={title} onClose={onClose}>
            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label className="label">Nombre *</label>
                    <input
                        type="text"
                        value={formData.nombre}
                        onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                        className="input"
                        required
                    />
                </div>
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="label">Icono</label>
                        <input
                            type="text"
                            value={formData.icono}
                            onChange={(e) => setFormData({ ...formData, icono: e.target.value })}
                            className="input"
                            maxLength={4}
                        />
                    </div>
                    <div>
                        <label className="label">Color</label>
                        <input
                            type="color"
                            value={formData.color}
                            onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                            className="input h-10"
                        />
                    </div>
                </div>
                <div>
                    <label className="label">Comisión %</label>
                    <input
                        type="number"
                        step="0.1"
                        min="0"
                        max="100"
                        value={formData.comision}
                        onChange={(e) => setFormData({ ...formData, comision: e.target.value })}
                        className="input"
                    />
                </div>
                <div>
                    <label className="label">Descripción</label>
                    <textarea
                        value={formData.descripcion}
                        onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })}
                        className="input"
                        rows={2}
                    />
                </div>
                <div className="flex items-center gap-2">
                    <input
                        type="checkbox"
                        id="activo"
                        checked={formData.activo}
                        onChange={(e) => setFormData({ ...formData, activo: e.target.checked })}
                        className="w-4 h-4"
                    />
                    <label htmlFor="activo" className="text-neutral-300">Activo</label>
                </div>
                <div className="flex justify-end gap-3 pt-2">
                    <button type="button" onClick={onClose} className="btn-secondary">
                        Cancelar
                    </button>
                    <button type="submit" disabled={loading} className="btn-primary">
                        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Guardar'}
                    </button>
                </div>
            </form>
        </Modal>
    );
}

function PlanForm({
    title,
    onClose,
    onSubmit,
    loading,
    initialData,
}: {
    title: string;
    onClose: () => void;
    onSubmit: (data: Partial<TipoCuota>) => void;
    loading: boolean;
    initialData?: TipoCuota;
}) {
    const [formData, setFormData] = useState({
        nombre: initialData?.nombre || '',
        precio: initialData?.precio?.toString() || '0',
        duracion_dias: initialData?.duracion_dias?.toString() || '30',
        activo: initialData?.activo ?? true,
        descripcion: initialData?.descripcion || '',
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSubmit({
            nombre: formData.nombre,
            precio: parseFloat(formData.precio) || 0,
            duracion_dias: parseInt(formData.duracion_dias) || 30,
            activo: formData.activo,
            descripcion: formData.descripcion || undefined,
        });
    };

    return (
        <Modal title={title} onClose={onClose}>
            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label className="label">Nombre *</label>
                    <input
                        type="text"
                        value={formData.nombre}
                        onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                        className="input"
                        required
                    />
                </div>
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="label">Precio</label>
                        <input
                            type="number"
                            step="0.01"
                            min="0"
                            value={formData.precio}
                            onChange={(e) => setFormData({ ...formData, precio: e.target.value })}
                            className="input"
                        />
                    </div>
                    <div>
                        <label className="label">Duración (días)</label>
                        <input
                            type="number"
                            min="1"
                            value={formData.duracion_dias}
                            onChange={(e) => setFormData({ ...formData, duracion_dias: e.target.value })}
                            className="input"
                        />
                    </div>
                </div>
                <div>
                    <label className="label">Descripción</label>
                    <textarea
                        value={formData.descripcion}
                        onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })}
                        className="input"
                        rows={2}
                    />
                </div>
                <div className="flex items-center gap-2">
                    <input
                        type="checkbox"
                        id="plan-activo"
                        checked={formData.activo}
                        onChange={(e) => setFormData({ ...formData, activo: e.target.checked })}
                        className="w-4 h-4"
                    />
                    <label htmlFor="plan-activo" className="text-neutral-300">Activo</label>
                </div>
                <div className="flex justify-end gap-3 pt-2">
                    <button type="button" onClick={onClose} className="btn-secondary">
                        Cancelar
                    </button>
                    <button type="submit" disabled={loading} className="btn-primary">
                        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Guardar'}
                    </button>
                </div>
            </form>
        </Modal>
    );
}
