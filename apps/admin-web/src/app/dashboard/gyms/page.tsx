'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Plus, Search, ExternalLink, Trash2, Power, Loader2, X, Check, AlertCircle,
    Grid3X3, List, ChevronLeft, ChevronRight, RefreshCw, Send, Bell, CheckSquare, Square, Settings
} from 'lucide-react';
import Link from 'next/link';
import { api, type Gym } from '@/lib/api';
import { CreateGymWizardModal } from './CreateGymWizardModal';

type ViewMode = 'cards' | 'table';

export default function GymsPage() {
    const [gyms, setGyms] = useState<Gym[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState('');
    const [onlyProdReady, setOnlyProdReady] = useState(false);
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
                production_ready: onlyProdReady ? true : undefined,
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
    }, [search, statusFilter, onlyProdReady, page, pageSize]);

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
        <tr className={selectedIds.has(gym.id) ? 'bg-primary-500/10' : ''}>
            <td className="w-10">
                <button onClick={() => toggleSelect(gym.id)} className="p-1">
                    {selectedIds.has(gym.id) ? (
                        <CheckSquare className="w-4 h-4 text-primary-400" />
                    ) : (
                        <Square className="w-4 h-4 text-slate-600" />
                    )}
                </button>
            </td>
            <td className="font-medium text-white">{gym.nombre}</td>
            <td>
                <a
                    href={`https://${gym.subdominio}.${tenantDomain}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary-400 hover:text-primary-300 flex items-center gap-1"
                >
                    {gym.subdominio}
                    <ExternalLink className="w-3 h-3" />
                </a>
            </td>
            <td className="text-slate-400 text-sm">{gym.db_name}</td>
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
                    <X className="w-4 h-4 text-slate-600" />
                )}
            </td>
            <td>
                {gym.production_ready ? (
                    <span className="badge badge-success">Prod</span>
                ) : (
                    <span className="badge bg-slate-800 text-slate-400 border border-slate-700">—</span>
                )}
            </td>
            <td>
                <div className="flex items-center gap-1">
                    <Link
                        href={`/dashboard/gyms/${gym.id}`}
                        className="p-2 rounded-lg hover:bg-primary-500/10 text-slate-400 hover:text-primary-400"
                        title="Configuración"
                    >
                        <Settings className="w-4 h-4" />
                    </Link>
                    <button
                        onClick={() => { setSelectedGym(gym); setStatusOpen(true); }}
                        className="p-2 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white"
                        title="Cambiar estado"
                    >
                        <Power className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => { setSelectedGym(gym); setDeleteOpen(true); }}
                        className="p-2 rounded-lg hover:bg-danger-500/10 text-slate-400 hover:text-danger-400"
                        title="Eliminar"
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                </div>
            </td>
        </tr>
    );

    const GymCard = ({ gym }: { gym: Gym }) => (
        <div className={`card p-4 ${selectedIds.has(gym.id) ? 'ring-2 ring-primary-500' : ''}`}>
            <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                    <button onClick={() => toggleSelect(gym.id)} className="p-1">
                        {selectedIds.has(gym.id) ? (
                            <CheckSquare className="w-4 h-4 text-primary-400" />
                        ) : (
                            <Square className="w-4 h-4 text-slate-600" />
                        )}
                    </button>
                    <div>
                        <h3 className="font-semibold text-white">{gym.nombre}</h3>
                        <a
                            href={`https://${gym.subdominio}.${tenantDomain}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-primary-400 hover:text-primary-300 flex items-center gap-1"
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
            {gym.production_ready ? (
                <div className="mb-2">
                    <span className="badge badge-success">Listo prod</span>
                </div>
            ) : null}
            <div className="flex items-center justify-between text-sm">
                <span className="text-slate-500">DB: {gym.db_name}</span>
                <div className="flex items-center gap-1">
                    <Link
                        href={`/dashboard/gyms/${gym.id}`}
                        className="p-1.5 rounded-lg hover:bg-primary-500/10 text-slate-400 hover:text-primary-400"
                        title="Configuración"
                    >
                        <Settings className="w-4 h-4" />
                    </Link>
                    <button
                        onClick={() => { setSelectedGym(gym); setStatusOpen(true); }}
                        className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400"
                    >
                        <Power className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => { setSelectedGym(gym); setDeleteOpen(true); }}
                        className="p-1.5 rounded-lg hover:bg-danger-500/10 text-slate-400 hover:text-danger-400"
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
                    <p className="text-slate-400 mt-1">Gestiona todos los gimnasios del sistema</p>
                </div>
                <button onClick={() => setCreateOpen(true)} className="btn-primary flex items-center gap-2">
                    <Plus className="w-4 h-4" />
                    Nuevo Gimnasio
                </button>
            </div>

            {/* Filters */}
            <div className="flex items-center gap-4 flex-wrap">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
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
                <label className="flex items-center gap-2 text-sm text-slate-300 select-none">
                    <input
                        type="checkbox"
                        checked={onlyProdReady}
                        onChange={(e) => { setOnlyProdReady(e.target.checked); setPage(1); }}
                    />
                    Listos prod
                </label>
                <div className="flex items-center gap-1 border border-slate-700 rounded-lg p-1">
                    <button
                        onClick={() => setViewMode('table')}
                        className={`p-2 rounded ${viewMode === 'table' ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'}`}
                    >
                        <List className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => setViewMode('cards')}
                        className={`p-2 rounded ${viewMode === 'cards' ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'}`}
                    >
                        <Grid3X3 className="w-4 h-4" />
                    </button>
                </div>
                <button onClick={loadGyms} className="p-2 rounded-lg hover:bg-slate-800 text-slate-400">
                    <RefreshCw className="w-4 h-4" />
                </button>
            </div>

            {/* Batch Actions Bar */}
            {selectedIds.size > 0 && (
                <div className="card p-4 flex items-center gap-4 flex-wrap">
                    <span className="text-sm text-slate-400">
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
                            className="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-white disabled:opacity-50"
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
                        <button onClick={selectAll} className="text-sm text-slate-400 hover:text-white">
                            Seleccionar todo
                        </button>
                        <button onClick={clearSelection} className="text-sm text-slate-400 hover:text-white">
                            Limpiar
                        </button>
                    </div>
                </div>
            )}

            {/* Content */}
            <div className="card overflow-hidden">
                {loading ? (
                    <div className="flex items-center justify-center py-16">
                        <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
                    </div>
                ) : viewMode === 'table' ? (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th className="w-10">
                                    <button onClick={selectedIds.size === gyms.length ? clearSelection : selectAll}>
                                        {selectedIds.size === gyms.length && gyms.length > 0 ? (
                                            <CheckSquare className="w-4 h-4 text-primary-400" />
                                        ) : (
                                            <Square className="w-4 h-4 text-slate-600" />
                                        )}
                                    </button>
                                </th>
                                <th>Nombre</th>
                                <th>Subdominio</th>
                                <th>DB</th>
                                <th>Estado</th>
                                <th>WhatsApp</th>
                                <th>Prod</th>
                                <th className="w-20">Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            {gyms.length === 0 ? (
                                <tr>
                                    <td colSpan={8} className="text-center text-slate-500 py-8">
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
                            <p className="col-span-full text-center text-slate-500 py-8">No hay gimnasios</p>
                        ) : (
                            gyms.map((gym) => <GymCard key={gym.id} gym={gym} />)
                        )}
                    </div>
                )}
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between">
                <div className="text-sm text-slate-400">
                    Página {page} de {lastPage} · {total} resultados
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setPage((p) => Math.max(1, p - 1))}
                        disabled={page <= 1}
                        className="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-white disabled:opacity-50"
                    >
                        <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => setPage((p) => Math.min(lastPage, p + 1))}
                        disabled={page >= lastPage}
                        className="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-white disabled:opacity-50"
                    >
                        <ChevronRight className="w-4 h-4" />
                    </button>
                </div>
            </div>

            <CreateGymWizardModal
                open={createOpen}
                onClose={() => setCreateOpen(false)}
                tenantDomain={tenantDomain}
                onCreated={(_gymId) => {
                    loadGyms();
                }}
            />

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
                            className="card w-full max-w-sm p-6"
                        >
                            <h2 className="text-xl font-bold text-white mb-2">Eliminar Gimnasio</h2>
                            <p className="text-slate-400 mb-4">
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
                            className="card w-full max-w-sm p-6"
                        >
                            <h2 className="text-xl font-bold text-white mb-4">Cambiar Estado</h2>
                            <p className="text-slate-400 mb-4">{selectedGym.nombre}</p>
                            <div className="space-y-2">
                                <button
                                    onClick={() => handleStatusChange('active')}
                                    disabled={formLoading}
                                    className="w-full p-3 rounded-xl text-left hover:bg-success-500/10 border border-slate-800 hover:border-success-500/30"
                                >
                                    <span className="text-success-400 font-medium">Activar</span>
                                </button>
                                <button
                                    onClick={() => handleStatusChange('maintenance')}
                                    disabled={formLoading}
                                    className="w-full p-3 rounded-xl text-left hover:bg-warning-500/10 border border-slate-800 hover:border-warning-500/30"
                                >
                                    <span className="text-warning-400 font-medium">Mantenimiento</span>
                                </button>
                                <button
                                    onClick={() => handleStatusChange('suspended')}
                                    disabled={formLoading}
                                    className="w-full p-3 rounded-xl text-left hover:bg-danger-500/10 border border-slate-800 hover:border-danger-500/30"
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
                            className="card w-full max-w-md p-6"
                        >
                            <h2 className="text-xl font-bold text-white mb-4">Suspender Gimnasios</h2>
                            <p className="text-slate-400 mb-4">{selectedIds.size} gimnasio(s) seleccionado(s)</p>
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
                                    <span className="text-slate-300">Hard suspend</span>
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

