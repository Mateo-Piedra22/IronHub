'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Plus, Search, MoreVertical, ExternalLink,
    Trash2, Edit, Power, Loader2, X, Check, AlertCircle
} from 'lucide-react';
import { api, type Gym } from '@/lib/api';

export default function GymsPage() {
    const [gyms, setGyms] = useState<Gym[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState('');

    // Modals
    const [createOpen, setCreateOpen] = useState(false);
    const [deleteOpen, setDeleteOpen] = useState(false);
    const [statusOpen, setStatusOpen] = useState(false);
    const [selectedGym, setSelectedGym] = useState<Gym | null>(null);

    // Form
    const [formData, setFormData] = useState({ nombre: '', subdominio: '', owner_phone: '' });
    const [formLoading, setFormLoading] = useState(false);
    const [formError, setFormError] = useState('');

    const loadGyms = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.getGyms({
                q: search || undefined,
                status: statusFilter || undefined,
                page_size: 50
            });
            if (res.ok && res.data) {
                setGyms(res.data.gyms || []);
            }
        } catch (error) {
            console.error('Error loading gyms:', error);
        } finally {
            setLoading(false);
        }
    }, [search, statusFilter]);

    useEffect(() => {
        loadGyms();
    }, [loadGyms]);

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
            const res = await api.createGym(formData);
            if (res.ok) {
                setCreateOpen(false);
                setFormData({ nombre: '', subdominio: '', owner_phone: '' });
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
            } else {
                setFormError(res.error || 'Error');
            }
        } catch {
            setFormError('Error de conexión');
        } finally {
            setFormLoading(false);
        }
    };

    const tenantDomain = process.env.NEXT_PUBLIC_TENANT_DOMAIN || 'ironhub.motiona.xyz';

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="page-title">Gimnasios</h1>
                    <p className="text-neutral-400 mt-1">Gestiona todos los gimnasios del sistema</p>
                </div>
                <button
                    onClick={() => setCreateOpen(true)}
                    className="btn-primary flex items-center gap-2"
                >
                    <Plus className="w-4 h-4" />
                    Nuevo Gimnasio
                </button>
            </div>

            {/* Filters */}
            <div className="flex items-center gap-4">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500" />
                    <input
                        type="text"
                        placeholder="Buscar gimnasios..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="input pl-10"
                    />
                </div>
                <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="input w-40"
                >
                    <option value="">Todos</option>
                    <option value="active">Activos</option>
                    <option value="suspended">Suspendidos</option>
                    <option value="maintenance">Mantenimiento</option>
                </select>
            </div>

            {/* Table */}
            <div className="glass-card overflow-hidden">
                {loading ? (
                    <div className="flex items-center justify-center py-16">
                        <Loader2 className="w-8 h-8 animate-spin text-iron-400" />
                    </div>
                ) : (
                    <table className="data-table">
                        <thead>
                            <tr>
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
                                    <td colSpan={6} className="text-center text-neutral-500 py-8">
                                        No hay gimnasios
                                    </td>
                                </tr>
                            ) : (
                                gyms.map((gym) => (
                                    <tr key={gym.id}>
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
                                ))
                            )}
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
                            className="glass-card w-full max-w-md p-6"
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
        </div>
    );
}
