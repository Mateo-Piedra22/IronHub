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
    CreditCard,
    KeyRound,
} from 'lucide-react';
import { Button, Modal, ConfirmModal, Input, useToast } from '@/components/ui';
import { api, type AccessCredential, type AccessDevice, type Usuario, type Etiqueta, type Estado, type Pago, type EstadoTemplate, type Asistencia, type Membership, type Sucursal, type UsuarioEntitlements } from '@/lib/api';
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

type TabType = 'resumen' | 'notas' | 'etiquetas' | 'estados' | 'membresia' | 'accesos' | 'credenciales';

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
    const [entitlementsModalOpen, setEntitlementsModalOpen] = useState(false);
    const [entitlementsSummaryLoading, setEntitlementsSummaryLoading] = useState(false);
    const [entitlementsSummary, setEntitlementsSummary] = useState<UsuarioEntitlements | null>(null);

    const [accessCreds, setAccessCreds] = useState<AccessCredential[]>([]);
    const [accessCredsLoading, setAccessCredsLoading] = useState(false);
    const [accessCredType, setAccessCredType] = useState<'fob' | 'card'>('fob');
    const [accessCredValue, setAccessCredValue] = useState('');
    const [accessCredLabel, setAccessCredLabel] = useState('');
    const [accessCredSaving, setAccessCredSaving] = useState(false);
    const [accessCredDelete, setAccessCredDelete] = useState<{ open: boolean; id?: number; label?: string | null }>({ open: false });
    const [enrollDevices, setEnrollDevices] = useState<AccessDevice[]>([]);
    const [enrollDevicesLoading, setEnrollDevicesLoading] = useState(false);
    const [enrollDeviceId, setEnrollDeviceId] = useState<string>('');
    const [enrollType, setEnrollType] = useState<'fob' | 'card'>('fob');
    const [enrollOverwrite, setEnrollOverwrite] = useState(true);
    const [enrollExpiresSeconds, setEnrollExpiresSeconds] = useState('90');
    const [enrollSaving, setEnrollSaving] = useState(false);

    // Notas
    const [notas, setNotas] = useState('');
    const [notasSaving, setNotasSaving] = useState(false);
    const notasTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const copyMenuRef = useRef<HTMLDetailsElement | null>(null);

    useEffect(() => {
        setEntitlementsSummary(null);
        setEntitlementsModalOpen(false);
        setEntitlementsSummaryLoading(false);
        setAccessCreds([]);
        setAccessCredType('fob');
        setAccessCredValue('');
        setAccessCredLabel('');
        setAccessCredDelete({ open: false });
        setEnrollDevices([]);
        setEnrollDeviceId('');
        setEnrollType('fob');
        setEnrollOverwrite(true);
        setEnrollExpiresSeconds('90');
    }, [usuario?.id]);

    const loadEnrollDevices = useCallback(async () => {
        setEnrollDevicesLoading(true);
        try {
            const res = await api.listAccessDevices();
            if (res.ok && res.data?.ok) {
                setEnrollDevices(res.data.items || []);
                if (!enrollDeviceId && (res.data.items || []).length > 0) {
                    setEnrollDeviceId(String((res.data.items || [])[0]?.id || ''));
                }
            } else {
                setEnrollDevices([]);
            }
        } finally {
            setEnrollDevicesLoading(false);
        }
    }, [enrollDeviceId]);

    useEffect(() => {
        if (!isOpen) return;
        if (activeTab !== 'credenciales') return;
        void loadEnrollDevices();
    }, [isOpen, activeTab, loadEnrollDevices]);

    useEffect(() => {
        if (!isOpen) return;
        if (activeTab !== 'credenciales') return;
        const t = setInterval(() => {
            void loadEnrollDevices();
        }, 2000);
        return () => clearInterval(t);
    }, [isOpen, activeTab, loadEnrollDevices]);

    const startEnrollment = useCallback(async () => {
        if (!usuario?.id) return;
        const did = Number(enrollDeviceId);
        if (!Number.isFinite(did) || did <= 0) return;
        const ms = enrollExpiresSeconds.trim();
        const exp = Number(ms);
        setEnrollSaving(true);
        try {
            const res = await api.startAccessDeviceEnrollment(did, {
                usuario_id: usuario.id,
                credential_type: enrollType,
                overwrite: enrollOverwrite,
                expires_seconds: Number.isFinite(exp) ? exp : 90,
            });
            if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo iniciar');
            success('Portal de enrolamiento iniciado');
        } catch (e) {
            error(e instanceof Error ? e.message : 'Error');
        } finally {
            setEnrollSaving(false);
        }
    }, [usuario?.id, enrollDeviceId, enrollType, enrollOverwrite, enrollExpiresSeconds, success, error]);

    const clearEnrollment = useCallback(async () => {
        const did = Number(enrollDeviceId);
        if (!Number.isFinite(did) || did <= 0) return;
        setEnrollSaving(true);
        try {
            const res = await api.clearAccessDeviceEnrollment(did);
            if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo cancelar');
            success('Portal cancelado');
        } catch (e) {
            error(e instanceof Error ? e.message : 'Error');
        } finally {
            setEnrollSaving(false);
        }
    }, [enrollDeviceId, success, error]);

    const loadAccessCreds = useCallback(async () => {
        if (!usuario?.id) return;
        setAccessCredsLoading(true);
        try {
            const res = await api.listAccessCredentials({ usuario_id: usuario.id });
            if (res.ok && res.data?.ok) {
                setAccessCreds(res.data.items || []);
            } else {
                setAccessCreds([]);
            }
        } finally {
            setAccessCredsLoading(false);
        }
    }, [usuario?.id]);

    useEffect(() => {
        void loadAccessCreds();
    }, [loadAccessCreds]);

    const createAccessCredential = useCallback(async () => {
        if (!usuario?.id) return;
        const v = accessCredValue.trim();
        if (!v) return;
        setAccessCredSaving(true);
        try {
            const res = await api.createAccessCredential({
                usuario_id: usuario.id,
                credential_type: accessCredType,
                value: v,
                label: accessCredLabel.trim() || null,
            });
            if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo crear');
            success('Credencial registrada');
            setAccessCredValue('');
            setAccessCredLabel('');
            await loadAccessCreds();
        } catch (e) {
            error(e instanceof Error ? e.message : 'Error');
        } finally {
            setAccessCredSaving(false);
        }
    }, [usuario?.id, accessCredValue, accessCredLabel, accessCredType, loadAccessCreds, success, error]);

    const deleteAccessCredential = useCallback(async () => {
        if (!accessCredDelete.id) return;
        setAccessCredSaving(true);
        try {
            const res = await api.deleteAccessCredential(accessCredDelete.id);
            if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo eliminar');
            success('Credencial desactivada');
            setAccessCredDelete({ open: false });
            await loadAccessCreds();
        } catch (e) {
            error(e instanceof Error ? e.message : 'Error');
        } finally {
            setAccessCredSaving(false);
        }
    }, [accessCredDelete.id, loadAccessCreds, success, error]);

    const loadEntitlementsSummary = useCallback(async () => {
        if (!usuario?.id) return;
        setEntitlementsSummaryLoading(true);
        try {
            const res = await api.getUsuarioEntitlementsSummaryGestion(usuario.id);
            if (res.ok && res.data) {
                setEntitlementsSummary(res.data);
            } else {
                setEntitlementsSummary(null);
            }
        } finally {
            setEntitlementsSummaryLoading(false);
        }
    }, [usuario?.id]);

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

    // Membresía / Pase libre
    const [membership, setMembership] = useState<Membership | null>(null);
    const [membershipAllowedSucursales, setMembershipAllowedSucursales] = useState<number[]>([]);
    const [sucursales, setSucursales] = useState<Sucursal[]>([]);
    const [membershipLoading, setMembershipLoading] = useState(false);
    const [membershipSaving, setMembershipSaving] = useState(false);
    const [membershipForm, setMembershipForm] = useState({
        plan_name: '',
        start_date: '',
        end_date: '',
        all_sucursales: true,
        sucursal_ids: [] as number[],
    });

    const [entitlementsLoading, setEntitlementsLoading] = useState(false);
    const [entitlementsSaving, setEntitlementsSaving] = useState(false);
    const [entitlementsSucursalMode, setEntitlementsSucursalMode] = useState<Record<number, { allow: 'none' | 'allow' | 'deny'; motivo: string }>>({});
    const [entitlementsClaseScope, setEntitlementsClaseScope] = useState<number | null>(null);
    const [entitlementsClaseTipoId, setEntitlementsClaseTipoId] = useState<number | null>(null);
    const [entitlementsClaseAllow, setEntitlementsClaseAllow] = useState<'allow' | 'deny'>('allow');
    const [entitlementsClaseMotivo, setEntitlementsClaseMotivo] = useState('');
    const [entitlementsClaseRules, setEntitlementsClaseRules] = useState<Array<{ sucursal_id: number | null; target_type: 'tipo_clase'; target_id: number; allow: boolean; motivo?: string }>>([]);
    const [claseTipos, setClaseTipos] = useState<Array<{ id: number; nombre: string; activo: boolean }>>([]);

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
            loadMembership();
            loadSucursales();
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

    useEffect(() => {
        if (!usuario || !isOpen) return;
        if (activeTab !== 'accesos') return;
        loadSucursales();
        loadClaseTipos();
        loadEntitlementsOverrides();
    }, [activeTab, usuario?.id, isOpen]);

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

    const loadSucursales = async () => {
        try {
            const res = await api.getSucursales();
            if (res.ok && res.data?.ok) {
                setSucursales(res.data.items || []);
            }
        } catch {
        }
    };

    const loadMembership = async () => {
        if (!usuario) return;
        setMembershipLoading(true);
        try {
            const res = await api.getUsuarioMembership(usuario.id);
            if (res.ok && res.data?.ok) {
                const m = res.data.membership || null;
                setMembership(m);
                const allowed = Array.isArray(res.data.sucursales) ? res.data.sucursales : [];
                setMembershipAllowedSucursales(allowed);
                setMembershipForm({
                    plan_name: (m?.plan_name || '') as string,
                    start_date: (m?.start_date || '') as string,
                    end_date: (m?.end_date || '') as string,
                    all_sucursales: m ? Boolean(m.all_sucursales) : true,
                    sucursal_ids: allowed,
                });
            } else {
                setMembership(null);
                setMembershipAllowedSucursales([]);
                setMembershipForm({
                    plan_name: '',
                    start_date: '',
                    end_date: '',
                    all_sucursales: true,
                    sucursal_ids: [],
                });
            }
        } finally {
            setMembershipLoading(false);
        }
    };

    const handleSaveMembership = async () => {
        if (!usuario) return;
        setMembershipSaving(true);
        try {
            const res = await api.setUsuarioMembership(usuario.id, {
                plan_name: membershipForm.plan_name || null,
                start_date: membershipForm.start_date || null,
                end_date: membershipForm.end_date || null,
                all_sucursales: Boolean(membershipForm.all_sucursales),
                sucursal_ids: Array.isArray(membershipForm.sucursal_ids) ? membershipForm.sucursal_ids : [],
            });
            if (res.ok && res.data?.ok) {
                success('Membresía guardada');
                loadMembership();
                onRefresh();
            } else {
                error(res.data?.error || 'Error al guardar membresía');
            }
        } catch {
            error('Error al guardar membresía');
        } finally {
            setMembershipSaving(false);
        }
    };

    const loadClaseTipos = async () => {
        try {
            const res = await api.getClaseTipos();
            if (res.ok && res.data?.tipos) {
                const items = (res.data.tipos || []).map((t: any) => ({ id: Number(t.id), nombre: String(t.nombre || ''), activo: Boolean(t.activo) }));
                setClaseTipos(items.filter((t) => Number.isFinite(t.id)));
            } else {
                setClaseTipos([]);
            }
        } catch {
            setClaseTipos([]);
        }
    };

    const loadEntitlementsOverrides = async () => {
        if (!usuario) return;
        setEntitlementsLoading(true);
        try {
            const res = await api.getUsuarioEntitlementsGestion(usuario.id);
            if (res.ok && res.data?.ok) {
                const next: Record<number, { allow: 'none' | 'allow' | 'deny'; motivo: string }> = {};
                const overrides = Array.isArray(res.data.branch_overrides) ? res.data.branch_overrides : [];
                overrides.forEach((o) => {
                    const sid = Number((o as any).sucursal_id);
                    if (!Number.isFinite(sid)) return;
                    next[sid] = { allow: (o.allow ? 'allow' : 'deny') as 'allow' | 'deny', motivo: String((o as any).motivo || '') };
                });
                setEntitlementsSucursalMode(next);
                const cr = Array.isArray(res.data.class_overrides) ? res.data.class_overrides : [];
                const rules = cr
                    .filter((r) => String((r as any).target_type || '').toLowerCase() === 'tipo_clase')
                    .map((r) => ({
                        sucursal_id: (r as any).sucursal_id ?? null,
                        target_type: 'tipo_clase' as const,
                        target_id: Number((r as any).target_id),
                        allow: Boolean((r as any).allow),
                        motivo: String((r as any).motivo || ''),
                    }))
                    .filter((r) => Number.isFinite(r.target_id));
                setEntitlementsClaseRules(rules);
            } else {
                setEntitlementsSucursalMode({});
                setEntitlementsClaseRules([]);
            }
        } catch {
            setEntitlementsSucursalMode({});
            setEntitlementsClaseRules([]);
        } finally {
            setEntitlementsLoading(false);
        }
    };

    const handleSaveEntitlementsOverrides = async () => {
        if (!usuario) return;
        setEntitlementsSaving(true);
        try {
            const branch_overrides = Object.entries(entitlementsSucursalMode || {})
                .filter(([_, v]) => v && v.allow !== 'none')
                .map(([sid, v]) => ({
                    sucursal_id: Number(sid),
                    allow: v.allow === 'allow',
                    motivo: v.motivo || undefined,
                    starts_at: null,
                    ends_at: null,
                }))
                .filter((x) => Number.isFinite(x.sucursal_id));

            const class_overrides = (entitlementsClaseRules || []).map((r) => ({
                sucursal_id: r.sucursal_id,
                target_type: r.target_type,
                target_id: r.target_id,
                allow: Boolean(r.allow),
                motivo: r.motivo || undefined,
                starts_at: null,
                ends_at: null,
            }));

            const res = await api.updateUsuarioEntitlementsGestion(usuario.id, { branch_overrides, class_overrides });
            if (res.ok && res.data?.ok) {
                success('Accesos guardados');
                loadEntitlementsOverrides();
                onRefresh();
            } else {
                error(res.error || 'Error al guardar accesos');
            }
        } catch {
            error('Error al guardar accesos');
        } finally {
            setEntitlementsSaving(false);
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
                        <button
                            type="button"
                            className="font-semibold text-white truncate text-left hover:underline"
                            onClick={() => {
                                setEntitlementsModalOpen(true);
                                if (!entitlementsSummary && !entitlementsSummaryLoading) {
                                    loadEntitlementsSummary();
                                }
                            }}
                        >
                            {usuario.tipo_cuota_nombre || '—'}
                        </button>
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

                        <div>
                            <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wide mb-2">Acceso</div>
                            <div className="text-xs text-slate-500 mb-2">
                                Llavero:{' '}
                                <span className="text-slate-300 font-medium">
                                    {accessCreds.filter((c) => c.active && c.credential_type === 'fob').length}
                                </span>
                                {' · '}
                                Tarjeta:{' '}
                                <span className="text-slate-300 font-medium">
                                    {accessCreds.filter((c) => c.active && c.credential_type === 'card').length}
                                </span>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                <Button size="sm" variant="secondary" onClick={() => setActiveTab('credenciales')}>
                                    <KeyRound className="w-3 h-3 mr-1" />
                                    Llavero/Tarjeta
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
                        { id: 'membresia', label: 'Membresía', icon: CreditCard },
                        { id: 'accesos', label: 'Accesos', icon: UserCheck },
                        { id: 'credenciales', label: 'Llavero/Tarjeta', icon: KeyRound },
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

                    {activeTab === 'membresia' && (
                        <div className="space-y-4">
                            <div className="rounded-lg bg-slate-800 border border-slate-700 px-3 py-2">
                                <div className="text-xs text-slate-500">Estado</div>
                                <div className="text-sm text-white">
                                    {membershipLoading
                                        ? 'Cargando...'
                                        : membership
                                            ? (membership.status || 'active')
                                            : 'Sin membresía'}
                                </div>
                            </div>

                            <Input
                                value={membershipForm.plan_name}
                                onChange={(e) => setMembershipForm({ ...membershipForm, plan_name: e.target.value })}
                                placeholder="Plan (ej. Pase libre)"
                            />

                            <div className="grid grid-cols-2 gap-2">
                                <Input
                                    type="date"
                                    value={membershipForm.start_date}
                                    onChange={(e) => setMembershipForm({ ...membershipForm, start_date: e.target.value })}
                                />
                                <Input
                                    type="date"
                                    value={membershipForm.end_date}
                                    onChange={(e) => setMembershipForm({ ...membershipForm, end_date: e.target.value })}
                                />
                            </div>

                            <label className="flex items-center gap-2 text-sm text-slate-300">
                                <input
                                    type="checkbox"
                                    checked={membershipForm.all_sucursales}
                                    onChange={(e) => {
                                        const checked = e.target.checked;
                                        setMembershipForm({
                                            ...membershipForm,
                                            all_sucursales: checked,
                                            sucursal_ids: checked ? [] : membershipForm.sucursal_ids,
                                        });
                                    }}
                                />
                                Pase libre (todas las sucursales)
                            </label>

                            {!membershipForm.all_sucursales && (
                                <div className="space-y-2">
                                    <div className="text-xs text-slate-500">Sucursales habilitadas</div>
                                    <div className="space-y-1">
                                        {sucursales.map((s) => {
                                            const checked = membershipForm.sucursal_ids.includes(s.id);
                                            return (
                                                <label key={s.id} className="flex items-center gap-2 text-sm text-slate-200">
                                                    <input
                                                        type="checkbox"
                                                        checked={checked}
                                                        onChange={(e) => {
                                                            const next = e.target.checked
                                                                ? Array.from(new Set([...membershipForm.sucursal_ids, s.id]))
                                                                : membershipForm.sucursal_ids.filter((x) => x !== s.id);
                                                            setMembershipForm({ ...membershipForm, sucursal_ids: next });
                                                        }}
                                                    />
                                                    <span>{s.nombre}</span>
                                                </label>
                                            );
                                        })}
                                        {sucursales.length === 0 && (
                                            <div className="text-sm text-slate-500">Sin sucursales</div>
                                        )}
                                    </div>
                                </div>
                            )}

                            <div className="flex items-center justify-end">
                                <Button size="sm" onClick={handleSaveMembership} disabled={membershipSaving || membershipLoading}>
                                    {membershipSaving && <Loader2 className="w-3 h-3 mr-1 animate-spin" />}
                                    Guardar
                                </Button>
                            </div>
                        </div>
                    )}

                    {activeTab === 'accesos' && (
                        <div className="space-y-4">
                            {entitlementsLoading ? (
                                <div className="text-sm text-slate-500">Cargando…</div>
                            ) : (
                                <>
                                    <div className="rounded-lg bg-slate-800 border border-slate-700 p-3 space-y-3">
                                        <div>
                                            <div className="text-xs font-medium text-slate-500">Overrides de sucursales</div>
                                            <div className="text-xs text-slate-500 mt-1">Permite o bloquea sucursales puntuales para este usuario.</div>
                                        </div>
                                        <div className="space-y-2">
                                            {sucursales.map((s) => {
                                                const row = entitlementsSucursalMode[s.id] || { allow: 'none' as const, motivo: '' };
                                                return (
                                                    <div key={s.id} className="flex flex-col gap-2 rounded-lg bg-slate-900/40 border border-slate-700 p-2">
                                                        <div className="flex items-center justify-between gap-2">
                                                            <div className="text-sm text-slate-200">{s.nombre}</div>
                                                            <select
                                                                className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1 text-sm text-slate-200"
                                                                value={row.allow}
                                                                onChange={(e) => {
                                                                    const v = e.target.value as 'none' | 'allow' | 'deny';
                                                                    setEntitlementsSucursalMode((prev) => ({
                                                                        ...prev,
                                                                        [s.id]: { allow: v, motivo: (prev[s.id]?.motivo || '') as string },
                                                                    }));
                                                                }}
                                                            >
                                                                <option value="none">Sin override</option>
                                                                <option value="allow">Permitir</option>
                                                                <option value="deny">Denegar</option>
                                                            </select>
                                                        </div>
                                                        {row.allow !== 'none' ? (
                                                            <Input
                                                                value={row.motivo}
                                                                onChange={(e) => {
                                                                    const v = e.target.value;
                                                                    setEntitlementsSucursalMode((prev) => ({
                                                                        ...prev,
                                                                        [s.id]: { allow: row.allow, motivo: v },
                                                                    }));
                                                                }}
                                                                placeholder="Motivo (opcional)"
                                                            />
                                                        ) : null}
                                                    </div>
                                                );
                                            })}
                                            {sucursales.length === 0 ? (
                                                <div className="text-sm text-slate-500">Sin sucursales</div>
                                            ) : null}
                                        </div>
                                    </div>

                                    <div className="rounded-lg bg-slate-800 border border-slate-700 p-3 space-y-3">
                                        <div>
                                            <div className="text-xs font-medium text-slate-500">Overrides de clases (por tipo)</div>
                                            <div className="text-xs text-slate-500 mt-1">Reglas puntuales para permitir o denegar tipos de clase.</div>
                                        </div>

                                        <div className="grid grid-cols-1 gap-2">
                                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                                <select
                                                    className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-2 text-sm text-slate-200"
                                                    value={entitlementsClaseScope === null ? '0' : String(entitlementsClaseScope)}
                                                    onChange={(e) => {
                                                        const v = e.target.value;
                                                        setEntitlementsClaseScope(v === '0' ? null : Number(v));
                                                    }}
                                                >
                                                    <option value="0">Todas las sucursales</option>
                                                    {sucursales.map((s) => (
                                                        <option key={s.id} value={String(s.id)}>
                                                            {s.nombre}
                                                        </option>
                                                    ))}
                                                </select>
                                                <select
                                                    className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-2 text-sm text-slate-200"
                                                    value={entitlementsClaseTipoId === null ? '' : String(entitlementsClaseTipoId)}
                                                    onChange={(e) => {
                                                        const v = e.target.value;
                                                        setEntitlementsClaseTipoId(v ? Number(v) : null);
                                                    }}
                                                >
                                                    <option value="">Tipo de clase…</option>
                                                    {claseTipos.filter((t) => t.activo).map((t) => (
                                                        <option key={t.id} value={String(t.id)}>
                                                            {t.nombre}
                                                        </option>
                                                    ))}
                                                </select>
                                            </div>

                                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                                <select
                                                    className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-2 text-sm text-slate-200"
                                                    value={entitlementsClaseAllow}
                                                    onChange={(e) => setEntitlementsClaseAllow(e.target.value as 'allow' | 'deny')}
                                                >
                                                    <option value="allow">Permitir</option>
                                                    <option value="deny">Denegar</option>
                                                </select>
                                                <Input
                                                    value={entitlementsClaseMotivo}
                                                    onChange={(e) => setEntitlementsClaseMotivo(e.target.value)}
                                                    placeholder="Motivo (opcional)"
                                                />
                                            </div>

                                            <div className="flex justify-end">
                                                <Button
                                                    size="sm"
                                                    onClick={() => {
                                                        if (!entitlementsClaseTipoId) return;
                                                        const rule = {
                                                            sucursal_id: entitlementsClaseScope,
                                                            target_type: 'tipo_clase' as const,
                                                            target_id: entitlementsClaseTipoId,
                                                            allow: entitlementsClaseAllow === 'allow',
                                                            motivo: entitlementsClaseMotivo || undefined,
                                                        };
                                                        setEntitlementsClaseRules((prev) => {
                                                            const next = prev.filter(
                                                                (r) =>
                                                                    !(r.target_type === 'tipo_clase' &&
                                                                        r.target_id === rule.target_id &&
                                                                        (r.sucursal_id ?? null) === (rule.sucursal_id ?? null))
                                                            );
                                                            next.unshift(rule);
                                                            return next;
                                                        });
                                                        setEntitlementsClaseMotivo('');
                                                    }}
                                                >
                                                    <Plus className="w-3 h-3 mr-1" />
                                                    Agregar
                                                </Button>
                                            </div>
                                        </div>

                                        <div className="space-y-2">
                                            {entitlementsClaseRules.map((r, idx) => {
                                                const scopeLabel = r.sucursal_id
                                                    ? (sucursales.find((s) => s.id === r.sucursal_id)?.nombre || `Sucursal ${r.sucursal_id}`)
                                                    : 'Todas las sucursales';
                                                const tipoLabel = claseTipos.find((t) => t.id === r.target_id)?.nombre || `Tipo ${r.target_id}`;
                                                return (
                                                    <div key={`${r.sucursal_id ?? 0}:${r.target_id}:${idx}`} className="flex items-center justify-between gap-2 rounded-lg bg-slate-900/40 border border-slate-700 px-3 py-2">
                                                        <div className="min-w-0">
                                                            <div className="text-sm text-slate-200 truncate">{tipoLabel}</div>
                                                            <div className="text-xs text-slate-500 truncate">
                                                                {scopeLabel} · {r.allow ? 'Permitir' : 'Denegar'}
                                                                {r.motivo ? ` · ${r.motivo}` : ''}
                                                            </div>
                                                        </div>
                                                        <button
                                                            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                                                            onClick={() => {
                                                                setEntitlementsClaseRules((prev) => prev.filter((_, i) => i !== idx));
                                                            }}
                                                        >
                                                            <Trash2 className="w-4 h-4" />
                                                        </button>
                                                    </div>
                                                );
                                            })}
                                            {entitlementsClaseRules.length === 0 ? (
                                                <div className="text-sm text-slate-500">Sin reglas.</div>
                                            ) : null}
                                        </div>
                                    </div>

                                    <div className="flex items-center justify-end">
                                        <Button size="sm" onClick={handleSaveEntitlementsOverrides} disabled={entitlementsSaving || entitlementsLoading}>
                                            {entitlementsSaving && <Loader2 className="w-3 h-3 mr-1 animate-spin" />}
                                            Guardar
                                        </Button>
                                    </div>
                                </>
                            )}
                        </div>
                    )}

                    {activeTab === 'credenciales' && (
                        <div className="space-y-4">
                            <div className="rounded-lg bg-slate-800 border border-slate-700 p-3 space-y-3">
                                <div>
                                    <div className="text-xs font-medium text-slate-500">Registrar (Access Agent)</div>
                                    <div className="text-xs text-slate-500 mt-1">
                                        Seleccioná un device con sucursal y habilitá el modo enrolamiento. Luego, en el Access Agent de ese device, escaneá la credencial una sola vez.
                                    </div>
                                </div>
                                {enrollDevicesLoading ? (
                                    <div className="text-sm text-slate-500">Cargando devices…</div>
                                ) : (
                                    <>
                                        <select
                                            className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-2 text-sm text-slate-200"
                                            value={enrollDeviceId}
                                            onChange={(e) => setEnrollDeviceId(e.target.value)}
                                        >
                                            {enrollDevices.map((d) => (
                                                <option key={d.id} value={String(d.id)}>
                                                    {d.name} {d.sucursal_id ? `(Sucursal #${d.sucursal_id})` : '(Sin sucursal)'}
                                                </option>
                                            ))}
                                        </select>
                                        {(() => {
                                            const d = enrollDevices.find((x) => String(x.id) === String(enrollDeviceId));
                                            if (!d) return null;
                                            const ls = (d as any).last_seen_at ? String((d as any).last_seen_at) : '';
                                            const t = ls ? Date.parse(ls) : NaN;
                                            const online = Number.isFinite(t) ? Date.now() - t < 90_000 : false;
                                            const cfg: any = (d as any).config && typeof (d as any).config === 'object' ? (d as any).config : {};
                                            const em = cfg?.enroll_mode && typeof cfg.enroll_mode === 'object' ? cfg.enroll_mode : null;
                                            const rt = cfg?.runtime_status && typeof cfg.runtime_status === 'object' ? cfg.runtime_status : null;
                                            const rtAt = rt?.updated_at ? Date.parse(String(rt.updated_at)) : NaN;
                                            const rtFresh = Number.isFinite(rtAt) ? Date.now() - rtAt < 20_000 : false;
                                            const ready = Boolean(rt?.enroll_ready) && rtFresh;
                                            const lt = rt?.last_test && typeof rt.last_test === 'object' ? rt.last_test : null;
                                            const ltLabel = lt?.kind ? String(lt.kind) : '';
                                            const ltAt = lt?.at ? String(lt.at) : '';
                                            const ltOk = lt ? Boolean(lt.ok) : false;
                                            return (
                                                <div className="text-xs text-slate-500">
                                                    Estado: {online ? 'online' : 'offline'}
                                                    {ls ? ` · last_seen ${ls}` : ''}
                                                    {em?.enabled ? ` · enroll activo (#${em.usuario_id} ${String(em.credential_type || '').toUpperCase()})` : ''}
                                                    {ready ? ' · ready' : ''}
                                                    {ltLabel ? ` · last_test ${ltLabel} ${ltOk ? 'ok' : 'fail'} ${ltAt ? `@ ${ltAt}` : ''}` : ''}
                                                </div>
                                            );
                                        })()}
                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                            <select
                                                className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-2 text-sm text-slate-200"
                                                value={enrollType}
                                                onChange={(e) => setEnrollType(e.target.value as 'fob' | 'card')}
                                            >
                                                <option value="fob">Llavero</option>
                                                <option value="card">Tarjeta</option>
                                            </select>
                                            <Input
                                                value={enrollExpiresSeconds}
                                                onChange={(e) => setEnrollExpiresSeconds(e.target.value)}
                                                placeholder="Expira (seg) ej 90"
                                            />
                                        </div>
                                        <label className="flex items-center gap-2 text-sm text-slate-300">
                                            <input type="checkbox" checked={enrollOverwrite} onChange={(e) => setEnrollOverwrite(e.target.checked)} />
                                            Sobrescribir (desactiva credenciales previas del mismo tipo)
                                        </label>
                                        <div className="flex items-center justify-between gap-2">
                                            <Button size="sm" variant="secondary" onClick={loadEnrollDevices} disabled={enrollSaving}>
                                                <RefreshCw className="w-3 h-3 mr-1" />
                                                Refrescar
                                            </Button>
                                            <div className="flex gap-2">
                                                <Button size="sm" variant="danger" onClick={clearEnrollment} disabled={enrollSaving || !enrollDeviceId}>
                                                    Cancelar
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    onClick={startEnrollment}
                                                    disabled={
                                                        enrollSaving ||
                                                        !enrollDeviceId ||
                                                        !(enrollDevices.find((d) => String(d.id) === String(enrollDeviceId))?.sucursal_id)
                                                    }
                                                >
                                                    {enrollSaving && <Loader2 className="w-3 h-3 mr-1 animate-spin" />}
                                                    Iniciar
                                                </Button>
                                            </div>
                                        </div>
                                        {enrollDeviceId && !(enrollDevices.find((d) => String(d.id) === String(enrollDeviceId))?.sucursal_id) ? (
                                            <div className="text-xs text-amber-400">
                                                Este device no tiene sucursal vinculada. Vinculalo primero para habilitar el portal.
                                            </div>
                                        ) : (
                                            <div className="text-xs text-slate-500">
                                                Si el device no está online, el portal no va a quedar listo.
                                            </div>
                                        )}
                                    </>
                                )}
                            </div>

                            <div className="rounded-lg bg-slate-800 border border-slate-700 p-3 space-y-3">
                                <div>
                                    <div className="text-xs font-medium text-slate-500">Carga manual</div>
                                    <div className="text-xs text-slate-500 mt-1">Pegá/escaneá el valor para registrar una credencial directo.</div>
                                </div>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                    <select
                                        className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-2 text-sm text-slate-200"
                                        value={accessCredType}
                                        onChange={(e) => setAccessCredType(e.target.value as 'fob' | 'card')}
                                    >
                                        <option value="fob">Llavero</option>
                                        <option value="card">Tarjeta</option>
                                    </select>
                                    <Input
                                        value={accessCredLabel}
                                        onChange={(e) => setAccessCredLabel(e.target.value)}
                                        placeholder="Etiqueta (opcional)"
                                    />
                                </div>
                                <Input
                                    value={accessCredValue}
                                    onChange={(e) => setAccessCredValue(e.target.value)}
                                    placeholder="Escaneá / pegá la credencial…"
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter') void createAccessCredential();
                                    }}
                                />
                                <div className="flex justify-end">
                                    <Button size="sm" onClick={createAccessCredential} disabled={accessCredSaving || !accessCredValue.trim()}>
                                        {accessCredSaving ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Plus className="w-3 h-3 mr-1" />}
                                        Agregar
                                    </Button>
                                </div>
                            </div>

                            <div className="rounded-lg bg-slate-800 border border-slate-700 p-3 space-y-2">
                                <div className="flex items-center justify-between">
                                    <div className="text-xs font-medium text-slate-500">Registradas</div>
                                    <Button size="sm" variant="secondary" onClick={loadAccessCreds} disabled={accessCredsLoading}>
                                        <RefreshCw className={`w-3 h-3 ${accessCredsLoading ? 'animate-spin' : ''}`} />
                                    </Button>
                                </div>
                                {accessCredsLoading ? (
                                    <div className="text-sm text-slate-500">Cargando…</div>
                                ) : accessCreds.length === 0 ? (
                                    <div className="text-sm text-slate-500">Sin credenciales.</div>
                                ) : (
                                    <div className="space-y-2">
                                        {accessCreds.map((c) => (
                                            <div
                                                key={c.id}
                                                className="flex items-center justify-between gap-2 rounded-lg bg-slate-900/40 border border-slate-700 px-3 py-2"
                                            >
                                                <div className="min-w-0">
                                                    <div className="text-sm text-slate-200 truncate">{c.label || c.credential_type}</div>
                                                    <div className="text-xs text-slate-500 truncate">{c.credential_type.toUpperCase()}</div>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <div className={`text-xs ${c.active ? 'text-success-400' : 'text-slate-500'}`}>
                                                        {c.active ? 'Activa' : 'Inactiva'}
                                                    </div>
                                                    <button
                                                        className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                                                        onClick={() => setAccessCredDelete({ open: true, id: c.id, label: c.label })}
                                                    >
                                                        <Trash2 className="w-4 h-4" />
                                                    </button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
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

            <Modal
                isOpen={entitlementsModalOpen}
                onClose={() => setEntitlementsModalOpen(false)}
                title={`Accesos - ${usuario?.nombre || ''}`}
                size="lg"
                footer={
                    <div className="flex items-center justify-end w-full">
                        <Button
                            variant="secondary"
                            onClick={() => loadEntitlementsSummary()}
                            isLoading={entitlementsSummaryLoading}
                        >
                            <RefreshCw className="w-4 h-4 mr-1" />
                            Refrescar
                        </Button>
                    </div>
                }
            >
                <div className="space-y-4">
                    {entitlementsSummaryLoading ? (
                        <div className="flex items-center justify-center py-10">
                            <Loader2 className="w-6 h-6 animate-spin text-primary-400" />
                        </div>
                    ) : entitlementsSummary ? (
                        <>
                            <div className="card p-4">
                                <div className="text-xs text-slate-500 mb-1">Sucursales</div>
                                <div className="flex flex-wrap gap-2">
                                    {(entitlementsSummary.allowed_sucursales || [])
                                        .filter((s) => s.activa)
                                        .map((s) => (
                                            <span
                                                key={s.id}
                                                className="px-2 py-1 rounded-md bg-slate-800 text-slate-200 text-xs"
                                            >
                                                {s.nombre}
                                            </span>
                                        ))}
                                    {(entitlementsSummary.allowed_sucursales || []).filter((s) => s.activa).length === 0 ? (
                                        <span className="text-sm text-slate-500">Sin sucursales permitidas</span>
                                    ) : null}
                                </div>
                            </div>

                            <div className="card p-4">
                                <div className="text-xs text-slate-500 mb-1">Clases</div>
                                {entitlementsSummary.class_allowlist_enabled ? (
                                    <div className="space-y-3">
                                        <div>
                                            <div className="text-xs text-slate-500 mb-2">Tipos de clase</div>
                                            <div className="flex flex-wrap gap-2">
                                                {(entitlementsSummary.allowed_tipo_clases || []).map((tc) => (
                                                    <span
                                                        key={tc.id}
                                                        className="px-2 py-1 rounded-md bg-slate-800 text-slate-200 text-xs"
                                                    >
                                                        {tc.nombre}
                                                    </span>
                                                ))}
                                                {(entitlementsSummary.allowed_tipo_clases || []).length === 0 ? (
                                                    <span className="text-sm text-slate-500">Sin tipos de clase permitidos</span>
                                                ) : null}
                                            </div>
                                        </div>
                                        <div>
                                            <div className="text-xs text-slate-500 mb-2">Clases específicas</div>
                                            <div className="flex flex-wrap gap-2">
                                                {(entitlementsSummary.allowed_clases || []).map((c) => (
                                                    <span
                                                        key={c.id}
                                                        className="px-2 py-1 rounded-md bg-slate-800 text-slate-200 text-xs"
                                                    >
                                                        {c.nombre}
                                                    </span>
                                                ))}
                                                {(entitlementsSummary.allowed_clases || []).length === 0 ? (
                                                    <span className="text-sm text-slate-500">Sin clases específicas permitidas</span>
                                                ) : null}
                                            </div>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="text-sm text-slate-400">
                                        Acceso por clase no restringido por cuota.
                                    </div>
                                )}
                            </div>
                        </>
                    ) : (
                        <div className="text-sm text-slate-400">
                            No se pudo cargar el detalle de accesos.
                        </div>
                    )}
                </div>
            </Modal>

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

            <ConfirmModal
                isOpen={accessCredDelete.open}
                onClose={() => setAccessCredDelete({ open: false })}
                title="Desactivar credencial"
                message="La credencial dejará de funcionar para el acceso."
                confirmText="Desactivar"
                cancelText="Cancelar"
                variant="danger"
                isLoading={accessCredSaving}
                onConfirm={deleteAccessCredential}
            />

            {/* Click outside to close */}
            <div
                className="fixed inset-0 bg-black/50 z-40"
                onClick={onClose}
            />
        </>
    );
}

