'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Plus, Search, ExternalLink, Trash2, Power, Loader2, X, Check, AlertCircle,
    Grid3X3, List, ChevronLeft, ChevronRight, RefreshCw, Send, Bell, CheckSquare, Square
} from 'lucide-react';
import { api, type Gym } from '@/lib/api';

type ViewMode = 'cards' | 'table';

export default function GymsPage() {
    const [gyms, setGyms] = useState<Gym[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState('');
    const [viewMode, setViewMode] = useState<ViewMode>('table');

    // Pagination
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const [total, setTotal] = useState(0);

    // Selection
    const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

    // Modals
    const [createOpen, setCreateOpen] = useState(false);
    const [deleteOpen, setDeleteOpen] = useState(false);
    const [statusOpen, setStatusOpen] = useState(false);
    const [suspendOpen, setSuspendOpen] = useState(false);
    const [selectedGym, setSelectedGym] = useState<Gym | null>(null);

    // Batch actions
    const [reminderMessage, setReminderMessage] = useState('');
    const [maintenanceMessage, setMaintenanceMessage] = useState('');
    const [batchLoading, setBatchLoading] = useState(false);

    // Create form
    const [formData, setFormData] = useState({
        nombre: '',
        subdominio: '',
        owner_phone: '',
        whatsapp_phone_id: '',
        whatsapp_access_token: '',
        whatsapp_business_account_id: '',
        whatsapp_verify_token: '',
        whatsapp_app_secret: '',
        whatsapp_nonblocking: false,
        whatsapp_send_timeout_seconds: '25',
    });
    const [formLoading, setFormLoading] = useState(false);
    const [formError, setFormError] = useState('');

    // Suspend form
    const [suspendData, setSuspendData] = useState({ reason: '', until: '', hard: false });

    const loadGyms = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.getGyms({
                q: search || undefined,
                status: statusFilter || undefined,
                page,
                page_size: pageSize,
            });
            if (res.ok && res.data) {
                setGyms(res.data.gyms || []);
                setTotal(res.data.total || 0);
            }
        } catch (error) {
            console.error('Error loading gyms:', error);
        } finally {
            setLoading(false);
        }
    }, [search, statusFilter, page, pageSize]);

    useEffect(() => {
        loadGyms();
    }, [loadGyms]);

    // Pagination
    const lastPage = Math.max(1, Math.ceil(total / pageSize));

    // Selection handlers
    const toggleSelect = (id: number) => {
        const newSet = new Set(selectedIds);
        if (newSet.has(id)) {
            newSet.delete(id);
        } else {
            newSet.add(id);
        }
        setSelectedIds(newSet);
    };

    const selectAll = () => {
        setSelectedIds(new Set(gyms.map((g) => g.id)));
    };

    const clearSelection = () => {
        setSelectedIds(new Set());
    };

    // Create gym
    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!formData.nombre.trim()) {
            setFormError('Nombre requerido');
            return;
        }
        setFormLoading(true);
        setFormError('');
        try {
            const res = await api.createGym({
                nombre: formData.nombre,
                subdominio: formData.subdominio || undefined,
                owner_phone: formData.owner_phone || undefined,
            });
            if (res.ok) {
                setCreateOpen(false);
                setFormData({
                    nombre: '', subdominio: '', owner_phone: '',
                    whatsapp_phone_id: '', whatsapp_access_token: '', whatsapp_business_account_id: '',
                    whatsapp_verify_token: '', whatsapp_app_secret: '', whatsapp_nonblocking: false,
                    whatsapp_send_timeout_seconds: '25',
                });
                loadGyms();
            } else {
                setFormError(res.error || 'Error al crear');
            }
        } catch {
            setFormError('Error de conexión');
        } finally {
            setFormLoading(false);
        }
    };

    // Delete gym
    const handleDelete = async () => {
        if (!selectedGym) return;
        setFormLoading(true);
        try {
            const res = await api.deleteGym(selectedGym.id);
            if (res.ok) {
                setDeleteOpen(false);
                setSelectedGym(null);
                loadGyms();
            } else {
                setFormError(res.error || 'Error al eliminar');
            }
        } catch {
            setFormError('Error de conexión');
        } finally {
            setFormLoading(false);
        }
    };

    // Change status
    const handleStatusChange = async (status: string) => {
        if (!selectedGym) return;
        setFormLoading(true);
        try {
            const res = await api.setGymStatus(selectedGym.id, status);
            if (res.ok) {
                setStatusOpen(false);
                setSelectedGym(null);
                loadGyms();
            }
        } catch {
            // Ignore
        } finally {
            setFormLoading(false);
        }
    };

    // Batch operations
    const handleBatchSuspend = async () => {
        if (selectedIds.size === 0) return;
        setBatchLoading(true);
        try {
            await api.batchSuspend(
                Array.from(selectedIds),
                suspendData.reason || undefined,
                suspendData.until || undefined,
                suspendData.hard
            );
            setSuspendOpen(false);
            setSuspendData({ reason: '', until: '', hard: false });
            clearSelection();
            loadGyms();
        } catch {
            // Ignore
        } finally {
            setBatchLoading(false);
        }
    };

    const handleBatchReactivate = async () => {
        if (selectedIds.size === 0) return;
        setBatchLoading(true);
        try {
            await api.batchReactivate(Array.from(selectedIds));
            clearSelection();
            loadGyms();
        } catch {
            // Ignore
        } finally {
            setBatchLoading(false);
        }
    };

    const handleBatchProvision = async () => {
        if (selectedIds.size === 0) return;
        setBatchLoading(true);
        try {
            await api.batchProvision(Array.from(selectedIds));
            clearSelection();
            loadGyms();
        } catch {
            // Ignore
        } finally {
            setBatchLoading(false);
        }
    };

    const handleSendReminder = async () => {
        if (selectedIds.size === 0 || !reminderMessage.trim()) return;
        setBatchLoading(true);
        try {
            await api.sendReminder(Array.from(selectedIds), reminderMessage);
            setReminderMessage('');
            clearSelection();
        } catch {
            // Ignore
        } finally {
            setBatchLoading(false);
        }
    };

    const handleSendMaintenance = async () => {
        if (selectedIds.size === 0 || !maintenanceMessage.trim()) return;
        setBatchLoading(true);
        try {
            await api.sendMaintenanceNotice(Array.from(selectedIds), maintenanceMessage);
            setMaintenanceMessage('');
            clearSelection();
        } catch {
            // Ignore
        } finally {
            setBatchLoading(false);
        }
    };

    const tenantDomain = process.env.NEXT_PUBLIC_TENANT_DOMAIN || 'ironhub.motiona.xyz';

    const GymRow = ({ gym }: { gym: Gym }) => (
        <tr className={selectedIds.has(gym.id) ? 'bg-iron-500/10' : ''}>
            <td className="w-10">
                <button onClick={() => toggleSelect(gym.id)} className="p-1">
                    {selectedIds.has(gym.id) ? (
                        <CheckSquare className="w-4 h-4 text-iron-400" />
                    ) : (
                        <Square className="w-4 h-4 text-neutral-600" />
                    )}
                </button>
            </td>
            <td className="font-medium text-white">{gym.nombre}</td>
            <td>
                <a
                    href={`https://${gym.subdominio}.${tenantDomain}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-iron-400 hover:text-iron-300 flex items-center gap-1"
                >
                    {gym.subdominio}
                    <ExternalLink className="w-3 h-3" />
                </a>
            </td>
            <td className="text-neutral-400 text-sm">{gym.db_name}</td>
            <td>
                <span className={`badge ${gym.status === 'active' ? 'badge-success' :
                    gym.status === 'maintenance' ? 'badge-warning' : 'badge-danger'
                    }`}>
                    {gym.status === 'active' ? 'Activo' :
                        gym.status === 'maintenance' ? 'Mantenimiento' : 'Suspendido'}
                </span>
            </td>
            <td>
                {gym.wa_configured ? (
                    <Check className="w-4 h-4 text-success-400" />
                ) : (
                    <X className="w-4 h-4 text-neutral-600" />
                )}
            </td>
            <td>
                <div className="flex items-center gap-1">
                    <button
                        onClick={() => { setSelectedGym(gym); setStatusOpen(true); }}
                        className="p-2 rounded-lg hover:bg-neutral-800 text-neutral-400 hover:text-white"
                        title="Cambiar estado"
                    >
                        <Power className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => { setSelectedGym(gym); setDeleteOpen(true); }}
                        className="p-2 rounded-lg hover:bg-danger-500/10 text-neutral-400 hover:text-danger-400"
                        title="Eliminar"
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                </div>
            </td>
        </tr>
    );

    const GymCard = ({ gym }: { gym: Gym }) => (
        <div className={`glass-card p-4 ${selectedIds.has(gym.id) ? 'ring-2 ring-iron-500' : ''}`}>
            <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                    <button onClick={() => toggleSelect(gym.id)} className="p-1">
                        {selectedIds.has(gym.id) ? (
                            <CheckSquare className="w-4 h-4 text-iron-400" />
                        ) : (
                            <Square className="w-4 h-4 text-neutral-600" />
                        )}
                    </button>
                    <div>
                        <h3 className="font-semibold text-white">{gym.nombre}</h3>
                        <a
                            href={`https://${gym.subdominio}.${tenantDomain}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-iron-400 hover:text-iron-300 flex items-center gap-1"
                        >
                            {gym.subdominio}.{tenantDomain}
                            <ExternalLink className="w-3 h-3" />
                        </a>
                    </div>
                </div>
                <span className={`badge ${gym.status === 'active' ? 'badge-success' :
                    gym.status === 'maintenance' ? 'badge-warning' : 'badge-danger'
                    }`}>
                    {gym.status === 'active' ? 'Activo' :
                        gym.status === 'maintenance' ? 'Mant.' : 'Susp.'}
                </span>
            </div>
            <div className="flex items-center justify-between text-sm">
                <span className="text-neutral-500">DB: {gym.db_name}</span>
                <div className="flex items-center gap-1">
                    <button
                        onClick={() => { setSelectedGym(gym); setStatusOpen(true); }}
                        className="p-1.5 rounded-lg hover:bg-neutral-800 text-neutral-400"
                    >
                        <Power className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => { setSelectedGym(gym); setDeleteOpen(true); }}
                        className="p-1.5 rounded-lg hover:bg-danger-500/10 text-neutral-400 hover:text-danger-400"
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                </div>
            </div>
        </div>
    );

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                    <h1 className="page-title">Gimnasios</h1>
                    <p className="text-neutral-400 mt-1">Gestiona todos los gimnasios del sistema</p>
                </div>
                <button onClick={() => setCreateOpen(true)} className="btn-primary flex items-center gap-2">
                    <Plus className="w-4 h-4" />
                    Nuevo Gimnasio
                </button>
            </div>

            {/* Filters */}
            <div className="flex items-center gap-4 flex-wrap">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500" />
                    <input
                        type="text"
                        placeholder="Buscar gimnasios..."
                        value={search}
                        onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                        className="input pl-10"
                    />
                </div>
                <select
                    value={statusFilter}
                    onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
                    className="input w-40"
                >
                    <option value="">Todos</option>
                    <option value="active">Activos</option>
                    <option value="suspended">Suspendidos</option>
                    <option value="maintenance">Mantenimiento</option>
                </select>
                <div className="flex items-center gap-1 border border-neutral-700 rounded-lg p-1">
                    <button
                        onClick={() => setViewMode('table')}
                        className={`p-2 rounded ${viewMode === 'table' ? 'bg-neutral-700 text-white' : 'text-neutral-400 hover:text-white'}`}
                    >
                        <List className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => setViewMode('cards')}
                        className={`p-2 rounded ${viewMode === 'cards' ? 'bg-neutral-700 text-white' : 'text-neutral-400 hover:text-white'}`}
                    >
                        <Grid3X3 className="w-4 h-4" />
                    </button>
                </div>
                <button onClick={loadGyms} className="p-2 rounded-lg hover:bg-neutral-800 text-neutral-400">
                    <RefreshCw className="w-4 h-4" />
                </button>
            </div>

            {/* Batch Actions Bar */}
            {selectedIds.size > 0 && (
                <div className="glass-card p-4 flex items-center gap-4 flex-wrap">
                    <span className="text-sm text-neutral-400">
                        {selectedIds.size} seleccionados
                    </span>
                    <button
                        onClick={handleBatchProvision}
                        disabled={batchLoading}
                        className="btn-primary text-sm py-1.5 px-3"
                    >
                        Provisionar
                    </button>
                    <button
                        onClick={handleBatchReactivate}
                        disabled={batchLoading}
                        className="bg-success-500/20 text-success-400 hover:bg-success-500/30 text-sm py-1.5 px-3 rounded-lg"
                    >
                        Reactivar
                    </button>
                    <button
                        onClick={() => setSuspendOpen(true)}
                        disabled={batchLoading}
                        className="bg-danger-500/20 text-danger-400 hover:bg-danger-500/30 text-sm py-1.5 px-3 rounded-lg"
                    >
                        Suspender
                    </button>
                    <div className="flex items-center gap-2">
                        <input
                            type="text"
                            placeholder="Mensaje recordatorio"
                            value={reminderMessage}
                            onChange={(e) => setReminderMessage(e.target.value)}
                            className="input text-sm py-1.5 w-48"
                        />
                        <button
                            onClick={handleSendReminder}
                            disabled={batchLoading || !reminderMessage.trim()}
                            className="p-2 rounded-lg bg-neutral-800 text-neutral-400 hover:text-white disabled:opacity-50"
                        >
                            <Send className="w-4 h-4" />
                        </button>
                    </div>
                    <div className="flex items-center gap-2">
                        <input
                            type="text"
                            placeholder="Aviso mantenimiento"
                            value={maintenanceMessage}
                            onChange={(e) => setMaintenanceMessage(e.target.value)}
                            className="input text-sm py-1.5 w-48"
                        />
                        <button
                            onClick={handleSendMaintenance}
                            disabled={batchLoading || !maintenanceMessage.trim()}
                            className="p-2 rounded-lg bg-warning-500/20 text-warning-400 hover:bg-warning-500/30 disabled:opacity-50"
                        >
                            <Bell className="w-4 h-4" />
                        </button>
                    </div>
                    <div className="ml-auto flex items-center gap-2">
                        <button onClick={selectAll} className="text-sm text-neutral-400 hover:text-white">
                            Seleccionar todo
                        </button>
                        <button onClick={clearSelection} className="text-sm text-neutral-400 hover:text-white">
                            Limpiar
                        </button>
                    </div>
                </div>
            )}

            {/* Content */}
            <div className="glass-card overflow-hidden">
                {loading ? (
                    <div className="flex items-center justify-center py-16">
                        <Loader2 className="w-8 h-8 animate-spin text-iron-400" />
                    </div>
                ) : viewMode === 'table' ? (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th className="w-10">
                                    <button onClick={selectedIds.size === gyms.length ? clearSelection : selectAll}>
                                        {selectedIds.size === gyms.length && gyms.length > 0 ? (
                                            <CheckSquare className="w-4 h-4 text-iron-400" />
                                        ) : (
                                            <Square className="w-4 h-4 text-neutral-600" />
                                        )}
                                    </button>
                                </th>
                                <th>Nombre</th>
                                <th>Subdominio</th>
                                <th>DB</th>
                                <th>Estado</th>
                                <th>WhatsApp</th>
                                <th className="w-20">Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            {gyms.length === 0 ? (
                                <tr>
                                    <td colSpan={7} className="text-center text-neutral-500 py-8">
                                        No hay gimnasios
                                    </td>
                                </tr>
                            ) : (
                                gyms.map((gym) => <GymRow key={gym.id} gym={gym} />)
                            )}
                        </tbody>
                    </table>
                ) : (
                    <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {gyms.length === 0 ? (
                            <p className="col-span-full text-center text-neutral-500 py-8">No hay gimnasios</p>
                        ) : (
                            gyms.map((gym) => <GymCard key={gym.id} gym={gym} />)
                        )}
                    </div>
                )}
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between">
                <div className="text-sm text-neutral-400">
                    Página {page} de {lastPage} · {total} resultados
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setPage((p) => Math.max(1, p - 1))}
                        disabled={page <= 1}
                        className="p-2 rounded-lg bg-neutral-800 text-neutral-400 hover:text-white disabled:opacity-50"
                    >
                        <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => setPage((p) => Math.min(lastPage, p + 1))}
                        disabled={page >= lastPage}
                        className="p-2 rounded-lg bg-neutral-800 text-neutral-400 hover:text-white disabled:opacity-50"
                    >
                        <ChevronRight className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Create Modal */}
            <AnimatePresence>
                {createOpen && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 overflow-y-auto"
                        onClick={() => setCreateOpen(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            onClick={(e) => e.stopPropagation()}
                            className="glass-card w-full max-w-lg p-6 my-8"
                        >
                            <h2 className="text-xl font-bold text-white mb-4">Nuevo Gimnasio</h2>
                            <form onSubmit={handleCreate} className="space-y-4">
                                <div>
                                    <label className="label">Nombre *</label>
                                    <input
                                        type="text"
                                        value={formData.nombre}
                                        onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                                        className="input"
                                        placeholder="Iron Fitness"
                                    />
                                </div>
                                <div>
                                    <label className="label">Subdominio</label>
                                    <div className="flex items-center gap-2">
                                        <input
                                            type="text"
                                            value={formData.subdominio}
                                            onChange={(e) => setFormData({ ...formData, subdominio: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '') })}
                                            className="input"
                                            placeholder="ironfitness"
                                        />
                                        <span className="text-neutral-500 whitespace-nowrap">.{tenantDomain}</span>
                                    </div>
                                </div>
                                <div>
                                    <label className="label">Teléfono Owner</label>
                                    <input
                                        type="text"
                                        value={formData.owner_phone}
                                        onChange={(e) => setFormData({ ...formData, owner_phone: e.target.value })}
                                        className="input"
                                        placeholder="+5493411234567"
                                    />
                                </div>

                                <details className="border border-neutral-700 rounded-lg">
                                    <summary className="cursor-pointer px-4 py-3 text-sm text-neutral-300 bg-neutral-800/50 rounded-lg">
                                        Configuración de WhatsApp (avanzado)
                                    </summary>
                                    <div className="p-4 space-y-3">
                                        <div>
                                            <label className="label text-xs">WhatsApp Phone ID</label>
                                            <input
                                                type="text"
                                                value={formData.whatsapp_phone_id}
                                                onChange={(e) => setFormData({ ...formData, whatsapp_phone_id: e.target.value })}
                                                className="input text-sm"
                                            />
                                        </div>
                                        <div>
                                            <label className="label text-xs">Access Token</label>
                                            <input
                                                type="text"
                                                value={formData.whatsapp_access_token}
                                                onChange={(e) => setFormData({ ...formData, whatsapp_access_token: e.target.value })}
                                                className="input text-sm"
                                            />
                                        </div>
                                        <div>
                                            <label className="label text-xs">WABA ID</label>
                                            <input
                                                type="text"
                                                value={formData.whatsapp_business_account_id}
                                                onChange={(e) => setFormData({ ...formData, whatsapp_business_account_id: e.target.value })}
                                                className="input text-sm"
                                            />
                                        </div>
                                        <div>
                                            <label className="label text-xs">Verify Token</label>
                                            <input
                                                type="text"
                                                value={formData.whatsapp_verify_token}
                                                onChange={(e) => setFormData({ ...formData, whatsapp_verify_token: e.target.value })}
                                                className="input text-sm"
                                            />
                                        </div>
                                        <div>
                                            <label className="label text-xs">App Secret</label>
                                            <input
                                                type="text"
                                                value={formData.whatsapp_app_secret}
                                                onChange={(e) => setFormData({ ...formData, whatsapp_app_secret: e.target.value })}
                                                className="input text-sm"
                                            />
                                        </div>
                                        <label className="flex items-center gap-2">
                                            <input
                                                type="checkbox"
                                                checked={formData.whatsapp_nonblocking}
                                                onChange={(e) => setFormData({ ...formData, whatsapp_nonblocking: e.target.checked })}
                                            />
                                            <span className="text-sm text-neutral-300">Envío no bloqueante</span>
                                        </label>
                                        <div>
                                            <label className="label text-xs">Timeout (segundos)</label>
                                            <input
                                                type="number"
                                                value={formData.whatsapp_send_timeout_seconds}
                                                onChange={(e) => setFormData({ ...formData, whatsapp_send_timeout_seconds: e.target.value })}
                                                className="input text-sm w-24"
                                                min="1"
                                                max="120"
                                            />
                                        </div>
                                    </div>
                                </details>

                                {formError && (
                                    <div className="flex items-center gap-2 text-danger-400 text-sm">
                                        <AlertCircle className="w-4 h-4" />
                                        {formError}
                                    </div>
                                )}
                                <div className="flex items-center justify-end gap-3 pt-2">
                                    <button type="button" onClick={() => setCreateOpen(false)} className="btn-secondary">
                                        Cancelar
                                    </button>
                                    <button type="submit" disabled={formLoading} className="btn-primary">
                                        {formLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Crear'}
                                    </button>
                                </div>
                            </form>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Delete Confirm Modal */}
            <AnimatePresence>
                {deleteOpen && selectedGym && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60"
                        onClick={() => setDeleteOpen(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            onClick={(e) => e.stopPropagation()}
                            className="glass-card w-full max-w-sm p-6"
                        >
                            <h2 className="text-xl font-bold text-white mb-2">Eliminar Gimnasio</h2>
                            <p className="text-neutral-400 mb-4">
                                ¿Eliminar <strong>{selectedGym.nombre}</strong>? Esta acción eliminará también su base de datos.
                            </p>
                            <div className="flex items-center justify-end gap-3">
                                <button onClick={() => setDeleteOpen(false)} className="btn-secondary">
                                    Cancelar
                                </button>
                                <button onClick={handleDelete} disabled={formLoading} className="btn-danger">
                                    {formLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Eliminar'}
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Status Change Modal */}
            <AnimatePresence>
                {statusOpen && selectedGym && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60"
                        onClick={() => setStatusOpen(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            onClick={(e) => e.stopPropagation()}
                            className="glass-card w-full max-w-sm p-6"
                        >
                            <h2 className="text-xl font-bold text-white mb-4">Cambiar Estado</h2>
                            <p className="text-neutral-400 mb-4">{selectedGym.nombre}</p>
                            <div className="space-y-2">
                                <button
                                    onClick={() => handleStatusChange('active')}
                                    disabled={formLoading}
                                    className="w-full p-3 rounded-xl text-left hover:bg-success-500/10 border border-neutral-800 hover:border-success-500/30"
                                >
                                    <span className="text-success-400 font-medium">Activar</span>
                                </button>
                                <button
                                    onClick={() => handleStatusChange('maintenance')}
                                    disabled={formLoading}
                                    className="w-full p-3 rounded-xl text-left hover:bg-warning-500/10 border border-neutral-800 hover:border-warning-500/30"
                                >
                                    <span className="text-warning-400 font-medium">Mantenimiento</span>
                                </button>
                                <button
                                    onClick={() => handleStatusChange('suspended')}
                                    disabled={formLoading}
                                    className="w-full p-3 rounded-xl text-left hover:bg-danger-500/10 border border-neutral-800 hover:border-danger-500/30"
                                >
                                    <span className="text-danger-400 font-medium">Suspender</span>
                                </button>
                            </div>
                            <button onClick={() => setStatusOpen(false)} className="btn-secondary w-full mt-4">
                                Cancelar
                            </button>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Suspend Modal */}
            <AnimatePresence>
                {suspendOpen && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60"
                        onClick={() => setSuspendOpen(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            onClick={(e) => e.stopPropagation()}
                            className="glass-card w-full max-w-md p-6"
                        >
                            <h2 className="text-xl font-bold text-white mb-4">Suspender Gimnasios</h2>
                            <p className="text-neutral-400 mb-4">{selectedIds.size} gimnasio(s) seleccionado(s)</p>
                            <div className="space-y-4">
                                <div>
                                    <label className="label">Razón</label>
                                    <input
                                        type="text"
                                        value={suspendData.reason}
                                        onChange={(e) => setSuspendData({ ...suspendData, reason: e.target.value })}
                                        className="input"
                                        placeholder="Falta de pago..."
                                    />
                                </div>
                                <div>
                                    <label className="label">Hasta</label>
                                    <input
                                        type="date"
                                        value={suspendData.until}
                                        onChange={(e) => setSuspendData({ ...suspendData, until: e.target.value })}
                                        className="input"
                                    />
                                </div>
                                <label className="flex items-center gap-2">
                                    <input
                                        type="checkbox"
                                        checked={suspendData.hard}
                                        onChange={(e) => setSuspendData({ ...suspendData, hard: e.target.checked })}
                                    />
                                    <span className="text-neutral-300">Hard suspend</span>
                                </label>
                            </div>
                            <div className="flex items-center justify-end gap-3 mt-6">
                                <button onClick={() => setSuspendOpen(false)} className="btn-secondary">
                                    Cancelar
                                </button>
                                <button onClick={handleBatchSuspend} disabled={batchLoading} className="btn-danger">
                                    {batchLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Suspender'}
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
