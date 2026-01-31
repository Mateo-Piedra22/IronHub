'use client';

import { useEffect, useMemo, useState } from 'react';
import { Briefcase, Copy, KeyRound, RefreshCw, Search, Shield } from 'lucide-react';
import { Button, Input, Modal, useToast } from '@/components/ui';
import { api, type StaffItem, type Sucursal } from '@/lib/api';
import { cn } from '@/lib/utils';

const roleOptions = [
    { value: 'empleado', label: 'Empleado' },
    { value: 'recepcionista', label: 'Recepcionista' },
    { value: 'profesor', label: 'Profesor' },
    { value: 'admin', label: 'Admin' },
];

const permissionModules = [
    { key: 'usuarios', label: 'Usuarios', read: 'usuarios:read', write: 'usuarios:write' },
    { key: 'pagos', label: 'Pagos', read: 'pagos:read', write: 'pagos:write' },
    { key: 'asistencias', label: 'Asistencias', read: 'asistencias:read', write: 'asistencias:write' },
    { key: 'clases', label: 'Clases', read: 'clases:read', write: 'clases:write' },
    { key: 'rutinas', label: 'Rutinas', read: 'rutinas:read', write: 'rutinas:write' },
    { key: 'ejercicios', label: 'Ejercicios', read: 'ejercicios:read', write: 'ejercicios:write' },
    { key: 'whatsapp', label: 'WhatsApp', read: 'whatsapp:read', write: 'whatsapp:send', extra: ['whatsapp:config'] },
    { key: 'configuracion', label: 'Configuración', read: 'configuracion:read', write: 'configuracion:write' },
    { key: 'reportes', label: 'Reportes', read: 'reportes:read', write: null },
] as const;

export default function EmpleadosPage() {
    const { toast } = useToast();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [pinSaving, setPinSaving] = useState(false);
    const [pinDraft, setPinDraft] = useState('');
    const [pinLast, setPinLast] = useState<string>('');
    const [search, setSearch] = useState('');
    const [items, setItems] = useState<StaffItem[]>([]);
    const [sucursales, setSucursales] = useState<Sucursal[]>([]);
    const [moduleFlags, setModuleFlags] = useState<Record<string, boolean> | null>(null);
    const [open, setOpen] = useState(false);
    const [selected, setSelected] = useState<StaffItem | null>(null);
    const [editRole, setEditRole] = useState('empleado');
    const [editActive, setEditActive] = useState(true);
    const [editBranches, setEditBranches] = useState<number[]>([]);
    const [editScopes, setEditScopes] = useState<string[]>([]);
    const [editTipo, setEditTipo] = useState<string>('empleado');
    const [editEstado, setEditEstado] = useState<string>('activo');

    const filtered = useMemo(() => {
        const t = search.trim().toLowerCase();
        if (!t) return items;
        return items.filter((i) => {
            return (
                i.nombre.toLowerCase().includes(t) ||
                (i.dni || '').toLowerCase().includes(t) ||
                (i.email || '').toLowerCase().includes(t) ||
                (i.rol || '').toLowerCase().includes(t)
            );
        });
    }, [items, search]);

    const load = async () => {
        setLoading(true);
        try {
            const [staffRes, sucRes, bootRes] = await Promise.all([
                api.getStaff('', { all: false }),
                api.getSucursales(),
                api.getBootstrap('auto'),
            ]);
            if (!staffRes.ok) throw new Error(staffRes.error || 'Error cargando staff');
            if (!sucRes.ok) throw new Error(sucRes.error || 'Error cargando sucursales');
            setItems(staffRes.data?.items || []);
            setSucursales((sucRes.data?.items || []).filter((s) => !!s.activa));
            if (bootRes.ok && (bootRes.data as any)?.flags?.modules) {
                setModuleFlags(((bootRes.data as any).flags.modules || null) as any);
            } else {
                setModuleFlags(null);
            }
        } catch (e) {
            toast({
                title: 'No se pudo cargar empleados',
                description: e instanceof Error ? e.message : 'Error inesperado',
                variant: 'error',
            });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(() => {
        const handler = () => void load();
        window.addEventListener('ironhub:sucursal-changed', handler as any);
        return () => window.removeEventListener('ironhub:sucursal-changed', handler as any);
    }, []);

    const openEdit = (item: StaffItem) => {
        setSelected(item);
        setEditRole(item.rol || 'empleado');
        setEditActive(!!item.activo);
        setEditBranches(item.sucursales || []);
        setEditScopes(item.scopes || []);
        setEditTipo(item.staff?.tipo || item.rol || 'empleado');
        setEditEstado(item.staff?.estado || 'activo');
        setPinDraft('');
        setPinLast('');
        setOpen(true);
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

    const isModuleEnabled = (key: string) => {
        if (!moduleFlags) return true;
        if (Object.prototype.hasOwnProperty.call(moduleFlags, key)) return moduleFlags[key] !== false;
        return true;
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

    const save = async () => {
        if (!selected) return;
        setSaving(true);
        try {
            const disabled = new Set<string>();
            for (const m of permissionModules) {
                if (!isModuleEnabled(m.key)) {
                    disabled.add(m.read);
                    if (m.write) disabled.add(m.write);
                    for (const ex of (m as any).extra || []) disabled.add(String(ex));
                }
            }
            const scopesSanitized = Array.from(new Set(editScopes)).filter((s) => !disabled.has(String(s)));
            const res = await api.updateStaff(selected.id, {
                rol: editRole,
                activo: editActive,
                sucursales: editBranches,
                scopes: scopesSanitized,
                tipo: editTipo,
                estado: editEstado,
            } as any);
            if (!res.ok) throw new Error(res.error || 'No se pudo guardar');
            toast({ title: 'Guardado', description: 'Cambios aplicados', variant: 'success' });
            setOpen(false);
            await load();
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
        if (!selected) return;
        setPinSaving(true);
        try {
            const res = await api.resetUsuarioPin(selected.id);
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
        if (!selected) return;
        const pin = String(pinDraft || '').trim();
        if (!pin) {
            toast({ title: 'Falta PIN', description: 'Ingresá un PIN', variant: 'error' });
            return;
        }
        setPinSaving(true);
        try {
            const res = await api.resetUsuarioPin(selected.id, pin);
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
        <div className="p-6 space-y-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-primary-500/20 text-primary-300 flex items-center justify-center">
                        <Briefcase className="w-5 h-5" />
                    </div>
                    <div>
                        <h1 className="text-xl font-semibold text-white">Empleados</h1>
                        <p className="text-sm text-slate-400">Asignaciones por sucursal y permisos finos.</p>
                    </div>
                </div>
                <div className="flex gap-2">
                    <Button
                        variant="secondary"
                        onClick={() => {
                            void load();
                        }}
                        leftIcon={<RefreshCw className="w-4 h-4" />}
                        disabled={loading}
                    >
                        Refrescar
                    </Button>
                </div>
            </div>

            <div className="flex items-center gap-3">
                <div className="w-full max-w-md">
                    <Input
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        leftIcon={<Search className="w-4 h-4" />}
                        placeholder="Buscar por nombre, DNI, email o rol"
                    />
                </div>
            </div>

            <div className="rounded-2xl border border-slate-800/60 bg-slate-900/40 backdrop-blur-lg overflow-hidden">
                <div className="grid grid-cols-12 gap-3 px-4 py-3 border-b border-slate-800/60 text-xs font-semibold text-slate-400">
                    <div className="col-span-5">Usuario</div>
                    <div className="col-span-2">Rol</div>
                    <div className="col-span-2">Sucursales</div>
                    <div className="col-span-1">Activo</div>
                    <div className="col-span-2 text-right">Acciones</div>
                </div>
                {loading ? (
                    <div className="p-4 text-sm text-slate-400">Cargando…</div>
                ) : filtered.length === 0 ? (
                    <div className="p-4 text-sm text-slate-400">Sin resultados.</div>
                ) : (
                    <div className="divide-y divide-slate-800/60">
                        {filtered.map((u) => (
                            <div key={u.id} className="grid grid-cols-12 gap-3 px-4 py-3 items-center">
                                <div className="col-span-5">
                                    <div className="text-sm font-medium text-white">{u.nombre}</div>
                                    <div className="text-xs text-slate-400">{u.dni || '—'} {u.email ? `• ${u.email}` : ''}</div>
                                </div>
                                <div className="col-span-2 text-sm text-slate-200">{u.rol}</div>
                                <div className="col-span-2 text-sm text-slate-200">{(u.sucursales || []).length}</div>
                                <div className="col-span-1 text-sm text-slate-200">{u.activo ? 'Sí' : 'No'}</div>
                                <div className="col-span-2 text-right">
                                    <Button size="sm" variant="secondary" leftIcon={<Shield className="w-4 h-4" />} onClick={() => openEdit(u)}>
                                        Editar
                                    </Button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <Modal
                isOpen={open}
                onClose={() => setOpen(false)}
                title="Editar empleado"
                description={selected ? `${selected.nombre} (${selected.dni || 'sin DNI'})` : undefined}
                size="lg"
                footer={
                    <div className="flex justify-end gap-2">
                        <Button variant="secondary" onClick={() => setOpen(false)} disabled={saving}>
                            Cancelar
                        </Button>
                        <Button onClick={save} isLoading={saving}>
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
                                {roleOptions.map((o) => (
                                    <option key={o.value} value={o.value}>
                                        {o.label}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div className="space-y-2">
                            <div className="text-sm font-medium text-slate-200">Activo</div>
                            <select
                                className="w-full h-10 rounded-xl bg-slate-950/40 border border-slate-800/60 text-slate-200 px-3 outline-none focus:ring-2 focus:ring-primary-500/40"
                                value={editActive ? 'true' : 'false'}
                                onChange={(e) => setEditActive(e.target.value === 'true')}
                            >
                                <option value="true">Sí</option>
                                <option value="false">No</option>
                            </select>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <div className="text-sm font-medium text-slate-200">Tipo</div>
                            <Input value={editTipo} onChange={(e) => setEditTipo(e.target.value)} placeholder="empleado / recepcionista" />
                        </div>
                        <div className="space-y-2">
                            <div className="text-sm font-medium text-slate-200">Estado</div>
                            <Input value={editEstado} onChange={(e) => setEditEstado(e.target.value)} placeholder="activo / inactivo" />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <div className="text-sm font-medium text-slate-200">Sucursales asignadas</div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            {sucursales.map((s) => (
                                <button
                                    key={s.id}
                                    type="button"
                                    onClick={() => toggleBranch(s.id)}
                                    className={[
                                        'h-10 px-3 rounded-xl border text-left transition-colors',
                                        editBranches.includes(s.id)
                                            ? 'bg-primary-500/20 border-primary-500/40 text-primary-200'
                                            : 'bg-slate-950/30 border-slate-800/60 text-slate-200 hover:bg-slate-900/40',
                                    ].join(' ')}
                                >
                                    {s.nombre}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="space-y-3">
                        <div className="text-sm font-medium text-slate-200">Permisos</div>
                        <div className="space-y-2">
                            {permissionModules.filter((m) => isModuleEnabled(m.key)).map((m) => {
                                const readOn = editScopes.includes(m.read) || (m.write ? editScopes.includes(m.write) : false);
                                const writeOn = m.write ? editScopes.includes(m.write) : false;
                                const extra = (m as any).extra as readonly string[] | undefined;
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
                    </div>

                    <div className="space-y-3 pt-4 border-t border-slate-800/60">
                        <div className="flex items-center gap-2 text-sm font-medium text-slate-200">
                            <KeyRound className="w-4 h-4 text-slate-400" />
                            Seguridad (PIN)
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div className="space-y-2">
                                <div className="text-xs text-slate-400">Setear PIN manual</div>
                                <Input
                                    value={pinDraft}
                                    onChange={(e) => setPinDraft(e.target.value)}
                                    placeholder="Ej: 1234 o 123456"
                                />
                                <Button
                                    variant="secondary"
                                    onClick={setPin}
                                    isLoading={pinSaving}
                                    disabled={!selected}
                                >
                                    Aplicar PIN
                                </Button>
                            </div>
                            <div className="space-y-2">
                                <div className="text-xs text-slate-400">Generar PIN</div>
                                <Button
                                    variant="secondary"
                                    onClick={generatePin}
                                    isLoading={pinSaving}
                                    disabled={!selected}
                                >
                                    Generar nuevo PIN
                                </Button>
                                {pinLast ? (
                                    <div className="flex items-center justify-between gap-2 p-3 rounded-xl bg-slate-950/30 border border-slate-800/60">
                                        <div className="text-sm text-slate-200 font-mono">{pinLast}</div>
                                        <Button size="sm" variant="secondary" onClick={() => copyToClipboard(pinLast)} leftIcon={<Copy className="w-4 h-4" />}>
                                            Copiar
                                        </Button>
                                    </div>
                                ) : (
                                    <div className="text-xs text-slate-500">
                                        El PIN solo se muestra después de generar/actualizar.
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </Modal>
        </div>
    );
}
