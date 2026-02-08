'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Copy, KeyRound } from 'lucide-react';
import { Button, Input, Modal, useToast } from '@/components/ui';
import { api, type Sucursal, type TeamMember } from '@/lib/api';
import { cn } from '@/lib/utils';

const permissionModules = [
    { key: 'usuarios', label: 'Usuarios', read: 'usuarios:read', write: 'usuarios:write' },
    { key: 'pagos', label: 'Pagos', read: 'pagos:read', write: 'pagos:write' },
    { key: 'asistencias', label: 'Asistencias', read: 'asistencias:read', write: 'asistencias:write' },
    { key: 'accesos', label: 'Accesos', read: 'accesos:read', write: 'accesos:write' },
    { key: 'clases', label: 'Clases', read: 'clases:read', write: 'clases:write' },
    { key: 'rutinas', label: 'Rutinas', read: 'rutinas:read', write: 'rutinas:write' },
    { key: 'ejercicios', label: 'Ejercicios', read: 'ejercicios:read', write: 'ejercicios:write' },
    { key: 'whatsapp', label: 'WhatsApp', read: 'whatsapp:read', write: 'whatsapp:send', extra: ['whatsapp:config'] },
    { key: 'configuracion', label: 'Configuración', read: 'configuracion:read', write: 'configuracion:write' },
    { key: 'reportes', label: 'Reportes', read: 'reportes:read', write: null },
] as const;

export default function TeamStaffModal({
    isOpen,
    onClose,
    member,
    onRefresh,
}: {
    isOpen: boolean;
    onClose: () => void;
    member: TeamMember | null;
    onRefresh: () => void;
}) {
    const { toast } = useToast();
    const [saving, setSaving] = useState(false);
    const [pinSaving, setPinSaving] = useState(false);
    const [pinDraft, setPinDraft] = useState('');
    const [pinLast, setPinLast] = useState<string>('');

    const [sucursales, setSucursales] = useState<Sucursal[]>([]);
    const [moduleFlags, setModuleFlags] = useState<Record<string, boolean> | null>(null);

    const [editRole, setEditRole] = useState('empleado');
    const [editActive, setEditActive] = useState(true);
    const [editBranches, setEditBranches] = useState<number[]>([]);
    const [editScopes, setEditScopes] = useState<string[]>([]);
    const [editTipo, setEditTipo] = useState<string>('empleado');
    const [editEstado, setEditEstado] = useState<string>('activo');

    const asRecord = (v: unknown): Record<string, unknown> | null => {
        if (!v || typeof v !== 'object') return null;
        return v as Record<string, unknown>;
    };

    useEffect(() => {
        if (!isOpen) return;
        (async () => {
            const [sucRes, bootRes] = await Promise.all([
                api.getSucursales(),
                api.getBootstrap('auto'),
            ]);
            if (sucRes.ok && sucRes.data?.ok) setSucursales((sucRes.data.items || []).filter((s) => !!s.activa));
            else setSucursales([]);
            const flagsObj = asRecord(bootRes.ok ? (bootRes.data?.flags as unknown) : null);
            const modulesCandidate = flagsObj ? flagsObj['modules'] : null;
            const modulesObj = asRecord(modulesCandidate);
            setModuleFlags(modulesObj ? (modulesObj as Record<string, boolean>) : null);
        })();
    }, [isOpen]);

    useEffect(() => {
        if (!isOpen || !member) return;
        setEditRole(member.rol || 'empleado');
        setEditActive(!!member.activo);
        setEditBranches(member.sucursales || []);
        setEditScopes(member.scopes || []);
        setEditTipo(member.staff?.tipo || member.rol || 'empleado');
        setEditEstado(member.staff?.estado || 'activo');
        setPinDraft('');
        setPinLast('');
    }, [isOpen, member]);

    const isModuleEnabled = useCallback((key: string) => {
        if (!moduleFlags) return true;
        if (Object.prototype.hasOwnProperty.call(moduleFlags, key)) return moduleFlags[key] !== false;
        return true;
    }, [moduleFlags]);

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

    const setModuleRead = (key: string, readScope: string, writeScope: string | null, extra: readonly string[] | undefined, enabled: boolean) => {
        if (!isModuleEnabled(key)) return;
        if (enabled) {
            toggleScope(readScope, true);
            return;
        }
        toggleScope(readScope, false);
        if (writeScope) toggleScope(writeScope, false);
        for (const ex of extra || []) toggleScope(ex, false);
    };

    const setModuleWrite = (key: string, readScope: string, writeScope: string | null, enabled: boolean) => {
        if (!isModuleEnabled(key)) return;
        if (!writeScope) return;
        if (enabled) {
            toggleScope(readScope, true);
            toggleScope(writeScope, true);
        } else {
            toggleScope(writeScope, false);
        }
    };

    const toggleBranch = (id: number) => {
        setEditBranches((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
    };

    const disabledScopes = useMemo(() => {
        const disabled = new Set<string>();
        for (const m of permissionModules) {
            if (!isModuleEnabled(m.key)) {
                disabled.add(m.read);
                if (m.write) disabled.add(m.write);
                const extra = 'extra' in m ? m.extra : undefined;
                for (const ex of extra || []) disabled.add(String(ex));
            }
        }
        return disabled;
    }, [isModuleEnabled]);

    const save = async () => {
        if (!member) return;
        setSaving(true);
        try {
            const scopesSanitized = Array.from(new Set(editScopes)).filter((s) => !disabledScopes.has(String(s)));
            const res = await api.updateStaff(member.id, {
                rol: editRole,
                activo: editActive,
                sucursales: editBranches,
                scopes: scopesSanitized,
                tipo: editTipo,
                estado: editEstado,
            });
            if (!res.ok) throw new Error(res.error || 'No se pudo guardar');
            toast({ title: 'Guardado', description: 'Cambios aplicados', variant: 'success' });
            onClose();
            onRefresh();
        } catch (e) {
            toast({
                title: 'No se pudo guardar',
                description: e instanceof Error ? e.message : 'Error inesperado',
                variant: 'error',
            });
        } finally {
            setSaving(false);
        }
    };

    const copyToClipboard = async (text: string) => {
        try {
            await navigator.clipboard.writeText(text);
            toast({ title: 'Copiado', description: 'PIN copiado al portapapeles', variant: 'success' });
        } catch {
            toast({ title: 'No se pudo copiar', description: 'Copiá manualmente el PIN', variant: 'error' });
        }
    };

    const generatePin = async () => {
        if (!member) return;
        setPinSaving(true);
        try {
            const res = await api.resetUsuarioPin(member.id);
            if (!res.ok || !res.data?.ok) throw new Error(res.error || res.data?.error || 'No se pudo generar el PIN');
            setPinLast(String(res.data.pin || ''));
            toast({ title: 'PIN generado', description: 'Guardalo: no se vuelve a mostrar', variant: 'success' });
        } catch (e) {
            toast({
                title: 'No se pudo generar PIN',
                description: e instanceof Error ? e.message : 'Error inesperado',
                variant: 'error',
            });
        } finally {
            setPinSaving(false);
        }
    };

    const setPin = async () => {
        if (!member) return;
        const pin = String(pinDraft || '').trim();
        if (!pin) {
            toast({ title: 'Falta PIN', description: 'Ingresá un PIN', variant: 'error' });
            return;
        }
        setPinSaving(true);
        try {
            const res = await api.resetUsuarioPin(member.id, pin);
            if (!res.ok || !res.data?.ok) throw new Error(res.error || res.data?.error || 'No se pudo actualizar el PIN');
            setPinLast(String(res.data.pin || pin));
            toast({ title: 'PIN actualizado', description: 'Guardalo: no se vuelve a mostrar', variant: 'success' });
            setPinDraft('');
        } catch (e) {
            toast({
                title: 'No se pudo actualizar PIN',
                description: e instanceof Error ? e.message : 'Error inesperado',
                variant: 'error',
            });
        } finally {
            setPinSaving(false);
        }
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={member ? `Editar staff: ${member.nombre}` : 'Editar staff'}
            size="lg"
            footer={
                <div className="flex justify-end gap-2">
                    <Button variant="secondary" onClick={onClose} disabled={saving}>
                        Cerrar
                    </Button>
                    <Button onClick={() => void save()} isLoading={saving}>
                        Guardar
                    </Button>
                </div>
            }
        >
            <div className="p-6 space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <div className="text-sm font-medium text-slate-200">Rol</div>
                        <select
                            className="w-full h-10 rounded-xl bg-slate-950/40 border border-slate-800/60 text-slate-200 px-3 outline-none focus:ring-2 focus:ring-primary-500/40"
                            value={editRole}
                            onChange={(e) => setEditRole(e.target.value)}
                        >
                            <option value="empleado">Empleado</option>
                            <option value="recepcionista">Recepcionista</option>
                            <option value="profesor">Profesor</option>
                            <option value="admin">Admin</option>
                        </select>
                    </div>
                    <div className="space-y-2">
                        <div className="text-sm font-medium text-slate-200">Activo</div>
                        <select
                            className="w-full h-10 rounded-xl bg-slate-950/40 border border-slate-800/60 text-slate-200 px-3 outline-none focus:ring-2 focus:ring-primary-500/40"
                            value={editActive ? 'activo' : 'inactivo'}
                            onChange={(e) => setEditActive(e.target.value === 'activo')}
                        >
                            <option value="activo">Activo</option>
                            <option value="inactivo">Inactivo</option>
                        </select>
                    </div>
                    <div className="space-y-2">
                        <div className="text-sm font-medium text-slate-200">Tipo</div>
                        <select
                            className="w-full h-10 rounded-xl bg-slate-950/40 border border-slate-800/60 text-slate-200 px-3 outline-none focus:ring-2 focus:ring-primary-500/40"
                            value={editTipo}
                            onChange={(e) => setEditTipo(e.target.value)}
                        >
                            <option value="empleado">Empleado</option>
                            <option value="recepcionista">Recepcionista</option>
                            <option value="staff">Staff</option>
                            <option value="profesor">Profesor</option>
                        </select>
                    </div>
                    <div className="space-y-2">
                        <div className="text-sm font-medium text-slate-200">Estado</div>
                        <select
                            className="w-full h-10 rounded-xl bg-slate-950/40 border border-slate-800/60 text-slate-200 px-3 outline-none focus:ring-2 focus:ring-primary-500/40"
                            value={editEstado}
                            onChange={(e) => setEditEstado(e.target.value)}
                        >
                            <option value="activo">Activo</option>
                            <option value="inactivo">Inactivo</option>
                        </select>
                    </div>
                </div>

                <div className="space-y-2">
                    <div className="text-sm font-medium text-slate-200">Sucursales asignadas</div>
                    <div className="flex flex-wrap gap-2">
                        {sucursales.map((s) => (
                            <button
                                key={s.id}
                                type="button"
                                onClick={() => toggleBranch(s.id)}
                                className={cn(
                                    'px-3 py-1.5 rounded-xl text-sm border transition-colors',
                                    editBranches.includes(s.id)
                                        ? 'bg-primary-500/20 border-primary-500/40 text-primary-200'
                                        : 'bg-slate-950/30 border-slate-800/60 text-slate-300 hover:bg-slate-900/40'
                                )}
                            >
                                {s.nombre}
                            </button>
                        ))}
                        {!sucursales.length ? <div className="text-sm text-slate-500">No hay sucursales</div> : null}
                    </div>
                </div>

                <div className="space-y-3">
                    <div className="text-sm font-medium text-slate-200">Permisos</div>
                    <div className="space-y-2">
                        {permissionModules.map((m) => {
                            const readOn = editScopes.includes(m.read);
                            const writeOn = m.write ? editScopes.includes(m.write) : false;
                            const enabled = isModuleEnabled(m.key);
                            const extra = 'extra' in m ? m.extra : undefined;
                            return (
                                <div key={m.key} className="flex items-center justify-between rounded-xl border border-slate-800/60 bg-slate-950/30 p-3">
                                    <div className={cn('text-sm font-medium', enabled ? 'text-slate-200' : 'text-slate-500')}>{m.label}</div>
                                    <div className="flex items-center gap-4">
                                        <label className={cn('flex items-center gap-2 text-xs', enabled ? 'text-slate-300' : 'text-slate-600')}>
                                            <input
                                                type="checkbox"
                                                checked={readOn}
                                                disabled={!enabled}
                                                onChange={(e) => setModuleRead(m.key, m.read, m.write, extra, e.target.checked)}
                                            />
                                            Ver
                                        </label>
                                        {m.write ? (
                                            <label className={cn('flex items-center gap-2 text-xs', enabled ? 'text-slate-300' : 'text-slate-600')}>
                                                <input
                                                    type="checkbox"
                                                    checked={writeOn}
                                                    disabled={!enabled}
                                                    onChange={(e) => setModuleWrite(m.key, m.read, m.write, e.target.checked)}
                                                />
                                                Editar
                                            </label>
                                        ) : null}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                <div className="space-y-3">
                    <div className="text-sm font-medium text-slate-200">PIN</div>
                    {pinLast ? (
                        <div className="flex items-center justify-between rounded-xl border border-slate-800/60 bg-slate-950/30 p-3">
                            <div className="text-sm text-slate-200">{pinLast}</div>
                            <Button size="sm" variant="secondary" leftIcon={<Copy className="w-4 h-4" />} onClick={() => void copyToClipboard(pinLast)}>
                                Copiar
                            </Button>
                        </div>
                    ) : (
                        <div className="text-xs text-slate-500">Generá o seteá un PIN para este usuario.</div>
                    )}
                    <div className="flex flex-wrap items-center gap-2">
                        <Button size="sm" variant="secondary" leftIcon={<KeyRound className="w-4 h-4" />} onClick={() => void generatePin()} isLoading={pinSaving}>
                            Generar PIN
                        </Button>
                        <div className="flex items-center gap-2">
                            <Input value={pinDraft} onChange={(e) => setPinDraft(e.target.value)} placeholder="Nuevo PIN" />
                            <Button size="sm" onClick={() => void setPin()} isLoading={pinSaving}>
                                Guardar PIN
                            </Button>
                        </div>
                    </div>
                </div>
            </div>
        </Modal>
    );
}
