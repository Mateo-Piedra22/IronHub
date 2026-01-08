'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { motion } from 'framer-motion';
import {
    Plus,
    Clock,
    Play,
    Square,
    Timer,
    Edit,
    Trash2,
    Calendar,
    User,
    Settings,
} from 'lucide-react';
import {
    Button,
    DataTable,
    Modal,
    ConfirmModal,
    useToast,
    Input,
    type Column,
} from '@/components/ui';
import ProfesorDetailModal from '@/components/ProfesorDetailModal';
import { api, type Profesor, type Sesion } from '@/lib/api';
import { formatDate, formatTime, cn } from '@/lib/utils';

// Profesor form modal
interface ProfesorFormModalProps {
    isOpen: boolean;
    onClose: () => void;
    profesor?: Profesor | null;
    onSuccess: () => void;
}

function ProfesorFormModal({ isOpen, onClose, profesor, onSuccess }: ProfesorFormModalProps) {
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        nombre: '',
        email: '',
        telefono: '',
    });
    const { success, error } = useToast();

    useEffect(() => {
        if (isOpen) {
            if (profesor) {
                setFormData({
                    nombre: profesor.nombre || '',
                    email: profesor.email || '',
                    telefono: profesor.telefono || '',
                });
            } else {
                setFormData({ nombre: '', email: '', telefono: '' });
            }
        }
    }, [isOpen, profesor]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!formData.nombre.trim()) {
            error('El nombre es requerido');
            return;
        }

        setLoading(true);
        try {
            if (profesor) {
                const res = await api.updateProfesor(profesor.id, formData);
                if (res.ok) {
                    success('Profesor actualizado');
                    onSuccess();
                    onClose();
                } else {
                    error(res.error || 'Error al actualizar');
                }
            } else {
                const res = await api.createProfesor(formData);
                if (res.ok) {
                    success('Profesor creado');
                    onSuccess();
                    onClose();
                } else {
                    error(res.error || 'Error al crear');
                }
            }
        } catch {
            error('Error de conexión');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={profesor ? 'Editar Profesor' : 'Nuevo Profesor'}
            size="md"
            footer={
                <>
                    <Button variant="secondary" onClick={onClose} disabled={loading}>
                        Cancelar
                    </Button>
                    <Button onClick={handleSubmit} isLoading={loading}>
                        {profesor ? 'Guardar' : 'Crear'}
                    </Button>
                </>
            }
        >
            <form onSubmit={handleSubmit} className="space-y-4">
                <Input
                    label="Nombre"
                    value={formData.nombre}
                    onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                    placeholder="Nombre del profesor"
                    required
                />
                <Input
                    label="Email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="profesor@email.com"
                />
                <Input
                    label="Teléfono"
                    value={formData.telefono}
                    onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
                    placeholder="3434567890"
                />
            </form>
        </Modal>
    );
}

// Session timer component
interface SessionTimerProps {
    profesor: Profesor;
    onSessionUpdate: () => void;
}

function SessionTimer({ profesor, onSessionUpdate }: SessionTimerProps) {
    const [isActive, setIsActive] = useState(false);
    const [startTime, setStartTime] = useState<Date | null>(null);
    const [elapsed, setElapsed] = useState(0);
    const [currentSesionId, setCurrentSesionId] = useState<number | null>(null);
    const [loading, setLoading] = useState(false);
    const { success, error } = useToast();

    useEffect(() => {
        let interval: NodeJS.Timeout;
        if (isActive && startTime) {
            interval = setInterval(() => {
                setElapsed(Math.floor((Date.now() - startTime.getTime()) / 1000));
            }, 1000);
        }
        return () => clearInterval(interval);
    }, [isActive, startTime]);

    const formatElapsed = (seconds: number) => {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    };

    const handleStart = async () => {
        setLoading(true);
        try {
            const res = await api.startSesion(profesor.id);
            if (res.ok && res.data) {
                setIsActive(true);
                setStartTime(new Date());
                setElapsed(0);
                setCurrentSesionId(res.data.id);
                success('Sesión iniciada');
            } else {
                error(res.error || 'Error al iniciar sesión');
            }
        } catch {
            error('Error de conexión');
        } finally {
            setLoading(false);
        }
    };

    const handleStop = async () => {
        if (!currentSesionId) return;

        setLoading(true);
        try {
            const res = await api.endSesion(profesor.id, currentSesionId);
            if (res.ok) {
                setIsActive(false);
                setStartTime(null);
                setElapsed(0);
                setCurrentSesionId(null);
                success('Sesión finalizada');
                onSessionUpdate();
            } else {
                error(res.error || 'Error al finalizar sesión');
            }
        } catch {
            error('Error de conexión');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex items-center gap-4">
            <div className={cn(
                'font-mono text-lg',
                isActive ? 'text-success-400' : 'text-slate-500'
            )}>
                {formatElapsed(elapsed)}
            </div>
            {isActive ? (
                <Button
                    variant="danger"
                    size="sm"
                    leftIcon={<Square className="w-3 h-3" />}
                    onClick={handleStop}
                    isLoading={loading}
                >
                    Finalizar
                </Button>
            ) : (
                <Button
                    variant="success"
                    size="sm"
                    leftIcon={<Play className="w-3 h-3" />}
                    onClick={handleStart}
                    isLoading={loading}
                >
                    Iniciar Sesión
                </Button>
            )}
        </div>
    );
}

export default function ProfesoresPage() {
    const { success, error } = useToast();

    // State
    const [profesores, setProfesores] = useState<Profesor[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedProfesor, setSelectedProfesor] = useState<Profesor | null>(null);
    const [sesiones, setSesiones] = useState<Sesion[]>([]);
    const [sesionesLoading, setSesionesLoading] = useState(false);

    // Modals
    const [formModalOpen, setFormModalOpen] = useState(false);
    const [profesorToEdit, setProfesorToEdit] = useState<Profesor | null>(null);
    const [deleteModalOpen, setDeleteModalOpen] = useState(false);
    const [profesorToDelete, setProfesorToDelete] = useState<Profesor | null>(null);

    // Detail modal
    const [detailOpen, setDetailOpen] = useState(false);

    // Load profesores
    const loadProfesores = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.getProfesores();
            if (res.ok && res.data) {
                setProfesores(res.data.profesores);
                // Select first by default
                if (res.data.profesores.length > 0 && !selectedProfesor) {
                    setSelectedProfesor(res.data.profesores[0]);
                }
            }
        } catch {
            error('Error al cargar profesores');
        } finally {
            setLoading(false);
        }
    }, [error, selectedProfesor]);

    // Load sesiones for selected profesor
    const loadSesiones = useCallback(async () => {
        if (!selectedProfesor) return;
        setSesionesLoading(true);
        try {
            const res = await api.getSesiones(selectedProfesor.id);
            if (res.ok && res.data) {
                setSesiones(res.data.sesiones);
            }
        } catch {
            error('Error al cargar sesiones');
        } finally {
            setSesionesLoading(false);
        }
    }, [selectedProfesor, error]);

    // Delete profesor
    const handleDelete = async () => {
        if (!profesorToDelete) return;
        try {
            const res = await api.deleteProfesor(profesorToDelete.id);
            if (res.ok) {
                success('Profesor eliminado');
                if (selectedProfesor?.id === profesorToDelete.id) {
                    setSelectedProfesor(null);
                }
                loadProfesores();
            } else {
                error(res.error || 'Error al eliminar');
            }
        } catch {
            error('Error de conexión');
        } finally {
            setDeleteModalOpen(false);
            setProfesorToDelete(null);
        }
    };

    useEffect(() => {
        loadProfesores();
    }, [loadProfesores]);

    useEffect(() => {
        loadSesiones();
    }, [loadSesiones]);

    // Sesiones columns
    const sesionesColumns: Column<Sesion>[] = [
        {
            key: 'fecha',
            header: 'Fecha',
            sortable: true,
            render: (row) => <span className="font-medium">{formatDate(row.fecha)}</span>,
        },
        {
            key: 'hora_inicio',
            header: 'Entrada',
            render: (row) => formatTime(row.hora_inicio),
        },
        {
            key: 'hora_fin',
            header: 'Salida',
            render: (row) => formatTime(row.hora_fin),
        },
        {
            key: 'minutos',
            header: 'Duración',
            render: (row) => (
                <span className="text-primary-400">
                    {Math.floor(row.minutos / 60)}h {row.minutos % 60}m
                </span>
            ),
        },
        {
            key: 'tipo',
            header: 'Tipo',
            render: (row) => (
                <span className={cn(
                    'inline-flex items-center px-2 py-1 rounded-md text-xs',
                    row.tipo === 'extra' ? 'bg-warning-500/20 text-warning-400' : 'bg-slate-800 text-slate-300'
                )}>
                    {row.tipo === 'extra' ? 'Extra' : 'Normal'}
                </span>
            ),
        },
    ];

    // Calculate totals for selected profesor
    const totalMinutos = sesiones.reduce((sum, s) => sum + s.minutos, 0);
    const totalHoras = Math.floor(totalMinutos / 60);
    const restMinutos = totalMinutos % 60;

    return (
        <div className="space-y-6">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
            >
                <div>
                    <h1 className="text-2xl font-display font-bold text-white">Profesores</h1>
                    <p className="text-slate-400 mt-1">
                        Gestión de staff y control de sesiones
                    </p>
                </div>
                <Button
                    leftIcon={<Plus className="w-4 h-4" />}
                    onClick={() => {
                        setProfesorToEdit(null);
                        setFormModalOpen(true);
                    }}
                >
                    Nuevo Profesor
                </Button>
            </motion.div>

            {/* Main content - two columns */}
            <div className="grid lg:grid-cols-3 gap-6">
                {/* Profesores list */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="card overflow-hidden"
                >
                    <div className="p-4 border-b border-slate-800">
                        <h2 className="font-semibold text-white flex items-center gap-2">
                            <User className="w-4 h-4 text-primary-400" />
                            Staff ({profesores.length})
                        </h2>
                    </div>
                    <div className="divide-y divide-neutral-800">
                        {loading ? (
                            Array.from({ length: 3 }).map((_, i) => (
                                <div key={i} className="p-4 animate-pulse">
                                    <div className="h-4 bg-slate-800 rounded w-3/4 mb-2" />
                                    <div className="h-3 bg-slate-800 rounded w-1/2" />
                                </div>
                            ))
                        ) : profesores.length === 0 ? (
                            <div className="p-8 text-center text-slate-500">
                                No hay profesores registrados
                            </div>
                        ) : (
                            profesores.map((prof) => (
                                <div
                                    key={prof.id}
                                    className={cn(
                                        'p-4 flex items-center justify-between transition-colors cursor-pointer',
                                        selectedProfesor?.id === prof.id
                                            ? 'bg-primary-500/10 border-l-2 border-l-primary-500'
                                            : 'hover:bg-slate-800/50'
                                    )}
                                    onClick={() => setSelectedProfesor(prof)}
                                >
                                    <div>
                                        <div className="font-medium text-white">{prof.nombre}</div>
                                        <div className="text-sm text-slate-500 mt-0.5">
                                            {prof.telefono || prof.email || 'Sin contacto'}
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                setProfesorToEdit(prof);
                                                setFormModalOpen(true);
                                            }}
                                            className="p-1.5 rounded text-slate-400 hover:text-white hover:bg-slate-800"
                                        >
                                            <Edit className="w-3.5 h-3.5" />
                                        </button>
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                setProfesorToDelete(prof);
                                                setDeleteModalOpen(true);
                                            }}
                                            className="p-1.5 rounded text-slate-400 hover:text-danger-400"
                                        >
                                            <Trash2 className="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </motion.div>

                {/* Selected profesor details */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="lg:col-span-2 space-y-6"
                >
                    {selectedProfesor ? (
                        <>
                            {/* Profesor header with timer */}
                            <div className="card p-6">
                                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                                    <div>
                                        <h2 className="text-xl font-display font-bold text-white">
                                            {selectedProfesor.nombre}
                                        </h2>
                                        <div className="text-sm text-slate-400 mt-1">
                                            {selectedProfesor.email || selectedProfesor.telefono || 'Sin contacto'}
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <Button
                                            variant="secondary"
                                            size="sm"
                                            leftIcon={<Settings className="w-4 h-4" />}
                                            onClick={() => setDetailOpen(true)}
                                        >
                                            Configurar
                                        </Button>
                                        <SessionTimer
                                            profesor={selectedProfesor}
                                            onSessionUpdate={loadSesiones}
                                        />
                                    </div>
                                </div>
                            </div>

                            {/* Stats */}
                            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                                <div className="card p-4">
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 rounded-xl bg-primary-500/20 flex items-center justify-center">
                                            <Timer className="w-5 h-5 text-primary-400" />
                                        </div>
                                        <div>
                                            <div className="text-xl font-bold text-white">
                                                {totalHoras}h {restMinutos}m
                                            </div>
                                            <div className="text-xs text-slate-500">Total horas</div>
                                        </div>
                                    </div>
                                </div>
                                <div className="card p-4">
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 rounded-xl bg-success-500/20 flex items-center justify-center">
                                            <Calendar className="w-5 h-5 text-success-400" />
                                        </div>
                                        <div>
                                            <div className="text-xl font-bold text-white">
                                                {sesiones.length}
                                            </div>
                                            <div className="text-xs text-slate-500">Sesiones</div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Sesiones table */}
                            <div className="card overflow-hidden">
                                <div className="p-4 border-b border-slate-800">
                                    <h3 className="font-semibold text-white flex items-center gap-2">
                                        <Clock className="w-4 h-4 text-primary-400" />
                                        Historial de Sesiones
                                    </h3>
                                </div>
                                <DataTable
                                    data={sesiones}
                                    columns={sesionesColumns}
                                    loading={sesionesLoading}
                                    emptyMessage="No hay sesiones registradas"
                                    compact
                                />
                            </div>
                        </>
                    ) : (
                        <div className="card p-12 text-center text-slate-500">
                            Selecciona un profesor para ver detalles
                        </div>
                    )}
                </motion.div>
            </div>

            {/* Form Modal */}
            <ProfesorFormModal
                isOpen={formModalOpen}
                onClose={() => {
                    setFormModalOpen(false);
                    setProfesorToEdit(null);
                }}
                profesor={profesorToEdit}
                onSuccess={loadProfesores}
            />

            {/* Delete Confirm */}
            <ConfirmModal
                isOpen={deleteModalOpen}
                onClose={() => {
                    setDeleteModalOpen(false);
                    setProfesorToDelete(null);
                }}
                onConfirm={handleDelete}
                title="Eliminar Profesor"
                message={`¿Estás seguro de eliminar a "${profesorToDelete?.nombre}"?`}
                confirmText="Eliminar"
                variant="danger"
            />

            {/* Detail Modal */}
            <ProfesorDetailModal
                isOpen={detailOpen}
                onClose={() => setDetailOpen(false)}
                profesor={selectedProfesor}
                onRefresh={loadProfesores}
            />
        </div>
    );
}


