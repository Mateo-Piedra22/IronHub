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
    QrCode,
    FileDown,
    Power,
} from 'lucide-react';
import {
    Button,
    DataTable,
    Modal,
    ConfirmModal,
    useToast,
    SearchInput,
    type Column,
} from '@/components/ui';
import { api, type Rutina, type Usuario } from '@/lib/api';
import { formatDate, cn } from '@/lib/utils';
import { UnifiedRutinaEditor } from '@/components/UnifiedRutinaEditor';
import { RutinaCreationWizard } from '@/components/RutinaCreationWizard';
import { AssignRutinaModal } from '@/components/AssignRutinaModal';
import { RutinaExportModal } from '@/components/RutinaExportModal';

// Sidebar navigation
const subtabs = [
    { id: 'plantillas', label: 'Plantillas', icon: FileText },
    { id: 'asignadas', label: 'Asignadas', icon: Users },
];

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
                        <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-primary-500/20 text-primary-300 text-xs">
                            {rutina.categoria}
                        </span>
                    )}
                    {rutina.usuario_nombre && (
                        <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-slate-800 text-xs">
                            Asignada a: {rutina.usuario_nombre}
                        </span>
                    )}
                    {rutina.uuid_rutina && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-slate-800 text-xs text-slate-400">
                            <QrCode className="w-3 h-3" />
                            QR Activo
                        </span>
                    )}
                </div>

                {/* Days */}
                <div className="space-y-3">
                    {(!rutina.dias || rutina.dias.length === 0) ? (
                        <div className="p-8 text-center text-slate-500">
                            Esta rutina no tiene días configurados
                        </div>
                    ) : (
                        rutina.dias.map((dia) => (
                            <div key={dia.numero} className="border border-slate-800 rounded-xl overflow-hidden">
                                <button
                                    onClick={() => toggleDay(dia.numero)}
                                    className="w-full flex items-center justify-between p-4 bg-slate-900/50 hover:bg-slate-800/50 transition-colors"
                                >
                                    <span className="font-medium text-white">
                                        Día {dia.numero}{dia.nombre ? `: ${dia.nombre}` : ''}
                                    </span>
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm text-slate-500">
                                            {dia.ejercicios?.length || 0} ejercicios
                                        </span>
                                        {expandedDays.includes(dia.numero) ? (
                                            <ChevronDown className="w-4 h-4 text-slate-400" />
                                        ) : (
                                            <ChevronRight className="w-4 h-4 text-slate-400" />
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
                                                        <span className="w-6 h-6 rounded-full bg-slate-800 flex items-center justify-center text-xs text-slate-400">
                                                            {idx + 1}
                                                        </span>
                                                        <div className="flex-1">
                                                            <div className="font-medium text-white">
                                                                {ej.ejercicio_nombre || `Ejercicio #${ej.ejercicio_id}`}
                                                            </div>
                                                            <div className="text-sm text-slate-500">
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
    const gymId = 1;

    // State
    const [activeTab, setActiveTab] = useState<'plantillas' | 'asignadas'>('plantillas');
    const [rutinas, setRutinas] = useState<Rutina[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');

    // Modals
    const [editorOpen, setEditorOpen] = useState(false);
    const [rutinaToEdit, setRutinaToEdit] = useState<Rutina | null>(null);

    // Wizard state
    const [wizardOpen, setWizardOpen] = useState(false);

    // Assign modal state
    const [assignModalOpen, setAssignModalOpen] = useState(false);
    const [rutinaToAssign, setRutinaToAssign] = useState<Rutina | null>(null);

    // Preview
    const [previewOpen, setPreviewOpen] = useState(false);
    const [rutinaToPreview, setRutinaToPreview] = useState<Rutina | null>(null);
    const [exportOpen, setExportOpen] = useState(false);
    const [rutinaToExport, setRutinaToExport] = useState<Rutina | null>(null);
    const [deleteOpen, setDeleteOpen] = useState(false);
    const [rutinaToDelete, setRutinaToDelete] = useState<Rutina | null>(null);

    const openRutinaPreview = useCallback(async (r: Rutina) => {
        setLoading(true);
        try {
            const resDetails = await api.getRutina(r.id);
            if (resDetails.ok && resDetails.data) {
                setRutinaToPreview(resDetails.data);
            } else {
                setRutinaToPreview(r);
            }
            setPreviewOpen(true);
        } catch {
            setRutinaToPreview(r);
            setPreviewOpen(true);
        } finally {
            setLoading(false);
        }
    }, []);

    const openRutinaEditor = useCallback(async (r: Rutina) => {
        setLoading(true);
        try {
            // Ensure we open the editor with the FULL routine payload (days + exercises)
            const resDetails = await api.getRutina(r.id);
            if (resDetails.ok && resDetails.data) {
                setRutinaToEdit(resDetails.data);
            } else {
                setRutinaToEdit(r);
            }
            setEditorOpen(true);
        } catch {
            setRutinaToEdit(r);
            setEditorOpen(true);
        } finally {
            setLoading(false);
        }
    }, []);

    const openRutinaExport = useCallback(async (r: Rutina) => {
        setLoading(true);
        try {
            const resDetails = await api.getRutina(r.id);
            if (resDetails.ok && resDetails.data) {
                setRutinaToExport(resDetails.data);
            } else {
                setRutinaToExport(r);
            }
            setExportOpen(true);
        } catch {
            setRutinaToExport(r);
            setExportOpen(true);
        } finally {
            setLoading(false);
        }
    }, []);

    // Load rutinas
    const loadRutinas = useCallback(async (searchTerm?: string) => {
        setLoading(true);
        try {
            const res = await api.getRutinas({
                plantillas: activeTab === 'plantillas',
                search: (searchTerm || '').trim() || undefined,
            });
            if (res.ok && res.data) {
                setRutinas(res.data.rutinas);
            }
        } catch {
            error('Error al cargar rutinas');
        } finally {
            setLoading(false);
        }
    }, [activeTab, error]);

    useEffect(() => {
        const t = setTimeout(() => {
            void loadRutinas(search);
        }, 250);
        return () => clearTimeout(t);
    }, [loadRutinas, search]);

    // CSV Export
    const exportToCSV = () => {
        const headers = ['Nombre', 'Categoría', 'Descripción', 'Días', 'Ejercicios Totales', 'Usuario Asignado', 'Fecha Creación'];
        const rows = rutinas.map(r => [
            r.nombre,
            r.categoria || '',
            r.descripcion?.replace(/[\n\r,]/g, ' ') || '',
            r.dias?.length || 0,
            r.dias?.reduce((acc, d) => acc + (d.ejercicios?.length || 0), 0) || 0,
            r.usuario_nombre || '',
            r.fecha_creacion ? new Date(r.fecha_creacion).toLocaleDateString() : '',
        ]);

        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `rutinas_${activeTab}_${new Date().toISOString().split('T')[0]}.csv`;
        link.click();
        URL.revokeObjectURL(url);
        success('CSV exportado correctamente');
    };

    // Delete handler
    const handleDelete = async () => {
        if (!rutinaToDelete) return;
        try {
            const res = await api.deleteRutina(rutinaToDelete.id);
            if (res.ok) {
                success('Rutina eliminada');
                loadRutinas(search);
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

    const handleDeleteClick = (rutina: Rutina) => {
        setRutinaToDelete(rutina);
        setDeleteOpen(true);
    };

    const handleDuplicate = async (rutina: Rutina) => {
        setLoading(true);
        try {
            const res = await api.duplicateRutina(rutina.id);
            if (res.ok) {
                success('Rutina duplicada');
                loadRutinas(search);
            } else {
                error(res.error || 'Error al duplicar');
            }
        } catch {
            error('Error de conexión');
        } finally {
            setLoading(false);
        }
    };

    // Toggle activa handler
    const handleToggleActiva = async (rutina: Rutina) => {
        try {
            const res = await api.toggleRutinaActiva(rutina.id);
            if (res.ok && res.data) {
                success(res.data.activa ? 'Rutina activada' : 'Rutina desactivada');
                loadRutinas(search);
            } else {
                error('Error al cambiar estado');
            }
        } catch {
            error('Error de conexión');
        }
    };

    const handleNewRutina = () => {
        if (activeTab === 'plantillas') {
            // If creating a template, go directly to editor
            setRutinaToEdit({
                es_plantilla: true,
                activa: true,
            } as Rutina);
            setEditorOpen(true);
        } else {
            // If creating an assigned routine, use wizard
            setWizardOpen(true);
        }
    };

    const handleAssign = async (template: Rutina, user: Usuario) => {
        setAssignModalOpen(false);
        setLoading(true);
        try {
            const assigned = await api.assignRutina(template.id, user.id);
            const newId = assigned.ok ? assigned.data?.id : null;
            if (!newId) {
                error(assigned.error || 'No se pudo asignar');
                return;
            }
            const resDetails = await api.getRutina(newId);
            if (resDetails.ok && resDetails.data) {
                setRutinaToEdit(resDetails.data);
            } else {
                setRutinaToEdit({ id: newId } as Rutina);
            }
            setEditorOpen(true);
            success(`Rutina asignada a ${user.nombre}`);

        } catch (e) {
            error('Error preparando asignación');
            console.error(e);
        } finally {
            setLoading(false);
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
                        <div className="text-sm text-slate-500 line-clamp-1">{row.descripcion}</div>
                    )}
                </div>
            ),
        },
        {
            key: 'categoria',
            header: 'Categoría',
            render: (row) => (
                row.categoria ? (
                    <span className="inline-flex items-center px-2 py-1 rounded-md bg-primary-500/20 text-primary-300 text-xs">
                        {row.categoria}
                    </span>
                ) : (
                    <span className="text-slate-600">-</span>
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
                <span className="text-primary-400 font-medium">{row.dias?.length || 0}</span>
            ),
        },
        {
            key: 'ejercicios_count',
            header: 'Ejercicios',
            align: 'center' as const,
            render: (row) => {
                const r = row as unknown;
                const explicit =
                    r && typeof r === 'object' && !Array.isArray(r) ? (r as Record<string, unknown>).ejercicios_count : undefined;
                const reduced = row.dias?.reduce((acc, d) => acc + (d.ejercicios?.length || 0), 0);
                const count = (typeof explicit === 'number') ? explicit : (reduced || 0);
                return <span className="text-slate-400">{count}</span>;
            },
        },
        {
            key: 'fecha_creacion',
            header: 'Creada',
            render: (row) => (
                row.fecha_creacion ? (
                    <span className="text-sm text-slate-400">{formatDate(row.fecha_creacion)}</span>
                ) : '-'
            ),
        },
        {
            key: 'actions',
            header: '',
            width: '150px',
            align: 'right' as const,
            render: (row) => (
                <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
                    <button
                        onClick={() => handleToggleActiva(row)}
                        className={cn(
                            "p-2 rounded-lg transition-colors",
                            row.activa
                                ? "text-success-400 hover:text-success-300 hover:bg-success-500/10"
                                : "text-slate-500 hover:text-slate-300 hover:bg-slate-800"
                        )}
                        title={row.activa ? 'Desactivar rutina' : 'Activar rutina'}
                    >
                        <Power className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => openRutinaExport(row)}
                        className="p-2 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                        title="Exportar PDF"
                    >
                        <FileDown className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => openRutinaPreview(row)}
                        className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                        title="Ver"
                    >
                        <Eye className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => {
                            openRutinaEditor(row);
                        }}
                        className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                        title="Editar"
                    >
                        <Edit className="w-4 h-4" />
                    </button>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDuplicate(row)}
                        title="Duplicar"
                    >
                        <Copy className="w-4 h-4 text-slate-400" />
                    </Button>
                    {activeTab === 'plantillas' && (
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                                setRutinaToAssign(row);
                                setAssignModalOpen(true);
                            }}
                            title="Asignar a usuario"
                        >
                            <Users className="w-4 h-4 text-slate-400 hover:text-primary-400" />
                        </Button>
                    )}
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteClick(row)}
                        title="Eliminar"
                    >
                        <Trash2 className="w-4 h-4 text-danger-400" />
                    </Button>
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
                    <p className="text-slate-400 mt-1">
                        Plantillas de entrenamiento y asignación a usuarios
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button
                        variant="secondary"
                        leftIcon={<Download className="w-4 h-4" />}
                        onClick={exportToCSV}
                        disabled={rutinas.length === 0}
                    >
                        Exportar CSV
                    </Button>
                    <Button
                        leftIcon={<Plus className="w-4 h-4" />}
                        onClick={handleNewRutina}
                    >
                        {activeTab === 'plantillas' ? 'Nueva Plantilla' : 'Nueva Rutina'}
                    </Button>
                </div>
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
                                ? 'bg-primary-500/20 text-primary-300 shadow-sm'
                                : 'text-slate-400 hover:bg-slate-800/50 hover:text-white'
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
                className="card p-4"
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

            {/* Unified Editor Modal */}
            <UnifiedRutinaEditor
                isOpen={editorOpen}
                onClose={() => {
                    setEditorOpen(false);
                    setRutinaToEdit(null);
                    // Also close wizard if it was open
                    setWizardOpen(false);
                }}
                rutina={rutinaToEdit}
                isPlantilla={rutinaToEdit?.es_plantilla || activeTab === 'plantillas'}
                gymId={gymId}
                onSuccess={() => {
                    loadRutinas(search);
                    setWizardOpen(false);
                }}
            />

            {/* Creation Wizard */}
            <RutinaCreationWizard
                isOpen={wizardOpen}
                onClose={() => setWizardOpen(false)}
                onProceed={async (data) => {
                    setWizardOpen(false);
                    setLoading(true);
                    try {
                        if (data.template_id) {
                            const assigned = await api.assignRutina(Number(data.template_id), Number(data.usuario_id));
                            const newId = assigned.ok ? assigned.data?.id : null;
                            if (!newId) {
                                error(assigned.error || 'No se pudo asignar');
                                return;
                            }
                            const resDetails = await api.getRutina(newId);
                            if (resDetails.ok && resDetails.data) {
                                setRutinaToEdit(resDetails.data);
                            } else {
                                setRutinaToEdit({ id: newId } as Rutina);
                            }
                            setEditorOpen(true);
                            return;
                        }

                        setRutinaToEdit({
                            usuario_id: data.usuario_id,
                            usuario_nombre: data.usuario_nombre || undefined,
                            es_plantilla: false,
                            activa: true,
                        } as Rutina);
                        setEditorOpen(true);
                    } finally {
                        setLoading(false);
                    }
                }}
            />

            {/* Assign Modal */}
            <AssignRutinaModal
                isOpen={assignModalOpen}
                onClose={() => {
                    setAssignModalOpen(false);
                    setRutinaToAssign(null);
                }}
                rutina={rutinaToAssign}
                onAssign={handleAssign}
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

            <RutinaExportModal
                isOpen={exportOpen}
                onClose={() => {
                    setExportOpen(false);
                    setRutinaToExport(null);
                }}
                rutina={rutinaToExport}
                gymId={gymId}
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

