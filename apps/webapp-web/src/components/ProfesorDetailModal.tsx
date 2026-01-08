'use client';

import { useState, useEffect } from 'react';
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
} from 'lucide-react';
import { Button, Modal, Input, Select, Textarea, useToast } from '@/components/ui';
import {
    api,
    type Profesor,
    type ProfesorHorario,
    type ProfesorConfig,
    type ProfesorResumen,
    type Usuario,
} from '@/lib/api';
import { formatTime, formatCurrency, cn } from '@/lib/utils';

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

export default function ProfesorDetailModal({
    isOpen,
    onClose,
    profesor,
    onRefresh,
}: ProfesorDetailModalProps) {
    const { success, error } = useToast();
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

    // Load data
    useEffect(() => {
        if (profesor && isOpen) {
            loadHorarios();
            loadResumen();
            loadConfig();
            loadUsuarios();
        }
    }, [profesor?.id, isOpen]);

    useEffect(() => {
        if (profesor && isOpen) {
            loadResumen();
        }
    }, [selectedMes, selectedAnio]);

    const loadHorarios = async () => {
        if (!profesor) return;
        const res = await api.getProfesorHorarios(profesor.id);
        if (res.ok && res.data) {
            setHorarios(res.data.horarios);
        }
    };

    const loadResumen = async () => {
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
    };

    const loadConfig = async () => {
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
    };

    const loadUsuarios = async () => {
        const res = await api.getUsuarios({ activo: true, limit: 500 });
        if (res.ok && res.data) {
            setUsuarios(res.data.usuarios);
        }
    };

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

