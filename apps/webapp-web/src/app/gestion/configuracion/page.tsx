'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
    Settings,
    DollarSign,
    CreditCard,
    FileText,
    Plus,
    Edit,
    Trash2,
    Check,
    X,
} from 'lucide-react';
import {
    Button,
    Modal,
    ConfirmModal,
    useToast,
    Input,
} from '@/components/ui';
import { api, type TipoCuota, type MetodoPago, type ConceptoPago, type FeatureFlags, type Sucursal, type ClaseTipo } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { formatCurrency, cn } from '@/lib/utils';

// Config section tabs
const tabs = [
    { id: 'cuotas', label: 'Tipos de Cuota', icon: DollarSign },
    { id: 'metodos', label: 'Métodos de Pago', icon: CreditCard },
    { id: 'conceptos', label: 'Conceptos', icon: FileText },
    { id: 'modulos', label: 'Módulos', icon: Settings },
];

// === TipoCuota Form Modal ===
interface CuotaFormModalProps {
    isOpen: boolean;
    onClose: () => void;
    item?: TipoCuota | null;
    onSuccess: () => void;
}

function CuotaFormModal({ isOpen, onClose, item, onSuccess }: CuotaFormModalProps) {
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        nombre: '',
        precio: '',
        duracion_dias: '',
    });
    const { success, error } = useToast();

    useEffect(() => {
        if (isOpen) {
            if (item) {
                setFormData({
                    nombre: item.nombre || '',
                    precio: item.precio?.toString() || '',
                    duracion_dias: item.duracion_dias?.toString() || '',
                });
            } else {
                setFormData({ nombre: '', precio: '', duracion_dias: '' });
            }
        }
    }, [isOpen, item]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!formData.nombre.trim()) {
            error('El nombre es requerido');
            return;
        }

        setLoading(true);
        try {
            const data = {
                nombre: formData.nombre,
                precio: formData.precio ? parseFloat(formData.precio) : undefined,
                duracion_dias: formData.duracion_dias ? parseInt(formData.duracion_dias) : undefined,
            };

            if (item) {
                const res = await api.updateTipoCuota(item.id, data);
                if (res.ok) {
                    success('Tipo de cuota actualizado');
                    onSuccess();
                    onClose();
                } else {
                    error(res.error || 'Error al actualizar');
                }
            } else {
                const res = await api.createTipoCuota(data);
                if (res.ok) {
                    success('Tipo de cuota creado');
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
            title={item ? 'Editar Tipo de Cuota' : 'Nuevo Tipo de Cuota'}
            size="sm"
            footer={
                <>
                    <Button variant="secondary" onClick={onClose} disabled={loading}>
                        Cancelar
                    </Button>
                    <Button onClick={handleSubmit} isLoading={loading}>
                        {item ? 'Guardar' : 'Crear'}
                    </Button>
                </>
            }
        >
            <form onSubmit={handleSubmit} className="space-y-4">
                <Input
                    label="Nombre"
                    value={formData.nombre}
                    onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                    placeholder="Ej: Mensual"
                    required
                />
                <Input
                    label="Precio"
                    type="number"
                    min={0}
                    step="0.01"
                    value={formData.precio}
                    onChange={(e) => setFormData({ ...formData, precio: e.target.value })}
                    placeholder="0"
                    leftIcon={<span className="text-slate-400">$</span>}
                />
                <Input
                    label="Duración (días)"
                    type="number"
                    min={1}
                    value={formData.duracion_dias}
                    onChange={(e) => setFormData({ ...formData, duracion_dias: e.target.value })}
                    placeholder="30"
                />
            </form>
        </Modal>
    );
}

// === MetodoPago / Concepto Form Modal ===
interface SimpleFormModalProps {
    isOpen: boolean;
    onClose: () => void;
    item?: { id: number; nombre: string } | null;
    type: 'metodo' | 'concepto';
    onSuccess: () => void;
}

function SimpleFormModal({ isOpen, onClose, item, type, onSuccess }: SimpleFormModalProps) {
    const [loading, setLoading] = useState(false);
    const [nombre, setNombre] = useState('');
    const { success, error } = useToast();

    useEffect(() => {
        if (isOpen) {
            setNombre(item?.nombre || '');
        }
    }, [isOpen, item]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!nombre.trim()) {
            error('El nombre es requerido');
            return;
        }

        setLoading(true);
        try {
            if (type === 'metodo') {
                if (item) {
                    const res = await api.updateMetodoPago(item.id, { nombre });
                    if (res.ok) {
                        success('Método de pago actualizado');
                        onSuccess();
                        onClose();
                    } else {
                        error(res.error || 'Error al actualizar');
                    }
                } else {
                    const res = await api.createMetodoPago({ nombre });
                    if (res.ok) {
                        success('Método de pago creado');
                        onSuccess();
                        onClose();
                    } else {
                        error(res.error || 'Error al crear');
                    }
                }
            } else {
                if (item) {
                    const res = await api.updateConcepto(item.id, { nombre });
                    if (res.ok) {
                        success('Concepto actualizado');
                        onSuccess();
                        onClose();
                    } else {
                        error(res.error || 'Error al actualizar');
                    }
                } else {
                    const res = await api.createConcepto({ nombre });
                    if (res.ok) {
                        success('Concepto creado');
                        onSuccess();
                        onClose();
                    } else {
                        error(res.error || 'Error al crear');
                    }
                }
            }
        } catch {
            error('Error de conexión');
        } finally {
            setLoading(false);
        }
    };

    const title = type === 'metodo'
        ? (item ? 'Editar Método de Pago' : 'Nuevo Método de Pago')
        : (item ? 'Editar Concepto' : 'Nuevo Concepto');

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={title}
            size="sm"
            footer={
                <>
                    <Button variant="secondary" onClick={onClose} disabled={loading}>
                        Cancelar
                    </Button>
                    <Button onClick={handleSubmit} isLoading={loading}>
                        {item ? 'Guardar' : 'Crear'}
                    </Button>
                </>
            }
        >
            <form onSubmit={handleSubmit} className="space-y-4">
                <Input
                    label="Nombre"
                    value={nombre}
                    onChange={(e) => setNombre(e.target.value)}
                    placeholder={type === 'metodo' ? 'Ej: Efectivo' : 'Ej: Cuota'}
                    required
                />
            </form>
        </Modal>
    );
}

interface CuotaEntitlementsModalProps {
    isOpen: boolean;
    onClose: () => void;
    item: TipoCuota | null;
}

function CuotaEntitlementsModal({ isOpen, onClose, item }: CuotaEntitlementsModalProps) {
    const { success, error } = useToast();
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [sucursales, setSucursales] = useState<Sucursal[]>([]);
    const [claseTipos, setClaseTipos] = useState<ClaseTipo[]>([]);
    const [allSucursales, setAllSucursales] = useState(true);
    const [selectedSucursales, setSelectedSucursales] = useState<number[]>([]);
    const [scopeKey, setScopeKey] = useState<string>('0');
    const [classRulesByScope, setClassRulesByScope] = useState<Record<string, number[]>>({});

    useEffect(() => {
        if (!isOpen || !item) return;
        setLoading(true);
        void (async () => {
            try {
                const [entRes, sucRes, tiposRes] = await Promise.all([
                    api.getTipoCuotaEntitlements(item.id),
                    api.getSucursales(),
                    api.getClaseTipos(),
                ]);
                if (sucRes.ok && sucRes.data?.ok) {
                    setSucursales((sucRes.data.items || []).filter((s) => !!s.activa));
                } else {
                    setSucursales([]);
                }
                if (tiposRes.ok && tiposRes.data?.tipos) {
                    setClaseTipos((tiposRes.data.tipos || []).filter((t) => !!t.activo));
                } else {
                    setClaseTipos([]);
                }
                if (entRes.ok && entRes.data?.ok) {
                    setAllSucursales(Boolean(entRes.data.tipo_cuota?.all_sucursales));
                    setSelectedSucursales(Array.isArray(entRes.data.sucursal_ids) ? entRes.data.sucursal_ids : []);
                    const map: Record<string, number[]> = {};
                    const rules = Array.isArray(entRes.data.class_rules) ? entRes.data.class_rules : [];
                    rules
                        .filter((r) => String(r.target_type || '').toLowerCase() === 'tipo_clase' && Boolean(r.allow))
                        .forEach((r) => {
                            const k = r.sucursal_id ? String(r.sucursal_id) : '0';
                            const arr = map[k] || [];
                            arr.push(Number(r.target_id));
                            map[k] = arr;
                        });
                    Object.keys(map).forEach((k) => {
                        map[k] = Array.from(new Set(map[k].filter((x) => Number.isFinite(x)))).sort((a, b) => a - b);
                    });
                    setClassRulesByScope(map);
                    setScopeKey('0');
                } else {
                    setAllSucursales(true);
                    setSelectedSucursales([]);
                    setClassRulesByScope({});
                    setScopeKey('0');
                }
            } catch {
                setAllSucursales(true);
                setSelectedSucursales([]);
                setClassRulesByScope({});
                setScopeKey('0');
                setSucursales([]);
                setClaseTipos([]);
            } finally {
                setLoading(false);
            }
        })();
    }, [isOpen, item?.id]);

    const toggleSucursal = (sid: number) => {
        setSelectedSucursales((prev) => {
            const set = new Set(prev);
            if (set.has(sid)) set.delete(sid);
            else set.add(sid);
            return Array.from(set).sort((a, b) => a - b);
        });
    };

    const toggleTipoClase = (tipoId: number) => {
        setClassRulesByScope((prev) => {
            const current = new Set(prev[scopeKey] || []);
            if (current.has(tipoId)) current.delete(tipoId);
            else current.add(tipoId);
            const next = { ...prev, [scopeKey]: Array.from(current).sort((a, b) => a - b) };
            return next;
        });
    };

    const handleSave = async () => {
        if (!item) return;
        setSaving(true);
        try {
            const class_rules: { sucursal_id?: number | null; target_type: 'tipo_clase'; target_id: number; allow: boolean }[] = [];
            Object.entries(classRulesByScope || {}).forEach(([k, ids]) => {
                const sid = k === '0' ? null : Number(k);
                (ids || []).forEach((id) => {
                    class_rules.push({ sucursal_id: Number.isFinite(sid as any) ? (sid as any) : null, target_type: 'tipo_clase', target_id: Number(id), allow: true });
                });
            });
            const res = await api.updateTipoCuotaEntitlements(item.id, {
                all_sucursales: Boolean(allSucursales),
                sucursal_ids: allSucursales ? [] : selectedSucursales,
                class_rules,
            });
            if (res.ok && res.data?.ok) {
                success('Accesos actualizados');
                onClose();
            } else {
                error(res.error || 'Error al guardar accesos');
            }
        } catch {
            error('Error de conexión');
        } finally {
            setSaving(false);
        }
    };

    const scopeOptions: { key: string; label: string }[] = [
        { key: '0', label: 'Todas las sucursales' },
        ...sucursales.map((s) => ({ key: String(s.id), label: s.nombre })),
    ];

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={item ? `Accesos: ${item.nombre}` : 'Accesos'}
            size="lg"
            footer={
                <>
                    <Button variant="secondary" onClick={onClose} disabled={saving}>
                        Cerrar
                    </Button>
                    <Button onClick={handleSave} isLoading={saving} disabled={loading || saving || !item}>
                        Guardar
                    </Button>
                </>
            }
        >
            {loading ? (
                <div className="text-sm text-slate-400">Cargando…</div>
            ) : !item ? (
                <div className="text-sm text-slate-400">Seleccioná un tipo de cuota.</div>
            ) : (
                <div className="space-y-5">
                    <div className="card p-4">
                        <label className="flex items-center justify-between gap-3">
                            <div>
                                <div className="text-sm font-medium text-white">Acceso a sucursales</div>
                                <div className="text-xs text-slate-400">Si desactivás “todas”, elegís una lista permitida.</div>
                            </div>
                            <input
                                type="checkbox"
                                checked={allSucursales}
                                onChange={(e) => setAllSucursales(e.target.checked)}
                            />
                        </label>
                        {!allSucursales ? (
                            <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
                                {sucursales.map((s) => (
                                    <label key={s.id} className="flex items-center justify-between gap-3 rounded-xl border border-slate-800/60 bg-slate-950/40 px-3 py-2">
                                        <span className="text-sm text-slate-200">{s.nombre}</span>
                                        <input
                                            type="checkbox"
                                            checked={selectedSucursales.includes(s.id)}
                                            onChange={() => toggleSucursal(s.id)}
                                        />
                                    </label>
                                ))}
                            </div>
                        ) : null}
                    </div>

                    <div className="card p-4">
                        <div className="text-sm font-medium text-white mb-1">Permisos de clases</div>
                        <div className="text-xs text-slate-400 mb-3">Definí allowlist por tipo de clase y por sucursal (o global).</div>

                        <div className="flex items-center gap-2 mb-3">
                            <span className="text-xs text-slate-400">Ámbito:</span>
                            <select
                                className="bg-slate-950/40 border border-slate-800/60 rounded-lg px-2 py-1 text-sm text-slate-200"
                                value={scopeKey}
                                onChange={(e) => setScopeKey(e.target.value)}
                            >
                                {scopeOptions.map((o) => (
                                    <option key={o.key} value={o.key}>
                                        {o.label}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {claseTipos.length ? (
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                {claseTipos.map((t) => {
                                    const selected = (classRulesByScope[scopeKey] || []).includes(t.id);
                                    return (
                                        <label key={t.id} className="flex items-center justify-between gap-3 rounded-xl border border-slate-800/60 bg-slate-950/40 px-3 py-2">
                                            <span className="text-sm text-slate-200">{t.nombre}</span>
                                            <input type="checkbox" checked={selected} onChange={() => toggleTipoClase(t.id)} />
                                        </label>
                                    );
                                })}
                            </div>
                        ) : (
                            <div className="text-sm text-slate-400">No hay tipos de clase activos.</div>
                        )}
                    </div>
                </div>
            )}
        </Modal>
    );
}

export default function ConfiguracionPage() {
    const { success, error } = useToast();
    const router = useRouter();
    const pathname = usePathname();
    const { user, isLoading: authLoading } = useAuth();

    useEffect(() => {
        const p = pathname || '';
        if (!p.startsWith('/gestion/configuracion')) return;
        if (authLoading) return;
        const rol = String(user?.rol || '').toLowerCase();
        if (rol === 'owner' || rol === 'admin') {
            router.replace('/dashboard/configuracion');
        } else {
            router.replace('/gestion');
        }
    }, [pathname, authLoading, user?.rol, router]);

    // State
    const [loading, setLoading] = useState(true);
    const [gymNombre, setGymNombre] = useState<string>('');
    const [gymLogoUrl, setGymLogoUrl] = useState<string>('');
    const [logoUploading, setLogoUploading] = useState(false);
    const [activeTab, setActiveTab] = useState<'cuotas' | 'metodos' | 'conceptos' | 'modulos'>('cuotas');
    const [cuotaFormOpen, setCuotaFormOpen] = useState(false);
    const [cuotaToEdit, setCuotaToEdit] = useState<TipoCuota | null>(null);
    const [cuotaEntitlementsOpen, setCuotaEntitlementsOpen] = useState(false);
    const [cuotaEntitlementsItem, setCuotaEntitlementsItem] = useState<TipoCuota | null>(null);
    const [simpleFormOpen, setSimpleFormOpen] = useState(false);
    const [simpleItemToEdit, setSimpleItemToEdit] = useState<MetodoPago | ConceptoPago | null>(null);
    const [deleteOpen, setDeleteOpen] = useState(false);
    const [itemToDelete, setItemToDelete] = useState<{ type: 'cuota' | 'metodo' | 'concepto'; item: TipoCuota | MetodoPago | ConceptoPago } | null>(null);
    const [deleteLoading, setDeleteLoading] = useState(false);

    // Data
    const [tiposCuota, setTiposCuota] = useState<TipoCuota[]>([]);
    const [metodosPago, setMetodosPago] = useState<MetodoPago[]>([]);
    const [conceptos, setConceptos] = useState<ConceptoPago[]>([]);
    const [featureFlags, setFeatureFlags] = useState<FeatureFlags>({ modules: {} });
    const [featureFlagsLoading, setFeatureFlagsLoading] = useState(false);
    const [featureFlagsSaving, setFeatureFlagsSaving] = useState(false);

    const logoInputRef = useRef<HTMLInputElement | null>(null);

    // Load data
    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const gymRes = await api.getGymData();
            if (gymRes.ok && gymRes.data) {
                setGymNombre(gymRes.data.nombre || '');
                setGymLogoUrl(gymRes.data.logo_url || '');
            }

            const [cuotasRes, metodosRes, conceptosRes] = await Promise.all([
                api.getTiposCuota(),
                api.getMetodosPago(),
                api.getConceptosPago(),
            ]);
            if (cuotasRes.ok && cuotasRes.data) setTiposCuota(cuotasRes.data.tipos);
            if (metodosRes.ok && metodosRes.data) setMetodosPago(metodosRes.data.metodos);
            if (conceptosRes.ok && conceptosRes.data) setConceptos(conceptosRes.data.conceptos);

            setFeatureFlagsLoading(true);
            try {
                const ffRes = await api.getFeatureFlags();
                if (ffRes.ok && ffRes.data?.ok) {
                    setFeatureFlags(ffRes.data.flags || { modules: {} });
                }
            } finally {
                setFeatureFlagsLoading(false);
            }
        } catch {
            error('Error al cargar configuración');
        } finally {
            setLoading(false);
        }
    }, [error]);

    const handleSaveFeatureFlags = async () => {
        setFeatureFlagsSaving(true);
        try {
            const res = await api.setFeatureFlags(featureFlags || { modules: {} });
            if (res.ok && res.data?.ok) {
                success('Módulos actualizados');
                setFeatureFlags(res.data.flags || { modules: {} });
            } else {
                error(res.error || 'Error al guardar módulos');
            }
        } catch {
            error('Error de conexión');
        } finally {
            setFeatureFlagsSaving(false);
        }
    };

    const handleLogoSelected = async (file: File | null) => {
        if (!file) return;
        setLogoUploading(true);
        try {
            const res = await api.uploadGymLogo(file);
            if (res.ok && res.data?.ok) {
                const url = res.data.logo_url || '';
                setGymLogoUrl(url);
                success('Logo actualizado');
            } else {
                error(res.error || res.data?.error || 'Error al subir logo');
            }
        } catch {
            error('Error de conexión');
        } finally {
            setLogoUploading(false);
        }
    };

    useEffect(() => {
        loadData();
    }, [loadData]);

    // Toggle active
    const handleToggle = async (type: 'cuota' | 'metodo' | 'concepto', item: TipoCuota | MetodoPago | ConceptoPago) => {
        try {
            let res;
            if (type === 'cuota') {
                res = await api.toggleTipoCuota(item.id);
            } else if (type === 'metodo') {
                res = await api.toggleMetodoPago(item.id);
            } else {
                res = await api.toggleConcepto(item.id);
            }

            if (res.ok) {
                success(item.activo ? 'Desactivado' : 'Activado');
                loadData();
            } else {
                error(res.error || 'Error al cambiar estado');
            }
        } catch {
            error('Error de conexión');
        }
    };

    // Delete handler
    const handleDelete = async () => {
        if (!itemToDelete) return;
        setDeleteLoading(true);
        try {
            let res;
            if (itemToDelete.type === 'cuota') {
                res = await api.deleteTipoCuota(itemToDelete.item.id);
            } else if (itemToDelete.type === 'metodo') {
                res = await api.deleteMetodoPago(itemToDelete.item.id);
            } else {
                res = await api.deleteConcepto(itemToDelete.item.id);
            }

            if (res.ok) {
                success('Eliminado correctamente');
                loadData();
            } else {
                error(res.error || 'Error al eliminar');
            }
        } catch {
            error('Error de conexión');
        } finally {
            setDeleteLoading(false);
            setDeleteOpen(false);
            setItemToDelete(null);
        }
    };

    const moduleOptions = [
        { key: 'usuarios', label: 'Usuarios' },
        { key: 'pagos', label: 'Pagos' },
        { key: 'profesores', label: 'Profesores' },
        { key: 'empleados', label: 'Empleados' },
        { key: 'rutinas', label: 'Rutinas' },
        { key: 'ejercicios', label: 'Ejercicios' },
        { key: 'clases', label: 'Clases' },
        { key: 'asistencias', label: 'Asistencias' },
        { key: 'whatsapp', label: 'WhatsApp' },
        { key: 'configuracion', label: 'Configuración' },
        { key: 'reportes', label: 'Reportes' },
        { key: 'entitlements_v2', label: 'Accesos avanzados (multi-sucursal y clases)' },
    ];

    // Render item list
    const renderItemList = () => {
        if (loading) {
            return (
                <div className="space-y-2">
                    {Array.from({ length: 3 }).map((_, i) => (
                        <div key={i} className="card p-4 animate-pulse">
                            <div className="h-5 bg-slate-800 rounded w-1/3" />
                        </div>
                    ))}
                </div>
            );
        }

        if (activeTab === 'modulos') {
            const modules = (featureFlags && featureFlags.modules) || {};
            return (
                <div className="space-y-3">
                    <div className="card p-4">
                        <div className="text-sm text-slate-300">
                            Activá o desactivá módulos del panel de gestión. Desactivar Configuración puede ocultar esta pantalla.
                        </div>
                    </div>
                    <div className="card p-4 space-y-3">
                        {moduleOptions.map((m) => (
                            <label key={m.key} className="flex items-center justify-between gap-3 py-1">
                                <span className="text-sm text-white">{m.label}</span>
                                <input
                                    type="checkbox"
                                    checked={modules[m.key] !== false}
                                    onChange={(e) => {
                                        const next = { ...(featureFlags.modules || {}) };
                                        next[m.key] = e.target.checked;
                                        setFeatureFlags({ ...(featureFlags || { modules: {} }), modules: next });
                                    }}
                                />
                            </label>
                        ))}
                        <div className="flex items-center justify-end pt-2">
                            <Button
                                size="sm"
                                onClick={handleSaveFeatureFlags}
                                isLoading={featureFlagsSaving}
                                disabled={featureFlagsSaving || featureFlagsLoading}
                            >
                                Guardar
                            </Button>
                        </div>
                    </div>
                </div>
            );
        }

        const items = activeTab === 'cuotas' ? tiposCuota : activeTab === 'metodos' ? metodosPago : conceptos;

        if (items.length === 0) {
            return (
                <div className="card p-8 text-center text-slate-500">
                    No hay elementos configurados
                </div>
            );
        }

        return (
            <div className="space-y-2">
                {items.map((item) => (
                    <div
                        key={item.id}
                        className={cn(
                            'card p-4 flex items-center justify-between gap-4',
                            !item.activo && 'opacity-50'
                        )}
                    >
                        <div className="flex items-center gap-4">
                            <button
                                onClick={() => handleToggle(activeTab === 'cuotas' ? 'cuota' : activeTab === 'metodos' ? 'metodo' : 'concepto', item)}
                                className={cn(
                                    'w-8 h-8 rounded-lg flex items-center justify-center transition-colors',
                                    item.activo
                                        ? 'bg-success-500/20 text-success-400 hover:bg-success-500/30'
                                        : 'bg-slate-800 text-slate-500 hover:bg-slate-700'
                                )}
                            >
                                {item.activo ? <Check className="w-4 h-4" /> : <X className="w-4 h-4" />}
                            </button>
                            <div>
                                <div className="font-medium text-white">{item.nombre}</div>
                                {activeTab === 'cuotas' && (item as TipoCuota).precio !== undefined && (
                                    <div className="text-sm text-slate-400">
                                        {formatCurrency((item as TipoCuota).precio || 0)}
                                        {(item as TipoCuota).duracion_dias && ` • ${(item as TipoCuota).duracion_dias} días`}
                                    </div>
                                )}
                            </div>
                        </div>
                        <div className="flex items-center gap-1">
                            <button
                                onClick={() => {
                                    if (activeTab === 'cuotas') {
                                        setCuotaToEdit(item as TipoCuota);
                                        setCuotaFormOpen(true);
                                    } else {
                                        setSimpleItemToEdit(item as MetodoPago | ConceptoPago);
                                        setSimpleFormOpen(true);
                                    }
                                }}
                                className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                            >
                                <Edit className="w-4 h-4" />
                            </button>
                            {activeTab === 'cuotas' ? (
                                <button
                                    onClick={() => {
                                        setCuotaEntitlementsItem(item as TipoCuota);
                                        setCuotaEntitlementsOpen(true);
                                    }}
                                    className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                                >
                                    <Settings className="w-4 h-4" />
                                </button>
                            ) : null}
                            <button
                                onClick={() => {
                                    setItemToDelete({
                                        type: activeTab === 'cuotas' ? 'cuota' : activeTab === 'metodos' ? 'metodo' : 'concepto',
                                        item,
                                    });
                                    setDeleteOpen(true);
                                }}
                                className="p-2 rounded-lg text-slate-400 hover:text-danger-400 hover:bg-danger-500/10 transition-colors"
                            >
                                <Trash2 className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        );
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between"
            >
                <div>
                    <h1 className="text-2xl font-display font-bold text-white flex items-center gap-3">
                        <Settings className="w-6 h-6 text-primary-400" />
                        Configuración
                    </h1>
                    <p className="text-slate-400 mt-1">
                        Configura tipos de cuota, métodos de pago y conceptos
                    </p>
                </div>
            </motion.div>

            {/* Branding / Logo */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05 }}
                className="card p-4"
            >
                <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                        <div className="w-14 h-14 rounded-xl bg-slate-800 border border-slate-700 overflow-hidden flex items-center justify-center">
                            {gymLogoUrl ? (
                                <img src={gymLogoUrl} alt="Logo" className="w-full h-full object-contain bg-white" />
                            ) : (
                                <span className="text-xs text-slate-500">Sin logo</span>
                            )}
                        </div>
                        <div>
                            <div className="text-sm text-slate-400">Gimnasio</div>
                            <div className="font-semibold text-white">{gymNombre || '—'}</div>
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        <input
                            ref={logoInputRef}
                            type="file"
                            accept="image/png,image/jpeg,image/jpg,image/svg+xml"
                            className="hidden"
                            disabled={logoUploading}
                            onChange={(e) => {
                                handleLogoSelected(e.target.files?.[0] || null);
                                e.currentTarget.value = '';
                            }}
                        />
                        <Button
                            type="button"
                            variant="secondary"
                            isLoading={logoUploading}
                            disabled={logoUploading}
                            onClick={() => logoInputRef.current?.click()}
                        >
                            Cargar logo
                        </Button>
                    </div>
                </div>
            </motion.div>

            {/* Tabs */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="flex items-center gap-2"
            >
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id as 'cuotas' | 'metodos' | 'conceptos' | 'modulos')}
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

            {/* Content */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
                className="space-y-4"
            >
                <div className="flex items-center justify-between">
                    <h2 className="text-lg font-semibold text-white">
                        {tabs.find((t) => t.id === activeTab)?.label}
                    </h2>
                    {activeTab !== 'modulos' && (
                        <Button
                            size="sm"
                            leftIcon={<Plus className="w-4 h-4" />}
                            onClick={() => {
                                if (activeTab === 'cuotas') {
                                    setCuotaToEdit(null);
                                    setCuotaFormOpen(true);
                                } else {
                                    setSimpleItemToEdit(null);
                                    setSimpleFormOpen(true);
                                }
                            }}
                        >
                            Agregar
                        </Button>
                    )}
                </div>

                {renderItemList()}
            </motion.div>

            {/* Cuota Form Modal */}
            <CuotaFormModal
                isOpen={cuotaFormOpen}
                onClose={() => {
                    setCuotaFormOpen(false);
                    setCuotaToEdit(null);
                }}
                item={cuotaToEdit}
                onSuccess={loadData}
            />

            <CuotaEntitlementsModal
                isOpen={cuotaEntitlementsOpen}
                onClose={() => {
                    setCuotaEntitlementsOpen(false);
                    setCuotaEntitlementsItem(null);
                }}
                item={cuotaEntitlementsItem}
            />

            {/* Simple Form Modal (Metodo/Concepto) */}
            <SimpleFormModal
                isOpen={simpleFormOpen}
                onClose={() => {
                    setSimpleFormOpen(false);
                    setSimpleItemToEdit(null);
                }}
                item={simpleItemToEdit}
                type={activeTab === 'metodos' ? 'metodo' : 'concepto'}
                onSuccess={loadData}
            />

            {/* Delete Confirm */}
            <ConfirmModal
                isOpen={deleteOpen}
                onClose={() => {
                    setDeleteOpen(false);
                    setItemToDelete(null);
                }}
                onConfirm={handleDelete}
                title="Eliminar"
                message={`¿Estás seguro de eliminar "${itemToDelete?.item.nombre}"?`}
                confirmText="Eliminar"
                variant="danger"
            />
        </div>
    );
}

