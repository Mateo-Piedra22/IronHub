'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    X,
    User,
    Calendar,
    Copy,
    Phone,
    Mail,
    Edit,
    Trash2,
    CheckCircle2,
    XCircle,
    Tag,
    Flag,
    FileText,
    History,
    QrCode,
    Dumbbell,
    Clock,
    Plus,
    Save,
    MessageSquare,
    DollarSign,
    UserCheck,
    UserMinus,
    Loader2,
    FileDown,
    RefreshCw,
} from 'lucide-react';
import { Button, Modal, ConfirmModal, Input, useToast } from '@/components/ui';
import { api, type Usuario, type Etiqueta, type Estado, type Pago, type EstadoTemplate, type Asistencia } from '@/lib/api';
import { formatDate, formatCurrency, getWhatsAppLink, cn } from '@/lib/utils';

interface UserSidebarProps {
    usuario: Usuario | null;
    isOpen: boolean;
    onClose: () => void;
    onEdit: (usuario: Usuario) => void;
    onDelete: (usuario: Usuario) => void;
    onToggleActivo: (usuario: Usuario) => void;
    onRefresh: () => void;
    onOpenPagoModal?: (usuario: Usuario) => void;
    onCreateRutina?: (usuario: Usuario) => void;
}

type TabType = 'resumen' | 'notas' | 'etiquetas' | 'estados';

export default function UserSidebar({
    usuario,
    isOpen,
    onClose,
    onEdit,
    onDelete,
    onToggleActivo,
    onRefresh,
    onOpenPagoModal,
    onCreateRutina,
}: UserSidebarProps) {
    const { success, error } = useToast();
    const [activeTab, setActiveTab] = useState<TabType>('notas');

    // Notas
    const [notas, setNotas] = useState('');
    const [notasSaving, setNotasSaving] = useState(false);
    const notasTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const copyMenuRef = useRef<HTMLDetailsElement | null>(null);

    // Etiquetas
    const [etiquetas, setEtiquetas] = useState<Etiqueta[]>([]);
    const [etiquetaInput, setEtiquetaInput] = useState('');
    const [etiquetaSuggestions, setEtiquetaSuggestions] = useState<string[]>([]);
    const [etiquetaFilter, setEtiquetaFilter] = useState('');

    // Estados
    const [estados, setEstados] = useState<Estado[]>([]);
    const [estadoTemplates, setEstadoTemplates] = useState<EstadoTemplate[]>([]);
    const [estadoForm, setEstadoForm] = useState({ nombre: '', descripcion: '', fecha_vencimiento: '' });
    const [estadoFilter, setEstadoFilter] = useState('');
    const [showExpiredEstados, setShowExpiredEstados] = useState(true);

    // Historial pagos
    const [pagos, setPagos] = useState<Pago[]>([]);

    // Asistencias list
    const [asistencias, setAsistencias] = useState<Asistencia[]>([]);

    // Asistencia state
    const [asistencias30d, setAsistencias30d] = useState<number>(0);
    const [hasAsistenciaHoy, setHasAsistenciaHoy] = useState(false);
    const [asistenciasHoyCount, setAsistenciasHoyCount] = useState(0);
    const [asistenciaLoading, setAsistenciaLoading] = useState(false);
    const [allowMultipleAsistenciasDia, setAllowMultipleAsistenciasDia] = useState(false);

    const [asistenciasModalOpen, setAsistenciasModalOpen] = useState(false);
    const [asistenciasModalLoading, setAsistenciasModalLoading] = useState(false);
    const [asistenciasModalItems, setAsistenciasModalItems] = useState<Asistencia[]>([]);
    const [asistenciasModalTotal, setAsistenciasModalTotal] = useState(0);
    const [asistenciasModalPage, setAsistenciasModalPage] = useState(1);
    const asistenciasModalPageSize = 50;
    const [asistenciasModalDesde, setAsistenciasModalDesde] = useState('');
    const [asistenciasModalHasta, setAsistenciasModalHasta] = useState('');
    const [asistenciasModalQ, setAsistenciasModalQ] = useState('');
    const [asistenciaDeleteConfirm, setAsistenciaDeleteConfirm] = useState<{ open: boolean; asistencia_id?: number }>({ open: false });

    // QR Modal
    const [qrModalOpen, setQrModalOpen] = useState(false);
    const [qrToken, setQrToken] = useState<string | null>(null);
    const [qrLoading, setQrLoading] = useState(false);
    const [qrStatus, setQrStatus] = useState<'waiting' | 'used' | 'expired'>('waiting');
    const qrPollRef = useRef<NodeJS.Timeout | null>(null);

    // Rutina
    const [rutinaActiva, setRutinaActiva] = useState<{ id: number; nombre_rutina: string; dias_semana: number; activa: boolean } | null>(null);

    // Load data when usuario changes
    useEffect(() => {
        if (usuario && isOpen) {
            setNotas(usuario.notas || '');
            loadEtiquetas();
            loadEstados();
            loadPagos();
            loadSuggestions();
            loadEstadoTemplates();
            void (async () => {
                try {
                    const res = await api.getGymData();
                    if (res.ok && res.data) {
                        setAllowMultipleAsistenciasDia(Boolean((res.data as any).attendance_allow_multiple_per_day));
                    }
                } catch {
                }
            })();
            loadAsistenciaStatus();
            loadRutinaActiva();
        }
        // Cleanup QR polling on unmount
        return () => {
            if (qrPollRef.current) clearInterval(qrPollRef.current);
        };
    }, [usuario?.id, isOpen]);

    const loadRutinaActiva = async () => {
        if (!usuario) return;
        const res = await api.getRutinas({ usuario_id: usuario.id });
        if (res.ok && res.data?.rutinas) {
            const activa = res.data.rutinas.find((r: any) => r.activa) as { id: number; nombre_rutina: string; dias_semana: number; activa: boolean } | undefined;
            setRutinaActiva(activa || null);
        } else {
            setRutinaActiva(null);
        }
    };

    const loadEtiquetas = async () => {
        if (!usuario) return;
        const res = await api.getEtiquetas(usuario.id);
        if (res.ok && res.data) {
            setEtiquetas(res.data.etiquetas);
        }
    };

    const loadEstados = async () => {
        if (!usuario) return;
        const res = await api.getEstados(usuario.id);
        if (res.ok && res.data) {
            setEstados(res.data.estados);
        }
    };

    const loadPagos = async () => {
        if (!usuario) return;
        const res = await api.getPagos({ usuario_id: usuario.id, limit: 10 });
        if (res.ok && res.data) {
            setPagos(res.data.pagos);
        }
    };

    const loadAsistenciaStatus = async () => {
        if (!usuario) return;
        try {
            const hoy = new Date().toISOString().split('T')[0];
            const todayRes = await api.getAsistencias({ usuario_id: usuario.id, desde: hoy, hasta: hoy, limit: 1 });
            if (todayRes.ok && todayRes.data) {
                const c = Number(todayRes.data.total || todayRes.data.asistencias?.length || 0);
                setAsistenciasHoyCount(c);
                setHasAsistenciaHoy(c > 0);
            }
            // Load recent 30d attendance count
            const recentRes = await api.getUserAsistencias(usuario.id, 200);
            if (recentRes.ok && recentRes.data) {
                setAsistencias(recentRes.data.asistencias || []);
                const thirtyDaysAgo = new Date();
                thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
                const recent = recentRes.data.asistencias.filter((a: Asistencia) => {
                    const fecha = new Date(a.fecha);
                    return fecha >= thirtyDaysAgo;
                });
                setAsistencias30d(recent.length);
            }
        } catch (e) {
            // Silently fail
        }
    };

    const handleCopy = async (value: string | number | null | undefined, label: string) => {
        if (value === null || value === undefined || String(value).trim() === '') {
            error(`${label} no disponible`);
            return;
        }
        try {
            await navigator.clipboard.writeText(String(value));
            success(`${label} copiado`);
        } catch {
            error(`No se pudo copiar ${label}`);
        }
    };

    const goTo = (path: string) => {
        window.location.href = path;
    };

    const loadSuggestions = async () => {
        const res = await api.getEtiquetasSuggestions();
        if (res.ok && res.data) {
            setEtiquetaSuggestions(res.data.etiquetas);
        }
    };

    const loadEstadoTemplates = async () => {
        const res = await api.getEstadoTemplates();
        if (res.ok && res.data) {
            setEstadoTemplates(res.data.templates);
        }
    };

    // Auto-save notas
    const saveNotas = useCallback(async (value: string) => {
        if (!usuario) return;
        setNotasSaving(true);
        const res = await api.updateUsuarioNotas(usuario.id, value);
        setNotasSaving(false);
        if (res.ok) {
            // Silent success
        } else {
            error('Error al guardar notas');
        }
    }, [usuario, error]);

    const handleNotasChange = (value: string) => {
        setNotas(value);
        // Debounce auto-save
        if (notasTimeoutRef.current) {
            clearTimeout(notasTimeoutRef.current);
        }
        notasTimeoutRef.current = setTimeout(() => {
            saveNotas(value);
        }, 1500);
    };

    const handleSaveNotasNow = async () => {
        if (notasTimeoutRef.current) {
            clearTimeout(notasTimeoutRef.current);
        }
        await saveNotas(notas);
        success('Notas guardadas');
    };

    // Etiquetas
    const handleAddEtiqueta = async () => {
        if (!usuario || !etiquetaInput.trim()) return;
        const res = await api.addEtiqueta(usuario.id, etiquetaInput.trim());
        if (res.ok) {
            setEtiquetaInput('');
            loadEtiquetas();
        } else {
            error(res.error || 'Error al agregar etiqueta');
        }
    };

    const handleDeleteEtiqueta = async (etiquetaId: number) => {
        if (!usuario) return;
        const res = await api.deleteEtiqueta(usuario.id, etiquetaId);
        if (res.ok) {
            loadEtiquetas();
        } else {
            error(res.error || 'Error al eliminar etiqueta');
        }
    };

    // Estados
    const handleAddEstado = async () => {
        if (!usuario || !estadoForm.nombre.trim()) return;
        const res = await api.addEstado(usuario.id, {
            nombre: estadoForm.nombre.trim(),
            descripcion: estadoForm.descripcion || undefined,
            fecha_vencimiento: estadoForm.fecha_vencimiento || undefined,
        });
        if (res.ok) {
            setEstadoForm({ nombre: '', descripcion: '', fecha_vencimiento: '' });
            loadEstados();
        } else {
            error(res.error || 'Error al agregar estado');
        }
    };

    const handleDeleteEstado = async (estadoId: number) => {
        if (!usuario) return;
        const res = await api.deleteEstado(usuario.id, estadoId);
        if (res.ok) {
            loadEstados();
        } else {
            error(res.error || 'Error al eliminar estado');
        }
    };

    // QR - Generate token and start polling
    const handleGenerateQR = async () => {
        if (!usuario) return;
        setQrLoading(true);
        setQrStatus('waiting');

        // Clear any existing poll
        if (qrPollRef.current) clearInterval(qrPollRef.current);

        const res = await api.createCheckinToken(usuario.id, 5);
        setQrLoading(false);

        if (res.ok && res.data) {
            setQrToken(res.data.token);
            setQrModalOpen(true);

            // Start polling for token status
            qrPollRef.current = setInterval(async () => {
                if (!res.data?.token) return;
                const statusRes = await api.getCheckinTokenStatus(res.data.token);
                if (statusRes.ok && statusRes.data) {
                    if (statusRes.data.used) {
                        setQrStatus('used');
                        setHasAsistenciaHoy(true);
                        if (qrPollRef.current) clearInterval(qrPollRef.current);
                        success('¡Asistencia registrada!');
                        onRefresh();
                        loadAsistenciaStatus();
                    } else if (statusRes.data.expired) {
                        setQrStatus('expired');
                        if (qrPollRef.current) clearInterval(qrPollRef.current);
                    }
                }
            }, 2000);
        } else {
            error(res.error || 'Error al generar QR');
        }
    };

    const handleCloseQRModal = () => {
        setQrModalOpen(false);
        if (qrPollRef.current) clearInterval(qrPollRef.current);
        setQrToken(null);
    };

    // Asistencia manual - toggle based on current state
    const handleToggleAsistencia = async () => {
        if (!usuario) return;
        setAsistenciaLoading(true);

        try {
            if (allowMultipleAsistenciasDia) {
                const res = await api.createAsistencia(usuario.id);
                if (res.ok) {
                    success('Asistencia registrada');
                    onRefresh();
                    loadAsistenciaStatus();
                } else {
                    error(res.error || 'Error al registrar asistencia');
                }
                return;
            }

            if (hasAsistenciaHoy) {
                const res = await api.deleteAsistencia(usuario.id);
                if (res.ok) {
                    success('Asistencia de hoy eliminada');
                    setHasAsistenciaHoy(false);
                    onRefresh();
                    loadAsistenciaStatus();
                } else {
                    error(res.error || 'Error al eliminar asistencia');
                }
            } else {
                const res = await api.createAsistencia(usuario.id);
                if (res.ok) {
                    success('Asistencia registrada');
                    setHasAsistenciaHoy(true);
                    onRefresh();
                    loadAsistenciaStatus();
                } else {
                    error(res.error || 'Error al registrar asistencia');
                }
            }
        } finally {
            setAsistenciaLoading(false);
        }

    };

    const loadAsistenciasModal = useCallback(async () => {
        if (!usuario) return;
        setAsistenciasModalLoading(true);
        try {
            const today = new Date().toISOString().split('T')[0];
            const desde = asistenciasModalDesde || new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
            const hasta = asistenciasModalHasta || today;
            const res = await api.getAsistencias({
                usuario_id: usuario.id,
                desde,
                hasta,
                q: asistenciasModalQ || undefined,
                page: asistenciasModalPage,
                limit: asistenciasModalPageSize,
            });
            if (res.ok && res.data) {
                setAsistenciasModalItems(res.data.asistencias || []);
                setAsistenciasModalTotal(Number(res.data.total || 0));
            }
        } finally {
            setAsistenciasModalLoading(false);
        }
    }, [usuario?.id, asistenciasModalDesde, asistenciasModalHasta, asistenciasModalQ, asistenciasModalPage]);

    useEffect(() => {
        if (!asistenciasModalOpen) return;
        loadAsistenciasModal();
    }, [asistenciasModalOpen, loadAsistenciasModal]);

    // Filter etiquetas
    const filteredEtiquetas = etiquetas.filter(e =>
        e.nombre.toLowerCase().includes(etiquetaFilter.toLowerCase())
    );

    // Filter estados
    const filteredEstados = estados.filter(e => {
        const matchesFilter = e.nombre.toLowerCase().includes(estadoFilter.toLowerCase());
        if (!showExpiredEstados && e.fecha_vencimiento) {
            const isExpired = new Date(e.fecha_vencimiento) < new Date();
            if (isExpired) return false;
        }
        return matchesFilter;
    });

    // Suggestions not already added
    const availableSuggestions = etiquetaSuggestions.filter(
        s => !etiquetas.some(e => e.nombre.toLowerCase() === s.toLowerCase())
    );

    if (!isOpen || !usuario) return null;

    return (
        <>
            <motion.div
                initial={{ opacity: 0, x: 300 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 300 }}
                className="fixed right-0 top-0 h-full w-[480px] max-w-full bg-slate-900 border-l border-slate-800 z-50 flex flex-col min-h-0 overflow-hidden"
            >
                {/* Header */}
                <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div
                            className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium"
                            style={{ backgroundColor: `hsl(${usuario.id * 37 % 360}, 60%, 35%)` }}
                        >
                            {usuario.nombre.charAt(0).toUpperCase()}
                        </div>
                        <div>
                            <h3 className="font-semibold text-white">{usuario.nombre}</h3>
                            {usuario.dni && <p className="text-xs text-slate-500">DNI: {usuario.dni}</p>}
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="flex-1 min-h-0 overflow-y-auto">
                {/* Stats Cards */}
                <div className="grid grid-cols-2 gap-3 p-4">
                    <div className="card p-3">
                        <div className="text-xs text-slate-500">Estado</div>
                        <div className={cn(
                            'font-semibold',
                            usuario.activo ? 'text-success-400' : 'text-danger-400'
                        )}>
                            {usuario.activo ? 'Activo' : 'Inactivo'}
                        </div>
                    </div>
                    <div className="card p-3">
                        <div className="text-xs text-slate-500">Vencimiento</div>
                        <div className="font-semibold text-white">
                            {usuario.fecha_proximo_vencimiento
                                ? formatDate(usuario.fecha_proximo_vencimiento)
                                : '—'}
                        </div>
                    </div>
                    <div className="card p-3">
                        <div className="text-xs text-slate-500">Cuotas vencidas</div>
                        <div className={cn(
                            'font-semibold',
                            (usuario.cuotas_vencidas || 0) > 0 ? 'text-danger-400' : 'text-white'
                        )}>
                            {usuario.cuotas_vencidas || 0}
                        </div>
                    </div>
                    <div className="card p-3">
                        <div className="text-xs text-slate-500">Tipo cuota</div>
                        <div className="font-semibold text-white truncate">
                            {usuario.tipo_cuota_nombre || '—'}
                        </div>
                    </div>
                </div>

                {/* Contact Info */}
                <div className="px-4 pb-4 space-y-2">
                    {usuario.telefono && (
                        <a
                            href={getWhatsAppLink(usuario.telefono)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-2 text-sm text-primary-400 hover:text-primary-300"
                        >
                            <Phone className="w-4 h-4" />
                            {usuario.telefono}
                        </a>
                    )}
                    {usuario.email && (
                        <a
                            href={`mailto:${usuario.email}`}
                            className="flex items-center gap-2 text-sm text-slate-400 hover:text-white"
                        >
                            <Mail className="w-4 h-4" />
                            {usuario.email}
                        </a>
                    )}
                </div>

                {/* Rutina Actual */}
                <div className="px-4 pb-4 border-b border-slate-800">
                    <h4 className="text-xs font-medium text-slate-500 mb-2">Rutina Actual</h4>
                    {rutinaActiva ? (
                        <div className="bg-slate-900 rounded-lg p-3">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="font-medium text-white">{rutinaActiva.nombre_rutina}</p>
                                    <p className="text-xs text-slate-400">{rutinaActiva.dias_semana} día(s) por semana</p>
                                </div>
                                <Button
                                    size="sm"
                                    variant="secondary"
                                    onClick={() => window.open(api.getRutinaExcelUrl(rutinaActiva.id), '_blank')}
                                >
                                    <FileDown className="w-3 h-3 mr-1" />
                                    Excel
                                </Button>
                            </div>
                        </div>
                    ) : (
                        <p className="text-xs text-slate-500">Sin rutina activa asignada</p>
                    )}
                </div>

                {/* Quick Actions */}
                <div className="px-4 pb-4">
                    <h4 className="text-xs font-medium text-slate-500 mb-2">Acciones rápidas</h4>
                    <div className="space-y-3">
                        <div>
                            <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wide mb-2">Gestión</div>
                            <div className="flex flex-wrap gap-2">
                                <Button size="sm" variant="secondary" onClick={() => onEdit(usuario)}>
                                    <Edit className="w-3 h-3 mr-1" />
                                    Editar
                                </Button>
                                <Button
                                    size="sm"
                                    variant="secondary"
                                    onClick={() => {
                                        onRefresh();
                                        loadAsistenciaStatus();
                                        loadPagos();
                                    }}
                                >
                                    <RefreshCw className="w-3 h-3 mr-1" />
                                    Actualizar
                                </Button>
                                <Button size="sm" variant="secondary" onClick={() => goTo(`/gestion/pagos?usuario_id=${usuario.id}`)}>
                                    <DollarSign className="w-3 h-3 mr-1" />
                                    Ver pagos
                                </Button>
                                <Button size="sm" variant="secondary" onClick={() => goTo(`/gestion/asistencias?usuario_id=${usuario.id}`)}>
                                    <Clock className="w-3 h-3 mr-1" />
                                    Ver asistencias
                                </Button>
                                <Button size="sm" variant="secondary" onClick={() => goTo(`/gestion/rutinas?usuario_id=${usuario.id}`)}>
                                    <Dumbbell className="w-3 h-3 mr-1" />
                                    Ver rutinas
                                </Button>
                                <Button size="sm" variant="secondary" onClick={() => onToggleActivo(usuario)}>
                                    {usuario.activo ? <XCircle className="w-3 h-3 mr-1" /> : <CheckCircle2 className="w-3 h-3 mr-1" />}
                                    {usuario.activo ? 'Desactivar' : 'Activar'}
                                </Button>
                                <Button size="sm" variant="danger" onClick={() => onDelete(usuario)}>
                                    <Trash2 className="w-3 h-3 mr-1" />
                                    Eliminar
                                </Button>
                            </div>
                        </div>

                        {(onOpenPagoModal || onCreateRutina || rutinaActiva) && (
                            <div>
                                <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wide mb-2">Acciones</div>
                                <div className="flex flex-wrap gap-2">
                                    {onOpenPagoModal && (
                                        <Button size="sm" variant="secondary" onClick={() => onOpenPagoModal(usuario)}>
                                            <DollarSign className="w-3 h-3 mr-1" />
                                            Registrar pago
                                        </Button>
                                    )}
                                    {onCreateRutina && (
                                        <Button size="sm" variant="secondary" onClick={() => onCreateRutina(usuario)}>
                                            <Dumbbell className="w-3 h-3 mr-1" />
                                            Crear rutina
                                        </Button>
                                    )}
                                    {rutinaActiva && (
                                        <Button
                                            size="sm"
                                            variant="secondary"
                                            onClick={() => window.open(api.getRutinaExcelUrl(rutinaActiva.id), '_blank')}
                                        >
                                            <FileDown className="w-3 h-3 mr-1" />
                                            Rutina Excel
                                        </Button>
                                    )}
                                </div>
                            </div>
                        )}

                        <div>
                            <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wide mb-2">Comunicación</div>
                            <div className="flex flex-wrap gap-2">
                                <Button
                                    size="sm"
                                    variant="secondary"
                                    onClick={() => {
                                        if (!usuario.telefono) {
                                            error('Teléfono no disponible');
                                            return;
                                        }
                                        window.open(getWhatsAppLink(usuario.telefono), '_blank');
                                    }}
                                >
                                    <MessageSquare className="w-3 h-3 mr-1" />
                                    WhatsApp
                                </Button>
                                <Button
                                    size="sm"
                                    variant="secondary"
                                    onClick={() => {
                                        if (!usuario.email) {
                                            error('Email no disponible');
                                            return;
                                        }
                                        window.location.href = `mailto:${usuario.email}`;
                                    }}
                                >
                                    <Mail className="w-3 h-3 mr-1" />
                                    Email
                                </Button>
                            </div>
                        </div>

                        <div>
                            <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wide mb-2">Asistencia</div>
                            <div className="text-xs text-slate-500 mb-2">
                                Hoy: <span className="text-slate-300 font-medium">{asistenciasHoyCount}</span> · Últ. 30d:{' '}
                                <span className="text-slate-300 font-medium">{asistencias30d}</span>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                <Button size="sm" variant="secondary" onClick={handleGenerateQR} isLoading={qrLoading}>
                                    <QrCode className="w-3 h-3 mr-1" />
                                    Emitir QR
                                </Button>
                                <Button
                                    size="sm"
                                    variant={allowMultipleAsistenciasDia ? 'primary' : hasAsistenciaHoy ? 'danger' : 'primary'}
                                    onClick={handleToggleAsistencia}
                                    isLoading={asistenciaLoading}
                                >
                                    {allowMultipleAsistenciasDia ? (
                                        <>
                                            <UserCheck className="w-3 h-3 mr-1" />
                                            Registrar asistencia
                                        </>
                                    ) : hasAsistenciaHoy ? (
                                        <>
                                            <UserMinus className="w-3 h-3 mr-1" />
                                            Quitar asistencia
                                        </>
                                    ) : (
                                        <>
                                            <UserCheck className="w-3 h-3 mr-1" />
                                            Registrar asistencia
                                        </>
                                    )}
                                </Button>
                                <Button
                                    size="sm"
                                    variant="secondary"
                                    onClick={() => {
                                        const today = new Date().toISOString().split('T')[0];
                                        const thirtyDaysAgo = new Date();
                                        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
                                        setAsistenciasModalDesde(thirtyDaysAgo.toISOString().slice(0, 10));
                                        setAsistenciasModalHasta(today);
                                        setAsistenciasModalQ('');
                                        setAsistenciasModalPage(1);
                                        setAsistenciasModalOpen(true);
                                    }}
                                >
                                    <History className="w-3 h-3 mr-1" />
                                    Ver asistencias
                                </Button>
                            </div>
                        </div>

                        <div>
                            <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wide mb-2">Copiar</div>
                            <details ref={copyMenuRef} className="relative inline-block">
                                <summary className="cursor-pointer list-none [&::-webkit-details-marker]:hidden">
                                    <div className="inline-flex items-center justify-center px-3 py-2 text-sm rounded-lg gap-2 bg-slate-800 border border-slate-700 text-slate-200 hover:bg-slate-700 hover:border-slate-600 transition-colors active:scale-[0.98]">
                                        <Copy className="w-3.5 h-3.5" />
                                        Copiar datos
                                    </div>
                                </summary>
                                <div className="absolute left-0 mt-2 w-56 rounded-xl border border-slate-700 bg-slate-900 shadow-elevated p-1 z-50">
                                    <button
                                        type="button"
                                        className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-200 hover:bg-slate-800"
                                        onClick={() => {
                                            handleCopy(usuario.id, 'ID');
                                            if (copyMenuRef.current) copyMenuRef.current.open = false;
                                        }}
                                    >
                                        <User className="w-3.5 h-3.5 text-slate-400" />
                                        Copiar ID
                                    </button>
                                    <button
                                        type="button"
                                        className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-200 hover:bg-slate-800"
                                        onClick={() => {
                                            handleCopy(usuario.nombre, 'Nombre');
                                            if (copyMenuRef.current) copyMenuRef.current.open = false;
                                        }}
                                    >
                                        <User className="w-3.5 h-3.5 text-slate-400" />
                                        Copiar nombre
                                    </button>
                                    <button
                                        type="button"
                                        className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-200 hover:bg-slate-800"
                                        onClick={() => {
                                            handleCopy(usuario.dni || '', 'DNI');
                                            if (copyMenuRef.current) copyMenuRef.current.open = false;
                                        }}
                                    >
                                        <FileText className="w-3.5 h-3.5 text-slate-400" />
                                        Copiar DNI
                                    </button>
                                    <button
                                        type="button"
                                        className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-200 hover:bg-slate-800"
                                        onClick={() => {
                                            handleCopy(usuario.email || '', 'Email');
                                            if (copyMenuRef.current) copyMenuRef.current.open = false;
                                        }}
                                    >
                                        <Mail className="w-3.5 h-3.5 text-slate-400" />
                                        Copiar email
                                    </button>
                                    <button
                                        type="button"
                                        className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-200 hover:bg-slate-800"
                                        onClick={() => {
                                            handleCopy(usuario.tipo_cuota_nombre || '', 'Tipo de cuota');
                                            if (copyMenuRef.current) copyMenuRef.current.open = false;
                                        }}
                                    >
                                        <DollarSign className="w-3.5 h-3.5 text-slate-400" />
                                        Copiar cuota
                                    </button>
                                    <button
                                        type="button"
                                        className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-200 hover:bg-slate-800"
                                        onClick={() => {
                                            handleCopy(usuario.telefono || '', 'Teléfono');
                                            if (copyMenuRef.current) copyMenuRef.current.open = false;
                                        }}
                                    >
                                        <Phone className="w-3.5 h-3.5 text-slate-400" />
                                        Copiar tel.
                                    </button>
                                </div>
                            </details>
                        </div>
                    </div>
                    {/* Attendance stat */}
                    <div className="mt-2 text-xs text-slate-500">
                        Asistencias (30 días): <span className="font-medium text-white">{asistencias30d}</span>
                    </div>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-slate-800 px-4">
                    {[
                        { id: 'resumen', label: 'Resumen', icon: History },
                        { id: 'notas', label: 'Notas', icon: FileText },
                        { id: 'etiquetas', label: 'Etiquetas', icon: Tag },
                        { id: 'estados', label: 'Estados', icon: Flag },
                    ].map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id as TabType)}
                            className={cn(
                                'flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors',
                                activeTab === tab.id
                                    ? 'text-primary-400 border-primary-400'
                                    : 'text-slate-500 border-transparent hover:text-white'
                            )}
                        >
                            <tab.icon className="w-3.5 h-3.5" />
                            {tab.label}
                        </button>
                    ))}
                </div>

                {/* Tab Content */}
                <div className="flex-1 overflow-y-auto p-4">
                    {activeTab === 'resumen' && (
                        <div className="space-y-4">
                            <div>
                                <h4 className="text-xs font-medium text-slate-500 mb-2">Pagos recientes</h4>
                                <div className="space-y-2">
                                    {pagos.slice(0, 8).map((p) => (
                                        <div key={p.id} className="flex items-center justify-between rounded-lg bg-slate-800 border border-slate-700 px-3 py-2">
                                            <div className="text-sm text-white">{formatDate(p.fecha)}</div>
                                            <div className="text-sm text-slate-300">{formatCurrency(p.monto)}</div>
                                        </div>
                                    ))}
                                    {pagos.length === 0 && (
                                        <p className="text-sm text-slate-500">Sin pagos registrados</p>
                                    )}
                                </div>
                            </div>

                            <div>
                                <h4 className="text-xs font-medium text-slate-500 mb-2">Asistencias recientes</h4>
                                <div className="space-y-2">
                                    {asistencias.slice(0, 8).map((a) => (
                                        <div key={a.id} className="flex items-center justify-between rounded-lg bg-slate-800 border border-slate-700 px-3 py-2">
                                            <div className="text-sm text-white">{formatDate(a.fecha)}</div>
                                            <div className="text-xs text-slate-400">{a.hora || a.hora_entrada || '—'}</div>
                                        </div>
                                    ))}
                                    {asistencias.length === 0 && (
                                        <p className="text-sm text-slate-500">Sin asistencias registradas</p>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}

                    {activeTab === 'notas' && (
                        <div className="space-y-3">
                            <textarea
                                value={notas}
                                onChange={(e) => handleNotasChange(e.target.value)}
                                placeholder="Apunta comentarios, lesiones, preferencias, objetivos..."
                                className="w-full h-40 bg-slate-800 border border-slate-700 rounded-lg p-3 text-white text-sm resize-none focus:outline-none focus:border-primary-500"
                            />
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-slate-500">{notas.length} caracteres</span>
                                <div className="flex items-center gap-2">
                                    {notasSaving && (
                                        <span className="text-xs text-slate-500">Guardando...</span>
                                    )}
                                    <Button size="sm" onClick={handleSaveNotasNow}>
                                        <Save className="w-3 h-3 mr-1" />
                                        Guardar
                                    </Button>
                                </div>
                            </div>
                        </div>
                    )}

                    {activeTab === 'etiquetas' && (
                        <div className="space-y-4">
                            <div className="flex gap-2">
                                <Input
                                    value={etiquetaInput}
                                    onChange={(e) => setEtiquetaInput(e.target.value)}
                                    placeholder="Nueva etiqueta..."
                                    onKeyDown={(e) => e.key === 'Enter' && handleAddEtiqueta()}
                                />
                                <Button onClick={handleAddEtiqueta}>
                                    <Plus className="w-4 h-4" />
                                </Button>
                            </div>
                            <Input
                                value={etiquetaFilter}
                                onChange={(e) => setEtiquetaFilter(e.target.value)}
                                placeholder="Filtrar etiquetas..."
                            />
                            {availableSuggestions.length > 0 && (
                                <div>
                                    <p className="text-xs text-slate-500 mb-2">Sugerencias:</p>
                                    <div className="flex flex-wrap gap-2">
                                        {availableSuggestions.slice(0, 5).map((s) => (
                                            <button
                                                key={s}
                                                onClick={() => setEtiquetaInput(s)}
                                                className="px-2 py-1 text-xs bg-slate-800 border border-slate-700 rounded-full hover:bg-slate-700"
                                            >
                                                {s}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                            <div className="flex flex-wrap gap-2">
                                {filteredEtiquetas.map((e) => (
                                    <div
                                        key={e.id}
                                        className="flex items-center gap-1 px-2 py-1 bg-primary-500/20 text-primary-400 rounded-full text-sm"
                                    >
                                        <span>{e.nombre}</span>
                                        <button
                                            onClick={() => handleDeleteEtiqueta(e.id)}
                                            className="hover:text-primary-300"
                                        >
                                            <X className="w-3 h-3" />
                                        </button>
                                    </div>
                                ))}
                                {filteredEtiquetas.length === 0 && (
                                    <p className="text-sm text-slate-500">Sin etiquetas</p>
                                )}
                            </div>
                        </div>
                    )}

                    {activeTab === 'estados' && (
                        <div className="space-y-4">
                            <div className="space-y-2">
                                <select
                                    value={estadoForm.nombre}
                                    onChange={(e) => setEstadoForm({ ...estadoForm, nombre: e.target.value })}
                                    className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-white text-sm"
                                >
                                    <option value="">Plantilla de estado...</option>
                                    {estadoTemplates.map((t) => (
                                        <option key={t.id} value={t.nombre}>{t.nombre}</option>
                                    ))}
                                </select>
                                <Input
                                    value={estadoForm.descripcion}
                                    onChange={(e) => setEstadoForm({ ...estadoForm, descripcion: e.target.value })}
                                    placeholder="Descripción (opcional)"
                                />
                                <div className="flex gap-2">
                                    <Input
                                        type="date"
                                        value={estadoForm.fecha_vencimiento}
                                        onChange={(e) => setEstadoForm({ ...estadoForm, fecha_vencimiento: e.target.value })}
                                    />
                                    <Button onClick={handleAddEstado}>
                                        <Plus className="w-4 h-4 mr-1" />
                                        Añadir
                                    </Button>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <Input
                                    value={estadoFilter}
                                    onChange={(e) => setEstadoFilter(e.target.value)}
                                    placeholder="Filtrar estados..."
                                />
                                <label className="flex items-center gap-1 text-xs text-slate-400 whitespace-nowrap">
                                    <input
                                        type="checkbox"
                                        checked={showExpiredEstados}
                                        onChange={(e) => setShowExpiredEstados(e.target.checked)}
                                    />
                                    Vencidos
                                </label>
                            </div>
                            <div className="space-y-2">
                                {filteredEstados.map((e) => {
                                    const isExpired = e.fecha_vencimiento && new Date(e.fecha_vencimiento) < new Date();
                                    return (
                                        <div
                                            key={e.id}
                                            className={cn(
                                                'flex items-center justify-between p-3 rounded-lg border',
                                                isExpired
                                                    ? 'bg-slate-800/50 border-slate-700 opacity-60'
                                                    : 'bg-slate-800 border-slate-700'
                                            )}
                                        >
                                            <div className="flex items-center gap-2">
                                                <div className="w-2 h-2 rounded-full bg-primary-500" />
                                                <div>
                                                    <div className="font-medium text-white">{e.nombre}</div>
                                                    {e.descripcion && (
                                                        <div className="text-xs text-slate-500">{e.descripcion}</div>
                                                    )}
                                                    {e.fecha_vencimiento && (
                                                        <div className="text-xs text-slate-500">
                                                            Vence: {formatDate(e.fecha_vencimiento)}
                                                            {isExpired && ' (vencido)'}
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                            <button
                                                onClick={() => handleDeleteEstado(e.id)}
                                                className="p-1 text-slate-400 hover:text-danger-400"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                    );
                                })}
                                {filteredEstados.length === 0 && (
                                    <p className="text-sm text-slate-500">Sin estados</p>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {/* Payment History */}
                <div className="border-t border-slate-800 p-4 max-h-[200px] overflow-y-auto">
                    <h4 className="text-xs font-medium text-slate-500 mb-2 flex items-center gap-1">
                        <History className="w-3 h-3" />
                        Historial de pagos
                    </h4>
                    <div className="space-y-2">
                        {pagos.map((p) => (
                            <div
                                key={p.id}
                                className="flex items-center justify-between text-sm py-1"
                            >
                                <span className="text-slate-400">
                                    {formatDate(p.fecha)}
                                </span>
                                <span className="text-white font-medium">
                                    {formatCurrency(p.monto)}
                                </span>
                            </div>
                        ))}
                        {pagos.length === 0 && (
                            <p className="text-sm text-slate-500">Sin pagos registrados</p>
                        )}
                    </div>
                </div>
                </div>
            </motion.div>

            {/* QR Modal */}
            <Modal
                isOpen={qrModalOpen}
                onClose={handleCloseQRModal}
                title="QR de Check-in"
                size="sm"
            >
                <div className="text-center space-y-4">
                    {qrToken && qrStatus === 'waiting' && (
                        <>
                            <div className="bg-white p-4 rounded-lg inline-block">
                                <img
                                    src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(qrToken)}`}
                                    alt="QR Code"
                                    className="w-48 h-48"
                                />
                            </div>
                            <div className="flex items-center justify-center gap-2 text-sm text-slate-400">
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Esperando que el usuario escanee...
                            </div>
                            <p className="text-xs text-slate-500">
                                El código expira en 5 minutos.
                            </p>
                        </>
                    )}
                    {qrStatus === 'used' && (
                        <>
                            <div className="w-16 h-16 mx-auto bg-success-500/20 rounded-full flex items-center justify-center">
                                <CheckCircle2 className="w-8 h-8 text-success-400" />
                            </div>
                            <p className="text-lg font-semibold text-success-400">
                                ¡Asistencia registrada!
                            </p>
                            <p className="text-sm text-slate-400">
                                El usuario escaneó el código correctamente.
                            </p>
                        </>
                    )}
                    {qrStatus === 'expired' && (
                        <>
                            <div className="w-16 h-16 mx-auto bg-danger-500/20 rounded-full flex items-center justify-center">
                                <XCircle className="w-8 h-8 text-danger-400" />
                            </div>
                            <p className="text-lg font-semibold text-danger-400">
                                Código expirado
                            </p>
                            <p className="text-sm text-slate-400">
                                Genera un nuevo código para intentar de nuevo.
                            </p>
                            <Button onClick={handleGenerateQR} isLoading={qrLoading}>
                                Generar nuevo QR
                            </Button>
                        </>
                    )}
                </div>
            </Modal>

            <Modal
                isOpen={asistenciasModalOpen}
                onClose={() => setAsistenciasModalOpen(false)}
                title={`Asistencias - ${usuario?.nombre || ''}`}
                size="xl"
                footer={
                    <div className="flex items-center justify-between w-full">
                        <div className="text-sm text-slate-400">
                            Total: <span className="text-slate-200 font-medium">{asistenciasModalTotal}</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <Button
                                variant="ghost"
                                onClick={() => setAsistenciasModalPage((p) => Math.max(1, p - 1))}
                                disabled={asistenciasModalPage <= 1}
                            >
                                Anterior
                            </Button>
                            <div className="text-xs text-slate-500">Página {asistenciasModalPage}</div>
                            <Button
                                variant="ghost"
                                onClick={() => setAsistenciasModalPage((p) => p + 1)}
                                disabled={asistenciasModalPage * asistenciasModalPageSize >= asistenciasModalTotal}
                            >
                                Siguiente
                            </Button>
                        </div>
                    </div>
                }
            >
                <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                        <Input
                            label="Desde"
                            type="date"
                            value={asistenciasModalDesde}
                            onChange={(e) => {
                                setAsistenciasModalPage(1);
                                setAsistenciasModalDesde(e.target.value);
                            }}
                        />
                        <Input
                            label="Hasta"
                            type="date"
                            value={asistenciasModalHasta}
                            onChange={(e) => {
                                setAsistenciasModalPage(1);
                                setAsistenciasModalHasta(e.target.value);
                            }}
                        />
                        <Input
                            label="Buscar"
                            value={asistenciasModalQ}
                            onChange={(e) => {
                                setAsistenciasModalPage(1);
                                setAsistenciasModalQ(e.target.value);
                            }}
                            placeholder="Nombre o DNI"
                        />
                        <div className="flex items-end gap-2">
                            <Button variant="secondary" onClick={loadAsistenciasModal} isLoading={asistenciasModalLoading}>
                                <RefreshCw className="w-4 h-4 mr-1" />
                                Refrescar
                            </Button>
                        </div>
                    </div>

                    <div className="rounded-xl border border-slate-800 overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="min-w-full text-sm">
                                <thead className="bg-slate-900/60">
                                    <tr className="text-left text-slate-400">
                                        <th className="px-4 py-3">Fecha</th>
                                        <th className="px-4 py-3">Hora</th>
                                        <th className="px-4 py-3">Usuario</th>
                                        <th className="px-4 py-3 text-right"></th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-800">
                                    {asistenciasModalLoading ? (
                                        <tr>
                                            <td className="px-4 py-6 text-slate-400" colSpan={4}>
                                                Cargando...
                                            </td>
                                        </tr>
                                    ) : asistenciasModalItems.length === 0 ? (
                                        <tr>
                                            <td className="px-4 py-6 text-slate-400" colSpan={4}>
                                                Sin asistencias para el filtro actual.
                                            </td>
                                        </tr>
                                    ) : (
                                        asistenciasModalItems.map((a) => (
                                            <tr key={a.id} className="text-slate-200">
                                                <td className="px-4 py-3">{String(a.fecha).slice(0, 10)}</td>
                                                <td className="px-4 py-3">{a.hora ? String(a.hora).slice(0, 8) : '—'}</td>
                                                <td className="px-4 py-3">{a.usuario_nombre || usuario?.nombre || ''}</td>
                                                <td className="px-4 py-3 text-right">
                                                    <Button
                                                        size="sm"
                                                        variant="danger"
                                                        onClick={() => setAsistenciaDeleteConfirm({ open: true, asistencia_id: a.id })}
                                                    >
                                                        <Trash2 className="w-4 h-4" />
                                                    </Button>
                                                </td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </Modal>

            <ConfirmModal
                isOpen={asistenciaDeleteConfirm.open}
                onClose={() => setAsistenciaDeleteConfirm({ open: false })}
                title="Eliminar asistencia"
                message="Esta acción no se puede deshacer."
                confirmText="Eliminar"
                cancelText="Cancelar"
                variant="danger"
                isLoading={asistenciaLoading}
                onConfirm={async () => {
                    if (!asistenciaDeleteConfirm.asistencia_id) return;
                    setAsistenciaLoading(true);
                    try {
                        const res = await api.deleteAsistenciaById(asistenciaDeleteConfirm.asistencia_id);
                        if (res.ok) {
                            success('Asistencia eliminada');
                            setAsistenciaDeleteConfirm({ open: false });
                            onRefresh();
                            loadAsistenciaStatus();
                            loadAsistenciasModal();
                        } else {
                            error(res.error || 'Error al eliminar asistencia');
                        }
                    } finally {
                        setAsistenciaLoading(false);
                    }
                }}
            />

            {/* Click outside to close */}
            <div
                className="fixed inset-0 bg-black/50 z-40"
                onClick={onClose}
            />
        </>
    );
}

