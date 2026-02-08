'use client';

import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import {
    Clock,
    Users,
    List,
    Plus,
    Trash2,
    UserPlus,
    Bell,
    X,
    Edit,
    Dumbbell,
    Layers,
    Search,
    GripVertical,
    Save,
} from 'lucide-react';
import { Button, Modal, Input, Select, ConfirmModal, useToast } from '@/components/ui';
import {
    api,
    type Clase,
    type ClaseHorario,
    type ClaseEjercicio,
    type ClaseBloque,
    type ClaseBloqueItem,
    type Inscripcion,
    type ListaEspera,
    type Profesor,
    type Usuario,
    type Ejercicio,
} from '@/lib/api';
import { formatTime, cn } from '@/lib/utils';

interface ClaseDetailModalProps {
    isOpen: boolean;
    onClose: () => void;
    clase: Clase | null;
    profesores: Profesor[];
    onRefresh: () => void;
}

type TabType = 'horarios' | 'inscripciones' | 'espera' | 'ejercicios' | 'bloques';

const diasSemana = [
    { value: 'Lunes', label: 'Lunes' },
    { value: 'Martes', label: 'Martes' },
    { value: 'Miércoles', label: 'Miércoles' },
    { value: 'Jueves', label: 'Jueves' },
    { value: 'Viernes', label: 'Viernes' },
    { value: 'Sábado', label: 'Sábado' },
    { value: 'Domingo', label: 'Domingo' },
];

export default function ClaseDetailModal({
    isOpen,
    onClose,
    clase,
    profesores,
    onRefresh,
}: ClaseDetailModalProps) {
    const { success, error } = useToast();
    const [activeTab, setActiveTab] = useState<TabType>('horarios');
    const [assignedProfesorIds, setAssignedProfesorIds] = useState<number[] | null>(null);
    const [assignedProfesoresLoading, setAssignedProfesoresLoading] = useState(false);

    // Horarios
    const [horarios, setHorarios] = useState<ClaseHorario[]>([]);
    const [horarioForm, setHorarioForm] = useState({
        dia: 'Lunes',
        hora_inicio: '09:00',
        hora_fin: '10:00',
        profesor_id: undefined as number | undefined,
        cupo: undefined as number | undefined,
    });
    const [selectedHorarioId, setSelectedHorarioId] = useState<number | null>(null);
    const [deleteHorarioOpen, setDeleteHorarioOpen] = useState(false);
    const [horarioToDelete, setHorarioToDelete] = useState<ClaseHorario | null>(null);
    const [editHorarioOpen, setEditHorarioOpen] = useState(false);
    const [horarioToEdit, setHorarioToEdit] = useState<ClaseHorario | null>(null);
    const [editHorarioForm, setEditHorarioForm] = useState({
        dia: 'Lunes',
        hora_inicio: '09:00',
        hora_fin: '10:00',
        profesor_id: undefined as number | undefined,
        cupo: undefined as number | undefined,
    });

    // Inscripciones
    const [inscripciones, setInscripciones] = useState<Inscripcion[]>([]);
    const [usuarios, setUsuarios] = useState<Usuario[]>([]);
    const [selectedUsuarioId, setSelectedUsuarioId] = useState<number | null>(null);
    const [usuariosSearch, setUsuariosSearch] = useState('');
    const [usuariosLoading, setUsuariosLoading] = useState(false);

    // Lista de espera
    const [listaEspera, setListaEspera] = useState<ListaEspera[]>([]);

    const [ejercicios, setEjercicios] = useState<Ejercicio[]>([]);
    const [ejerciciosLoading, setEjerciciosLoading] = useState(false);
    const [ejerciciosSearch, setEjerciciosSearch] = useState('');
    const [claseEjercicios, setClaseEjercicios] = useState<ClaseEjercicio[]>([]);
    const [selectedEjercicioIds, setSelectedEjercicioIds] = useState<number[]>([]);
    const [savingEjercicios, setSavingEjercicios] = useState(false);

    const [bloques, setBloques] = useState<ClaseBloque[]>([]);
    const [bloquesLoading, setBloquesLoading] = useState(false);
    const [selectedBloqueId, setSelectedBloqueId] = useState<number | null>(null);
    const [bloqueNombre, setBloqueNombre] = useState('');
    const [bloqueItems, setBloqueItems] = useState<ClaseBloqueItem[]>([]);
    const [, setBloqueItemsLoading] = useState(false);
    const [savingBloque, setSavingBloque] = useState(false);

    const loadHorarios = useCallback(async () => {
        if (!clase) return;
        const res = await api.getClaseHorarios(clase.id);
        if (res.ok && res.data) {
            setHorarios(res.data.horarios);
            if (res.data.horarios.length > 0 && !selectedHorarioId) {
                setSelectedHorarioId(res.data.horarios[0].id);
            }
        }
    }, [clase, selectedHorarioId]);

    const loadProfesoresAsignados = useCallback(async () => {
        if (!clase?.id) return;
        setAssignedProfesoresLoading(true);
        try {
            const res = await api.getClaseProfesoresAsignados(clase.id);
            if (res.ok && res.data?.profesor_ids) {
                setAssignedProfesorIds(
                    (res.data.profesor_ids || [])
                        .map((x) => Number(x))
                        .filter((x) => Number.isFinite(x))
                );
            } else {
                setAssignedProfesorIds([]);
            }
        } catch {
            setAssignedProfesorIds([]);
        } finally {
            setAssignedProfesoresLoading(false);
        }
    }, [clase?.id]);

    const loadInscripciones = useCallback(async () => {
        if (!selectedHorarioId) return;
        const res = await api.getInscripciones(selectedHorarioId);
        if (res.ok && res.data) {
            setInscripciones(res.data.inscripciones);
        }
    }, [selectedHorarioId]);

    const loadListaEspera = useCallback(async () => {
        if (!selectedHorarioId) return;
        const res = await api.getListaEspera(selectedHorarioId);
        if (res.ok && res.data) {
            setListaEspera(res.data.lista);
        }
    }, [selectedHorarioId]);

    // Load data
    useEffect(() => {
        if (clase && isOpen) {
            void loadHorarios();
            void loadProfesoresAsignados();
            setActiveTab('horarios');
            setUsuarios([]);
            setUsuariosSearch('');
            setSelectedUsuarioId(null);
            setEjerciciosSearch('');
            setSelectedEjercicioIds([]);
            setSelectedBloqueId(null);
            setBloques([]);
            setBloqueItems([]);
        }
    }, [clase, isOpen, loadHorarios, loadProfesoresAsignados]);

    useEffect(() => {
        if (selectedHorarioId) {
            void loadInscripciones();
            void loadListaEspera();
        }
    }, [selectedHorarioId, loadInscripciones, loadListaEspera]);

    useEffect(() => {
        if (!isOpen || !clase?.id) return;
        if (!assignedProfesorIds || assignedProfesorIds.length === 0) return;
        const first = assignedProfesorIds[0];
        if (!Number.isFinite(first)) return;
        setHorarioForm((prev) => {
            if (prev.profesor_id && assignedProfesorIds.includes(prev.profesor_id)) return prev;
            return { ...prev, profesor_id: Number(first) };
        });
    }, [assignedProfesorIds, clase?.id, isOpen]);

    const loadUsuarios = useCallback(async (search: string) => {
        setUsuariosLoading(true);
        try {
            const res = await api.getUsuarios({ activo: true, limit: 60, search: search.trim() || undefined });
            if (res.ok && res.data) {
                setUsuarios(res.data.usuarios);
                setSelectedUsuarioId(null);
            }
        } finally {
            setUsuariosLoading(false);
        }
    }, []);

    const loadClaseEjercicios = useCallback(async () => {
        if (!clase) return;
        const res = await api.getClaseEjercicios(clase.id);
        if (res.ok && res.data) {
            const items = res.data.ejercicios || [];
            setClaseEjercicios(items);
            setSelectedEjercicioIds(items.map((it) => Number(it.ejercicio_id)).filter((n) => Number.isFinite(n)));
        }
    }, [clase]);

    const loadEjerciciosCatalog = useCallback(async (search: string) => {
        setEjerciciosLoading(true);
        try {
            const res = await api.getEjercicios({ search: search || undefined });
            if (res.ok && res.data) setEjercicios(res.data.ejercicios || []);
        } finally {
            setEjerciciosLoading(false);
        }
    }, []);

    const loadBloques = useCallback(async () => {
        if (!clase) return;
        setBloquesLoading(true);
        try {
            const res = await api.getClaseBloques(clase.id);
            if (res.ok && res.data) {
                const list = res.data || [];
                setBloques(list);
                if (!selectedBloqueId && list.length) {
                    setSelectedBloqueId(list[0].id);
                    setBloqueNombre(list[0].nombre || '');
                }
            }
        } finally {
            setBloquesLoading(false);
        }
    }, [clase, selectedBloqueId]);

    const claseId = clase?.id;

    const loadBloqueItems = useCallback(async (bloqueId: number) => {
        if (!claseId) return;
        setBloqueItemsLoading(true);
        try {
            const res = await api.getClaseBloqueItems(claseId, bloqueId);
            // Race guard
            if (bloqueId !== selectedBloqueIdRef.current) return;

            if (res.ok && res.data) setBloqueItems(res.data || []);
        } finally {
            setBloqueItemsLoading(false);
        }
    }, [claseId]);

    // Race condition guard
    const selectedBloqueIdRef = useRef<number | null>(null);
    useEffect(() => {
        selectedBloqueIdRef.current = selectedBloqueId;
    }, [selectedBloqueId]);

    const activeTabRef = useRef(activeTab);
    useEffect(() => { activeTabRef.current = activeTab; }, [activeTab]);

    useEffect(() => {
        if (!isOpen || !clase) return;
        if (activeTab === 'ejercicios') void loadClaseEjercicios();
        if (activeTab === 'ejercicios' || activeTab === 'bloques') void loadEjerciciosCatalog('');
        if (activeTab === 'bloques') void loadBloques();
        if (activeTab === 'inscripciones' || activeTab === 'espera') void loadUsuarios('');
    }, [activeTab, isOpen, clase, loadBloques, loadClaseEjercicios, loadEjerciciosCatalog, loadUsuarios]);

    useEffect(() => {
        if (!isOpen) return;
        if (activeTab !== 'ejercicios' && activeTab !== 'bloques') return;
        if (!ejerciciosSearch.trim()) return;
        const t = setTimeout(() => {
            void loadEjerciciosCatalog(ejerciciosSearch);
        }, 250);
        return () => clearTimeout(t);
    }, [ejerciciosSearch, activeTab, isOpen, loadEjerciciosCatalog]);

    useEffect(() => {
        if (!isOpen) return;
        if (activeTab !== 'inscripciones' && activeTab !== 'espera') return;
        const t = setTimeout(() => {
            void loadUsuarios(usuariosSearch);
        }, 250);
        return () => clearTimeout(t);
    }, [usuariosSearch, activeTab, isOpen, loadUsuarios]);

    useEffect(() => {
        if (!isOpen || activeTab !== 'bloques') return;
        if (!selectedBloqueId) return;
        void loadBloqueItems(selectedBloqueId);
        const b = bloques.find((x) => x.id === selectedBloqueId);
        setBloqueNombre(b?.nombre || '');
    }, [selectedBloqueId, bloques, activeTab, isOpen, loadBloqueItems]);

    // Horario CRUD
    const handleAddHorario = async () => {
        if (!clase) return;
        const res = await api.createClaseHorario(clase.id, horarioForm);
        if (res.ok) {
            success('Horario agregado');
            loadHorarios();
            onRefresh();
            setHorarioForm({
                dia: 'Lunes',
                hora_inicio: '09:00',
                hora_fin: '10:00',
                profesor_id: undefined,
                cupo: undefined,
            });
        } else {
            error(res.error || 'Error al agregar horario');
        }
    };

    const handleDeleteHorario = (horarioId: number) => {
        const h = horarios.find((x) => x.id === horarioId) || null;
        setHorarioToDelete(h);
        setDeleteHorarioOpen(true);
    };

    const confirmDeleteHorario = async () => {
        if (!clase || !horarioToDelete) return;
        const horarioId = horarioToDelete.id;
        const res = await api.deleteClaseHorario(clase.id, horarioId);
        if (res.ok) {
            success('Horario eliminado');
            loadHorarios();
            onRefresh();
            if (selectedHorarioId === horarioId) {
                setSelectedHorarioId(null);
            }
        } else {
            error(res.error || 'Error al eliminar');
        }
        setDeleteHorarioOpen(false);
        setHorarioToDelete(null);
    };

    const openEditHorario = (horario: ClaseHorario) => {
        setHorarioToEdit(horario);
        setEditHorarioForm({
            dia: String(horario.dia || 'Lunes'),
            hora_inicio: String(horario.hora_inicio || '09:00').slice(0, 5),
            hora_fin: String(horario.hora_fin || '10:00').slice(0, 5),
            profesor_id: horario.profesor_id ? Number(horario.profesor_id) : undefined,
            cupo: typeof horario.cupo === 'number' ? Number(horario.cupo) : undefined,
        });
        setEditHorarioOpen(true);
    };

    const saveEditHorario = async () => {
        if (!clase || !horarioToEdit) return;
        const res = await api.updateClaseHorario(clase.id, horarioToEdit.id, editHorarioForm);
        if (res.ok) {
            success('Horario actualizado');
            setEditHorarioOpen(false);
            setHorarioToEdit(null);
            loadHorarios();
            onRefresh();
        } else {
            error(res.error || 'Error al actualizar horario');
        }
    };

    const toggleEjercicio = (id: number, checked: boolean) => {
        setSelectedEjercicioIds((prev) => {
            const has = prev.includes(id);
            if (checked && !has) return [...prev, id];
            if (!checked && has) return prev.filter((x) => x !== id);
            return prev;
        });
    };

    const saveEjercicios = async () => {
        if (!clase) return;
        setSavingEjercicios(true);
        try {
            const res = await api.updateClaseEjercicios(clase.id, selectedEjercicioIds);
            if (res.ok) {
                success('Ejercicios actualizados');
                loadClaseEjercicios();
            } else {
                error(res.error || 'Error al guardar ejercicios');
            }
        } finally {
            setSavingEjercicios(false);
        }
    };

    // Inscripciones
    const handleInscribir = async () => {
        if (!selectedHorarioId || !selectedUsuarioId) return;
        const res = await api.inscribirUsuario(selectedHorarioId, selectedUsuarioId);
        if (res.ok) {
            success('Usuario inscripto');
            loadInscripciones();
            loadHorarios();
            onRefresh();
            setSelectedUsuarioId(null);
        } else {
            error(res.error || 'Error al inscribir');
        }
    };

    const handleDesinscribir = async (usuarioId: number) => {
        if (!selectedHorarioId) return;
        const res = await api.desinscribirUsuario(selectedHorarioId, usuarioId);
        if (res.ok) {
            success('Usuario desinscripto');
            loadInscripciones();
            loadHorarios();
            onRefresh();
        } else {
            error(res.error || 'Error al desinscribir');
        }
    };

    // Lista de espera
    const handleAddToWaitlist = async () => {
        if (!selectedHorarioId || !selectedUsuarioId) return;
        const res = await api.addToListaEspera(selectedHorarioId, selectedUsuarioId);
        if (res.ok) {
            success('Agregado a lista de espera');
            loadListaEspera();
            setSelectedUsuarioId(null);
        } else {
            error(res.error || 'Error al agregar');
        }
    };

    const handleRemoveFromWaitlist = async (usuarioId: number) => {
        if (!selectedHorarioId) return;
        const res = await api.removeFromListaEspera(selectedHorarioId, usuarioId);
        if (res.ok) {
            success('Removido de lista de espera');
            loadListaEspera();
        } else {
            error(res.error || 'Error al remover');
        }
    };

    const handleNotifyWaitlist = async () => {
        if (!selectedHorarioId) return;
        const res = await api.notifyListaEspera(selectedHorarioId);
        if (res.ok) {
            success(res.data?.notified_user
                ? `Notificado: ${res.data.notified_user}`
                : 'Notificación enviada');
            loadListaEspera();
            loadInscripciones();
        } else {
            error(res.error || 'Error al notificar');
        }
    };

    // Filter available usuarios for inscription
    const inscriptoIds = new Set(inscripciones.map(i => i.usuario_id));
    const esperaIds = new Set(listaEspera.map(l => l.usuario_id));
    const availableUsuarios = usuarios.filter(u => !inscriptoIds.has(u.id));
    const availableForWaitlist = usuarios.filter(u => !inscriptoIds.has(u.id) && !esperaIds.has(u.id));

    const profesoresParaClase = useMemo(() => {
        if (assignedProfesoresLoading) return profesores;
        if (!assignedProfesorIds || assignedProfesorIds.length === 0) return profesores;
        const setIds = new Set(assignedProfesorIds);
        return profesores.filter((p) => setIds.has(p.id));
    }, [profesores, assignedProfesorIds, assignedProfesoresLoading]);

    const selectedHorario = horarios.find(h => h.id === selectedHorarioId);

    if (!isOpen || !clase) return null;

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={`Gestionar: ${clase.nombre}`}
            size="xl"
        >
            <div className="space-y-4">
                {/* Horario selector */}
                {horarios.length > 0 && (
                    <div className="flex items-center gap-2 pb-4 border-b border-slate-800">
                        <span className="text-sm text-slate-400">Horario:</span>
                        <select
                            value={selectedHorarioId || ''}
                            onChange={(e) => setSelectedHorarioId(Number(e.target.value))}
                            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                        >
                            {horarios.map((h) => (
                                <option key={h.id} value={h.id}>
                                    {h.dia} {formatTime(h.hora_inicio)}-{formatTime(h.hora_fin)}
                                    {h.profesor_nombre && ` (${h.profesor_nombre})`}
                                </option>
                            ))}
                        </select>
                        {selectedHorario && (
                            <span className="text-sm text-slate-500 ml-auto">
                                {selectedHorario.inscriptos_count || 0}
                                {selectedHorario.cupo && `/${selectedHorario.cupo}`} inscriptos
                            </span>
                        )}
                    </div>
                )}

                {/* Tabs */}
                <div className="flex border-b border-slate-800">
                    {[
                        { id: 'horarios', label: 'Horarios', icon: Clock },
                        { id: 'inscripciones', label: 'Inscriptos', icon: Users },
                        { id: 'espera', label: 'Lista de Espera', icon: List },
                        { id: 'ejercicios', label: 'Ejercicios', icon: Dumbbell },
                        { id: 'bloques', label: 'Bloques', icon: Layers },
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
                <div className="min-h-[300px]">
                    {activeTab === 'horarios' && (
                        <div className="space-y-4">
                            {/* Add horario form */}
                            <div className="card p-4 space-y-3">
                                <h4 className="text-sm font-medium text-white">Agregar Horario</h4>
                                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                                    <Select
                                        value={horarioForm.dia}
                                        onChange={(e) => setHorarioForm({ ...horarioForm, dia: e.target.value })}
                                        options={diasSemana}
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
                                    <Select
                                        value={horarioForm.profesor_id?.toString() || ''}
                                        onChange={(e) => setHorarioForm({ ...horarioForm, profesor_id: e.target.value ? Number(e.target.value) : undefined })}
                                        placeholder="Profesor"
                                        options={profesoresParaClase.map(p => ({ value: p.id.toString(), label: p.nombre }))}
                                    />
                                    <div className="flex gap-2">
                                        <Input
                                            type="number"
                                            value={horarioForm.cupo || ''}
                                            onChange={(e) => setHorarioForm({ ...horarioForm, cupo: e.target.value ? Number(e.target.value) : undefined })}
                                            placeholder="Cupo"
                                            min={1}
                                        />
                                        <Button onClick={handleAddHorario}>
                                            <Plus className="w-4 h-4" />
                                        </Button>
                                    </div>
                                </div>
                            </div>

                            {/* Horarios list */}
                            <div className="space-y-2">
                                {horarios.map((h) => (
                                    <div
                                        key={h.id}
                                        className={cn(
                                            'flex items-center justify-between p-3 rounded-lg border',
                                            selectedHorarioId === h.id
                                                ? 'bg-primary-500/10 border-primary-500/50'
                                                : 'bg-slate-800/50 border-slate-700'
                                        )}
                                    >
                                        <div className="flex items-center gap-4">
                                            <button
                                                onClick={() => setSelectedHorarioId(h.id)}
                                                className="text-left"
                                            >
                                                <div className="font-medium text-white">{h.dia}</div>
                                                <div className="text-sm text-slate-400">
                                                    {formatTime(h.hora_inicio)} - {formatTime(h.hora_fin)}
                                                </div>
                                            </button>
                                            {h.profesor_nombre && (
                                                <span className="text-sm text-slate-500">{h.profesor_nombre}</span>
                                            )}
                                            <span className="text-sm text-slate-400">
                                                {h.inscriptos_count || 0}{h.cupo && `/${h.cupo}`}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <button
                                                onClick={() => openEditHorario(h)}
                                                className="p-2 text-slate-400 hover:text-white"
                                                title="Editar horario"
                                            >
                                                <Edit className="w-4 h-4" />
                                            </button>
                                            <button
                                                onClick={() => handleDeleteHorario(h.id)}
                                                className="p-2 text-slate-400 hover:text-danger-400"
                                                title="Eliminar horario"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </div>
                                ))}
                                {horarios.length === 0 && (
                                    <div className="text-center text-slate-500 py-8">
                                        Sin horarios configurados
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {activeTab === 'inscripciones' && (
                        <div className="space-y-4">
                            {!selectedHorarioId ? (
                                <div className="text-center text-slate-500 py-8">
                                    Selecciona un horario primero
                                </div>
                            ) : (
                                <>
                                    <div className="flex flex-col sm:flex-row gap-2">
                                        <input
                                            className="input flex-1"
                                            value={usuariosSearch}
                                            onChange={(e) => setUsuariosSearch(e.target.value)}
                                            placeholder="Buscar usuarios (nombre o DNI)…"
                                        />
                                        <Button variant="secondary" onClick={() => loadUsuarios(usuariosSearch)} isLoading={usuariosLoading}>
                                            Buscar
                                        </Button>
                                    </div>

                                    {/* Add inscription */}
                                    <div className="flex gap-2">
                                        <Select
                                            value={selectedUsuarioId?.toString() || ''}
                                            onChange={(e) => setSelectedUsuarioId(Number(e.target.value))}
                                            placeholder="Seleccionar usuario..."
                                            options={availableUsuarios.map(u => ({
                                                value: u.id.toString(),
                                                label: `${u.nombre}${u.dni ? ` (${u.dni})` : ''}`
                                            }))}
                                        />
                                        <Button onClick={handleInscribir} disabled={!selectedUsuarioId}>
                                            <UserPlus className="w-4 h-4 mr-1" />
                                            Inscribir
                                        </Button>
                                    </div>

                                    {/* Inscriptions list */}
                                    <div className="space-y-2">
                                        {inscripciones.map((i) => (
                                            <div
                                                key={i.id}
                                                className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg border border-slate-700"
                                            >
                                                <div>
                                                    <div className="font-medium text-white">{i.usuario_nombre}</div>
                                                    {i.usuario_telefono && (
                                                        <div className="text-xs text-slate-500">{i.usuario_telefono}</div>
                                                    )}
                                                </div>
                                                <button
                                                    onClick={() => handleDesinscribir(i.usuario_id)}
                                                    className="p-2 text-slate-400 hover:text-danger-400"
                                                >
                                                    <X className="w-4 h-4" />
                                                </button>
                                            </div>
                                        ))}
                                        {inscripciones.length === 0 && (
                                            <div className="text-center text-slate-500 py-8">
                                                Sin inscriptos
                                            </div>
                                        )}
                                    </div>
                                </>
                            )}
                        </div>
                    )}

                    {activeTab === 'espera' && (
                        <div className="space-y-4">
                            {!selectedHorarioId ? (
                                <div className="text-center text-slate-500 py-8">
                                    Selecciona un horario primero
                                </div>
                            ) : (
                                <>
                                    {/* Actions */}
                                    <div className="flex gap-2">
                                        <Select
                                            value={selectedUsuarioId?.toString() || ''}
                                            onChange={(e) => setSelectedUsuarioId(Number(e.target.value))}
                                            placeholder="Agregar usuario a lista de espera..."
                                            options={availableForWaitlist.map(u => ({
                                                value: u.id.toString(),
                                                label: `${u.nombre}${u.dni ? ` (${u.dni})` : ''}`
                                            }))}
                                        />
                                        <Button onClick={handleAddToWaitlist} disabled={!selectedUsuarioId}>
                                            <Plus className="w-4 h-4 mr-1" />
                                            Agregar
                                        </Button>
                                        {listaEspera.length > 0 && (
                                            <Button variant="secondary" onClick={handleNotifyWaitlist}>
                                                <Bell className="w-4 h-4 mr-1" />
                                                Notificar Próximo
                                            </Button>
                                        )}
                                    </div>

                                    {/* Waitlist */}
                                    <div className="space-y-2">
                                        {listaEspera.map((item, index) => (
                                            <div
                                                key={item.id}
                                                className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg border border-slate-700"
                                            >
                                                <div className="flex items-center gap-3">
                                                    <span className="w-6 h-6 rounded-full bg-slate-700 flex items-center justify-center text-xs font-medium">
                                                        {index + 1}
                                                    </span>
                                                    <div className="font-medium text-white">{item.usuario_nombre}</div>
                                                </div>
                                                <button
                                                    onClick={() => handleRemoveFromWaitlist(item.usuario_id)}
                                                    className="p-2 text-slate-400 hover:text-danger-400"
                                                >
                                                    <X className="w-4 h-4" />
                                                </button>
                                            </div>
                                        ))}
                                        {listaEspera.length === 0 && (
                                            <div className="text-center text-slate-500 py-8">
                                                Lista de espera vacía
                                            </div>
                                        )}
                                    </div>
                                </>
                            )}
                        </div>
                    )}

                    {activeTab === 'ejercicios' && (
                        <div className="space-y-6">
                            <div className="card-bordered p-4 bg-slate-900/50">
                                <h3 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
                                    <Search className="w-4 h-4 text-primary-400" />
                                    Catálogo de Ejercicios
                                </h3>
                                <div className="flex gap-2 mb-4">
                                    <div className="relative flex-1">
                                        <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
                                        <input
                                            className="input w-full pl-9"
                                            value={ejerciciosSearch}
                                            onChange={(e) => {
                                                setEjerciciosSearch(e.target.value);
                                                if (e.target.value.length > 1) {
                                                    loadEjerciciosCatalog(e.target.value);
                                                }
                                            }}
                                            placeholder="Buscar para agregar..."
                                        />
                                    </div>
                                    <Button onClick={saveEjercicios} isLoading={savingEjercicios}>
                                        Guardar asignados
                                    </Button>
                                </div>

                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-[300px] overflow-y-auto">
                                    {ejerciciosLoading ? (
                                        <div className="col-span-full py-8 text-center text-slate-500">
                                            Cargando catálogo...
                                        </div>
                                    ) : ejerciciosSearch && ejercicios.length === 0 ? (
                                        <div className="col-span-full py-8 text-center text-slate-500">
                                            Sin resultados
                                        </div>
                                    ) : (
                                        ejercicios.map((e) => {
                                            const isSelected = selectedEjercicioIds.includes(Number(e.id));
                                            return (
                                                <button
                                                    key={e.id}
                                                    onClick={() => toggleEjercicio(Number(e.id), !isSelected)}
                                                    className={cn(
                                                        "flex items-center justify-between p-3 rounded-lg border text-left transition-all",
                                                        isSelected
                                                            ? "bg-primary-500/20 border-primary-500/50 text-white"
                                                            : "bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-white"
                                                    )}
                                                >
                                                    <span className="truncate pr-2 font-medium text-sm">{e.nombre}</span>
                                                    {isSelected && <div className="w-2 h-2 rounded-full bg-primary-500" />}
                                                </button>
                                            );
                                        })
                                    )}
                                </div>
                            </div>

                            <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider">
                                        Ejercicios Asignados ({selectedEjercicioIds.length})
                                    </h3>
                                    <Button
                                        variant="secondary"
                                        size="sm"
                                        onClick={() => setSelectedEjercicioIds([])}
                                        disabled={!selectedEjercicioIds.length}
                                    >
                                        Limpiar todos
                                    </Button>
                                </div>

                                <div className="overflow-x-auto rounded-xl border border-slate-800">
                                    <table className="min-w-full text-sm">
                                        <thead className="bg-slate-900 text-slate-500">
                                            <tr>
                                                <th className="px-4 py-3 text-left">Ejercicio</th>
                                                <th className="px-4 py-3 text-right">Acciones</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-800">
                                            {selectedEjercicioIds.length === 0 ? (
                                                <tr>
                                                    <td colSpan={2} className="px-4 py-8 text-center text-slate-500">
                                                        No hay ejercicios asignados a esta clase.
                                                    </td>
                                                </tr>
                                            ) : (
                                                selectedEjercicioIds.map(id => {
                                                    const ej = claseEjercicios.find(ce => Number(ce.ejercicio_id) === id)?.ejercicio || ejercicios.find(e => Number(e.id) === id) || { id, nombre: 'Cargando/Desconocido' };
                                                    return (
                                                        <tr key={id} className="group hover:bg-slate-900/50">
                                                            <td className="px-4 py-3 font-medium text-slate-300">
                                                                {ej.nombre}
                                                            </td>
                                                            <td className="px-4 py-3 text-right">
                                                                <button
                                                                    className="text-slate-500 hover:text-danger-400 p-1"
                                                                    onClick={() => toggleEjercicio(id, false)}
                                                                >
                                                                    <Trash2 className="w-4 h-4" />
                                                                </button>
                                                            </td>
                                                        </tr>
                                                    );
                                                })
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    )}

                    {activeTab === 'bloques' && (
                        <div className="flex flex-col md:flex-row h-[600px] gap-4 -mx-2 -mb-2">
                            {/* Sidebar: Blocks List */}
                            <div className="w-full md:w-1/3 flex flex-col gap-4 border-r border-slate-800 pr-4">
                                <div className="flex items-center justify-between">
                                    <h3 className="font-semibold text-white">Bloques</h3>
                                    <Button
                                        size="sm"
                                        leftIcon={<Plus className="w-3 h-3" />}
                                        onClick={async () => {
                                            if (!clase) return;
                                            const nombre = 'Nuevo Bloque';
                                            setSavingBloque(true);
                                            try {
                                                const res = await api.createClaseBloque(clase.id, { nombre, items: [] });
                                                if (!res.ok || !res.data?.id) return;
                                                await loadBloques();
                                                setSelectedBloqueId(res.data.id);
                                                setBloqueNombre(nombre);
                                                setBloqueItems([]);
                                            } finally {
                                                setSavingBloque(false);
                                            }
                                        }}
                                    >
                                        Nuevo
                                    </Button>
                                </div>

                                <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                                    {bloquesLoading ? (
                                        <div className="text-center py-4 text-sm text-slate-500">Cargando...</div>
                                    ) : bloques.length === 0 ? (
                                        <div className="text-center py-8 border border-dashed border-slate-800 rounded-lg text-slate-500 text-sm p-4">
                                            No hay bloques definidos.<br />Crea uno para empezar.
                                        </div>
                                    ) : (
                                        bloques.map((b) => (
                                            <div
                                                key={b.id}
                                                onClick={() => {
                                                    setSelectedBloqueId(b.id);
                                                    setBloqueNombre(b.nombre);
                                                    // Load items is separate effect or manual call here
                                                    (async () => {
                                                        const res = await api.getClaseBloqueItems(clase!.id, b.id);
                                                        if (res.ok && res.data) setBloqueItems(res.data);
                                                    })();
                                                }}
                                                className={cn(
                                                    "p-3 rounded-lg border cursor-pointer transition-all flex items-center justify-between group",
                                                    selectedBloqueId === b.id
                                                        ? "bg-primary-500/20 border-primary-500/50 text-white"
                                                        : "bg-slate-900/40 border-slate-800 text-slate-400 hover:bg-slate-800 hover:text-white"
                                                )}
                                            >
                                                <div className="font-medium text-sm">{b.nombre}</div>
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        // Quick delete logic
                                                        if (confirm('¿Eliminar bloque?')) {
                                                            api.deleteClaseBloque(clase!.id, b.id).then(() => {
                                                                loadBloques();
                                                                if (selectedBloqueId === b.id) {
                                                                    setSelectedBloqueId(null);
                                                                    setBloqueItems([]);
                                                                }
                                                            });
                                                        }
                                                    }}
                                                    className="opacity-0 group-hover:opacity-100 p-1 hover:text-danger-400"
                                                >
                                                    <Trash2 className="w-3 h-3" />
                                                </button>
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>

                            {/* Main: Block Editor */}
                            <div className="flex-1 flex flex-col bg-slate-900/30 rounded-xl overflow-hidden border border-slate-800">
                                {selectedBloqueId ? (
                                    <>
                                        <div className="p-4 border-b border-slate-800 flex items-center gap-3 bg-slate-900/80">
                                            <div className="flex-1">
                                                <label className="text-xs text-slate-500 mb-1 block">Nombre del bloque</label>
                                                <input
                                                    className="input w-full"
                                                    value={bloqueNombre}
                                                    onChange={(e) => setBloqueNombre(e.target.value)}
                                                />
                                            </div>
                                            <div className="self-end pb-0.5">
                                                <Button
                                                    onClick={async () => {
                                                        if (!selectedBloqueId) return;
                                                        setSavingBloque(true);
                                                        // Update items
                                                        // We just send items as is, backend handles replace
                                                        await api.updateClaseBloque(clase!.id, selectedBloqueId, {
                                                            nombre: bloqueNombre,
                                                            items: bloqueItems
                                                        });
                                                        setSavingBloque(false);
                                                        success('Guardado');
                                                        loadBloques();
                                                    }}
                                                    isLoading={savingBloque}
                                                    leftIcon={<Save className="w-4 h-4" />}
                                                >
                                                    Guardar Bloque
                                                </Button>
                                            </div>
                                        </div>

                                        <div className="flex-1 overflow-y-auto p-4 space-y-4">
                                            {/* Items List */}
                                            <div className="space-y-2">
                                                {bloqueItems.map((item, idx) => (
                                                    <div key={idx} className="flex gap-2 items-start p-3 rounded-lg bg-slate-950/50 border border-slate-800">
                                                        <div className="pt-2 text-slate-500 cursor-move">
                                                            <GripVertical className="w-4 h-4" />
                                                        </div>
                                                        <div className="flex-1 grid grid-cols-12 gap-2">
                                                            <div className="col-span-12 sm:col-span-4">
                                                                <label className="text-[10px] text-slate-500 uppercase">Ejercicio</label>
                                                                <div className="text-sm font-medium text-slate-200 truncate" title={item.nombre_ejercicio}>
                                                                    {item.nombre_ejercicio || 'Ejercicio'}
                                                                </div>
                                                            </div>
                                                            <div className="col-span-3 sm:col-span-2">
                                                                <label className="text-[10px] text-slate-500 uppercase">Series</label>
                                                                <input
                                                                    type="number" className="input h-7 px-2 text-xs"
                                                                    value={item.series}
                                                                    onChange={(e) => {
                                                                        const copy = [...bloqueItems];
                                                                        copy[idx] = { ...copy[idx], series: Number(e.target.value) };
                                                                        setBloqueItems(copy);
                                                                    }}
                                                                />
                                                            </div>
                                                            <div className="col-span-3 sm:col-span-2">
                                                                <label className="text-[10px] text-slate-500 uppercase">Reps</label>
                                                                <input
                                                                    type="text" className="input h-7 px-2 text-xs"
                                                                    value={item.repeticiones}
                                                                    onChange={(e) => {
                                                                        const copy = [...bloqueItems];
                                                                        copy[idx] = { ...copy[idx], repeticiones: e.target.value };
                                                                        setBloqueItems(copy);
                                                                    }}
                                                                />
                                                            </div>
                                                            <div className="col-span-3 sm:col-span-2">
                                                                <label className="text-[10px] text-slate-500 uppercase">Desc(s)</label>
                                                                <input
                                                                    type="number" className="input h-7 px-2 text-xs"
                                                                    value={item.descanso_segundos}
                                                                    onChange={(e) => {
                                                                        const copy = [...bloqueItems];
                                                                        copy[idx] = { ...copy[idx], descanso_segundos: Number(e.target.value) };
                                                                        setBloqueItems(copy);
                                                                    }}
                                                                />
                                                            </div>
                                                            <div className="col-span-3 sm:col-span-2 text-right pt-4">
                                                                <button
                                                                    onClick={() => {
                                                                        const copy = [...bloqueItems];
                                                                        copy.splice(idx, 1);
                                                                        setBloqueItems(copy);
                                                                    }}
                                                                    className="text-slate-500 hover:text-danger-400"
                                                                >
                                                                    <Trash2 className="w-4 h-4" />
                                                                </button>
                                                            </div>
                                                            <div className="col-span-12">
                                                                <input
                                                                    className="input h-7 px-2 text-xs w-full bg-transparent border-slate-800 placeholder:text-slate-600 focus:bg-slate-900"
                                                                    placeholder="Notas técnicas..."
                                                                    value={item.notas || ''}
                                                                    onChange={(e) => {
                                                                        const copy = [...bloqueItems];
                                                                        copy[idx] = { ...copy[idx], notas: e.target.value };
                                                                        setBloqueItems(copy);
                                                                    }}
                                                                />
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))}
                                                {!bloqueItems.length && (
                                                    <div className="text-center py-8 text-slate-500">
                                                        Este bloque no tiene ejercicios.
                                                    </div>
                                                )}
                                            </div>

                                            {/* Add Item Panel */}
                                            <div className="mt-4 p-4 border border-dashed border-slate-700 bg-slate-900/20 rounded-xl">
                                                <h4 className="text-xs font-semibold text-slate-400 uppercase mb-3">Agregar Ejercicio al Bloque</h4>
                                                <div className="flex gap-2">
                                                    <div className="relative flex-1">
                                                        <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
                                                        <input
                                                            className="input w-full pl-9"
                                                            placeholder="Buscar en catálogo..."
                                                            onChange={(e) => {
                                                                if (e.target.value.length > 1) loadEjerciciosCatalog(e.target.value);
                                                            }}
                                                        />
                                                    </div>
                                                </div>
                                                {/* Mini Results */}
                                                {ejercicios.length > 0 && (
                                                    <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-[150px] overflow-y-auto">
                                                        {ejercicios.slice(0, 10).map(e => (
                                                            <button
                                                                key={e.id}
                                                                onClick={() => {
                                                                    setBloqueItems((prev) => [
                                                                        ...prev,
                                                                        {
                                                                            bloque_id: selectedBloqueId ?? undefined,
                                                                            ejercicio_id: Number(e.id),
                                                                            nombre_ejercicio: String(e.nombre || ''),
                                                                            series: 3,
                                                                            repeticiones: '10',
                                                                            descanso_segundos: 60,
                                                                            orden: prev.length,
                                                                        },
                                                                    ]);
                                                                    setEjercicios([]); // clear search results
                                                                }}
                                                                className="text-left text-xs p-2 rounded border border-slate-800 hover:bg-slate-800 hover:text-white text-slate-300 transition-colors"
                                                            >
                                                                {e.nombre}
                                                            </button>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </>
                                ) : (
                                    <div className="flex-1 flex flex-col items-center justify-center text-slate-500">
                                        <Layers className="w-12 h-12 mb-2 opacity-20" />
                                        <p>Selecciona un bloque para editar</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            <ConfirmModal
                isOpen={deleteHorarioOpen}
                onClose={() => {
                    setDeleteHorarioOpen(false);
                    setHorarioToDelete(null);
                }}
                onConfirm={confirmDeleteHorario}
                title="Eliminar horario"
                message={`¿Eliminar el horario ${horarioToDelete?.dia || ''} ${horarioToDelete ? `${formatTime(horarioToDelete.hora_inicio)}-${formatTime(horarioToDelete.hora_fin)}` : ''}?`}
                confirmText="Eliminar"
                variant="danger"
            />

            <Modal
                isOpen={editHorarioOpen}
                onClose={() => {
                    setEditHorarioOpen(false);
                    setHorarioToEdit(null);
                }}
                title="Editar horario"
                size="lg"
                footer={
                    <>
                        <Button
                            variant="secondary"
                            onClick={() => {
                                setEditHorarioOpen(false);
                                setHorarioToEdit(null);
                            }}
                        >
                            Cancelar
                        </Button>
                        <Button onClick={saveEditHorario}>Guardar</Button>
                    </>
                }
            >
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <Select value={editHorarioForm.dia} onChange={(e) => setEditHorarioForm({ ...editHorarioForm, dia: e.target.value })} options={diasSemana} />
                    <Select
                        value={editHorarioForm.profesor_id?.toString() || ''}
                        onChange={(e) => setEditHorarioForm({ ...editHorarioForm, profesor_id: e.target.value ? Number(e.target.value) : undefined })}
                        placeholder="Profesor"
                        options={profesoresParaClase.map((p) => ({ value: p.id.toString(), label: p.nombre }))}
                    />
                    <Input type="time" value={editHorarioForm.hora_inicio} onChange={(e) => setEditHorarioForm({ ...editHorarioForm, hora_inicio: e.target.value })} />
                    <Input type="time" value={editHorarioForm.hora_fin} onChange={(e) => setEditHorarioForm({ ...editHorarioForm, hora_fin: e.target.value })} />
                    <Input
                        type="number"
                        value={editHorarioForm.cupo || ''}
                        onChange={(e) => setEditHorarioForm({ ...editHorarioForm, cupo: e.target.value ? Number(e.target.value) : undefined })}
                        placeholder="Cupo"
                        min={1}
                    />
                </div>
            </Modal>
        </Modal>
    );
}

