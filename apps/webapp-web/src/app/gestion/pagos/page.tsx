'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
    Plus,
    Download,
    Filter,
    Calendar,
    Printer,
    Eye,
    Trash2,
    FileText,
    RefreshCw,
    Settings,
} from 'lucide-react';
import {
    Button,
    SearchInput,
    DataTable,
    Modal,
    ConfirmModal,
    useToast,
    Input,
    Select,
    Textarea,
    type Column,
} from '@/components/ui';
import ReciboPreviewModal, { ReciboConfigModal } from '@/components/ReciboPreviewModal';
import { api, type Pago, type PagoCreateInput, type Usuario, type TipoCuota, type MetodoPago, type ConceptoPago } from '@/lib/api';
import { formatDate, formatCurrency, cn, getMonthName } from '@/lib/utils';

// Pago form modal
interface PagoFormModalProps {
    isOpen: boolean;
    onClose: () => void;
    pago?: Pago | null;
    usuarios: Usuario[];
    tiposCuota: TipoCuota[];
    metodosPago: MetodoPago[];
    conceptos: ConceptoPago[];
    preselectedUsuarioId?: number;
    onSuccess: () => void;
}

function PagoFormModal({
    isOpen,
    onClose,
    pago,
    usuarios,
    tiposCuota,
    metodosPago,
    conceptos,
    preselectedUsuarioId,
    onSuccess,
}: PagoFormModalProps) {
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState<PagoCreateInput>({
        usuario_id: 0,
        monto: 0,
        fecha: new Date().toISOString().split('T')[0],
        mes: new Date().getMonth() + 1,
        anio: new Date().getFullYear(),
        metodo_pago_id: undefined,
        concepto_id: undefined,
        tipo_cuota_id: undefined,
        notas: '',
    });
    const { success, error } = useToast();

    useEffect(() => {
        if (isOpen) {
            if (pago) {
                setFormData({
                    usuario_id: pago.usuario_id,
                    monto: pago.monto,
                    fecha: pago.fecha,
                    mes: pago.mes || new Date().getMonth() + 1,
                    anio: pago.anio || new Date().getFullYear(),
                    metodo_pago_id: pago.metodo_pago_id,
                    concepto_id: pago.concepto_id,
                    tipo_cuota_id: pago.tipo_cuota_id,
                    notas: pago.notas || '',
                });
            } else {
                const now = new Date();
                setFormData({
                    usuario_id: preselectedUsuarioId || 0,
                    monto: 0,
                    fecha: now.toISOString().split('T')[0],
                    mes: now.getMonth() + 1,
                    anio: now.getFullYear(),
                    metodo_pago_id: metodosPago[0]?.id,
                    concepto_id: conceptos[0]?.id,
                    tipo_cuota_id: tiposCuota[0]?.id,
                    notas: '',
                });
            }
        }
    }, [isOpen, pago, preselectedUsuarioId, metodosPago, conceptos, tiposCuota]);

    // Auto-fill monto when tipo_cuota changes
    useEffect(() => {
        if (formData.tipo_cuota_id && !pago) {
            const tipo = tiposCuota.find((t) => t.id === formData.tipo_cuota_id);
            if (tipo?.precio) {
                setFormData((prev) => ({ ...prev, monto: tipo.precio! }));
            }
        }
    }, [formData.tipo_cuota_id, tiposCuota, pago]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!formData.usuario_id) {
            error('Selecciona un usuario');
            return;
        }
        if (!formData.monto || formData.monto <= 0) {
            error('El monto debe ser mayor a 0');
            return;
        }

        setLoading(true);
        try {
            const res = await api.createPago(formData);
            if (res.ok) {
                success('Pago registrado');
                onSuccess();
                onClose();
            } else {
                error(res.error || 'Error al registrar pago');
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
            title="Registrar Pago"
            size="lg"
            footer={
                <>
                    <Button variant="secondary" onClick={onClose} disabled={loading}>
                        Cancelar
                    </Button>
                    <Button onClick={handleSubmit} isLoading={loading}>
                        Registrar Pago
                    </Button>
                </>
            }
        >
            <form onSubmit={handleSubmit} className="space-y-4">
                <Select
                    label="Usuario"
                    value={formData.usuario_id?.toString() || ''}
                    onChange={(e) => setFormData({ ...formData, usuario_id: Number(e.target.value) })}
                    placeholder="Seleccionar usuario"
                    options={usuarios.map((u) => ({
                        value: u.id.toString(),
                        label: `${u.nombre}${u.dni ? ` (${u.dni})` : ''}`,
                    }))}
                />

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Select
                        label="Tipo de Cuota"
                        value={formData.tipo_cuota_id?.toString() || ''}
                        onChange={(e) => setFormData({ ...formData, tipo_cuota_id: e.target.value ? Number(e.target.value) : undefined })}
                        placeholder="Seleccionar"
                        options={tiposCuota.map((tc) => ({
                            value: tc.id.toString(),
                            label: `${tc.nombre}${tc.precio ? ` - ${formatCurrency(tc.precio)}` : ''}`,
                        }))}
                    />
                    <Input
                        label="Monto"
                        type="number"
                        min={0}
                        step={0.01}
                        value={formData.monto || ''}
                        onChange={(e) => setFormData({ ...formData, monto: Number(e.target.value) })}
                        leftIcon={<span className="text-neutral-400">$</span>}
                    />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Input
                        label="Fecha"
                        type="date"
                        value={formData.fecha || ''}
                        onChange={(e) => setFormData({ ...formData, fecha: e.target.value })}
                    />
                    <Select
                        label="Mes"
                        value={formData.mes?.toString() || ''}
                        onChange={(e) => setFormData({ ...formData, mes: Number(e.target.value) })}
                        options={Array.from({ length: 12 }, (_, i) => ({
                            value: (i + 1).toString(),
                            label: getMonthName(i + 1),
                        }))}
                    />
                    <Input
                        label="Año"
                        type="number"
                        min={2020}
                        max={2100}
                        value={formData.anio || ''}
                        onChange={(e) => setFormData({ ...formData, anio: Number(e.target.value) })}
                    />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Select
                        label="Método de Pago"
                        value={formData.metodo_pago_id?.toString() || ''}
                        onChange={(e) => setFormData({ ...formData, metodo_pago_id: e.target.value ? Number(e.target.value) : undefined })}
                        placeholder="Seleccionar"
                        options={metodosPago.map((m) => ({
                            value: m.id.toString(),
                            label: m.nombre,
                        }))}
                    />
                    <Select
                        label="Concepto"
                        value={formData.concepto_id?.toString() || ''}
                        onChange={(e) => setFormData({ ...formData, concepto_id: e.target.value ? Number(e.target.value) : undefined })}
                        placeholder="Seleccionar"
                        options={conceptos.map((c) => ({
                            value: c.id.toString(),
                            label: c.nombre,
                        }))}
                    />
                </div>

                <Textarea
                    label="Notas"
                    value={formData.notas || ''}
                    onChange={(e) => setFormData({ ...formData, notas: e.target.value })}
                    placeholder="Notas adicionales..."
                />
            </form>
        </Modal>
    );
}

export default function PagosPage() {
    const { success, error } = useToast();

    // State
    const [pagos, setPagos] = useState<Pago[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [filterDesde, setFilterDesde] = useState('');
    const [filterHasta, setFilterHasta] = useState('');
    const [filterMetodo, setFilterMetodo] = useState<number | undefined>();
    const [page, setPage] = useState(1);
    const [total, setTotal] = useState(0);
    const pageSize = 25;

    // Config data
    const [usuarios, setUsuarios] = useState<Usuario[]>([]);
    const [tiposCuota, setTiposCuota] = useState<TipoCuota[]>([]);
    const [metodosPago, setMetodosPago] = useState<MetodoPago[]>([]);
    const [conceptos, setConceptos] = useState<ConceptoPago[]>([]);

    // Modals
    const [formModalOpen, setFormModalOpen] = useState(false);
    const [deleteModalOpen, setDeleteModalOpen] = useState(false);
    const [pagoToDelete, setPagoToDelete] = useState<Pago | null>(null);

    // Recibo modals
    const [reciboPreviewOpen, setReciboPreviewOpen] = useState(false);
    const [reciboConfigOpen, setReciboConfigOpen] = useState(false);
    const [selectedPago, setSelectedPago] = useState<Pago | null>(null);

    // Load data
    const loadPagos = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.getPagos({
                desde: filterDesde || undefined,
                hasta: filterHasta || undefined,
                metodo_id: filterMetodo,
                page,
                limit: pageSize,
            });
            if (res.ok && res.data) {
                setPagos(res.data.pagos);
                setTotal(res.data.total);
            }
        } catch {
            error('Error al cargar pagos');
        } finally {
            setLoading(false);
        }
    }, [filterDesde, filterHasta, filterMetodo, page, error]);

    // Load config
    useEffect(() => {
        (async () => {
            const [usuariosRes, tiposRes, metodosRes, conceptosRes] = await Promise.all([
                api.getUsuarios({ limit: 1000 }),
                api.getTiposCuota(),
                api.getMetodosPago(),
                api.getConceptosPago(),
            ]);
            if (usuariosRes.ok && usuariosRes.data) setUsuarios(usuariosRes.data.usuarios);
            if (tiposRes.ok && tiposRes.data) setTiposCuota(tiposRes.data.tipos);
            if (metodosRes.ok && metodosRes.data) setMetodosPago(metodosRes.data.metodos);
            if (conceptosRes.ok && conceptosRes.data) setConceptos(conceptosRes.data.conceptos);
        })();
    }, []);

    useEffect(() => {
        loadPagos();
    }, [loadPagos]);

    // Delete
    const handleDelete = async () => {
        if (!pagoToDelete) return;
        try {
            const res = await api.deletePago(pagoToDelete.id);
            if (res.ok) {
                success('Pago eliminado');
                loadPagos();
            } else {
                error(res.error || 'Error al eliminar');
            }
        } catch {
            error('Error de conexión');
        } finally {
            setDeleteModalOpen(false);
            setPagoToDelete(null);
        }
    };

    // Table columns
    const columns: Column<Pago>[] = [
        {
            key: 'fecha',
            header: 'Fecha',
            sortable: true,
            render: (row) => (
                <div>
                    <div className="font-medium text-white">{formatDate(row.fecha)}</div>
                    <div className="text-xs text-neutral-500">
                        {row.mes && row.anio ? `${getMonthName(row.mes)} ${row.anio}` : ''}
                    </div>
                </div>
            ),
        },
        {
            key: 'usuario_nombre',
            header: 'Usuario',
            sortable: true,
            render: (row) => (
                <span className="font-medium">{row.usuario_nombre || `ID: ${row.usuario_id}`}</span>
            ),
        },
        {
            key: 'monto',
            header: 'Monto',
            sortable: true,
            render: (row) => (
                <span className="font-semibold text-success-400">{formatCurrency(row.monto)}</span>
            ),
        },
        {
            key: 'tipo_cuota_nombre',
            header: 'Tipo',
            render: (row) => (
                <span className="text-sm">{row.tipo_cuota_nombre || '-'}</span>
            ),
        },
        {
            key: 'metodo_pago_nombre',
            header: 'Método',
            render: (row) => (
                <span className="inline-flex items-center px-2 py-1 rounded-md bg-neutral-800 text-xs">
                    {row.metodo_pago_nombre || '-'}
                </span>
            ),
        },
        {
            key: 'recibo_numero',
            header: 'Recibo',
            align: 'center',
            render: (row) => (
                row.recibo_numero ? (
                    <span className="text-iron-400 font-mono text-sm">#{row.recibo_numero}</span>
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
                            setSelectedPago(row);
                            setReciboPreviewOpen(true);
                        }}
                        className="p-2 rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors"
                        title="Ver recibo"
                    >
                        <FileText className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => {
                            setPagoToDelete(row);
                            setDeleteModalOpen(true);
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

    // Calculate totals
    const totalMonto = pagos.reduce((sum, p) => sum + p.monto, 0);

    return (
        <div className="space-y-6">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
            >
                <div>
                    <h1 className="text-2xl font-display font-bold text-white">Pagos</h1>
                    <p className="text-neutral-400 mt-1">
                        Registro y gestión de pagos de cuotas
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        variant="secondary"
                        leftIcon={<Settings className="w-4 h-4" />}
                        onClick={() => setReciboConfigOpen(true)}
                    >
                        Config Recibos
                    </Button>
                    <Button
                        leftIcon={<Plus className="w-4 h-4" />}
                        onClick={() => setFormModalOpen(true)}
                    >
                        Nuevo Pago
                    </Button>
                </div>
            </motion.div>

            {/* Stats */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="grid grid-cols-2 md:grid-cols-4 gap-4"
            >
                <div className="glass-card p-4">
                    <div className="text-sm text-neutral-400">Total mostrado</div>
                    <div className="text-2xl font-display font-bold text-success-400 mt-1">
                        {formatCurrency(totalMonto)}
                    </div>
                </div>
                <div className="glass-card p-4">
                    <div className="text-sm text-neutral-400">Registros</div>
                    <div className="text-2xl font-display font-bold text-white mt-1">
                        {total}
                    </div>
                </div>
            </motion.div>

            {/* Filters */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
                className="glass-card p-4"
            >
                <div className="flex flex-col lg:flex-row items-stretch lg:items-center gap-4">
                    <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        <Input
                            label="Desde"
                            type="date"
                            value={filterDesde}
                            onChange={(e) => {
                                setFilterDesde(e.target.value);
                                setPage(1);
                            }}
                        />
                        <Input
                            label="Hasta"
                            type="date"
                            value={filterHasta}
                            onChange={(e) => {
                                setFilterHasta(e.target.value);
                                setPage(1);
                            }}
                        />
                        <Select
                            label="Método"
                            value={filterMetodo?.toString() || ''}
                            onChange={(e) => {
                                setFilterMetodo(e.target.value ? Number(e.target.value) : undefined);
                                setPage(1);
                            }}
                            options={[
                                { value: '', label: 'Todos' },
                                ...metodosPago.map((m) => ({
                                    value: m.id.toString(),
                                    label: m.nombre,
                                })),
                            ]}
                        />
                        <div className="flex items-end">
                            <Button
                                variant="ghost"
                                onClick={loadPagos}
                                className="w-full"
                            >
                                <RefreshCw className="w-4 h-4 mr-2" />
                                Actualizar
                            </Button>
                        </div>
                    </div>
                </div>
            </motion.div>

            {/* Table */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
            >
                <DataTable
                    data={pagos}
                    columns={columns}
                    loading={loading}
                    emptyMessage="No se encontraron pagos"
                    pagination={{
                        page,
                        pageSize,
                        total,
                        onPageChange: setPage,
                    }}
                />
            </motion.div>

            {/* Form Modal */}
            <PagoFormModal
                isOpen={formModalOpen}
                onClose={() => setFormModalOpen(false)}
                pago={null}
                usuarios={usuarios}
                tiposCuota={tiposCuota}
                metodosPago={metodosPago}
                conceptos={conceptos}
                onSuccess={loadPagos}
            />

            {/* Delete Confirm */}
            <ConfirmModal
                isOpen={deleteModalOpen}
                onClose={() => {
                    setDeleteModalOpen(false);
                    setPagoToDelete(null);
                }}
                onConfirm={handleDelete}
                title="Eliminar Pago"
                message={`¿Estás seguro de eliminar este pago de ${pagoToDelete ? formatCurrency(pagoToDelete.monto) : ''}? Esta acción no se puede deshacer.`}
                confirmText="Eliminar"
                variant="danger"
            />

            {/* Recibo Preview Modal */}
            <ReciboPreviewModal
                isOpen={reciboPreviewOpen}
                onClose={() => {
                    setReciboPreviewOpen(false);
                    setSelectedPago(null);
                }}
                pago={selectedPago}
            />

            {/* Recibo Config Modal */}
            <ReciboConfigModal
                isOpen={reciboConfigOpen}
                onClose={() => setReciboConfigOpen(false)}
            />
        </div>
    );
}

