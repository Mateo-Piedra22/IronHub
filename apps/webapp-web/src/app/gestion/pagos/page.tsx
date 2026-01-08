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
    X,
    Copy,
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
import {
    api,
    type Pago,
    type PagoCreateInput,
    type PagoConceptoItem,
    type Usuario,
    type TipoCuota,
    type MetodoPago,
    type ConceptoPago,
    PAGO_PRESET_TEMPLATES
} from '@/lib/api';
import { formatDate, formatCurrency, cn, getMonthName } from '@/lib/utils';

// Line item state for multi-concept form
interface ConceptoLineItem {
    id: string; // Unique key for React
    mode: 'registered' | 'custom';
    concepto_id?: number;
    descripcion: string;
    cantidad: number;
    precio_unitario: number;
}

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

function createEmptyLineItem(): ConceptoLineItem {
    return {
        id: crypto.randomUUID(),
        mode: 'custom',
        concepto_id: undefined,
        descripcion: '',
        cantidad: 1,
        precio_unitario: 0,
    };
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
    const [usuarioId, setUsuarioId] = useState<number>(0);
    const [fechaPago, setFechaPago] = useState<string>(new Date().toISOString().split('T')[0]);
    const [mes, setMes] = useState<number>(new Date().getMonth() + 1);
    const [anio, setAnio] = useState<number>(new Date().getFullYear());
    const [metodoPagoId, setMetodoPagoId] = useState<number | undefined>();
    const [notas, setNotas] = useState<string>('');
    const [lineItems, setLineItems] = useState<ConceptoLineItem[]>([createEmptyLineItem()]);
    const { success, error } = useToast();

    // Reset form when modal opens
    useEffect(() => {
        if (isOpen) {
            const now = new Date();
            setUsuarioId(preselectedUsuarioId || 0);
            setFechaPago(now.toISOString().split('T')[0]);
            setMes(now.getMonth() + 1);
            setAnio(now.getFullYear());
            setMetodoPagoId(metodosPago[0]?.id);
            setNotas('');
            setLineItems([createEmptyLineItem()]);
        }
    }, [isOpen, preselectedUsuarioId, metodosPago]);

    // Auto-fill first line item from tipo_cuota when user is selected
    useEffect(() => {
        if (usuarioId && lineItems.length === 1 && !lineItems[0].descripcion && lineItems[0].precio_unitario === 0) {
            const user = usuarios.find(u => u.id === usuarioId);
            if (user?.tipo_cuota_id) {
                const tipo = tiposCuota.find(t => t.id === user.tipo_cuota_id);
                if (tipo) {
                    setLineItems([{
                        ...lineItems[0],
                        descripcion: tipo.nombre,
                        precio_unitario: tipo.precio || 0,
                    }]);
                }
            }
        }
    }, [usuarioId, usuarios, tiposCuota, lineItems]);

    // Calculate total
    const total = lineItems.reduce((sum, item) => sum + (item.cantidad * item.precio_unitario), 0);

    // Add new line item
    const addLineItem = () => {
        setLineItems([...lineItems, createEmptyLineItem()]);
    };

    // Remove line item
    const removeLineItem = (id: string) => {
        if (lineItems.length > 1) {
            setLineItems(lineItems.filter(item => item.id !== id));
        }
    };

    // Update line item
    const updateLineItem = (id: string, updates: Partial<ConceptoLineItem>) => {
        setLineItems(lineItems.map(item =>
            item.id === id ? { ...item, ...updates } : item
        ));
    };

    // Handle registered concept selection
    const handleConceptoSelect = (id: string, conceptoId: number | undefined) => {
        if (conceptoId) {
            const concepto = conceptos.find(c => c.id === conceptoId);
            updateLineItem(id, {
                concepto_id: conceptoId,
                descripcion: concepto?.nombre || '',
                mode: 'registered',
            });
        }
    };

    // Apply preset template
    const applyPreset = (presetId: string) => {
        const preset = PAGO_PRESET_TEMPLATES.find(p => p.id === presetId);
        if (preset) {
            const newItems: ConceptoLineItem[] = preset.conceptos.map(c => ({
                id: crypto.randomUUID(),
                mode: 'custom' as const,
                concepto_id: undefined,
                descripcion: c.descripcion || '',
                cantidad: c.cantidad,
                precio_unitario: c.precio_unitario,
            }));
            setLineItems(newItems);
        }
    };

    // Validation
    const validateForm = (): boolean => {
        if (!usuarioId) {
            error('Selecciona un usuario');
            return false;
        }
        if (lineItems.length === 0) {
            error('Agrega al menos un concepto');
            return false;
        }
        for (const item of lineItems) {
            if (!item.concepto_id && !item.descripcion.trim()) {
                error('Cada concepto debe tener una descripción o estar seleccionado');
                return false;
            }
            if (item.cantidad <= 0) {
                error('La cantidad debe ser mayor a 0');
                return false;
            }
            if (item.precio_unitario < 0) {
                error('El precio no puede ser negativo');
                return false;
            }
        }
        if (total <= 0) {
            error('El total debe ser mayor a 0');
            return false;
        }
        return true;
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!validateForm()) return;

        setLoading(true);
        try {
            const payload: PagoCreateInput = {
                usuario_id: usuarioId,
                fecha_pago: fechaPago,
                mes,
                anio,
                metodo_pago_id: metodoPagoId,
                notas: notas || undefined,
                conceptos: lineItems.map(item => ({
                    concepto_id: item.concepto_id,
                    descripcion: item.descripcion || undefined,
                    cantidad: item.cantidad,
                    precio_unitario: item.precio_unitario,
                })),
            };

            const res = await api.createPago(payload);
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
            size="xl"
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
            <form onSubmit={handleSubmit} className="space-y-5">
                {/* User Selection */}
                <Select
                    label="Usuario"
                    value={usuarioId?.toString() || ''}
                    onChange={(e) => setUsuarioId(Number(e.target.value))}
                    placeholder="Seleccionar usuario"
                    options={usuarios.map((u) => ({
                        value: u.id.toString(),
                        label: `${u.nombre}${u.dni ? ` (${u.dni})` : ''}`,
                    }))}
                />

                {/* Preset Templates */}
                <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm text-slate-400">Plantillas:</span>
                    {PAGO_PRESET_TEMPLATES.map((preset) => (
                        <button
                            key={preset.id}
                            type="button"
                            onClick={() => applyPreset(preset.id)}
                            className="px-3 py-1.5 text-xs rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors border border-slate-700"
                        >
                            <Copy className="w-3 h-3 inline mr-1.5" />
                            {preset.nombre}
                        </button>
                    ))}
                </div>

                {/* Line Items */}
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <label className="text-sm font-medium text-slate-300">Conceptos</label>
                        <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={addLineItem}
                            leftIcon={<Plus className="w-4 h-4" />}
                        >
                            Agregar
                        </Button>
                    </div>

                    <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                        {lineItems.map((item, index) => (
                            <div
                                key={item.id}
                                className="p-3 rounded-lg bg-slate-800/50 border border-slate-700/50 space-y-3"
                            >
                                <div className="flex items-center gap-2">
                                    <span className="text-xs text-slate-500 font-medium">#{index + 1}</span>
                                    <div className="flex gap-1 text-xs">
                                        <button
                                            type="button"
                                            onClick={() => updateLineItem(item.id, { mode: 'registered', descripcion: '' })}
                                            className={cn(
                                                'px-2 py-1 rounded transition-colors',
                                                item.mode === 'registered'
                                                    ? 'bg-primary-500/20 text-primary-400'
                                                    : 'text-slate-500 hover:text-slate-300'
                                            )}
                                        >
                                            Concepto
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => updateLineItem(item.id, { mode: 'custom', concepto_id: undefined })}
                                            className={cn(
                                                'px-2 py-1 rounded transition-colors',
                                                item.mode === 'custom'
                                                    ? 'bg-primary-500/20 text-primary-400'
                                                    : 'text-slate-500 hover:text-slate-300'
                                            )}
                                        >
                                            Personalizado
                                        </button>
                                    </div>
                                    <div className="flex-1" />
                                    {lineItems.length > 1 && (
                                        <button
                                            type="button"
                                            onClick={() => removeLineItem(item.id)}
                                            className="p-1 text-slate-500 hover:text-danger-400 transition-colors"
                                        >
                                            <X className="w-4 h-4" />
                                        </button>
                                    )}
                                </div>

                                <div className="grid grid-cols-12 gap-3">
                                    {/* Description/Concept (6 cols) */}
                                    <div className="col-span-6">
                                        {item.mode === 'registered' ? (
                                            <Select
                                                value={item.concepto_id?.toString() || ''}
                                                onChange={(e) => handleConceptoSelect(item.id, e.target.value ? Number(e.target.value) : undefined)}
                                                placeholder="Seleccionar concepto"
                                                options={conceptos.map((c) => ({
                                                    value: c.id.toString(),
                                                    label: c.nombre,
                                                }))}
                                            />
                                        ) : (
                                            <Input
                                                value={item.descripcion}
                                                onChange={(e) => updateLineItem(item.id, { descripcion: e.target.value })}
                                                placeholder="Descripción..."
                                            />
                                        )}
                                    </div>

                                    {/* Quantity (2 cols) */}
                                    <div className="col-span-2">
                                        <Input
                                            type="number"
                                            min={1}
                                            value={item.cantidad}
                                            onChange={(e) => updateLineItem(item.id, { cantidad: Math.max(1, Number(e.target.value)) })}
                                            placeholder="Cant."
                                        />
                                    </div>

                                    {/* Unit Price (4 cols) */}
                                    <div className="col-span-4">
                                        <Input
                                            type="number"
                                            min={0}
                                            step={0.01}
                                            value={item.precio_unitario || ''}
                                            onChange={(e) => updateLineItem(item.id, { precio_unitario: Number(e.target.value) })}
                                            leftIcon={<span className="text-slate-400">$</span>}
                                            placeholder="Precio"
                                        />
                                    </div>
                                </div>

                                {/* Line subtotal */}
                                <div className="text-right text-sm text-slate-400">
                                    Subtotal: <span className="text-white font-medium">{formatCurrency(item.cantidad * item.precio_unitario)}</span>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Total */}
                    <div className="flex justify-end p-3 rounded-lg bg-success-500/10 border border-success-500/20">
                        <div className="text-right">
                            <span className="text-sm text-slate-400">Total:</span>
                            <span className="ml-3 text-xl font-bold text-success-400">{formatCurrency(total)}</span>
                        </div>
                    </div>
                </div>

                {/* Date, Month, Year */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Input
                        label="Fecha"
                        type="date"
                        value={fechaPago}
                        onChange={(e) => setFechaPago(e.target.value)}
                    />
                    <Select
                        label="Mes"
                        value={mes?.toString() || ''}
                        onChange={(e) => setMes(Number(e.target.value))}
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
                        value={anio || ''}
                        onChange={(e) => setAnio(Number(e.target.value))}
                    />
                </div>

                {/* Payment Method */}
                <Select
                    label="Método de Pago"
                    value={metodoPagoId?.toString() || ''}
                    onChange={(e) => setMetodoPagoId(e.target.value ? Number(e.target.value) : undefined)}
                    placeholder="Seleccionar"
                    options={metodosPago.map((m) => ({
                        value: m.id.toString(),
                        label: m.nombre,
                    }))}
                />

                {/* Notes */}
                <Textarea
                    label="Notas"
                    value={notas}
                    onChange={(e) => setNotas(e.target.value)}
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
                    <div className="text-xs text-slate-500">
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
                <span className="inline-flex items-center px-2 py-1 rounded-md bg-slate-800 text-xs">
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
                    <span className="text-primary-400 font-mono text-sm">#{row.recibo_numero}</span>
                ) : (
                    <span className="text-slate-600">-</span>
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
                        className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                        title="Ver recibo"
                    >
                        <FileText className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => {
                            setPagoToDelete(row);
                            setDeleteModalOpen(true);
                        }}
                        className="p-2 rounded-lg text-slate-400 hover:text-danger-400 hover:bg-danger-500/10 transition-colors"
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
                    <p className="text-slate-400 mt-1">
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
                <div className="card p-4">
                    <div className="text-sm text-slate-400">Total mostrado</div>
                    <div className="text-2xl font-display font-bold text-success-400 mt-1">
                        {formatCurrency(totalMonto)}
                    </div>
                </div>
                <div className="card p-4">
                    <div className="text-sm text-slate-400">Registros</div>
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
                className="card p-4"
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


