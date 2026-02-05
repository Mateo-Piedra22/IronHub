'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Plus, Search, UsersRound } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api, type Profesor, type TeamMember } from '@/lib/api';
import { Button, Input, Modal, useToast } from '@/components/ui';
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
                setSucursalActualId((r.data.sucursal_actual_id ?? null) as any);
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
        window.addEventListener('ironhub:sucursal-changed', handler as any);
        return () => window.removeEventListener('ironhub:sucursal-changed', handler as any);
    }, [loadSucursalActual]);

    const filtered = useMemo(() => {
        if (tab === 'todos') return items;
        if (tab === 'profesores') return items.filter((i) => i.profesor != null || i.kind === 'profesor');
        return items.filter((i) => i.staff != null || i.kind === 'staff');
    }, [items, tab]);

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
                    dni: (u as any).dni,
                    email: (u as any).email,
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
                const res = await api.promoteTeamMember({
                    usuario_id: existingUserId,
                    kind: createKind,
                    rol: createKind === 'staff' ? createRol : undefined,
                });
                if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo asociar');
            } else {
                if (createKind === 'staff') {
                    const nombre = createNombre.trim();
                    const dni = createDni.trim();
                    const telefono = createTelefono.trim();
                    if (!nombre || !dni) throw new Error('Nombre y DNI son obligatorios');
                    const r = await api.createUsuario({ nombre, dni, telefono, rol: createRol } as any);
                    if (!r.ok || !r.data?.id) throw new Error(r.error || 'No se pudo crear el usuario');
                    const res = await api.promoteTeamMember({
                        usuario_id: r.data.id,
                        kind: 'staff',
                        rol: createRol,
                    });
                    if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo asociar');
                } else {
                    const nombre = createNombre.trim();
                    const telefono = createTelefono.trim();
                    if (!nombre) throw new Error('Nombre es obligatorio');
                    const res = await api.createProfesor({ nombre, telefono } as any);
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
                                                <button
                                                    onClick={() => {
                                                        setProfesorEditProfesor({
                                                            id: m.profesor?.id as number,
                                                            usuario_id: m.id,
                                                            nombre: m.nombre,
                                                            telefono: m.telefono,
                                                            activo: m.activo,
                                                            tipo: m.profesor?.tipo || null,
                                                            estado: m.profesor?.estado || null,
                                                            scopes: m.scopes || [],
                                                            sucursales: (m.sucursales || []).map((id) => ({ id, nombre: '' })),
                                                        } as any);
                                                        setProfesorEditOpen(true);
                                                    }}
                                                    className="text-xs text-slate-300 hover:text-white"
                                                >
                                                    Editar profesor
                                                </button>
                                            ) : (
                                                <button
                                                    onClick={async () => {
                                                        const r = await api.promoteTeamMember({ usuario_id: m.id, kind: 'profesor' });
                                                        if (r.ok && r.data?.ok) {
                                                            toast({ title: 'Actualizado', description: 'Ahora es profesor', variant: 'success' });
                                                            load();
                                                        } else {
                                                            toast({ title: 'Error', description: r.error || 'No se pudo promover', variant: 'error' });
                                                        }
                                                    }}
                                                    className="text-xs text-primary-200 hover:text-primary-100"
                                                >
                                                    Hacer profesor
                                                </button>
                                            )}
                                            {m.staff ? (
                                                <button
                                                    onClick={() => {
                                                        setStaffEditMember(m);
                                                        setStaffEditOpen(true);
                                                    }}
                                                    className="text-xs text-slate-300 hover:text-white"
                                                >
                                                    Editar staff
                                                </button>
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
                                onChange={(e) => setCreateRol(e.target.value as any)}
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
        </div>
    );
}
