'use client';

import { useState, useEffect, useMemo } from 'react';
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
} from 'lucide-react';
import { Button, Modal, Input, Select, Checkbox, ConfirmModal, useToast } from '@/components/ui';
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
    const [bloqueItemsLoading, setBloqueItemsLoading] = useState(false);
    const [newBloqueOpen, setNewBloqueOpen] = useState(false);
    const [newBloqueNombre, setNewBloqueNombre] = useState('');
    const [savingBloque, setSavingBloque] = useState(false);

    // Load data
    useEffect(() => {
        if (clase && isOpen) {
            loadHorarios();
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
    }, [clase?.id, isOpen]);

    useEffect(() => {
        if (selectedHorarioId) {
            loadInscripciones();
            loadListaEspera();
        }
    }, [selectedHorarioId]);

    const loadHorarios = async () => {
        if (!clase) return;
        const res = await api.getClaseHorarios(clase.id);
        if (res.ok && res.data) {
            setHorarios(res.data.horarios);
            if (res.data.horarios.length > 0 && !selectedHorarioId) {
                setSelectedHorarioId(res.data.horarios[0].id);
            }
        }
    };

    const loadInscripciones = async () => {
        if (!selectedHorarioId) return;
        const res = await api.getInscripciones(selectedHorarioId);
        if (res.ok && res.data) {
            setInscripciones(res.data.inscripciones);
        }
    };

    const loadListaEspera = async () => {
        if (!selectedHorarioId) return;
        const res = await api.getListaEspera(selectedHorarioId);
        if (res.ok && res.data) {
            setListaEspera(res.data.lista);
        }
    };

    const loadUsuarios = async (search: string) => {
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
    };

    const loadClaseEjercicios = async () => {
        if (!clase) return;
        const res = await api.getClaseEjercicios(clase.id);
        if (res.ok && res.data) {
            const items = res.data.ejercicios || [];
            setClaseEjercicios(items);
            setSelectedEjercicioIds(items.map((it) => Number(it.ejercicio_id)).filter((n) => Number.isFinite(n)));
        }
    };

    const loadEjerciciosCatalog = async (search: string) => {
        setEjerciciosLoading(true);
        try {
            const res = await api.getEjercicios({ search: search || undefined });
            if (res.ok && res.data) setEjercicios(res.data.ejercicios || []);
        } finally {
            setEjerciciosLoading(false);
        }
    };

    const loadBloques = async () => {
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
    };

    const loadBloqueItems = async (bloqueId: number) => {
        if (!clase) return;
        setBloqueItemsLoading(true);
        try {
            const res = await api.getClaseBloqueItems(clase.id, bloqueId);
            if (res.ok && res.data) setBloqueItems(res.data || []);
        } finally {
            setBloqueItemsLoading(false);
        }
    };

    const addEjercicioToBloque = (e: Ejercicio) => {
        setBloqueItems((prev) => [
            ...prev,
            {
                ejercicio_id: Number(e.id),
                nombre_ejercicio: String(e.nombre || ''),
                orden: prev.length,
                series: 0,
                repeticiones: '',
                descanso_segundos: 0,
                notas: '',
            },
        ]);
    };

    const removeBloqueItem = (index: number) => {
        setBloqueItems((prev) => prev.filter((_, i) => i !== index).map((it, i) => ({ ...it, orden: i })));
    };

    const saveBloque = async () => {
        if (!clase || !selectedBloqueId) return;
        setSavingBloque(true);
        try {
            const items = (bloqueItems || []).map((it, idx) => ({
                ejercicio_id: Number(it.ejercicio_id),
                orden: idx,
                series: Number(it.series || 0),
                repeticiones: String(it.repeticiones || ''),
                descanso_segundos: Number(it.descanso_segundos || 0),
                notas: String(it.notas || ''),
            }));
            const res = await api.updateClaseBloque(clase.id, selectedBloqueId, { nombre: bloqueNombre || 'Bloque', items });
            if (res.ok) {
                success('Bloque actualizado');
                loadBloques();
                loadBloqueItems(selectedBloqueId);
            } else {
                error(res.error || 'Error al guardar bloque');
            }
        } finally {
            setSavingBloque(false);
        }
    };

    const createBloque = async () => {
        if (!clase) return;
        const nombre = newBloqueNombre.trim();
        if (!nombre) return;
        setSavingBloque(true);
        try {
            const res = await api.createClaseBloque(clase.id, { nombre, items: [] });
            if (res.ok && res.data?.id) {
                success('Bloque creado');
                setNewBloqueNombre('');
                setNewBloqueOpen(false);
                await loadBloques();
                setSelectedBloqueId(res.data.id);
            } else {
                error(res.error || 'Error al crear bloque');
            }
        } finally {
            setSavingBloque(false);
        }
    };

    const deleteBloque = async () => {
        if (!clase || !selectedBloqueId) return;
        setSavingBloque(true);
        try {
            const res = await api.deleteClaseBloque(clase.id, selectedBloqueId);
            if (res.ok) {
                success('Bloque eliminado');
                setSelectedBloqueId(null);
                setBloqueItems([]);
                setBloqueNombre('');
                loadBloques();
            } else {
                error(res.error || 'Error al eliminar bloque');
            }
        } finally {
            setSavingBloque(false);
        }
    };

    useEffect(() => {
        if (!isOpen || !clase) return;
        if (activeTab === 'ejercicios') loadClaseEjercicios();
        if (activeTab === 'ejercicios' || activeTab === 'bloques') loadEjerciciosCatalog('');
        if (activeTab === 'bloques') loadBloques();
        if (activeTab === 'inscripciones' || activeTab === 'espera') loadUsuarios('');
    }, [activeTab, isOpen, clase?.id]);

    useEffect(() => {
        if (!isOpen) return;
        if (activeTab !== 'ejercicios' && activeTab !== 'bloques') return;
        if (!ejerciciosSearch.trim()) return;
        const t = setTimeout(() => {
            loadEjerciciosCatalog(ejerciciosSearch);
        }, 250);
        return () => clearTimeout(t);
    }, [ejerciciosSearch, activeTab, isOpen]);

    useEffect(() => {
        if (!isOpen) return;
        if (activeTab !== 'inscripciones' && activeTab !== 'espera') return;
        const t = setTimeout(() => {
            loadUsuarios(usuariosSearch);
        }, 250);
        return () => clearTimeout(t);
    }, [usuariosSearch, activeTab, isOpen]);

    useEffect(() => {
        if (!isOpen || activeTab !== 'bloques') return;
        if (!selectedBloqueId) return;
        loadBloqueItems(selectedBloqueId);
        const b = bloques.find((x) => x.id === selectedBloqueId);
        setBloqueNombre(b?.nombre || '');
    }, [selectedBloqueId, bloques, activeTab, isOpen]);

    // Horario CRUD
    const handleAddHorario = async () => {
        if (!clase) return;
        const res = await api.createClaseHorario(clase.id, horarioForm);
        if (res.ok) {
            success('Horario agregado');
            loadHorarios();
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
                                        options={profesores.map(p => ({ value: p.id.toString(), label: p.nombre }))}
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
                        <div className="space-y-4">
                            <div className="flex flex-col sm:flex-row sm:items-end gap-2">
                                <div className="flex-1">
                                    <div className="text-xs text-slate-500 mb-1">Buscar</div>
                                    <input
                                        className="input w-full"
                                        value={ejerciciosSearch}
                                        onChange={(e) => setEjerciciosSearch(e.target.value)}
                                        placeholder="Buscar ejercicio..."
                                    />
                                </div>
                                <Button onClick={saveEjercicios} isLoading={savingEjercicios}>
                                    Guardar
                                </Button>
                            </div>

                            <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                                <div className="text-xs text-slate-500">Seleccionados: {selectedEjercicioIds.length}</div>
                                <div className="mt-3 space-y-2 max-h-[340px] overflow-y-auto pr-1">
                                    {ejerciciosLoading ? (
                                        <div className="text-sm text-slate-400">Cargando…</div>
                                    ) : (
                                        <>
                                            {ejercicios.map((e) => (
                                                <Checkbox
                                                    key={String(e.id)}
                                                    label={String(e.nombre || `Ejercicio #${e.id}`)}
                                                    checked={selectedEjercicioIds.includes(Number(e.id))}
                                                    onChange={(ev) => toggleEjercicio(Number(e.id), Boolean((ev.target as HTMLInputElement).checked))}
                                                />
                                            ))}
                                            {!ejercicios.length ? <div className="text-sm text-slate-400">Sin resultados</div> : null}
                                        </>
                                    )}
                                </div>
                            </div>

                            {claseEjercicios.length ? (
                                <div className="text-xs text-slate-500">
                                    En la clase: {claseEjercicios.length} asignados
                                </div>
                            ) : (
                                <div className="text-xs text-slate-500">En la clase: sin ejercicios asignados</div>
                            )}
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
                        options={profesores.map((p) => ({ value: p.id.toString(), label: p.nombre }))}
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

