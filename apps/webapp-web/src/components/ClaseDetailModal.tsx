'use client';

import { useState, useEffect } from 'react';
import {
    Clock,
    Users,
    List,
    Plus,
    Trash2,
    UserPlus,
    Bell,
    X,
    ChevronDown,
} from 'lucide-react';
import { Button, Modal, Input, Select, useToast } from '@/components/ui';
import {
    api,
    type Clase,
    type ClaseHorario,
    type Inscripcion,
    type ListaEspera,
    type Profesor,
    type Usuario,
} from '@/lib/api';
import { formatTime, cn } from '@/lib/utils';

interface ClaseDetailModalProps {
    isOpen: boolean;
    onClose: () => void;
    clase: Clase | null;
    profesores: Profesor[];
    onRefresh: () => void;
}

type TabType = 'horarios' | 'inscripciones' | 'espera';

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

    // Inscripciones
    const [inscripciones, setInscripciones] = useState<Inscripcion[]>([]);
    const [usuarios, setUsuarios] = useState<Usuario[]>([]);
    const [selectedUsuarioId, setSelectedUsuarioId] = useState<number | null>(null);

    // Lista de espera
    const [listaEspera, setListaEspera] = useState<ListaEspera[]>([]);

    // Load data
    useEffect(() => {
        if (clase && isOpen) {
            loadHorarios();
            loadUsuarios();
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

    const loadUsuarios = async () => {
        const res = await api.getUsuarios({ activo: true, limit: 500 });
        if (res.ok && res.data) {
            setUsuarios(res.data.usuarios);
        }
    };

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

    const handleDeleteHorario = async (horarioId: number) => {
        if (!clase) return;
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
                                        <button
                                            onClick={() => handleDeleteHorario(h.id)}
                                            className="p-2 text-slate-400 hover:text-danger-400"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
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
                </div>
            </div>
        </Modal>
    );
}

