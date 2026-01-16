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
} from '@/components/ui';
import ClaseDetailModal from '@/components/ClaseDetailModal';
import { api, type Clase, type ClaseAgendaItem, type Profesor } from '@/lib/api';
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
function ScheduleGrid({ clases, agenda, onEdit, onDelete, onManage }: {
    clases: Clase[];
    agenda: ClaseAgendaItem[];
    onEdit: (c: Clase) => void;
    onDelete: (c: Clase) => void;
    onManage: (c: Clase) => void;
}) {
    const diaToValue = (dia: string) => {
        const d = (dia || '').trim().toLowerCase();
        if (d === 'lunes') return 1;
        if (d === 'martes') return 2;
        if (d === 'miércoles' || d === 'miercoles') return 3;
        if (d === 'jueves') return 4;
        if (d === 'viernes') return 5;
        if (d === 'sábado' || d === 'sabado') return 6;
        if (d === 'domingo') return 0;
        return 0;
    };

    const clasesById = new Map<number, Clase>(clases.map((c) => [c.id, c]));

    const byDay: Record<number, ClaseAgendaItem[]> = {};
    diasSemana.forEach((d) => { byDay[d.value] = []; });
    agenda.forEach((a) => {
        const day = diaToValue(a.dia);
        byDay[day] = byDay[day] || [];
        byDay[day].push(a);
    });
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
                            byDay[dia.value].map((item) => {
                                const clase = clasesById.get(item.clase_id) || { id: item.clase_id, nombre: item.clase_nombre, descripcion: item.clase_descripcion || undefined };
                                const cupoTxt =
                                    item.cupo && item.cupo > 0
                                        ? `${item.inscriptos_count || 0}/${item.cupo}`
                                        : `${item.inscriptos_count || 0}`;
                                return (
                                <div
                                    key={item.horario_id}
                                    className={cn(
                                        'p-3 rounded-xl border border-slate-800 bg-slate-900/50',
                                        'hover:border-primary-500/50 transition-colors group cursor-pointer'
                                    )}
                                    onClick={() => onManage(clase)}
                                >
                                    <div className="font-medium text-white text-sm">{item.clase_nombre}</div>
                                    <div className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                                        <Clock className="w-3 h-3" />
                                        {formatTime(item.hora_inicio)} - {formatTime(item.hora_fin)}
                                    </div>
                                    <div className="text-xs text-slate-500 mt-1 flex items-center justify-between gap-2">
                                        <span className="truncate">{item.profesor_nombre || 'Sin profesor'}</span>
                                        <span className="tabular-nums">{cupoTxt}</span>
                                    </div>
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
                                );
                            })
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
    onSuccess: () => void;
}

function ClaseFormModal({ isOpen, onClose, clase, onSuccess }: ClaseFormModalProps) {
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        nombre: '',
        descripcion: '',
    });
    const { success, error } = useToast();

    useEffect(() => {
        if (isOpen) {
            if (clase) {
                setFormData({
                    nombre: clase.nombre,
                    descripcion: clase.descripcion || '',
                });
            } else {
                setFormData({
                    nombre: '',
                    descripcion: '',
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
    const [agenda, setAgenda] = useState<ClaseAgendaItem[]>([]);
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
            const [resClases, resAgenda] = await Promise.all([api.getClases(), api.getClasesAgenda()]);
            if (resClases.ok && resClases.data) setClases(resClases.data.clases);
            if (resAgenda.ok && resAgenda.data) setAgenda(resAgenda.data.agenda || []);
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
                        agenda={agenda}
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


