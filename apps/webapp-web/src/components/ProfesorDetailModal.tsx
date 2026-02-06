'use client';

import { useState, useEffect, useCallback } from 'react';
import {
    Clock,
    Calendar,
    DollarSign,
    Award,
    User,
    Plus,
    Trash2,
    Save,
    Settings,
    Lock,
} from 'lucide-react';
import { Button, Modal, Input, Select, Textarea, useToast } from '@/components/ui';
import {
    api,
    type Profesor,
    type ProfesorHorario,
    type ProfesorConfig,
    type ProfesorResumen,
    type Usuario,
    type Sucursal,
    type Clase,
} from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { formatTime, cn } from '@/lib/utils';

interface ProfesorDetailModalProps {
    isOpen: boolean;
    onClose: () => void;
    profesor: Profesor | null;
    onRefresh: () => void;
}

type TabType = 'horarios' | 'resumen' | 'config';

const diasSemana = [
    'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'
];

type PermissionModule = {
    key: string;
    label: string;
    read: string;
    write?: string;
    extra?: readonly string[];
};

const permissionModules: PermissionModule[] = [
    { key: 'usuarios', label: 'Usuarios', read: 'usuarios:read', write: 'usuarios:write' },
    { key: 'pagos', label: 'Pagos', read: 'pagos:read', write: 'pagos:write' },
    { key: 'asistencias', label: 'Asistencias', read: 'asistencias:read', write: 'asistencias:write' },
    { key: 'clases', label: 'Clases', read: 'clases:read', write: 'clases:write' },
    { key: 'rutinas', label: 'Rutinas', read: 'rutinas:read', write: 'rutinas:write' },
    { key: 'ejercicios', label: 'Ejercicios', read: 'ejercicios:read', write: 'ejercicios:write' },
    { key: 'whatsapp', label: 'WhatsApp', read: 'whatsapp:read', write: 'whatsapp:send', extra: ['whatsapp:config'] },
    { key: 'configuracion', label: 'Configuración', read: 'configuracion:read', write: 'configuracion:write' },
    { key: 'reportes', label: 'Reportes', read: 'reportes:read' },
];

export default function ProfesorDetailModal({
    isOpen,
    onClose,
    profesor,
    onRefresh,
}: ProfesorDetailModalProps) {
    const { success, error } = useToast();
    const { user } = useAuth();
    const [activeTab, setActiveTab] = useState<TabType>('horarios');

    // Horarios
    const [horarios, setHorarios] = useState<ProfesorHorario[]>([]);
    const [horarioForm, setHorarioForm] = useState({
        dia: 'Lunes',
        hora_inicio: '09:00',
        hora_fin: '18:00',
        disponible: true,
    });

    // Resumen
    const [resumenMensual, setResumenMensual] = useState<ProfesorResumen | null>(null);
    const [resumenSemanal, setResumenSemanal] = useState<ProfesorResumen | null>(null);
    const [selectedMes, setSelectedMes] = useState(new Date().getMonth() + 1);
    const [selectedAnio, setSelectedAnio] = useState(new Date().getFullYear());

    // Config
    const [config, setConfig] = useState<Partial<ProfesorConfig>>({
        monto: undefined,
        monto_tipo: 'mensual',
        especialidad: '',
        experiencia_anios: undefined,
        certificaciones: '',
        usuario_vinculado_id: undefined,
        notas: '',
    });
    const [configLoading, setConfigLoading] = useState(false);
    const [usuarios, setUsuarios] = useState<Usuario[]>([]);
    const [sucursales, setSucursales] = useState<Sucursal[]>([]);
    const [sucursalActualId, setSucursalActualId] = useState<number | null>(null);
    const [editBranches, setEditBranches] = useState<number[]>([]);
    const [branchesSaving, setBranchesSaving] = useState(false);
    const [clases, setClases] = useState<Clase[]>([]);
    const [clasesLoading, setClasesLoading] = useState(false);
    const [editClases, setEditClases] = useState<number[]>([]);
    const [clasesSaving, setClasesSaving] = useState(false);

    // Password state
    const [newPassword, setNewPassword] = useState('');
    const [passwordLoading, setPasswordLoading] = useState(false);

    const [moduleFlags, setModuleFlags] = useState<Record<string, boolean> | null>(null);
    const [editScopes, setEditScopes] = useState<string[]>([]);
    const [permsLoading, setPermsLoading] = useState(false);

    const asRecord = (v: unknown): Record<string, unknown> | null => {
        if (!v || typeof v !== 'object') return null;
        return v as Record<string, unknown>;
    };

    const loadHorarios = useCallback(async () => {
        if (!profesor) return;
        const res = await api.getProfesorHorarios(profesor.id);
        if (res.ok && res.data) {
            setHorarios(res.data.horarios);
        }
    }, [profesor]);

    const loadResumen = useCallback(async () => {
        if (!profesor) return;
        const [mensual, semanal] = await Promise.all([
            api.getProfesorResumenMensual(profesor.id, selectedMes, selectedAnio),
            api.getProfesorResumenSemanal(profesor.id),
        ]);
        if (mensual.ok && mensual.data) {
            setResumenMensual(mensual.data);
        }
        if (semanal.ok && semanal.data) {
            setResumenSemanal(semanal.data);
        }
    }, [profesor, selectedMes, selectedAnio]);

    const loadConfig = useCallback(async () => {
        if (!profesor) return;
        const res = await api.getProfesorConfig(profesor.id);
        if (res.ok && res.data) {
            setConfig({
                monto: res.data.monto,
                monto_tipo: res.data.monto_tipo || 'mensual',
                especialidad: res.data.especialidad || '',
                experiencia_anios: res.data.experiencia_anios,
                certificaciones: res.data.certificaciones || '',
                usuario_vinculado_id: res.data.usuario_vinculado_id,
                notas: res.data.notas || '',
            });
        }
    }, [profesor]);

    const loadUsuarios = useCallback(async () => {
        const role = String(user?.rol || '').toLowerCase();
        const includeAll = ['owner', 'dueño', 'dueno', 'admin', 'administrador'].includes(role);
        const res = await api.getUsuariosDirectorio({ activo: true, limit: 500, include_all: includeAll || undefined });
        if (res.ok && res.data) {
            setUsuarios(res.data.usuarios);
        }
    }, [user?.rol]);

    const loadSucursales = useCallback(async () => {
        const res = await api.getSucursales();
        if (res.ok && res.data?.ok) {
            setSucursales((res.data.items || []).filter((s) => !!s.activa));
            const currentId = res.data.sucursal_actual_id ?? null;
            setSucursalActualId(typeof currentId === 'number' ? currentId : null);
        } else {
            setSucursales([]);
            setSucursalActualId(null);
        }
    }, []);

    const loadClases = useCallback(async () => {
        if (!sucursalActualId) {
            setClases([]);
            return;
        }
        setClasesLoading(true);
        try {
            const res = await api.getClases();
            if (res.ok && res.data) {
                setClases((res.data.clases || []).filter((c) => (c.activa ?? c.activo) !== false));
            } else {
                setClases([]);
            }
        } finally {
            setClasesLoading(false);
        }
    }, [sucursalActualId]);

    const loadClasesAsignadas = useCallback(async () => {
        if (!profesor?.id || !sucursalActualId) {
            setEditClases([]);
            return;
        }
        try {
            const res = await api.getProfesorClasesAsignadas(profesor.id);
            if (res.ok && res.data?.clase_ids) {
                setEditClases((res.data.clase_ids || []).map((x) => Number(x)).filter((x) => Number.isFinite(x)));
            } else {
                setEditClases([]);
            }
        } catch {
            setEditClases([]);
        }
    }, [profesor?.id, sucursalActualId]);

    const handlePasswordChange = async () => {
        if (!profesor || !newPassword) return;
        setPasswordLoading(true);
        const res = await api.updateProfesorPassword(profesor.id, newPassword);
        setPasswordLoading(false);
        if (res.ok) {
            success('Contraseña actualizada');
            setNewPassword('');
        } else {
            error(res.error || 'Error al actualizar contraseña');
        }
    };

    // Load data
    useEffect(() => {
        if (profesor && isOpen) {
            setEditScopes(profesor.scopes || []);
            setEditBranches((profesor.sucursales || []).map((s) => Number(s.id)).filter((x) => Number.isFinite(x)));
            void loadHorarios();
            void loadResumen();
            void loadConfig();
            void loadUsuarios();
            void loadSucursales();
            (async () => {
                try {
                    const boot = await api.getBootstrap('auto');
                    const flagsObj = asRecord(boot.ok ? (boot.data?.flags as unknown) : null);
                    const modulesObj = asRecord(flagsObj ? flagsObj['modules'] : null);
                    setModuleFlags(modulesObj ? (modulesObj as Record<string, boolean>) : null);
                } catch {
                    setModuleFlags(null);
                }
            })();
        }
    }, [isOpen, profesor, loadConfig, loadHorarios, loadResumen, loadSucursales, loadUsuarios]);

    useEffect(() => {
        if (profesor && isOpen) {
            void loadResumen();
        }
    }, [isOpen, loadResumen, profesor, selectedAnio, selectedMes]);

    const isModuleEnabled = (key: string) => {
        if (!moduleFlags) return true;
        if (Object.prototype.hasOwnProperty.call(moduleFlags, key)) return moduleFlags[key] !== false;
        return true;
    };

    const toggleScope = (scope: string, enabled: boolean) => {
        const s = String(scope || '').trim();
        if (!s) return;
        setEditScopes((prev) => {
            const has = prev.includes(s);
            if (enabled && !has) return [...prev, s];
            if (!enabled && has) return prev.filter((x) => x !== s);
            return prev;
        });
    };

    const setModuleRead = (key: string, readScope: string, writeScope: string | undefined, extra: readonly string[] | undefined, enabled: boolean) => {
        if (!isModuleEnabled(key)) return;
        if (enabled) {
            toggleScope(readScope, true);
            return;
        }
        toggleScope(readScope, false);
        if (writeScope) toggleScope(writeScope, false);
        for (const ex of extra || []) toggleScope(ex, false);
    };

    const setModuleWrite = (key: string, readScope: string, writeScope: string | undefined, enabled: boolean) => {
        if (!isModuleEnabled(key)) return;
        if (!writeScope) return;
        if (enabled) {
            toggleScope(readScope, true);
            toggleScope(writeScope, true);
        } else {
            toggleScope(writeScope, false);
        }
    };

    const savePerms = async () => {
        if (!profesor?.usuario_id) return;
        setPermsLoading(true);
        try {
            const disabled = new Set<string>();
            for (const m of permissionModules) {
                if (!isModuleEnabled(m.key)) {
                    disabled.add(m.read);
                    if (m.write) disabled.add(m.write);
                    const extra = 'extra' in m ? m.extra : undefined;
                    for (const ex of extra || []) disabled.add(String(ex));
                }
            }
            const scopesSanitized = Array.from(new Set(editScopes)).filter((s) => !disabled.has(String(s)));
            const res = await api.updateStaff(profesor.usuario_id, { scopes: scopesSanitized });
            if (!res.ok) throw new Error(res.error || 'No se pudo guardar permisos');
            success('Permisos actualizados');
            onRefresh();
        } catch (e) {
            error(e instanceof Error ? e.message : 'No se pudo guardar permisos');
        } finally {
            setPermsLoading(false);
        }
    };

    const toggleBranch = (id: number, enabled: boolean) => {
        const sid = Number(id);
        if (!Number.isFinite(sid) || sid <= 0) return;
        setEditBranches((prev) => {
            const has = prev.includes(sid);
            if (enabled && !has) return [...prev, sid];
            if (!enabled && has) return prev.filter((x) => x !== sid);
            return prev;
        });
    };

    const saveBranches = async () => {
        if (!profesor?.usuario_id) return;
        setBranchesSaving(true);
        try {
            const ids = Array.from(new Set(editBranches)).filter((x) => Number.isFinite(x) && x > 0);
            const res = await api.updateStaff(profesor.usuario_id, { sucursales: ids });
            if (!res.ok) throw new Error(res.error || 'No se pudieron guardar sucursales');
            success('Sucursales actualizadas');
            onRefresh();
        } catch (e) {
            error(e instanceof Error ? e.message : 'No se pudieron guardar sucursales');
        } finally {
            setBranchesSaving(false);
        }
    };

    const toggleClase = (id: number, enabled: boolean) => {
        const cid = Number(id);
        if (!Number.isFinite(cid) || cid <= 0) return;
        setEditClases((prev) => {
            const has = prev.includes(cid);
            if (enabled && !has) return [...prev, cid];
            if (!enabled && has) return prev.filter((x) => x !== cid);
            return prev;
        });
    };

    const saveClases = async () => {
        if (!profesor?.id) return;
        if (!sucursalActualId) return;
        const canAssign = editBranches.includes(sucursalActualId);
        if (!canAssign) {
            error('El profesor no está asignado a la sucursal actual');
            return;
        }
        setClasesSaving(true);
        try {
            const ids = Array.from(new Set(editClases)).filter((x) => Number.isFinite(x) && x > 0);
            const res = await api.updateProfesorClasesAsignadas(profesor.id, { clase_ids: ids });
            if (!res.ok || !res.data?.ok) throw new Error(res.error || res.data?.error || 'No se pudieron guardar clases');
            success('Clases asignadas actualizadas');
            onRefresh();
        } catch (e) {
            error(e instanceof Error ? e.message : 'No se pudieron guardar clases');
        } finally {
            setClasesSaving(false);
        }
    };

    useEffect(() => {
        if (!isOpen) return;
        void loadClases();
        void loadClasesAsignadas();
    }, [isOpen, loadClases, loadClasesAsignadas]);

    // Horario CRUD
    const handleAddHorario = async () => {
        if (!profesor) return;
        const res = await api.createProfesorHorario(profesor.id, horarioForm);
        if (res.ok) {
            success('Horario agregado');
            loadHorarios();
            setHorarioForm({
                dia: 'Lunes',
                hora_inicio: '09:00',
                hora_fin: '18:00',
                disponible: true,
            });
        } else {
            error(res.error || 'Error al agregar');
        }
    };

    const handleDeleteHorario = async (horarioId: number) => {
        if (!profesor) return;
        const res = await api.deleteProfesorHorario(profesor.id, horarioId);
        if (res.ok) {
            success('Horario eliminado');
            loadHorarios();
        } else {
            error(res.error || 'Error al eliminar');
        }
    };

    // Config save
    const handleSaveConfig = async () => {
        if (!profesor) return;
        setConfigLoading(true);
        const res = await api.updateProfesorConfig(profesor.id, config);
        setConfigLoading(false);
        if (res.ok) {
            success('Configuración guardada');
            onRefresh();
        } else {
            error(res.error || 'Error al guardar');
        }
    };

    // Group horarios by day
    const horariosByDay: Record<string, ProfesorHorario[]> = {};
    diasSemana.forEach(d => { horariosByDay[d] = []; });
    horarios.forEach(h => {
        if (horariosByDay[h.dia]) {
            horariosByDay[h.dia].push(h);
        }
    });

    if (!isOpen || !profesor) return null;

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={`Configurar: ${profesor.nombre}`}
            size="xl"
        >
            <div className="space-y-4">
                {/* Tabs */}
                <div className="flex border-b border-slate-800">
                    {[
                        { id: 'horarios', label: 'Horarios', icon: Clock },
                        { id: 'resumen', label: 'Resumen', icon: Calendar },
                        { id: 'config', label: 'Configuración', icon: Settings },
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
                            <tab.icon className="w-4 h-4" />
                            {tab.label}
                        </button>
                    ))}
                </div>

                {/* Tab Content */}
                <div className="min-h-[350px]">
                    {activeTab === 'horarios' && (
                        <div className="space-y-4">
                            {/* Add horario form */}
                            <div className="card p-4 space-y-3">
                                <h4 className="text-sm font-medium text-white">Agregar Disponibilidad</h4>
                                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                                    <Select
                                        value={horarioForm.dia}
                                        onChange={(e) => setHorarioForm({ ...horarioForm, dia: e.target.value })}
                                        options={diasSemana.map(d => ({ value: d, label: d }))}
                                    />
                                    <Input
                                        type="time"
                                        value={horarioForm.hora_inicio}
                                        onChange={(e) => setHorarioForm({ ...horarioForm, hora_inicio: e.target.value })}
                                    />
                                    <Input
                                        type="time"
                                        value={horarioForm.hora_fin}
                                        onChange={(e) => setHorarioForm({ ...horarioForm, hora_fin: e.target.value })}
                                    />
                                    <label className="flex items-center gap-2 text-sm text-slate-400">
                                        <input
                                            type="checkbox"
                                            checked={horarioForm.disponible}
                                            onChange={(e) => setHorarioForm({ ...horarioForm, disponible: e.target.checked })}
                                        />
                                        Disponible
                                    </label>
                                    <Button onClick={handleAddHorario}>
                                        <Plus className="w-4 h-4 mr-1" />
                                        Agregar
                                    </Button>
                                </div>
                            </div>

                            {/* Horarios grid */}
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                                {diasSemana.map((dia) => (
                                    <div key={dia} className="card p-3">
                                        <div className="text-sm font-medium text-white mb-2">{dia}</div>
                                        <div className="space-y-1">
                                            {horariosByDay[dia].length === 0 ? (
                                                <div className="text-xs text-slate-500">Sin horarios</div>
                                            ) : (
                                                horariosByDay[dia].map((h) => (
                                                    <div
                                                        key={h.id}
                                                        className={cn(
                                                            'flex items-center justify-between p-2 rounded text-xs',
                                                            h.disponible ? 'bg-success-500/10' : 'bg-slate-800'
                                                        )}
                                                    >
                                                        <span className="text-slate-300">
                                                            {formatTime(h.hora_inicio)} - {formatTime(h.hora_fin)}
                                                        </span>
                                                        <button
                                                            onClick={() => handleDeleteHorario(h.id)}
                                                            className="text-slate-400 hover:text-danger-400"
                                                        >
                                                            <Trash2 className="w-3 h-3" />
                                                        </button>
                                                    </div>
                                                ))
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {activeTab === 'resumen' && (
                        <div className="space-y-4">
                            {/* Month selector */}
                            <div className="flex items-center gap-3">
                                <Select
                                    value={selectedMes.toString()}
                                    onChange={(e) => setSelectedMes(Number(e.target.value))}
                                    options={[
                                        { value: '1', label: 'Enero' },
                                        { value: '2', label: 'Febrero' },
                                        { value: '3', label: 'Marzo' },
                                        { value: '4', label: 'Abril' },
                                        { value: '5', label: 'Mayo' },
                                        { value: '6', label: 'Junio' },
                                        { value: '7', label: 'Julio' },
                                        { value: '8', label: 'Agosto' },
                                        { value: '9', label: 'Septiembre' },
                                        { value: '10', label: 'Octubre' },
                                        { value: '11', label: 'Noviembre' },
                                        { value: '12', label: 'Diciembre' },
                                    ]}
                                />
                                <Input
                                    type="number"
                                    value={selectedAnio}
                                    onChange={(e) => setSelectedAnio(Number(e.target.value))}
                                    min={2020}
                                    max={2030}
                                    className="w-24"
                                />
                            </div>

                            {/* Monthly summary */}
                            <div className="card p-4">
                                <h4 className="text-sm font-medium text-white mb-4">Resumen Mensual</h4>
                                {resumenMensual ? (
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-white">{resumenMensual.horas_trabajadas}h</div>
                                            <div className="text-xs text-slate-500">Trabajadas</div>
                                        </div>
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-slate-400">{resumenMensual.horas_proyectadas}h</div>
                                            <div className="text-xs text-slate-500">Proyectadas</div>
                                        </div>
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-warning-400">{resumenMensual.horas_extra}h</div>
                                            <div className="text-xs text-slate-500">Extra</div>
                                        </div>
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-success-400">{resumenMensual.horas_totales}h</div>
                                            <div className="text-xs text-slate-500">Total</div>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="text-center text-slate-500 py-4">Sin datos</div>
                                )}
                            </div>

                            {/* Weekly summary */}
                            <div className="card p-4">
                                <h4 className="text-sm font-medium text-white mb-4">Resumen Semanal (esta semana)</h4>
                                {resumenSemanal ? (
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-white">{resumenSemanal.horas_trabajadas}h</div>
                                            <div className="text-xs text-slate-500">Trabajadas</div>
                                        </div>
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-slate-400">{resumenSemanal.horas_proyectadas}h</div>
                                            <div className="text-xs text-slate-500">Proyectadas</div>
                                        </div>
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-warning-400">{resumenSemanal.horas_extra}h</div>
                                            <div className="text-xs text-slate-500">Extra</div>
                                        </div>
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-success-400">{resumenSemanal.horas_totales}h</div>
                                            <div className="text-xs text-slate-500">Total</div>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="text-center text-slate-500 py-4">Sin datos</div>
                                )}
                            </div>
                        </div>
                    )}

                    {activeTab === 'config' && (
                        <div className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {/* Salary */}
                                <div className="space-y-3">
                                    <h4 className="text-sm font-medium text-white flex items-center gap-1">
                                        <DollarSign className="w-4 h-4" />
                                        Compensación
                                    </h4>
                                    <div className="flex gap-2">
                                        <Input
                                            type="number"
                                            value={config.monto || ''}
                                            onChange={(e) => setConfig({ ...config, monto: e.target.value ? Number(e.target.value) : undefined })}
                                            placeholder="Monto"
                                        />
                                        <Select
                                            value={config.monto_tipo || 'mensual'}
                                            onChange={(e) => setConfig({ ...config, monto_tipo: e.target.value as 'mensual' | 'hora' })}
                                            options={[
                                                { value: 'mensual', label: 'Mensual' },
                                                { value: 'hora', label: 'Por hora' },
                                            ]}
                                        />
                                    </div>
                                </div>

                                {/* User link */}
                                <div className="space-y-3">
                                    <h4 className="text-sm font-medium text-white flex items-center gap-1">
                                        <User className="w-4 h-4" />
                                        Usuario Vinculado
                                    </h4>
                                    <Select
                                        value={config.usuario_vinculado_id?.toString() || ''}
                                        onChange={(e) => setConfig({ ...config, usuario_vinculado_id: e.target.value ? Number(e.target.value) : undefined })}
                                        placeholder="Vincular usuario..."
                                        options={usuarios.map(u => ({
                                            value: u.id.toString(),
                                            label: `${u.nombre}${u.dni ? ` (${u.dni})` : ''}`
                                        }))}
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {/* Professional info */}
                                <div className="space-y-3">
                                    <h4 className="text-sm font-medium text-white flex items-center gap-1">
                                        <Award className="w-4 h-4" />
                                        Información Profesional
                                    </h4>
                                    <Input
                                        label="Especialidad"
                                        value={config.especialidad || ''}
                                        onChange={(e) => setConfig({ ...config, especialidad: e.target.value })}
                                        placeholder="Ej: Musculación, Funcional, CrossFit"
                                    />
                                    <Input
                                        label="Años de experiencia"
                                        type="number"
                                        value={config.experiencia_anios || ''}
                                        onChange={(e) => setConfig({ ...config, experiencia_anios: e.target.value ? Number(e.target.value) : undefined })}
                                        min={0}
                                    />
                                </div>

                                {/* Certifications */}
                                <div className="space-y-3">
                                    <h4 className="text-sm font-medium text-white">Certificaciones</h4>
                                    <Textarea
                                        value={config.certificaciones || ''}
                                        onChange={(e) => setConfig({ ...config, certificaciones: e.target.value })}
                                        placeholder="Lista de certificaciones, títulos, cursos..."
                                        rows={4}
                                    />
                                </div>
                            </div>

                            {/* Notes */}
                            <div className="space-y-3">
                                <h4 className="text-sm font-medium text-white">Notas Internas</h4>
                                <Textarea
                                    value={config.notas || ''}
                                    onChange={(e) => setConfig({ ...config, notas: e.target.value })}
                                    placeholder="Notas privadas sobre el profesor..."
                                    rows={3}
                                />
                            </div>

                            {(() => {
                                const rol = String(user?.rol || '').toLowerCase();
                                if (!(rol === 'owner' || rol === 'admin')) return null;
                                return (
                                    <div className="space-y-3 pt-4 border-t border-slate-800">
                                        <h4 className="text-sm font-medium text-white flex items-center gap-1">
                                            <User className="w-4 h-4" />
                                            Sucursales del profesor
                                        </h4>
                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                            {sucursales.map((s) => {
                                                const on = editBranches.includes(s.id);
                                                return (
                                                    <button
                                                        key={s.id}
                                                        type="button"
                                                        onClick={() => toggleBranch(s.id, !on)}
                                                        className={cn(
                                                            'h-10 px-3 rounded-xl border text-sm transition-colors text-left',
                                                            on
                                                                ? 'bg-primary-500/20 border-primary-500/40 text-primary-200'
                                                                : 'bg-slate-950/30 border-slate-800/60 text-slate-200 hover:bg-slate-900/40'
                                                        )}
                                                    >
                                                        {s.nombre}
                                                    </button>
                                                );
                                            })}
                                            {!sucursales.length ? <div className="text-sm text-slate-400">Sin sucursales</div> : null}
                                        </div>
                                        <div className="flex justify-end">
                                            <Button onClick={saveBranches} isLoading={branchesSaving} variant="secondary" disabled={!profesor?.usuario_id}>
                                                Guardar sucursales
                                            </Button>
                                        </div>

                                        <div className="border-t border-slate-800 pt-4" />

                                        <h4 className="text-sm font-medium text-white flex items-center gap-1">
                                            <Settings className="w-4 h-4" />
                                            Clases (sucursal actual)
                                        </h4>
                                        {!sucursalActualId ? (
                                            <div className="text-sm text-slate-400">Seleccioná una sucursal para asignar clases.</div>
                                        ) : !editBranches.includes(sucursalActualId) ? (
                                            <div className="text-sm text-slate-400">El profesor no trabaja en la sucursal seleccionada.</div>
                                        ) : clasesLoading ? (
                                            <div className="text-sm text-slate-400">Cargando clases…</div>
                                        ) : (
                                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                                {clases.map((c) => {
                                                    const on = editClases.includes(c.id);
                                                    return (
                                                        <button
                                                            key={c.id}
                                                            type="button"
                                                            onClick={() => toggleClase(c.id, !on)}
                                                            className={cn(
                                                                'h-10 px-3 rounded-xl border text-sm transition-colors text-left',
                                                                on
                                                                    ? 'bg-primary-500/20 border-primary-500/40 text-primary-200'
                                                                    : 'bg-slate-950/30 border-slate-800/60 text-slate-200 hover:bg-slate-900/40'
                                                            )}
                                                        >
                                                            {c.nombre}
                                                        </button>
                                                    );
                                                })}
                                                {!clases.length ? <div className="text-sm text-slate-400">Sin clases</div> : null}
                                            </div>
                                        )}
                                        <div className="flex justify-end">
                                            <Button onClick={saveClases} isLoading={clasesSaving} variant="secondary" disabled={!profesor?.id || !sucursalActualId || !editBranches.includes(sucursalActualId)}>
                                                Guardar clases
                                            </Button>
                                        </div>

                                        <div className="border-t border-slate-800 pt-4" />
                                        <h4 className="text-sm font-medium text-white flex items-center gap-1">
                                            <Settings className="w-4 h-4" />
                                            Permisos (por módulo)
                                        </h4>
                                        <div className="space-y-2">
                                            {permissionModules.filter((m) => isModuleEnabled(m.key)).map((m) => {
                                                const readOn = editScopes.includes(m.read) || (m.write ? editScopes.includes(m.write) : false);
                                                const writeOn = m.write ? editScopes.includes(m.write) : false;
                                                const extra = m.extra;
                                                const configOn = extra ? extra.every((s) => editScopes.includes(s)) : false;
                                                return (
                                                    <div key={m.key} className="flex items-center justify-between gap-3 p-3 rounded-xl border border-slate-800/60 bg-slate-950/20">
                                                        <div className="min-w-0">
                                                            <div className="text-sm font-medium text-white truncate">{m.label}</div>
                                                        </div>
                                                        <div className="flex items-center gap-2">
                                                            <button
                                                                type="button"
                                                                onClick={() => setModuleRead(m.key, m.read, m.write, extra, !readOn)}
                                                                className={cn(
                                                                    'h-9 px-3 rounded-xl border text-xs font-semibold transition-colors',
                                                                    readOn
                                                                        ? 'bg-primary-500/20 border-primary-500/40 text-primary-200'
                                                                        : 'bg-slate-950/30 border-slate-800/60 text-slate-200 hover:bg-slate-900/40'
                                                                )}
                                                            >
                                                                Ver
                                                            </button>
                                                            <button
                                                                type="button"
                                                                disabled={!m.write}
                                                                onClick={() => setModuleWrite(m.key, m.read, m.write, !writeOn)}
                                                                className={cn(
                                                                    'h-9 px-3 rounded-xl border text-xs font-semibold transition-colors',
                                                                    writeOn
                                                                        ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-200'
                                                                        : 'bg-slate-950/30 border-slate-800/60 text-slate-200 hover:bg-slate-900/40',
                                                                    !m.write ? 'opacity-50 cursor-not-allowed hover:bg-slate-950/30' : ''
                                                                )}
                                                            >
                                                                Usar
                                                            </button>
                                                            {extra ? (
                                                                <button
                                                                    type="button"
                                                                    onClick={() => {
                                                                        const next = !configOn;
                                                                        for (const s of extra) toggleScope(s, next);
                                                                        if (next) toggleScope(m.read, true);
                                                                    }}
                                                                    className={cn(
                                                                        'h-9 px-3 rounded-xl border text-xs font-semibold transition-colors',
                                                                        configOn
                                                                            ? 'bg-violet-500/15 border-violet-500/30 text-violet-200'
                                                                            : 'bg-slate-950/30 border-slate-800/60 text-slate-200 hover:bg-slate-900/40'
                                                                    )}
                                                                >
                                                                    Config
                                                                </button>
                                                            ) : null}
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                        <div className="flex justify-end">
                                            <Button onClick={savePerms} isLoading={permsLoading} variant="secondary" disabled={!profesor?.usuario_id}>
                                                Guardar permisos
                                            </Button>
                                        </div>
                                    </div>
                                );
                            })()}

                            {/* Security / Password */}
                            <div className="space-y-3 pt-4 border-t border-slate-800">
                                <h4 className="text-sm font-medium text-white flex items-center gap-1">
                                    <Lock className="w-4 h-4" />
                                    Seguridad (PIN / Contraseña)
                                </h4>
                                <div className="flex gap-2 items-end">
                                    <div className="flex-1">
                                        <Input
                                            type="password"
                                            value={newPassword}
                                            onChange={(e) => setNewPassword(e.target.value)}
                                            placeholder="Nueva contraseña o PIN"
                                        />
                                    </div>
                                    <Button
                                        onClick={handlePasswordChange}
                                        isLoading={passwordLoading}
                                        disabled={!newPassword || newPassword.length < 4}
                                        variant="secondary"
                                    >
                                        Actualizar
                                    </Button>
                                </div>
                                <p className="text-xs text-slate-500">
                                    Esta contraseña se usa para ingresar al panel de gestión y también como PIN de asistencia.
                                </p>
                            </div>

                            {/* Save button */}
                            <div className="flex justify-end pt-4">
                                <Button onClick={handleSaveConfig} isLoading={configLoading}>
                                    <Save className="w-4 h-4 mr-1" />
                                    Guardar Configuración
                                </Button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </Modal>
    );
}

