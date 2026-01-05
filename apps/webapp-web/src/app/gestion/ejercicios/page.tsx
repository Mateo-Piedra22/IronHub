'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
    Plus,
    Search,
    Video,
    Edit,
    Trash2,
    Filter,
} from 'lucide-react';
import {
    Button,
    DataTable,
    Modal,
    ConfirmModal,
    useToast,
    Input,
    Textarea,
    SearchInput,
    Select,
    type Column,
} from '@/components/ui';
import { api, type Ejercicio } from '@/lib/api';
import { cn } from '@/lib/utils';

// Muscle groups for filtering
const gruposMusculares = [
    'Pecho', 'Espalda', 'Hombros', 'Bíceps', 'Tríceps',
    'Cuádriceps', 'Isquiotibiales', 'Glúteos', 'Pantorrillas',
    'Abdominales', 'Core', 'Antebrazos', 'Full Body', 'Cardio',
];

// Ejercicio form modal
interface EjercicioFormModalProps {
    isOpen: boolean;
    onClose: () => void;
    ejercicio?: Ejercicio | null;
    onSuccess: () => void;
}

function EjercicioFormModal({ isOpen, onClose, ejercicio, onSuccess }: EjercicioFormModalProps) {
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        nombre: '',
        descripcion: '',
        grupo_muscular: '',
        equipamiento: '',
        video_url: '',
    });
    const { success, error } = useToast();

    useEffect(() => {
        if (isOpen) {
            if (ejercicio) {
                setFormData({
                    nombre: ejercicio.nombre || '',
                    descripcion: ejercicio.descripcion || '',
                    grupo_muscular: ejercicio.grupo_muscular || '',
                    equipamiento: ejercicio.equipamiento || '',
                    video_url: ejercicio.video_url || '',
                });
            } else {
                setFormData({
                    nombre: '',
                    descripcion: '',
                    grupo_muscular: '',
                    equipamiento: '',
                    video_url: '',
                });
            }
        }
    }, [isOpen, ejercicio]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!formData.nombre.trim()) {
            error('El nombre es requerido');
            return;
        }

        setLoading(true);
        try {
            if (ejercicio) {
                const res = await api.updateEjercicio(ejercicio.id, formData);
                if (res.ok) {
                    success('Ejercicio actualizado');
                    onSuccess();
                    onClose();
                } else {
                    error(res.error || 'Error al actualizar');
                }
            } else {
                const res = await api.createEjercicio(formData);
                if (res.ok) {
                    success('Ejercicio creado');
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
            title={ejercicio ? 'Editar Ejercicio' : 'Nuevo Ejercicio'}
            size="lg"
            footer={
                <>
                    <Button variant="secondary" onClick={onClose} disabled={loading}>
                        Cancelar
                    </Button>
                    <Button onClick={handleSubmit} isLoading={loading}>
                        {ejercicio ? 'Guardar' : 'Crear'}
                    </Button>
                </>
            }
        >
            <form onSubmit={handleSubmit} className="space-y-4">
                <Input
                    label="Nombre del ejercicio"
                    value={formData.nombre}
                    onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                    placeholder="Ej: Press de Banca"
                    required
                />
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Select
                        label="Grupo Muscular"
                        value={formData.grupo_muscular}
                        onChange={(e) => setFormData({ ...formData, grupo_muscular: e.target.value })}
                        placeholder="Seleccionar"
                        options={gruposMusculares.map((g) => ({ value: g, label: g }))}
                    />
                    <Input
                        label="Equipamiento"
                        value={formData.equipamiento}
                        onChange={(e) => setFormData({ ...formData, equipamiento: e.target.value })}
                        placeholder="Ej: Barra, Mancuernas"
                    />
                </div>
                <Input
                    label="URL de Video"
                    value={formData.video_url}
                    onChange={(e) => setFormData({ ...formData, video_url: e.target.value })}
                    placeholder="https://youtube.com/watch?v=..."
                    leftIcon={<Video className="w-4 h-4" />}
                />
                <Textarea
                    label="Descripción / Instrucciones"
                    value={formData.descripcion}
                    onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })}
                    placeholder="Describe el ejercicio y su ejecución correcta..."
                />
            </form>
        </Modal>
    );
}

export default function EjerciciosPage() {
    const { success, error } = useToast();

    // State
    const [ejercicios, setEjercicios] = useState<Ejercicio[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [filterGrupo, setFilterGrupo] = useState('');

    // Modals
    const [formOpen, setFormOpen] = useState(false);
    const [ejercicioToEdit, setEjercicioToEdit] = useState<Ejercicio | null>(null);
    const [deleteOpen, setDeleteOpen] = useState(false);
    const [ejercicioToDelete, setEjercicioToDelete] = useState<Ejercicio | null>(null);

    // Load
    const loadEjercicios = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.getEjercicios({
                search: search || undefined,
                grupo: filterGrupo || undefined,
            });
            if (res.ok && res.data) {
                setEjercicios(res.data.ejercicios);
            }
        } catch {
            error('Error al cargar ejercicios');
        } finally {
            setLoading(false);
        }
    }, [search, filterGrupo, error]);

    useEffect(() => {
        loadEjercicios();
    }, [loadEjercicios]);

    // Delete
    const handleDelete = async () => {
        if (!ejercicioToDelete) return;
        try {
            const res = await api.deleteEjercicio(ejercicioToDelete.id);
            if (res.ok) {
                success('Ejercicio eliminado');
                loadEjercicios();
            } else {
                error(res.error || 'Error al eliminar');
            }
        } catch {
            error('Error de conexión');
        } finally {
            setDeleteOpen(false);
            setEjercicioToDelete(null);
        }
    };

    // Table columns
    const columns: Column<Ejercicio>[] = [
        {
            key: 'nombre',
            header: 'Ejercicio',
            sortable: true,
            render: (row) => (
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-iron-500/20 flex items-center justify-center">
                        {row.video_url ? (
                            <Video className="w-5 h-5 text-iron-400" />
                        ) : (
                            <span className="text-iron-400 text-lg">💪</span>
                        )}
                    </div>
                    <div>
                        <div className="font-medium text-white">{row.nombre}</div>
                        {row.descripcion && (
                            <div className="text-sm text-neutral-500 line-clamp-1 max-w-[200px]">
                                {row.descripcion}
                            </div>
                        )}
                    </div>
                </div>
            ),
        },
        {
            key: 'grupo_muscular',
            header: 'Grupo Muscular',
            sortable: true,
            render: (row) => (
                row.grupo_muscular ? (
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-iron-500/20 text-iron-300 text-xs">
                        {row.grupo_muscular}
                    </span>
                ) : (
                    <span className="text-neutral-600">-</span>
                )
            ),
        },
        {
            key: 'equipamiento',
            header: 'Equipamiento',
            render: (row) => (
                <span className="text-sm">{row.equipamiento || '-'}</span>
            ),
        },
        {
            key: 'video_url',
            header: 'Video',
            align: 'center',
            render: (row) => (
                row.video_url ? (
                    <a
                        href={row.video_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-iron-400 hover:text-iron-300"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <Video className="w-4 h-4" />
                    </a>
                ) : (
                    <span className="text-neutral-600">-</span>
                )
            ),
        },
        {
            key: 'actions',
            header: '',
            width: '100px',
            align: 'right',
            render: (row) => (
                <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
                    <button
                        onClick={() => {
                            setEjercicioToEdit(row);
                            setFormOpen(true);
                        }}
                        className="p-2 rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors"
                        title="Editar"
                    >
                        <Edit className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => {
                            setEjercicioToDelete(row);
                            setDeleteOpen(true);
                        }}
                        className="p-2 rounded-lg text-neutral-400 hover:text-danger-400 hover:bg-danger-500/10 transition-colors"
                        title="Eliminar"
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                </div>
            ),
        },
    ];

    return (
        <div className="space-y-6">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
            >
                <div>
                    <h1 className="text-2xl font-display font-bold text-white">Ejercicios</h1>
                    <p className="text-neutral-400 mt-1">
                        Biblioteca de ejercicios para tus rutinas
                    </p>
                </div>
                <Button
                    leftIcon={<Plus className="w-4 h-4" />}
                    onClick={() => {
                        setEjercicioToEdit(null);
                        setFormOpen(true);
                    }}
                >
                    Nuevo Ejercicio
                </Button>
            </motion.div>

            {/* Filters */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="glass-card p-4"
            >
                <div className="flex flex-col sm:flex-row gap-4">
                    <div className="flex-1">
                        <SearchInput
                            placeholder="Buscar ejercicios..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                    </div>
                    <Select
                        value={filterGrupo}
                        onChange={(e) => setFilterGrupo(e.target.value)}
                        options={[
                            { value: '', label: 'Todos los grupos' },
                            ...gruposMusculares.map((g) => ({ value: g, label: g })),
                        ]}
                    />
                </div>
            </motion.div>

            {/* Stats */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
                className="glass-card p-4"
            >
                <div className="text-sm text-neutral-400">
                    Total: <span className="text-white font-medium">{ejercicios.length} ejercicios</span>
                </div>
            </motion.div>

            {/* Table */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
            >
                <DataTable
                    data={ejercicios}
                    columns={columns}
                    loading={loading}
                    emptyMessage="No se encontraron ejercicios"
                />
            </motion.div>

            {/* Form Modal */}
            <EjercicioFormModal
                isOpen={formOpen}
                onClose={() => {
                    setFormOpen(false);
                    setEjercicioToEdit(null);
                }}
                ejercicio={ejercicioToEdit}
                onSuccess={loadEjercicios}
            />

            {/* Delete Confirm */}
            <ConfirmModal
                isOpen={deleteOpen}
                onClose={() => {
                    setDeleteOpen(false);
                    setEjercicioToDelete(null);
                }}
                onConfirm={handleDelete}
                title="Eliminar Ejercicio"
                message={`¿Estás seguro de eliminar "${ejercicioToDelete?.nombre}"?`}
                confirmText="Eliminar"
                variant="danger"
            />
        </div>
    );
}
