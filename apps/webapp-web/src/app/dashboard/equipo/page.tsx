'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Plus, Search, UsersRound } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api, type Profesor, type TeamImpact, type TeamMember } from '@/lib/api';
import { Button, ConfirmModal, Input, Modal, useToast } from '@/components/ui';
import ProfesorDetailModal from '@/components/ProfesorDetailModal';
import TeamStaffModal from '@/components/TeamStaffModal';

export default function EquipoPage() {
    const [sucursalActualId, setSucursalActualId] = useState<number | null>(null);
    const [loadingSucursal, setLoadingSucursal] = useState(false);
    const [loading, setLoading] = useState(false);
    const [errorGeneral, setErrorGeneral] = useState('');
    const [search, setSearch] = useState('');
    const [items, setItems] = useState<TeamMember[]>([]);
    const [tab, setTab] = useState<'todos' | 'profesores' | 'staff'>('todos');
    const { toast } = useToast();

    const [createOpen, setCreateOpen] = useState(false);
    const [createSaving, setCreateSaving] = useState(false);
    const [createKind, setCreateKind] = useState<'staff' | 'profesor'>('staff');
    const [createMode, setCreateMode] = useState<'nuevo' | 'existente'>('nuevo');
    const [createNombre, setCreateNombre] = useState('');
    const [createDni, setCreateDni] = useState('');
    const [createTelefono, setCreateTelefono] = useState('');
    const [createRol, setCreateRol] = useState<'empleado' | 'recepcionista' | 'staff' | 'profesor'>('empleado');
    const [existingSearch, setExistingSearch] = useState('');
    const [existingLoading, setExistingLoading] = useState(false);
    const [existingUsers, setExistingUsers] = useState<Array<{ id: number; nombre: string; dni?: string; email?: string }>>([]);
    const [existingUserId, setExistingUserId] = useState<number | null>(null);

    const [staffEditOpen, setStaffEditOpen] = useState(false);
    const [staffEditMember, setStaffEditMember] = useState<TeamMember | null>(null);
    const [profesorEditOpen, setProfesorEditOpen] = useState(false);
    const [profesorEditProfesor, setProfesorEditProfesor] = useState<Profesor | null>(null);

    const [userEditOpen, setUserEditOpen] = useState(false);
    const [userEditSaving, setUserEditSaving] = useState(false);
    const [userEditMember, setUserEditMember] = useState<TeamMember | null>(null);
    const [userEditNombre, setUserEditNombre] = useState('');
    const [userEditDni, setUserEditDni] = useState('');
    const [userEditTelefono, setUserEditTelefono] = useState('');

    const [confirmOpen, setConfirmOpen] = useState(false);
    const [confirmLoading, setConfirmLoading] = useState(false);
    const [confirmTitle, setConfirmTitle] = useState('');
    const [confirmMessage, setConfirmMessage] = useState('');
    const [confirmText, setConfirmText] = useState('Confirmar');
    const [confirmVariant, setConfirmVariant] = useState<'danger' | 'warning' | 'info'>('warning');
    const [pendingConvert, setPendingConvert] = useState<null | { usuario_id: number; target: 'staff' | 'profesor' | 'usuario'; rol?: string; force?: boolean }>(null);
    const [pendingDeleteProfile, setPendingDeleteProfile] = useState<null | { usuario_id: number; kind: 'staff' | 'profesor'; force?: boolean }>(null);

    const tabs = useMemo(
        () => [
            { key: 'todos' as const, label: 'Todos' },
            { key: 'profesores' as const, label: 'Profesores' },
            { key: 'staff' as const, label: 'Staff' },
        ],
        []
    );

    const loadSucursalActual = useCallback(async () => {
        setLoadingSucursal(true);
        try {
            const r = await api.getSucursales();
            if (r.ok && r.data?.ok) {
                setSucursalActualId(r.data.sucursal_actual_id ?? null);
            } else {
                setSucursalActualId(null);
            }
        } finally {
            setLoadingSucursal(false);
        }
    }, []);

    const load = useCallback(async () => {
        setLoading(true);
        setErrorGeneral('');
        try {
            const r = await api.getTeam({
                search: search || undefined,
                all: !sucursalActualId,
                sucursal_id: sucursalActualId || undefined,
            });
            if (r.ok && r.data?.ok) setItems((r.data.items || []) as TeamMember[]);
            else setErrorGeneral(r.error || 'No se pudo cargar equipo');
        } catch (e) {
            setErrorGeneral(String(e) || 'No se pudieron cargar datos');
        } finally {
            setLoading(false);
        }
    }, [sucursalActualId, search]);

    useEffect(() => {
        loadSucursalActual();
    }, [loadSucursalActual]);

    useEffect(() => {
        load();
    }, [load]);

    useEffect(() => {
        const handler = () => loadSucursalActual();
        const eventName = 'ironhub:sucursal-changed' as unknown as keyof WindowEventMap;
        window.addEventListener(eventName, handler);
        return () => window.removeEventListener(eventName, handler);
    }, [loadSucursalActual]);

    const filtered = useMemo(() => {
        if (tab === 'todos') return items;
        if (tab === 'profesores') return items.filter((i) => i.profesor != null);
        return items.filter((i) => i.staff != null || i.kind === 'staff');
    }, [items, tab]);

    const openUserEdit = (m: TeamMember) => {
        setUserEditMember(m);
        setUserEditNombre(m.nombre || '');
        setUserEditDni(m.dni || '');
        setUserEditTelefono(m.telefono || '');
        setUserEditOpen(true);
    };

    const saveUserEdit = async () => {
        if (!userEditMember) return;
        setUserEditSaving(true);
        try {
            const payload = {
                nombre: String(userEditNombre || '').trim(),
                dni: String(userEditDni || '').trim(),
                telefono: String(userEditTelefono || '').trim(),
            };
            const res = await api.updateUsuario(userEditMember.id, payload);
            if (!res.ok) throw new Error(res.error || 'No se pudo guardar');
            toast({ title: 'Guardado', description: 'Datos actualizados', variant: 'success' });
            setUserEditOpen(false);
            setUserEditMember(null);
            await load();
        } catch (e) {
            toast({
                title: 'No se pudo guardar',
                description: e instanceof Error ? e.message : 'Error inesperado',
                variant: 'error',
            });
        } finally {
            setUserEditSaving(false);
        }
    };

    const convertMember = async (data: { usuario_id: number; target: 'staff' | 'profesor' | 'usuario'; rol?: string; force?: boolean }) => {
        const res = await api.convertTeamMember(data);
        if (!res.ok || !res.data?.ok) {
            const msg = res.error || res.data?.error || 'No se pudo actualizar';
            throw new Error(msg);
        }
    };

    const deleteProfile = async (data: { usuario_id: number; kind: 'staff' | 'profesor'; force?: boolean }) => {
        const res = await api.deleteTeamProfile(data);
        if (!res.ok || !res.data?.ok) {
            const msg = res.error || res.data?.error || 'No se pudo eliminar el perfil';
            throw new Error(msg);
        }
    };

    const openConvertConfirm = async (member: TeamMember, data: { target: 'staff' | 'profesor' | 'usuario'; rol?: string }) => {
        try {
            const impactRes = await api.getTeamImpact(member.id);
            const impact: TeamImpact | null = impactRes.ok && impactRes.data?.ok ? (impactRes.data as TeamImpact) : null;

            if (impact?.profesor?.exists && data.target !== 'profesor') {
                const sesiones = Number(impact.profesor.sesiones_activas || 0);
                if (sesiones > 0) {
                    toast({
                        title: 'No se puede convertir',
                        description: `Tiene ${sesiones} sesión activa. Cerrala antes de continuar.`,
                        variant: 'error',
                    });
                    return;
                }
            }
            if (data.target !== 'staff') {
                const sesionesStaff = Number(impact?.staff?.sesiones_activas || 0);
                if (sesionesStaff > 0) {
                    toast({
                        title: 'No se puede convertir',
                        description: `Tiene ${sesionesStaff} sesión de staff activa. Cerrala antes de continuar.`,
                        variant: 'error',
                    });
                    return;
                }
            }

            let title = 'Confirmar';
            let message = '¿Confirmás la acción?';
            let variant: 'danger' | 'warning' | 'info' = 'warning';
            let confirmTextLocal = 'Confirmar';
            let force = false;

            if (data.target === 'staff') {
                title = 'Convertir a staff';
                message = `Convertir a "${member.nombre}" a staff (rol: ${data.rol || 'empleado'}).`;
                confirmTextLocal = 'Convertir';
                variant = 'warning';
                const clases = Number(impact?.profesor?.clases_asignadas_activas || 0);
                if (clases > 0) {
                    force = true;
                    message = `${message}\nTiene ${clases} clase(s) asignada(s). Se desactivarán esas asignaciones.`;
                }
            } else if (data.target === 'profesor') {
                title = 'Convertir a profesor';
                message = `Convertir a "${member.nombre}" a profesor.`;
                confirmTextLocal = 'Convertir';
                variant = 'warning';
                const scopes = Number(impact?.staff?.scopes_count || 0);
                const sucursales = Number(impact?.staff?.sucursales_count || 0);
                const parts: string[] = [];
                if (scopes > 0) parts.push(`${scopes} permiso(s)`);
                if (sucursales > 0) parts.push(`${sucursales} sucursal(es)`);
                if (parts.length) {
                    message = `${message}\nSe va a desactivar staff y limpiar: ${parts.join(', ')}.`;
                }
            } else if (data.target === 'usuario') {
                title = 'Quitar del equipo';
                message = `Quitar a "${member.nombre}" del equipo (vuelve a usuario normal).`;
                confirmTextLocal = 'Quitar';
                variant = 'danger';
                const clases = Number(impact?.profesor?.clases_asignadas_activas || 0);
                const scopes = Number(impact?.staff?.scopes_count || 0);
                const sucursales = Number(impact?.staff?.sucursales_count || 0);
                const parts: string[] = [];
                if (clases > 0) parts.push(`${clases} clase(s) asignada(s)`);
                if (scopes > 0) parts.push(`${scopes} permiso(s)`);
                if (sucursales > 0) parts.push(`${sucursales} sucursal(es)`);
                if (parts.length) {
                    force = clases > 0;
                    message = `${message}\nSe van a limpiar: ${parts.join(', ')}.`;
                }
            }

            setConfirmTitle(title);
            setConfirmMessage(message);
            setConfirmVariant(variant);
            setConfirmText(confirmTextLocal);
            setPendingConvert({ usuario_id: member.id, target: data.target, rol: data.rol, force });
            setPendingDeleteProfile(null);
            setConfirmOpen(true);
        } catch {
            toast({ title: 'Error', description: 'No se pudo evaluar el impacto', variant: 'error' });
        }
    };

    const openDeleteProfileConfirm = async (member: TeamMember, kind: 'staff' | 'profesor') => {
        try {
            const impactRes = await api.getTeamImpact(member.id);
            const impact: TeamImpact | null = impactRes.ok && impactRes.data?.ok ? (impactRes.data as TeamImpact) : null;

            if (kind === 'profesor') {
                const sesiones = Number(impact?.profesor?.sesiones_activas || 0);
                if (sesiones > 0) {
                    toast({
                        title: 'No se puede eliminar',
                        description: `Tiene ${sesiones} sesión activa. Cerrala antes de continuar.`,
                        variant: 'error',
                    });
                    return;
                }
            } else {
                const sesionesStaff = Number(impact?.staff?.sesiones_activas || 0);
                if (sesionesStaff > 0) {
                    toast({
                        title: 'No se puede eliminar',
                        description: `Tiene ${sesionesStaff} sesión de staff activa. Cerrala antes de continuar.`,
                        variant: 'error',
                    });
                    return;
                }
            }

            let force = false;
            let message = `Eliminar el perfil de ${kind} de "${member.nombre}".`;
            if (kind === 'profesor') {
                const clases = Number(impact?.profesor?.clases_asignadas_activas || 0);
                if (clases > 0) {
                    force = true;
                    message = `${message}\nTiene ${clases} clase(s) asignada(s). Se desactivarán esas asignaciones.`;
                }
                message = `${message}\nEsta acción puede borrar datos asociados (horarios/sesiones).`;
            } else {
                const scopes = Number(impact?.staff?.scopes_count || 0);
                const sucursales = Number(impact?.staff?.sucursales_count || 0);
                const parts: string[] = [];
                if (scopes > 0) parts.push(`${scopes} permiso(s)`);
                if (sucursales > 0) parts.push(`${sucursales} sucursal(es)`);
                if (parts.length) message = `${message}\nSe van a eliminar: ${parts.join(', ')}.`;
                message = `${message}\nEsta acción puede borrar datos asociados (sesiones).`;
            }

            setConfirmTitle(`Eliminar perfil ${kind}`);
            setConfirmMessage(message);
            setConfirmVariant('danger');
            setConfirmText('Eliminar');
            setPendingDeleteProfile({ usuario_id: member.id, kind, force });
            setPendingConvert(null);
            setConfirmOpen(true);
        } catch {
            toast({ title: 'Error', description: 'No se pudo evaluar el impacto', variant: 'error' });
        }
    };

    const runConfirm = async () => {
        if (!pendingConvert && !pendingDeleteProfile) return;
        setConfirmLoading(true);
        try {
            if (pendingConvert) {
                await convertMember(pendingConvert);
                toast({ title: 'Actualizado', description: 'Cambios aplicados', variant: 'success' });
            } else if (pendingDeleteProfile) {
                await deleteProfile(pendingDeleteProfile);
                toast({ title: 'Actualizado', description: 'Perfil eliminado', variant: 'success' });
            }
            setConfirmOpen(false);
            setPendingConvert(null);
            setPendingDeleteProfile(null);
            await load();
        } catch (e) {
            toast({
                title: 'Error',
                description: e instanceof Error ? e.message : 'No se pudo actualizar',
                variant: 'error',
            });
            setConfirmOpen(false);
            setPendingConvert(null);
            setPendingDeleteProfile(null);
        } finally {
            setConfirmLoading(false);
        }
    };

    const searchUsuariosExistentes = async () => {
        const term = String(existingSearch || '').trim();
        if (!term) {
            setExistingUsers([]);
            return;
        }
        setExistingLoading(true);
        try {
            const res = await api.getUsuarios({ search: term, limit: 10 });
            if (res.ok && res.data?.usuarios) {
                const mapped = (res.data.usuarios || []).map((u) => ({
                    id: u.id,
                    nombre: u.nombre,
                    dni: u.dni,
                    email: u.email,
                }));
                setExistingUsers(mapped);
            } else {
                setExistingUsers([]);
            }
        } catch {
            setExistingUsers([]);
        } finally {
            setExistingLoading(false);
        }
    };

    const createOrPromote = async () => {
        setCreateSaving(true);
        try {
            if (createMode === 'existente') {
                if (!existingUserId) throw new Error('Seleccioná un usuario existente');
                const res = await api.convertTeamMember({
                    usuario_id: existingUserId,
                    target: createKind,
                    rol: createKind === 'staff' ? createRol : undefined,
                });
                if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo asociar');
            } else {
                if (createKind === 'staff') {
                    const nombre = createNombre.trim();
                    const dni = createDni.trim();
                    const telefono = createTelefono.trim();
                    if (!nombre || !dni) throw new Error('Nombre y DNI son obligatorios');
                    const r = await api.createUsuario({ nombre, dni, telefono, rol: createRol });
                    if (!r.ok || !r.data?.id) throw new Error(r.error || 'No se pudo crear el usuario');
                    const res = await api.convertTeamMember({
                        usuario_id: r.data.id,
                        target: 'staff',
                        rol: createRol,
                    });
                    if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo asociar');
                } else {
                    const nombre = createNombre.trim();
                    const telefono = createTelefono.trim();
                    if (!nombre) throw new Error('Nombre es obligatorio');
                    const res = await api.createProfesor({ nombre, telefono });
                    if (!res.ok) throw new Error(res.error || 'No se pudo crear el profesor');
                }
            }

            toast({ title: 'Guardado', description: 'Equipo actualizado', variant: 'success' });
            setCreateOpen(false);
            setCreateSaving(false);
            setCreateNombre('');
            setCreateDni('');
            setCreateTelefono('');
            setCreateRol('empleado');
            setCreateKind('staff');
            setCreateMode('nuevo');
            setExistingSearch('');
            setExistingUsers([]);
            setExistingUserId(null);
            await load();
        } catch (e) {
            toast({
                title: 'No se pudo guardar',
                description: e instanceof Error ? e.message : 'Error inesperado',
                variant: 'error',
            });
            setCreateSaving(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-primary-500/20 text-primary-300 flex items-center justify-center">
                    <UsersRound className="w-5 h-5" />
                </div>
                <div>
                    <h1 className="text-xl font-semibold text-white">Equipo</h1>
                    <p className="text-sm text-slate-400">
                        {sucursalActualId ? 'Gestión completa por sucursal seleccionada.' : 'Vista general (todas las sucursales).'}
                    </p>
                </div>
            </div>

            <div className="flex flex-col gap-3">
                <div className="flex flex-wrap items-center gap-2">
                    {tabs.map((t) => (
                        <button
                            key={t.key}
                            onClick={() => setTab(t.key)}
                            className={cn(
                                'h-9 px-4 rounded-xl text-sm font-medium transition-colors border',
                                tab === t.key
                                    ? 'bg-primary-500/20 text-primary-200 border-primary-500/30'
                                    : 'bg-slate-900/30 text-slate-300 border-slate-800/60 hover:bg-slate-900/50'
                            )}
                        >
                            {t.label}
                        </button>
                    ))}
                    <button
                        onClick={() => setCreateOpen(true)}
                        className="h-9 px-3 rounded-xl text-sm font-medium transition-colors border bg-slate-900/30 text-slate-200 border-slate-800/60 hover:bg-slate-900/50 flex items-center gap-2"
                    >
                        <Plus className="w-4 h-4" />
                        Agregar
                    </button>
                    <div className="relative">
                        <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                            className="input h-9 w-72 pl-9"
                            placeholder="Buscar por nombre/DNI..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                    </div>
                </div>
                {loadingSucursal ? <div className="text-xs text-slate-500">Cargando sucursal…</div> : null}
                {errorGeneral ? <div className="text-xs text-danger-400">{errorGeneral}</div> : null}
                {loading ? <div className="text-xs text-slate-500">Cargando…</div> : null}
            </div>

            <div className="rounded-2xl border border-slate-800/60 bg-slate-900/20">
                <div className="p-4 overflow-x-auto">
                    <table className="min-w-full text-sm">
                        <thead>
                            <tr className="text-slate-500">
                                <th className="text-left font-medium py-2 pr-4">Nombre</th>
                                <th className="text-left font-medium py-2 pr-4">Rol</th>
                                <th className="text-left font-medium py-2 pr-4">Profesor</th>
                                <th className="text-left font-medium py-2 pr-4">Staff</th>
                                <th className="text-left font-medium py-2 pr-4">Sucursales</th>
                                <th className="text-left font-medium py-2 pr-4">Activo</th>
                                <th className="text-right font-medium py-2">Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filtered.map((m) => (
                                <tr key={String(m.id)} className="border-t border-slate-800/60">
                                    <td className="py-2 pr-4 text-slate-200">
                                        <div className="font-medium">{m.nombre || `#${m.id}`}</div>
                                        <div className="text-xs text-slate-500">{m.dni || '—'} {m.telefono ? `• ${m.telefono}` : ''}</div>
                                    </td>
                                    <td className="py-2 pr-4 text-slate-400">{m.rol || '-'}</td>
                                    <td className="py-2 pr-4 text-slate-400">{m.profesor ? `${m.profesor.tipo || '-'} • ${m.profesor.estado || '-'}` : '-'}</td>
                                    <td className="py-2 pr-4 text-slate-400">{m.staff ? `${m.staff.tipo || '-'} • ${m.staff.estado || '-'}` : '-'}</td>
                                    <td className="py-2 pr-4 text-slate-400">{(m.sucursales || []).length ? (m.sucursales || []).join(', ') : 'Sin sucursal'}</td>
                                    <td className="py-2 pr-4 text-slate-400">{m.activo ? 'Sí' : 'No'}</td>
                                    <td className="py-2 text-right">
                                        <div className="flex items-center justify-end gap-2">
                                            {m.profesor ? (
                                                    <>
                                                        <button
                                                            onClick={() => {
                                                                const prof: Profesor = {
                                                                    id: m.profesor?.id as number,
                                                                    usuario_id: m.id,
                                                                    nombre: m.nombre,
                                                                    telefono: m.telefono,
                                                                    activo: m.activo,
                                                                    tipo: m.profesor?.tipo || null,
                                                                    estado: m.profesor?.estado || null,
                                                                    scopes: m.scopes || [],
                                                                    sucursales: (m.sucursales || []).map((id) => ({ id, nombre: '' })),
                                                                };
                                                                setProfesorEditProfesor(prof);
                                                                setProfesorEditOpen(true);
                                                            }}
                                                            className="text-xs text-slate-300 hover:text-white"
                                                        >
                                                            Editar profesor
                                                        </button>
                                                        <button
                                                            onClick={() => void openConvertConfirm(m, { target: 'staff', rol: 'empleado' })}
                                                            className="text-xs text-warning-200 hover:text-warning-100"
                                                        >
                                                            Convertir a staff
                                                        </button>
                                                        <button
                                                            onClick={() => void openDeleteProfileConfirm(m, 'profesor')}
                                                            className="text-xs text-danger-300 hover:text-danger-200"
                                                        >
                                                            Eliminar perfil profesor
                                                        </button>
                                                    </>
                                            ) : (
                                                <button
                                                    onClick={() => void openConvertConfirm(m, { target: 'profesor' })}
                                                    className="text-xs text-primary-200 hover:text-primary-100"
                                                >
                                                    Hacer profesor
                                                </button>
                                            )}
                                            {!m.profesor ? (
                                                <>
                                                    {m.staff ? (
                                                        <>
                                                            <button
                                                                onClick={() => {
                                                                    setStaffEditMember(m);
                                                                    setStaffEditOpen(true);
                                                                }}
                                                                className="text-xs text-slate-300 hover:text-white"
                                                            >
                                                                Editar staff
                                                            </button>
                                                            <button
                                                                onClick={() => void openDeleteProfileConfirm(m, 'staff')}
                                                                className="text-xs text-danger-300 hover:text-danger-200"
                                                            >
                                                                Eliminar perfil staff
                                                            </button>
                                                        </>
                                                    ) : (
                                                        <button
                                                            onClick={() => {
                                                                setStaffEditMember(m);
                                                                setStaffEditOpen(true);
                                                            }}
                                                            className="text-xs text-primary-200 hover:text-primary-100"
                                                        >
                                                            Configurar staff
                                                        </button>
                                                    )}
                                                </>
                                            ) : null}
                                            <button
                                                onClick={() => openUserEdit(m)}
                                                className="text-xs text-slate-300 hover:text-white"
                                            >
                                                Editar datos
                                            </button>
                                            <button
                                                onClick={() => void openConvertConfirm(m, { target: 'usuario' })}
                                                className="text-xs text-danger-300 hover:text-danger-200"
                                            >
                                                Quitar del equipo
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                            {!filtered.length ? (
                                <tr>
                                    <td className="py-3 text-slate-400" colSpan={7}>
                                        Sin resultados
                                    </td>
                                </tr>
                            ) : null}
                        </tbody>
                    </table>
                </div>
            </div>

            <Modal
                isOpen={createOpen}
                onClose={() => setCreateOpen(false)}
                title="Agregar al equipo"
                size="md"
                footer={
                    <div className="flex justify-end gap-2">
                        <Button variant="secondary" onClick={() => setCreateOpen(false)} disabled={createSaving}>
                            Cancelar
                        </Button>
                        <Button onClick={() => void createOrPromote()} isLoading={createSaving}>
                            Guardar
                        </Button>
                    </div>
                }
            >
                <div className="p-6 space-y-4">
                    <div className="grid grid-cols-2 gap-2">
                        <button
                            type="button"
                            onClick={() => setCreateKind('staff')}
                            className={cn(
                                'h-10 rounded-xl border text-sm font-semibold transition-colors',
                                createKind === 'staff'
                                    ? 'bg-primary-500/20 border-primary-500/40 text-primary-200'
                                    : 'bg-slate-950/30 border-slate-800/60 text-slate-200 hover:bg-slate-900/40'
                            )}
                        >
                            Staff
                        </button>
                        <button
                            type="button"
                            onClick={() => setCreateKind('profesor')}
                            className={cn(
                                'h-10 rounded-xl border text-sm font-semibold transition-colors',
                                createKind === 'profesor'
                                    ? 'bg-primary-500/20 border-primary-500/40 text-primary-200'
                                    : 'bg-slate-950/30 border-slate-800/60 text-slate-200 hover:bg-slate-900/40'
                            )}
                        >
                            Profesor
                        </button>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                        <button
                            type="button"
                            onClick={() => {
                                setCreateMode('nuevo');
                                setExistingUsers([]);
                                setExistingUserId(null);
                            }}
                            className={cn(
                                'h-10 rounded-xl border text-sm font-semibold transition-colors',
                                createMode === 'nuevo'
                                    ? 'bg-primary-500/20 border-primary-500/40 text-primary-200'
                                    : 'bg-slate-950/30 border-slate-800/60 text-slate-200 hover:bg-slate-900/40'
                            )}
                        >
                            Nuevo
                        </button>
                        <button
                            type="button"
                            onClick={() => {
                                setCreateMode('existente');
                                setCreateNombre('');
                                setCreateDni('');
                                setCreateTelefono('');
                            }}
                            className={cn(
                                'h-10 rounded-xl border text-sm font-semibold transition-colors',
                                createMode === 'existente'
                                    ? 'bg-primary-500/20 border-primary-500/40 text-primary-200'
                                    : 'bg-slate-950/30 border-slate-800/60 text-slate-200 hover:bg-slate-900/40'
                            )}
                        >
                            Existente
                        </button>
                    </div>

                    {createMode === 'existente' ? (
                        <div className="space-y-2">
                            <div className="flex gap-2">
                                <Input value={existingSearch} onChange={(e) => setExistingSearch(e.target.value)} placeholder="Buscar usuario" />
                                <Button variant="secondary" onClick={() => void searchUsuariosExistentes()} isLoading={existingLoading}>
                                    Buscar
                                </Button>
                            </div>
                            <div className="space-y-2">
                                {existingUsers.map((u) => {
                                    const on = existingUserId === u.id;
                                    return (
                                        <button
                                            key={u.id}
                                            type="button"
                                            onClick={() => setExistingUserId(u.id)}
                                            className={cn(
                                                'w-full p-3 rounded-xl border text-left transition-colors',
                                                on
                                                    ? 'bg-primary-500/20 border-primary-500/40 text-primary-200'
                                                    : 'bg-slate-950/30 border-slate-800/60 text-slate-200 hover:bg-slate-900/40'
                                            )}
                                        >
                                            <div className="text-sm font-medium">{u.nombre}</div>
                                            <div className="text-xs text-slate-400">{u.dni || '—'} {u.email ? `• ${u.email}` : ''}</div>
                                        </button>
                                    );
                                })}
                                {!existingLoading && existingSearch.trim() && existingUsers.length === 0 ? (
                                    <div className="text-sm text-slate-400">Sin resultados</div>
                                ) : null}
                            </div>
                        </div>
                    ) : (
                        <>
                            <div className="space-y-2">
                                <div className="text-sm font-medium text-slate-200">Nombre</div>
                                <Input value={createNombre} onChange={(e) => setCreateNombre(e.target.value)} placeholder="Nombre y apellido" />
                            </div>
                            {createKind === 'staff' ? (
                                <div className="space-y-2">
                                    <div className="text-sm font-medium text-slate-200">DNI</div>
                                    <Input value={createDni} onChange={(e) => setCreateDni(e.target.value)} placeholder="DNI" />
                                </div>
                            ) : null}
                            <div className="space-y-2">
                                <div className="text-sm font-medium text-slate-200">Teléfono</div>
                                <Input value={createTelefono} onChange={(e) => setCreateTelefono(e.target.value)} placeholder="Teléfono" />
                            </div>
                        </>
                    )}

                    {createKind === 'staff' ? (
                        <div className="space-y-2">
                            <div className="text-sm font-medium text-slate-200">Rol</div>
                            <select
                                className="w-full h-10 rounded-xl bg-slate-950/40 border border-slate-800/60 text-slate-200 px-3 outline-none focus:ring-2 focus:ring-primary-500/40"
                                value={createRol}
                                onChange={(e) => {
                                    const v = e.target.value;
                                    if (v === 'empleado' || v === 'recepcionista' || v === 'staff' || v === 'profesor') {
                                        setCreateRol(v);
                                    }
                                }}
                            >
                                <option value="empleado">Empleado</option>
                                <option value="recepcionista">Recepcionista</option>
                                <option value="staff">Staff</option>
                                <option value="profesor">Profesor</option>
                            </select>
                        </div>
                    ) : null}
                </div>
            </Modal>

            <TeamStaffModal
                isOpen={staffEditOpen}
                onClose={() => setStaffEditOpen(false)}
                member={staffEditMember}
                onRefresh={() => void load()}
            />

            <ProfesorDetailModal
                isOpen={profesorEditOpen}
                onClose={() => setProfesorEditOpen(false)}
                profesor={profesorEditProfesor}
                onRefresh={() => void load()}
            />

            <Modal
                isOpen={userEditOpen}
                onClose={() => {
                    setUserEditOpen(false);
                    setUserEditMember(null);
                }}
                title={userEditMember ? `Editar: ${userEditMember.nombre}` : 'Editar'}
                size="sm"
                footer={
                    <div className="flex justify-end gap-2">
                        <Button variant="secondary" onClick={() => setUserEditOpen(false)} disabled={userEditSaving}>
                            Cancelar
                        </Button>
                        <Button onClick={() => void saveUserEdit()} isLoading={userEditSaving}>
                            Guardar
                        </Button>
                    </div>
                }
            >
                <div className="p-6 space-y-3">
                    <div className="space-y-2">
                        <div className="text-sm font-medium text-slate-200">Nombre</div>
                        <Input value={userEditNombre} onChange={(e) => setUserEditNombre(e.target.value)} placeholder="Nombre y apellido" />
                    </div>
                    <div className="space-y-2">
                        <div className="text-sm font-medium text-slate-200">DNI</div>
                        <Input value={userEditDni} onChange={(e) => setUserEditDni(e.target.value)} placeholder="DNI" />
                    </div>
                    <div className="space-y-2">
                        <div className="text-sm font-medium text-slate-200">Teléfono</div>
                        <Input value={userEditTelefono} onChange={(e) => setUserEditTelefono(e.target.value)} placeholder="Teléfono" />
                    </div>
                </div>
            </Modal>

            <ConfirmModal
                isOpen={confirmOpen}
                onClose={() => {
                    setConfirmOpen(false);
                    setPendingConvert(null);
                }}
                onConfirm={() => void runConfirm()}
                title={confirmTitle}
                message={confirmMessage}
                confirmText={confirmText}
                variant={confirmVariant}
                isLoading={confirmLoading}
            />
        </div>
    );
}
