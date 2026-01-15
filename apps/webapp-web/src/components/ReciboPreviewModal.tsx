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
    const [loading, setLoading] = useState(false);
    const [downloading, setDownloading] = useState(false);

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
        } else {
            error(res.error || 'Error al cargar vista previa');
        }
        setLoading(false);
    };

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

    const handlePrint = () => {
        window.print();
    };

    if (!isOpen || !pago) return null;

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title="Vista Previa de Recibo"
            size="lg"
            footer={
                <>
                    <Button variant="secondary" onClick={onClose}>
                        Cerrar
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
            ) : preview ? (
                <div className="bg-white text-black rounded-lg p-6 print:p-0" id="recibo-preview">
                    {/* Header */}
                    <div className="flex items-center justify-between border-b border-gray-200 pb-4 mb-4">
                        <div>
                            {preview.mostrar_logo && (
                                <div className="w-16 h-16 bg-gray-200 rounded-lg mb-2 flex items-center justify-center text-gray-500 text-xs overflow-hidden">
                                    {preview.logo_url ? (
                                        <img src={preview.logo_url} alt="Logo" className="w-full h-full object-contain bg-white" />
                                    ) : (
                                        <>Logo</>
                                    )}
                                </div>
                            )}
                            <h2 className="text-xl font-bold">{preview.gym_nombre}</h2>
                            {preview.gym_direccion && (
                                <p className="text-gray-600 text-sm">{preview.gym_direccion}</p>
                            )}
                        </div>
                        <div className="text-right">
                            <h1 className="text-2xl font-bold text-gray-800">{preview.titulo || 'RECIBO'}</h1>
                            {preview.numero && (
                                <p className="text-gray-600 font-mono">N° {preview.numero}</p>
                            )}
                            <p className="text-gray-600">{preview.fecha}</p>
                        </div>
                    </div>

                    {/* Customer info */}
                    <div className="mb-6">
                        <h3 className="font-semibold text-gray-700">Cliente</h3>
                        <p className="text-lg">{preview.usuario_nombre}</p>
                        {preview.mostrar_dni && preview.usuario_dni && (
                            <p className="text-gray-600">DNI: {preview.usuario_dni}</p>
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
                            {preview.items.map((item, idx) => (
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
                                <span>{formatCurrency(preview.subtotal)}</span>
                            </div>
                            <div className="flex justify-between py-2 font-bold text-lg">
                                <span>Total</span>
                                <span>{formatCurrency(preview.total)}</span>
                            </div>
                        </div>
                    </div>

                    {/* Payment method */}
                    {preview.mostrar_metodo && preview.metodo_pago && (
                        <div className="mt-4 text-gray-600">
                            Método de pago: <strong>{preview.metodo_pago}</strong>
                        </div>
                    )}

                    {/* Notes */}
                    {preview.observaciones && (
                        <div className="mt-4 p-3 bg-gray-50 rounded text-sm text-gray-600">
                            {preview.observaciones}
                        </div>
                    )}

                    {/* Footer */}
                    <div className="mt-8 pt-4 border-t border-gray-200 text-center text-gray-500 text-sm">
                        {preview.emitido_por && <p>Emitido por: {preview.emitido_por}</p>}
                        <p>Gracias por su preferencia</p>
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

