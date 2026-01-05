'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Plus,
    FileText,
    Users,
    Edit,
    Trash2,
    Copy,
    Eye,
    Download,
    ChevronDown,
    ChevronRight,
    GripVertical,
    QrCode,
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
    type Column,
} from '@/components/ui';
import { api, type Rutina, type Ejercicio } from '@/lib/api';
import { formatDate, cn } from '@/lib/utils';

// Sidebar navigation
const subtabs = [
    { id: 'plantillas', label: 'Plantillas', icon: FileText },
    { id: 'asignadas', label: 'Asignadas', icon: Users },
];

// Rutina form/editor modal
interface RutinaEditorModalProps {
    isOpen: boolean;
    onClose: () => void;
    rutina?: Rutina | null;
    ejercicios: Ejercicio[];
    isPlantilla: boolean;
    onSuccess: () => void;
}

function RutinaEditorModal({
    isOpen,
    onClose,
    rutina,
    ejercicios,
    isPlantilla,
    onSuccess,
}: RutinaEditorModalProps) {
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        nombre: '',
        descripcion: '',
        categoria: '',
    });
    const { success, error } = useToast();

    useEffect(() => {
        if (isOpen) {
            if (rutina) {
                setFormData({
                    nombre: rutina.nombre || '',
                    descripcion: rutina.descripcion || '',
                    categoria: rutina.categoria || '',
                });
            } else {
                setFormData({ nombre: '', descripcion: '', categoria: '' });
            }
        }
    }, [isOpen, rutina]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!formData.nombre.trim()) {
            error('El nombre es requerido');
            return;
        }

        setLoading(true);
        try {
            if (rutina) {
                const res = await api.updateRutina(rutina.id, {
                    ...formData,
                    es_plantilla: isPlantilla,
                });
                if (res.ok) {
                    success('Rutina actualizada');
                    onSuccess();
                    onClose();
                } else {
                    error(res.error || 'Error al actualizar');
                }
            } else {
                const res = await api.createRutina({
                    ...formData,
                    es_plantilla: isPlantilla,
                    activa: true,
                    dias: [],
                });
                if (res.ok) {
                    success('Rutina creada');
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
            title={rutina ? 'Editar Rutina' : 'Nueva Plantilla'}
            size="lg"
            footer={
                <>
                    <Button variant="secondary" onClick={onClose} disabled={loading}>
                        Cancelar
                    </Button>
                    <Button onClick={handleSubmit} isLoading={loading}>
                        {rutina ? 'Guardar' : 'Crear'}
                    </Button>
                </>
            }
        >
            <form onSubmit={handleSubmit} className="space-y-4">
                <Input
                    label="Nombre de la rutina"
                    value={formData.nombre}
                    onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                    placeholder="Ej: Rutina Full Body Principiante"
                    required
                />
                <Input
                    label="Categoría"
                    value={formData.categoria}
                    onChange={(e) => setFormData({ ...formData, categoria: e.target.value })}
                    placeholder="Ej: Fuerza, Hipertofia, Cardio"
                />
                <Textarea
                    label="Descripción"
                    value={formData.descripcion}
                    onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })}
                    placeholder="Descripción breve de la rutina..."
                />
            </form>
        </Modal>
    );
}

// Rutina preview modal
interface RutinaPreviewModalProps {
    isOpen: boolean;
    onClose: () => void;
    rutina: Rutina | null;
}

function RutinaPreviewModal({ isOpen, onClose, rutina }: RutinaPreviewModalProps) {
    const [expandedDays, setExpandedDays] = useState<number[]>([]);

    const toggleDay = (dayNum: number) => {
        setExpandedDays((prev) =>
            prev.includes(dayNum) ? prev.filter((d) => d !== dayNum) : [...prev, dayNum]
        );
    };

    if (!rutina) return null;

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={rutina.nombre}
            description={rutina.descripcion}
            size="xl"
        >
            <div className="space-y-4">
                {/* Info */}
                <div className="flex flex-wrap gap-2">
                    {rutina.categoria && (
                        <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-iron-500/20 text-iron-300 text-xs">
                            {rutina.categoria}
                        </span>
                    )}
                    {rutina.usuario_nombre && (
                        <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-neutral-800 text-xs">
                            Asignada a: {rutina.usuario_nombre}
                        </span>
                    )}
                    {rutina.uuid_rutina && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-neutral-800 text-xs text-neutral-400">
                            <QrCode className="w-3 h-3" />
                            QR Activo
                        </span>
                    )}
                </div>

                {/* Days */}
                <div className="space-y-3">
                    {rutina.dias.length === 0 ? (
                        <div className="p-8 text-center text-neutral-500">
                            Esta rutina no tiene días configurados
                        </div>
                    ) : (
                        rutina.dias.map((dia) => (
                            <div key={dia.numero} className="border border-neutral-800 rounded-xl overflow-hidden">
                                <button
                                    onClick={() => toggleDay(dia.numero)}
                                    className="w-full flex items-center justify-between p-4 bg-neutral-900/50 hover:bg-neutral-800/50 transition-colors"
                                >
                                    <span className="font-medium text-white">
                                        Día {dia.numero}{dia.nombre ? `: ${dia.nombre}` : ''}
                                    </span>
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm text-neutral-500">
                                            {dia.ejercicios.length} ejercicios
                                        </span>
                                        {expandedDays.includes(dia.numero) ? (
                                            <ChevronDown className="w-4 h-4 text-neutral-400" />
                                        ) : (
                                            <ChevronRight className="w-4 h-4 text-neutral-400" />
                                        )}
                                    </div>
                                </button>
                                <AnimatePresence>
                                    {expandedDays.includes(dia.numero) && (
                                        <motion.div
                                            initial={{ height: 0 }}
                                            animate={{ height: 'auto' }}
                                            exit={{ height: 0 }}
                                            className="overflow-hidden"
                                        >
                                            <div className="divide-y divide-neutral-800">
                                                {dia.ejercicios.map((ej, idx) => (
                                                    <div key={idx} className="p-4 flex items-center gap-4">
                                                        <span className="w-6 h-6 rounded-full bg-neutral-800 flex items-center justify-center text-xs text-neutral-400">
                                                            {idx + 1}
                                                        </span>
                                                        <div className="flex-1">
                                                            <div className="font-medium text-white">
                                                                {ej.ejercicio_nombre || `Ejercicio #${ej.ejercicio_id}`}
                                                            </div>
                                                            <div className="text-sm text-neutral-500">
                                                                {ej.series} series x {ej.repeticiones} reps
                                                                {ej.descanso && ` • ${ej.descanso}s descanso`}
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </Modal>
    );
}

export default function RutinasPage() {
    const { success, error } = useToast();

    // State
    const [activeTab, setActiveTab] = useState<'plantillas' | 'asignadas'>('plantillas');
    const [rutinas, setRutinas] = useState<Rutina[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [ejercicios, setEjercicios] = useState<Ejercicio[]>([]);

    // Modals
    const [editorOpen, setEditorOpen] = useState(false);
    const [rutinaToEdit, setRutinaToEdit] = useState<Rutina | null>(null);
    const [previewOpen, setPreviewOpen] = useState(false);
    const [rutinaToPreview, setRutinaToPreview] = useState<Rutina | null>(null);
    const [deleteOpen, setDeleteOpen] = useState(false);
    const [rutinaToDelete, setRutinaToDelete] = useState<Rutina | null>(null);

    // Load rutinas
    const loadRutinas = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.getRutinas({
                plantillas: activeTab === 'plantillas',
            });
            if (res.ok && res.data) {
                let items = res.data.rutinas;
                if (search) {
                    items = items.filter((r) =>
                        r.nombre.toLowerCase().includes(search.toLowerCase()) ||
                        r.categoria?.toLowerCase().includes(search.toLowerCase())
                    );
                }
                setRutinas(items);
            }
        } catch {
            error('Error al cargar rutinas');
        } finally {
            setLoading(false);
        }
    }, [activeTab, search, error]);

    // Load ejercicios
    useEffect(() => {
        (async () => {
            const res = await api.getEjercicios({});
            if (res.ok && res.data) {
                setEjercicios(res.data.ejercicios);
            }
        })();
    }, []);

    useEffect(() => {
        loadRutinas();
    }, [loadRutinas]);

    // Delete handler
    const handleDelete = async () => {
        if (!rutinaToDelete) return;
        try {
            const res = await api.deleteRutina(rutinaToDelete.id);
            if (res.ok) {
                success('Rutina eliminada');
                loadRutinas();
            } else {
                error(res.error || 'Error al eliminar');
            }
        } catch {
            error('Error de conexión');
        } finally {
            setDeleteOpen(false);
            setRutinaToDelete(null);
        }
    };

    // Table columns
    const columns: Column<Rutina>[] = [
        {
            key: 'nombre',
            header: 'Rutina',
            sortable: true,
            render: (row) => (
                <div>
                    <div className="font-medium text-white">{row.nombre}</div>
                    {row.descripcion && (
                        <div className="text-sm text-neutral-500 line-clamp-1">{row.descripcion}</div>
                    )}
                </div>
            ),
        },
        {
            key: 'categoria',
            header: 'Categoría',
            render: (row) => (
                row.categoria ? (
                    <span className="inline-flex items-center px-2 py-1 rounded-md bg-iron-500/20 text-iron-300 text-xs">
                        {row.categoria}
                    </span>
                ) : (
                    <span className="text-neutral-600">-</span>
                )
            ),
        },
        ...(activeTab === 'asignadas'
            ? [
                {
                    key: 'usuario_nombre',
                    header: 'Asignada a',
                    render: (row: Rutina) => (
                        <span className="text-sm">{row.usuario_nombre || '-'}</span>
                    ),
                },
            ]
            : []),
        {
            key: 'dias',
            header: 'Días',
            align: 'center' as const,
            render: (row) => (
                <span className="text-iron-400 font-medium">{row.dias?.length || 0}</span>
            ),
        },
        {
            key: 'fecha_creacion',
            header: 'Creada',
            render: (row) => (
                row.fecha_creacion ? (
                    <span className="text-sm text-neutral-400">{formatDate(row.fecha_creacion)}</span>
                ) : '-'
            ),
        },
        {
            key: 'actions',
            header: '',
            width: '120px',
            align: 'right' as const,
            render: (row) => (
                <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
                    <button
                        onClick={() => {
                            setRutinaToPreview(row);
                            setPreviewOpen(true);
                        }}
                        className="p-2 rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors"
                        title="Ver"
                    >
                        <Eye className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => {
                            setRutinaToEdit(row);
                            setEditorOpen(true);
                        }}
                        className="p-2 rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors"
                        title="Editar"
                    >
                        <Edit className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => {
                            setRutinaToDelete(row);
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
                    <h1 className="text-2xl font-display font-bold text-white">Rutinas</h1>
                    <p className="text-neutral-400 mt-1">
                        Plantillas de entrenamiento y asignación a usuarios
                    </p>
                </div>
                <Button
                    leftIcon={<Plus className="w-4 h-4" />}
                    onClick={() => {
                        setRutinaToEdit(null);
                        setEditorOpen(true);
                    }}
                >
                    Nueva Plantilla
                </Button>
            </motion.div>

            {/* Tabs */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="flex items-center gap-2"
            >
                {subtabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id as 'plantillas' | 'asignadas')}
                        className={cn(
                            'flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all duration-200',
                            activeTab === tab.id
                                ? 'bg-iron-500/20 text-iron-300 shadow-glow-sm'
                                : 'text-neutral-400 hover:bg-neutral-800/50 hover:text-white'
                        )}
                    >
                        <tab.icon className="w-4 h-4" />
                        {tab.label}
                    </button>
                ))}
            </motion.div>

            {/* Filters */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
                className="glass-card p-4"
            >
                <SearchInput
                    placeholder="Buscar rutinas por nombre o categoría..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
            </motion.div>

            {/* Table */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
            >
                <DataTable
                    data={rutinas}
                    columns={columns}
                    loading={loading}
                    emptyMessage={
                        activeTab === 'plantillas'
                            ? 'No hay plantillas creadas'
                            : 'No hay rutinas asignadas'
                    }
                />
            </motion.div>

            {/* Editor Modal */}
            <RutinaEditorModal
                isOpen={editorOpen}
                onClose={() => {
                    setEditorOpen(false);
                    setRutinaToEdit(null);
                }}
                rutina={rutinaToEdit}
                ejercicios={ejercicios}
                isPlantilla={activeTab === 'plantillas'}
                onSuccess={loadRutinas}
            />

            {/* Preview Modal */}
            <RutinaPreviewModal
                isOpen={previewOpen}
                onClose={() => {
                    setPreviewOpen(false);
                    setRutinaToPreview(null);
                }}
                rutina={rutinaToPreview}
            />

            {/* Delete Confirm */}
            <ConfirmModal
                isOpen={deleteOpen}
                onClose={() => {
                    setDeleteOpen(false);
                    setRutinaToDelete(null);
                }}
                onConfirm={handleDelete}
                title="Eliminar Rutina"
                message={`¿Estás seguro de eliminar "${rutinaToDelete?.nombre}"? Esta acción no se puede deshacer.`}
                confirmText="Eliminar"
                variant="danger"
            />
        </div>
    );
}
