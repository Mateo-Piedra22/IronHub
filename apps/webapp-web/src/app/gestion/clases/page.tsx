'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
    Plus,
    Clock,
    Edit,
    Trash2,
    Settings,
} from 'lucide-react';
import {
    Button,
    Modal,
    ConfirmModal,
    useToast,
    Input,
    Textarea,
    Select,
} from '@/components/ui';
import ClaseDetailModal from '@/components/ClaseDetailModal';
import { api, type Clase, type Profesor } from '@/lib/api';
import { formatTime, cn } from '@/lib/utils';

// Days of week
const diasSemana = [
    { value: 1, label: 'Lunes' },
    { value: 2, label: 'Martes' },
    { value: 3, label: 'Miércoles' },
    { value: 4, label: 'Jueves' },
    { value: 5, label: 'Viernes' },
    { value: 6, label: 'Sábado' },
    { value: 0, label: 'Domingo' },
];

// Schedule grid view
function ScheduleGrid({ clases, onEdit, onDelete, onManage }: {
    clases: Clase[];
    onEdit: (c: Clase) => void;
    onDelete: (c: Clase) => void;
    onManage: (c: Clase) => void;
}) {
    // Group by day
    const byDay: Record<number, Clase[]> = {};
    diasSemana.forEach((d) => { byDay[d.value] = []; });
    clases.forEach((c) => {
        if (byDay[c.dia_semana]) {
            byDay[c.dia_semana].push(c);
        }
    });

    // Sort each day by time
    Object.values(byDay).forEach((arr) => arr.sort((a, b) => a.hora_inicio.localeCompare(b.hora_inicio)));

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-7 gap-4">
            {diasSemana.map((dia) => (
                <div key={dia.value} className="card overflow-hidden">
                    <div className="p-3 bg-slate-900/80 border-b border-slate-800">
                        <h3 className="font-semibold text-white text-center">{dia.label}</h3>
                    </div>
                    <div className="p-3 space-y-2 min-h-[200px]">
                        {byDay[dia.value].length === 0 ? (
                            <div className="text-center text-slate-600 text-sm py-4">
                                Sin clases
                            </div>
                        ) : (
                            byDay[dia.value].map((clase) => (
                                <div
                                    key={clase.id}
                                    className={cn(
                                        'p-3 rounded-xl border border-slate-800 bg-slate-900/50',
                                        'hover:border-primary-500/50 transition-colors group cursor-pointer'
                                    )}
                                    style={clase.color ? { borderLeftColor: clase.color, borderLeftWidth: 3 } : {}}
                                    onClick={() => onManage(clase)}
                                >
                                    <div className="font-medium text-white text-sm">{clase.nombre}</div>
                                    <div className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                                        <Clock className="w-3 h-3" />
                                        {formatTime(clase.hora_inicio)} - {formatTime(clase.hora_fin)}
                                    </div>
                                    {clase.profesor_nombre && (
                                        <div className="text-xs text-slate-500 mt-1">
                                            {clase.profesor_nombre}
                                        </div>
                                    )}
                                    <div className="hidden group-hover:flex items-center gap-1 mt-2">
                                        <button
                                            onClick={(e) => { e.stopPropagation(); onManage(clase); }}
                                            className="p-1 rounded text-primary-400 hover:text-primary-300"
                                            title="Gestionar horarios e inscripciones"
                                        >
                                            <Settings className="w-3 h-3" />
                                        </button>
                                        <button
                                            onClick={(e) => { e.stopPropagation(); onEdit(clase); }}
                                            className="p-1 rounded text-slate-400 hover:text-white"
                                        >
                                            <Edit className="w-3 h-3" />
                                        </button>
                                        <button
                                            onClick={(e) => { e.stopPropagation(); onDelete(clase); }}
                                            className="p-1 rounded text-slate-400 hover:text-danger-400"
                                        >
                                            <Trash2 className="w-3 h-3" />
                                        </button>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            ))}
        </div>
    );
}


// Clase form modal
interface ClaseFormModalProps {
    isOpen: boolean;
    onClose: () => void;
    clase?: Clase | null;
    profesores: Profesor[];
    onSuccess: () => void;
}

function ClaseFormModal({ isOpen, onClose, clase, profesores, onSuccess }: ClaseFormModalProps) {
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        nombre: '',
        descripcion: '',
        dia_semana: 1,
        hora_inicio: '09:00',
        hora_fin: '10:00',
        profesor_id: undefined as number | undefined,
        capacidad: undefined as number | undefined,
        color: '#8b5cf6',
    });
    const { success, error } = useToast();

    useEffect(() => {
        if (isOpen) {
            if (clase) {
                setFormData({
                    nombre: clase.nombre,
                    descripcion: clase.descripcion || '',
                    dia_semana: clase.dia_semana,
                    hora_inicio: clase.hora_inicio,
                    hora_fin: clase.hora_fin,
                    profesor_id: clase.profesor_id,
                    capacidad: clase.capacidad,
                    color: clase.color || '#8b5cf6',
                });
            } else {
                setFormData({
                    nombre: '',
                    descripcion: '',
                    dia_semana: 1,
                    hora_inicio: '09:00',
                    hora_fin: '10:00',
                    profesor_id: undefined,
                    capacidad: undefined,
                    color: '#8b5cf6',
                });
            }
        }
    }, [isOpen, clase]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!formData.nombre.trim()) {
            error('El nombre es requerido');
            return;
        }

        setLoading(true);
        try {
            if (clase) {
                const res = await api.updateClase(clase.id, formData);
                if (res.ok) {
                    success('Clase actualizada');
                    onSuccess();
                    onClose();
                } else {
                    error(res.error || 'Error al actualizar');
                }
            } else {
                const res = await api.createClase(formData);
                if (res.ok) {
                    success('Clase creada');
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
            title={clase ? 'Editar Clase' : 'Nueva Clase'}
            size="lg"
            footer={
                <>
                    <Button variant="secondary" onClick={onClose} disabled={loading}>
                        Cancelar
                    </Button>
                    <Button onClick={handleSubmit} isLoading={loading}>
                        {clase ? 'Guardar' : 'Crear'}
                    </Button>
                </>
            }
        >
            <form onSubmit={handleSubmit} className="space-y-4">
                <Input
                    label="Nombre de la clase"
                    value={formData.nombre}
                    onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                    placeholder="Ej: Spinning"
                    required
                />
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Select
                        label="Día"
                        value={formData.dia_semana.toString()}
                        onChange={(e) => setFormData({ ...formData, dia_semana: Number(e.target.value) })}
                        options={diasSemana.map((d) => ({ value: d.value.toString(), label: d.label }))}
                    />
                    <Select
                        label="Profesor"
                        value={formData.profesor_id?.toString() || ''}
                        onChange={(e) => setFormData({ ...formData, profesor_id: e.target.value ? Number(e.target.value) : undefined })}
                        placeholder="Seleccionar"
                        options={profesores.map((p) => ({ value: p.id.toString(), label: p.nombre }))}
                    />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Input
                        label="Hora inicio"
                        type="time"
                        value={formData.hora_inicio}
                        onChange={(e) => setFormData({ ...formData, hora_inicio: e.target.value })}
                    />
                    <Input
                        label="Hora fin"
                        type="time"
                        value={formData.hora_fin}
                        onChange={(e) => setFormData({ ...formData, hora_fin: e.target.value })}
                    />
                    <Input
                        label="Capacidad"
                        type="number"
                        min={1}
                        value={formData.capacidad || ''}
                        onChange={(e) => setFormData({ ...formData, capacidad: e.target.value ? Number(e.target.value) : undefined })}
                        placeholder="Ilimitado"
                    />
                </div>
                <div className="flex items-center gap-4">
                    <label className="text-sm font-medium text-slate-300">Color</label>
                    <input
                        type="color"
                        value={formData.color}
                        onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                        className="w-10 h-10 rounded-lg cursor-pointer"
                    />
                </div>
                <Textarea
                    label="Descripción"
                    value={formData.descripcion}
                    onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })}
                    placeholder="Descripción de la clase..."
                />
            </form>
        </Modal>
    );
}

export default function ClasesPage() {
    const { success, error } = useToast();

    // State
    const [clases, setClases] = useState<Clase[]>([]);
    const [loading, setLoading] = useState(true);
    const [profesores, setProfesores] = useState<Profesor[]>([]);

    // Modals
    const [formOpen, setFormOpen] = useState(false);
    const [claseToEdit, setClaseToEdit] = useState<Clase | null>(null);
    const [deleteOpen, setDeleteOpen] = useState(false);
    const [claseToDelete, setClaseToDelete] = useState<Clase | null>(null);
    const [deleteLoading, setDeleteLoading] = useState(false);

    // Detail modal
    const [detailOpen, setDetailOpen] = useState(false);
    const [detailClase, setDetailClase] = useState<Clase | null>(null);

    // Load
    const loadClases = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.getClases();
            if (res.ok && res.data) {
                setClases(res.data.clases);
            }
        } catch {
            error('Error al cargar clases');
        } finally {
            setLoading(false);
        }
    }, [error]);

    useEffect(() => {
        loadClases();
        (async () => {
            const res = await api.getProfesores();
            if (res.ok && res.data) setProfesores(res.data.profesores);
        })();
    }, [loadClases]);

    // Delete handler
    const handleDelete = async () => {
        if (!claseToDelete) return;
        setDeleteLoading(true);
        try {
            const res = await api.deleteClase(claseToDelete.id);
            if (res.ok) {
                success('Clase eliminada');
                loadClases();
            } else {
                error(res.error || 'Error al eliminar');
            }
        } catch {
            error('Error de conexión');
        } finally {
            setDeleteLoading(false);
            setDeleteOpen(false);
            setClaseToDelete(null);
        }
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
            >
                <div>
                    <h1 className="text-2xl font-display font-bold text-white">Clases</h1>
                    <p className="text-slate-400 mt-1">
                        Horarios de clases grupales
                    </p>
                </div>
                <Button
                    leftIcon={<Plus className="w-4 h-4" />}
                    onClick={() => {
                        setClaseToEdit(null);
                        setFormOpen(true);
                    }}
                >
                    Nueva Clase
                </Button>
            </motion.div>

            {/* Schedule Grid */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
            >
                {loading ? (
                    <div className="card p-12 text-center text-slate-500">
                        Cargando horarios...
                    </div>
                ) : (
                    <ScheduleGrid
                        clases={clases}
                        onEdit={(c) => {
                            setClaseToEdit(c);
                            setFormOpen(true);
                        }}
                        onDelete={(c) => {
                            setClaseToDelete(c);
                            setDeleteOpen(true);
                        }}
                        onManage={(c) => {
                            setDetailClase(c);
                            setDetailOpen(true);
                        }}
                    />
                )}
            </motion.div>

            {/* Form Modal */}
            <ClaseFormModal
                isOpen={formOpen}
                onClose={() => {
                    setFormOpen(false);
                    setClaseToEdit(null);
                }}
                clase={claseToEdit}
                profesores={profesores}
                onSuccess={loadClases}
            />

            {/* Delete Confirm */}
            <ConfirmModal
                isOpen={deleteOpen}
                onClose={() => {
                    setDeleteOpen(false);
                    setClaseToDelete(null);
                }}
                onConfirm={handleDelete}
                title="Eliminar Clase"
                message={`¿Estás seguro de eliminar "${claseToDelete?.nombre}"?`}
                confirmText="Eliminar"
                variant="danger"
            />

            {/* Detail Modal */}
            <ClaseDetailModal
                isOpen={detailOpen}
                onClose={() => {
                    setDetailOpen(false);
                    setDetailClase(null);
                }}
                clase={detailClase}
                profesores={profesores}
                onRefresh={loadClases}
            />
        </div>
    );
}


