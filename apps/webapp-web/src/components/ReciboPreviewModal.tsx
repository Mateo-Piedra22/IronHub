'use client';

import { useState, useEffect } from 'react';
import {
    FileText,
    Download,
    Printer,
    Settings,
    Plus,
    Trash2,
    DollarSign,
    X,
} from 'lucide-react';
import { Button, Modal, Input, useToast } from '@/components/ui';
import { api, type ReciboPreview, type ReciboItem, type ReciboConfig, type Pago } from '@/lib/api';
import { formatCurrency, formatDate, cn } from '@/lib/utils';

interface ReciboPreviewModalProps {
    isOpen: boolean;
    onClose: () => void;
    pago: Pago | null;
}

export default function ReciboPreviewModal({
    isOpen,
    onClose,
    pago,
}: ReciboPreviewModalProps) {
    const { success, error } = useToast();
    const [preview, setPreview] = useState<ReciboPreview | null>(null);
    const [draft, setDraft] = useState<ReciboPreview | null>(null);
    const [loading, setLoading] = useState(false);
    const [downloading, setDownloading] = useState(false);
    const [editing, setEditing] = useState(false);
    const [pdfPreviewUrl, setPdfPreviewUrl] = useState<string | null>(null);
    const [pdfLoading, setPdfLoading] = useState(false);

    // Load preview
    useEffect(() => {
        if (pago && isOpen) {
            loadPreview();
        }
    }, [pago?.id, isOpen]);

    const loadPreview = async () => {
        if (!pago) return;
        setLoading(true);
        const res = await api.getReciboPreview(pago.id);
        if (res.ok && res.data) {
            setPreview(res.data);
            setDraft(res.data);
        } else {
            error(res.error || 'Error al cargar vista previa');
        }
        setLoading(false);
    };

    useEffect(() => {
        if (!isOpen) return;
        if (!editing) return;
        if (!draft) return;
        if (!pago) return;

        const handle = window.setTimeout(async () => {
            try {
                setPdfLoading(true);
                const payload = {
                    usuario: {
                        id: pago.usuario_id,
                        nombre: draft.usuario_nombre,
                        dni: draft.usuario_dni,
                        tipo_cuota: pago.tipo_cuota_nombre,
                    },
                    pago: {
                        monto: draft.total,
                        mes: pago.mes,
                        anio: pago.anio,
                        metodo_pago_id: pago.metodo_pago_id,
                        metodo_pago_nombre: draft.metodo_pago,
                    },
                    detalles: (draft.items || []).map((it) => ({
                        descripcion: it.descripcion,
                        cantidad: Number(it.cantidad) || 1,
                        precio_unitario: Number(it.precio) || 0,
                    })),
                    totales: {
                        subtotal: draft.subtotal,
                        total: draft.total,
                    },
                    branding: {
                        gym_name: draft.gym_nombre,
                        gym_address: draft.gym_direccion,
                        logo_url: draft.logo_url,
                    },
                    observaciones: draft.observaciones,
                    emitido_por: draft.emitido_por,
                    mostrar_logo: draft.mostrar_logo,
                    mostrar_metodo: draft.mostrar_metodo,
                    mostrar_dni: draft.mostrar_dni,
                    tipo_cuota_override: pago.tipo_cuota_nombre,
                };

                const res = await api.previewReceipt(payload);
                if (!res.ok || !res.data?.blob) return;
                const nextUrl = URL.createObjectURL(res.data.blob);
                setPdfPreviewUrl((prev) => {
                    if (prev) URL.revokeObjectURL(prev);
                    return nextUrl;
                });
            } finally {
                setPdfLoading(false);
            }
        }, 600);

        return () => window.clearTimeout(handle);
    }, [isOpen, editing, draft, pago]);

    useEffect(() => {
        if (!isOpen) return;
        return () => {
            setPdfPreviewUrl((prev) => {
                if (prev) URL.revokeObjectURL(prev);
                return null;
            });
        };
    }, [isOpen]);

    const handleDownload = async () => {
        if (!pago) return;
        setDownloading(true);
        const res = await api.downloadReciboPDF(pago.id);
        setDownloading(false);
        if (res.ok && res.data?.pdf_url) {
            window.open(res.data.pdf_url, '_blank');
            success('PDF generado');
        } else {
            error(res.error || 'Error al generar PDF');
        }
    };

    const handlePrint = async () => {
        if (!pago) return;
        try {
            const res = await api.downloadReciboPDF(pago.id);
            if (res.ok && res.data?.pdf_url) {
                const iframe = document.createElement('iframe');
                iframe.style.position = 'fixed';
                iframe.style.right = '0';
                iframe.style.bottom = '0';
                iframe.style.width = '0';
                iframe.style.height = '0';
                iframe.style.border = '0';
                iframe.src = res.data.pdf_url;
                document.body.appendChild(iframe);

                const cleanup = () => {
                    try {
                        document.body.removeChild(iframe);
                    } catch {
                    }
                };

                iframe.onload = () => {
                    try {
                        iframe.contentWindow?.focus();
                        iframe.contentWindow?.print();
                    } catch {
                    } finally {
                        window.setTimeout(cleanup, 1200);
                    }
                };
                return;
            }
            error(res.error || 'Error al generar PDF');
        } catch {
            error('Error al imprimir');
        }
    };

    if (!isOpen || !pago) return null;

    const data = draft || preview;

    const recalcTotals = (items: ReciboItem[]) => {
        const subtotal = items.reduce((acc, it) => acc + (Number(it.cantidad) || 0) * (Number(it.precio) || 0), 0);
        return { subtotal, total: subtotal };
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title="Vista Previa de Recibo"
            size={editing ? 'full' : 'lg'}
            footer={
                <>
                    <Button variant="secondary" onClick={onClose}>
                        Cerrar
                    </Button>
                    <Button
                        variant="secondary"
                        leftIcon={<Settings className="w-4 h-4" />}
                        onClick={() => setEditing((v) => !v)}
                    >
                        {editing ? 'Cerrar editor' : 'Editar'}
                    </Button>
                    <Button
                        variant="secondary"
                        leftIcon={<Printer className="w-4 h-4" />}
                        onClick={handlePrint}
                    >
                        Imprimir
                    </Button>
                    <Button
                        leftIcon={<Download className="w-4 h-4" />}
                        onClick={handleDownload}
                        isLoading={downloading}
                    >
                        Descargar PDF
                    </Button>
                </>
            }
        >
            {loading ? (
                <div className="text-center py-8 text-slate-500">Cargando...</div>
            ) : data ? (
                <div className={cn(editing ? 'grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-4' : '')}>
                    {editing && (
                        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4 space-y-4 max-h-[70vh] overflow-auto">
                            <div className="space-y-2">
                                <div className="text-sm font-medium text-slate-200">Contenido</div>
                                <Input
                                    label="Título"
                                    value={data.titulo || ''}
                                    onChange={(e) => setDraft((prev) => prev ? ({ ...prev, titulo: e.target.value }) : prev)}
                                />
                                <Input
                                    label="Gimnasio"
                                    value={data.gym_nombre || ''}
                                    onChange={(e) => setDraft((prev) => prev ? ({ ...prev, gym_nombre: e.target.value }) : prev)}
                                />
                                <Input
                                    label="Dirección"
                                    value={data.gym_direccion || ''}
                                    onChange={(e) => setDraft((prev) => prev ? ({ ...prev, gym_direccion: e.target.value }) : prev)}
                                />
                                <Input
                                    label="Observaciones"
                                    value={data.observaciones || ''}
                                    onChange={(e) => setDraft((prev) => prev ? ({ ...prev, observaciones: e.target.value }) : prev)}
                                />
                                <Input
                                    label="Emitido por"
                                    value={data.emitido_por || ''}
                                    onChange={(e) => setDraft((prev) => prev ? ({ ...prev, emitido_por: e.target.value }) : prev)}
                                />
                            </div>

                            <div className="space-y-2">
                                <div className="text-sm font-medium text-slate-200">Visibilidad</div>
                                <label className="flex items-center gap-2 text-sm text-slate-300">
                                    <input
                                        type="checkbox"
                                        checked={!!data.mostrar_logo}
                                        onChange={(e) => setDraft((prev) => prev ? ({ ...prev, mostrar_logo: e.target.checked }) : prev)}
                                    />
                                    Mostrar logo
                                </label>
                                <label className="flex items-center gap-2 text-sm text-slate-300">
                                    <input
                                        type="checkbox"
                                        checked={!!data.mostrar_dni}
                                        onChange={(e) => setDraft((prev) => prev ? ({ ...prev, mostrar_dni: e.target.checked }) : prev)}
                                    />
                                    Mostrar DNI
                                </label>
                                <label className="flex items-center gap-2 text-sm text-slate-300">
                                    <input
                                        type="checkbox"
                                        checked={!!data.mostrar_metodo}
                                        onChange={(e) => setDraft((prev) => prev ? ({ ...prev, mostrar_metodo: e.target.checked }) : prev)}
                                    />
                                    Mostrar método de pago
                                </label>
                            </div>

                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <div className="text-sm font-medium text-slate-200">Items</div>
                                    <Button
                                        size="sm"
                                        variant="secondary"
                                        leftIcon={<Plus className="w-4 h-4" />}
                                        onClick={() => {
                                            const nextItems = [...(data.items || []), { descripcion: 'Pago', cantidad: 1, precio: 0 }];
                                            const totals = recalcTotals(nextItems);
                                            setDraft((prev) => prev ? ({ ...prev, items: nextItems, ...totals }) : prev);
                                        }}
                                    >
                                        Agregar
                                    </Button>
                                </div>

                                <div className="space-y-3">
                                    {(data.items || []).map((item, idx) => (
                                        <div key={idx} className="rounded-lg border border-slate-800 p-3 space-y-2">
                                            <Input
                                                label="Descripción"
                                                value={item.descripcion}
                                                onChange={(e) => {
                                                    const nextItems = (data.items || []).map((it, i) => i === idx ? ({ ...it, descripcion: e.target.value }) : it);
                                                    const totals = recalcTotals(nextItems);
                                                    setDraft((prev) => prev ? ({ ...prev, items: nextItems, ...totals }) : prev);
                                                }}
                                            />
                                            <div className="grid grid-cols-2 gap-2">
                                                <Input
                                                    label="Cantidad"
                                                    type="number"
                                                    value={String(item.cantidad)}
                                                    onChange={(e) => {
                                                        const n = Number(e.target.value);
                                                        const nextItems = (data.items || []).map((it, i) => i === idx ? ({ ...it, cantidad: Number.isFinite(n) ? n : 1 }) : it);
                                                        const totals = recalcTotals(nextItems);
                                                        setDraft((prev) => prev ? ({ ...prev, items: nextItems, ...totals }) : prev);
                                                    }}
                                                />
                                                <Input
                                                    label="Precio"
                                                    type="number"
                                                    value={String(item.precio)}
                                                    onChange={(e) => {
                                                        const n = Number(e.target.value);
                                                        const nextItems = (data.items || []).map((it, i) => i === idx ? ({ ...it, precio: Number.isFinite(n) ? n : 0 }) : it);
                                                        const totals = recalcTotals(nextItems);
                                                        setDraft((prev) => prev ? ({ ...prev, items: nextItems, ...totals }) : prev);
                                                    }}
                                                />
                                            </div>
                                            <div className="flex justify-end">
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    leftIcon={<Trash2 className="w-4 h-4" />}
                                                    onClick={() => {
                                                        const nextItems = (data.items || []).filter((_, i) => i !== idx);
                                                        const totals = recalcTotals(nextItems);
                                                        setDraft((prev) => prev ? ({ ...prev, items: nextItems, ...totals }) : prev);
                                                    }}
                                                >
                                                    Quitar
                                                </Button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="rounded-lg border border-slate-800 p-3 text-sm text-slate-300">
                                <div className="flex items-center justify-between">
                                    <span>Subtotal</span>
                                    <span>{formatCurrency(data.subtotal)}</span>
                                </div>
                                <div className="flex items-center justify-between font-medium">
                                    <span>Total</span>
                                    <span>{formatCurrency(data.total)}</span>
                                </div>
                            </div>
                        </div>
                    )}

                    <div className="space-y-4">
                        <div className="bg-white text-black rounded-lg p-6 print:p-0" id="recibo-preview">
                    {/* Header */}
                    <div className="flex items-center justify-between border-b border-gray-200 pb-4 mb-4">
                        <div>
                            {data.mostrar_logo && (
                                <div className="w-16 h-16 bg-gray-200 rounded-lg mb-2 flex items-center justify-center text-gray-500 text-xs overflow-hidden">
                                    {data.logo_url ? (
                                        <img src={data.logo_url} alt="Logo" className="w-full h-full object-contain bg-white" />
                                    ) : (
                                        <>Logo</>
                                    )}
                                </div>
                            )}
                            <h2 className="text-xl font-bold">{data.gym_nombre}</h2>
                            {data.gym_direccion && (
                                <p className="text-gray-600 text-sm">{data.gym_direccion}</p>
                            )}
                        </div>
                        <div className="text-right">
                            <h1 className="text-2xl font-bold text-gray-800">{data.titulo || 'RECIBO'}</h1>
                            {data.numero && (
                                <p className="text-gray-600 font-mono">N° {data.numero}</p>
                            )}
                            <p className="text-gray-600">{data.fecha}</p>
                        </div>
                    </div>

                    {/* Customer info */}
                    <div className="mb-6">
                        <h3 className="font-semibold text-gray-700">Cliente</h3>
                        <p className="text-lg">{data.usuario_nombre}</p>
                        {data.mostrar_dni && data.usuario_dni && (
                            <p className="text-gray-600">DNI: {data.usuario_dni}</p>
                        )}
                    </div>

                    {/* Items */}
                    <table className="w-full mb-6">
                        <thead>
                            <tr className="border-b-2 border-gray-200">
                                <th className="text-left py-2">Descripción</th>
                                <th className="text-center py-2 w-20">Cant.</th>
                                <th className="text-right py-2 w-28">Precio</th>
                                <th className="text-right py-2 w-28">Subtotal</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data.items.map((item, idx) => (
                                <tr key={idx} className="border-b border-gray-100">
                                    <td className="py-2">{item.descripcion}</td>
                                    <td className="text-center py-2">{item.cantidad}</td>
                                    <td className="text-right py-2">{formatCurrency(item.precio)}</td>
                                    <td className="text-right py-2">{formatCurrency(item.cantidad * item.precio)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>

                    {/* Totals */}
                    <div className="flex justify-end">
                        <div className="w-64">
                            <div className="flex justify-between py-2 border-b border-gray-100">
                                <span>Subtotal</span>
                                <span>{formatCurrency(data.subtotal)}</span>
                            </div>
                            <div className="flex justify-between py-2 font-bold text-lg">
                                <span>Total</span>
                                <span>{formatCurrency(data.total)}</span>
                            </div>
                        </div>
                    </div>

                    {/* Payment method */}
                    {data.mostrar_metodo && data.metodo_pago && (
                        <div className="mt-4 text-gray-600">
                            Método de pago: <strong>{data.metodo_pago}</strong>
                        </div>
                    )}

                    {/* Notes */}
                    {data.observaciones && (
                        <div className="mt-4 p-3 bg-gray-50 rounded text-sm text-gray-600">
                            {data.observaciones}
                        </div>
                    )}

                    {/* Footer */}
                    <div className="mt-8 pt-4 border-t border-gray-200 text-center text-gray-500 text-sm">
                        {data.emitido_por && <p>Emitido por: {data.emitido_por}</p>}
                        <p>Gracias por su preferencia</p>
                    </div>
                        </div>

                        {editing && (
                            <div className="bg-slate-950 rounded-lg border border-slate-800 overflow-hidden">
                                <div className="flex items-center justify-between px-3 py-2 border-b border-slate-800">
                                    <div className="text-sm text-slate-200">Vista previa PDF</div>
                                    <div className="text-xs text-slate-500">{pdfLoading ? 'Generando...' : (pdfPreviewUrl ? 'Listo' : '—')}</div>
                                </div>
                                <div className="h-[420px] bg-slate-900">
                                    {pdfPreviewUrl ? (
                                        <iframe src={pdfPreviewUrl} className="w-full h-full" />
                                    ) : (
                                        <div className="h-full flex items-center justify-center text-slate-500 text-sm">
                                            Edita el recibo para generar el PDF
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            ) : (
                <div className="text-center py-8 text-slate-500">
                    No se pudo cargar la vista previa
                </div>
            )}
        </Modal>
    );
}

// Config modal component
interface ReciboConfigModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export function ReciboConfigModal({ isOpen, onClose }: ReciboConfigModalProps) {
    const { success, error } = useToast();
    const [config, setConfig] = useState<Partial<ReciboConfig>>({
        prefijo: 'REC',
        separador: '-',
        numero_inicial: 1,
        longitud_numero: 6,
        reiniciar_anual: false,
        incluir_anio: true,
        incluir_mes: false,
    });
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [nextNumber, setNextNumber] = useState<string>('');

    useEffect(() => {
        if (isOpen) {
            loadConfig();
            loadNextNumber();
        }
    }, [isOpen]);

    const loadConfig = async () => {
        setLoading(true);
        const res = await api.getReciboConfig();
        if (res.ok && res.data) {
            setConfig({
                prefijo: res.data.prefijo || 'REC',
                separador: res.data.separador || '-',
                numero_inicial: res.data.numero_inicial || 1,
                longitud_numero: res.data.longitud_numero || 6,
                reiniciar_anual: res.data.reiniciar_anual ?? false,
                incluir_anio: res.data.incluir_anio ?? true,
                incluir_mes: res.data.incluir_mes ?? false,
            });
        }
        setLoading(false);
    };

    const loadNextNumber = async () => {
        const res = await api.getNextReciboNumber();
        if (res.ok && res.data) {
            setNextNumber(res.data.numero);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        const res = await api.updateReciboConfig(config);
        setSaving(false);
        if (res.ok) {
            success('Configuración guardada');
            loadNextNumber();
        } else {
            error(res.error || 'Error al guardar');
        }
    };

    // Preview number format
    const previewNumber = () => {
        const parts: string[] = [];
        if (config.prefijo) parts.push(config.prefijo);
        if (config.incluir_anio) parts.push(new Date().getFullYear().toString());
        if (config.incluir_mes) parts.push(String(new Date().getMonth() + 1).padStart(2, '0'));
        parts.push(String(config.numero_inicial || 1).padStart(config.longitud_numero || 6, '0'));
        return parts.join(config.separador || '-');
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title="Configuración de Recibos"
            size="md"
            footer={
                <>
                    <Button variant="secondary" onClick={onClose}>
                        Cancelar
                    </Button>
                    <Button onClick={handleSave} isLoading={saving}>
                        Guardar
                    </Button>
                </>
            }
        >
            {loading ? (
                <div className="text-center py-8 text-slate-500">Cargando...</div>
            ) : (
                <div className="space-y-4">
                    {/* Preview */}
                    <div className="p-4 rounded-lg bg-slate-800 border border-slate-700 text-center">
                        <div className="text-xs text-slate-500 mb-1">Vista previa del próximo número</div>
                        <div className="text-xl font-mono font-bold text-white">{previewNumber()}</div>
                        {nextNumber && (
                            <div className="text-xs text-slate-500 mt-1">Actual: {nextNumber}</div>
                        )}
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <Input
                            label="Prefijo"
                            value={config.prefijo || ''}
                            onChange={(e) => setConfig({ ...config, prefijo: e.target.value })}
                            placeholder="REC"
                        />
                        <Input
                            label="Separador"
                            value={config.separador || ''}
                            onChange={(e) => setConfig({ ...config, separador: e.target.value })}
                            placeholder="-"
                            maxLength={1}
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <Input
                            label="Número inicial"
                            type="number"
                            value={config.numero_inicial || ''}
                            onChange={(e) => setConfig({ ...config, numero_inicial: Number(e.target.value) })}
                            min={1}
                        />
                        <Input
                            label="Longitud número"
                            type="number"
                            value={config.longitud_numero || ''}
                            onChange={(e) => setConfig({ ...config, longitud_numero: Number(e.target.value) })}
                            min={1}
                            max={10}
                        />
                    </div>

                    <div className="space-y-2">
                        <label className="flex items-center gap-2 text-sm text-slate-300">
                            <input
                                type="checkbox"
                                checked={config.incluir_anio}
                                onChange={(e) => setConfig({ ...config, incluir_anio: e.target.checked })}
                            />
                            Incluir año en el número
                        </label>
                        <label className="flex items-center gap-2 text-sm text-slate-300">
                            <input
                                type="checkbox"
                                checked={config.incluir_mes}
                                onChange={(e) => setConfig({ ...config, incluir_mes: e.target.checked })}
                            />
                            Incluir mes en el número
                        </label>
                        <label className="flex items-center gap-2 text-sm text-slate-300">
                            <input
                                type="checkbox"
                                checked={config.reiniciar_anual}
                                onChange={(e) => setConfig({ ...config, reiniciar_anual: e.target.checked })}
                            />
                            Reiniciar numeración cada año
                        </label>
                    </div>
                </div>
            )}
        </Modal>
    );
}

