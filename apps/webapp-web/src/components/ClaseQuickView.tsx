'use client';

import { useState, useEffect, type ComponentType } from 'react';
import { motion } from 'framer-motion';
import { Clock, Users, Layers, Calendar, ChevronRight } from 'lucide-react';
import { api, type Clase, type ClaseBloque, type ClaseHorario, type Inscripcion, type ClaseBloqueItem } from '@/lib/api';
import { cn, formatTime } from '@/lib/utils';
import { Button } from '@/components/ui';

interface ClaseQuickViewProps {
    clase: Clase | null;
    onClose: () => void;
    onManage: () => void;
}

const diasMap: Record<string, number> = {
    'lunes': 1, 'martes': 2, 'miércoles': 3, 'miercoles': 3,
    'jueves': 4, 'viernes': 5, 'sábado': 6, 'sabado': 6, 'domingo': 0
};

type TabId = 'proxima' | 'estructura' | 'horarios';

export default function ClaseQuickView({ clase, onClose, onManage }: ClaseQuickViewProps) {
    const [activeTab, setActiveTab] = useState<TabId>('proxima');

    // Data
    const [horarios, setHorarios] = useState<ClaseHorario[]>([]);
    const [bloques, setBloques] = useState<ClaseBloque[]>([]);
    const [bloqueItems, setBloqueItems] = useState<Record<number, ClaseBloqueItem[]>>({});

    // Derived Next Session
    const [nextSession, setNextSession] = useState<{
        horario: ClaseHorario;
        date: Date;
        inscripciones: Inscripcion[];
    } | null>(null);
    const [loadingNext, setLoadingNext] = useState(false);

    useEffect(() => {
        if (!clase) return;

        let mounted = true;
        const load = async () => {
            setLoading(true);
            try {
                // 1. Load Horarios & Bloques
                const [resHorarios, resBloques] = await Promise.all([
                    api.getClaseHorarios(clase.id),
                    api.getClaseBloques(clase.id)
                ]);

                if (!mounted) return;

                if (resHorarios.ok && resHorarios.data) {
                    setHorarios(resHorarios.data.horarios);
                }
                if (resBloques.ok && resBloques.data) {
                    setBloques(resBloques.data);
                }
            } catch (e) {
                console.error(e);
            } finally {
                if (mounted) setLoading(false);
            }
        };

        load();
        return () => { mounted = false; };
    }, [clase]);

    // Calculate Next Session and load assistants
    useEffect(() => {
        if (!horarios.length) {
            setNextSession(null);
            return;
        }

        const findNext = () => {
            const now = new Date();
            const currentDay = now.getDay(); // 0=Sun, 1=Mon...
            const currentTotalMin = now.getHours() * 60 + now.getMinutes();

            let best: { horario: ClaseHorario; date: Date; diff: number } | null = null;

            for (const h of horarios) {
                const hDay = diasMap[h.dia.toLowerCase()] ?? -1;
                if (hDay === -1) continue;

                // Parse time
                const [hh, mm] = (h.hora_inicio || '00:00').split(':').map(Number);
                const hTotalMin = hh * 60 + mm;

                // Calculate diff in minutes from now
                let diffDays = hDay - currentDay;
                if (diffDays < 0) diffDays += 7;

                // If today, check if time has passed
                if (diffDays === 0 && hTotalMin < currentTotalMin) {
                    diffDays = 7; // Next week
                }

                const diffMin = (diffDays * 24 * 60) + (hTotalMin - currentTotalMin);

                if (best === null || diffMin < best.diff) {
                    const d = new Date(now);
                    d.setDate(d.getDate() + diffDays);
                    d.setHours(hh, mm, 0, 0);
                    best = { horario: h, date: d, diff: diffMin };
                }
            }

            return best;
        };

        const next = findNext();
        if (next) {
            setLoadingNext(true);
            api.getInscripciones(next.horario.id).then(res => {
                if (res.ok && res.data) {
                    setNextSession({
                        horario: next.horario,
                        date: next.date,
                        inscripciones: res.data.inscripciones
                    });
                }
                setLoadingNext(false);
            });
        } else {
            setNextSession(null);
        }
    }, [horarios]);

    // Load items for expanded blocks (lazy)
    const toggleBloque = async (bloqueId: number) => {
        if (bloqueItems[bloqueId]) return; // already loaded

        try {
            const res = await api.getClaseBloqueItems(clase!.id, bloqueId);
            if (res.ok && res.data) {
                setBloqueItems(prev => ({ ...prev, [bloqueId]: res.data || [] }));
            }
        } catch { }
    };

    if (!clase) return null;

    return (
        <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden bg-slate-900 border-t border-slate-800 shadow-xl"
        >
            <div className="p-6">
                <div className="flex items-start justify-between mb-6">
                    <div>
                        <h2 className="text-xl font-display font-bold text-white flex items-center gap-2">
                            {clase.nombre}
                            <span className="text-xs font-sans font-normal text-slate-400 bg-slate-800 px-2 py-0.5 rounded-full">
                                Vista Rápida
                            </span>
                        </h2>
                        <p className="text-slate-400 text-sm mt-1 max-w-2xl">{clase.descripcion || 'Sin descripción'}</p>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button variant="secondary" onClick={onManage}>
                            Gestionar Clase
                        </Button>
                        <button
                            onClick={onClose}
                            className="p-2 text-slate-400 hover:text-white transition-colors"
                        >
                            Or cerrar
                        </button>
                    </div>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-slate-800 mb-6">
                    {(
                        [
                            { id: 'proxima', label: 'Próxima Sesión', icon: Calendar },
                            { id: 'estructura', label: 'Estructura (Bloques)', icon: Layers },
                            { id: 'horarios', label: 'Horarios', icon: Clock },
                        ] satisfies Array<{ id: TabId; label: string; icon: ComponentType<{ className?: string }> }>
                    ).map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={cn(
                                'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors relative',
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

                {/* Content */}
                <div className="min-h-[300px]">
                    {activeTab === 'proxima' && (
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                            <div className="col-span-1 space-y-4">
                                <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider">Detalles</h3>
                                {loadingNext ? (
                                    <div className="animate-pulse space-y-2">
                                        <div className="h-4 bg-slate-800 rounded w-1/2"></div>
                                        <div className="h-4 bg-slate-800 rounded w-3/4"></div>
                                    </div>
                                ) : nextSession ? (
                                    <div className="card p-4 bg-slate-950/50 border-slate-800">
                                        <div className="text-2xl font-bold text-white mb-1">
                                            {nextSession.date.toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long' })}
                                        </div>
                                        <div className="text-lg text-primary-400 font-mono mb-4">
                                            {formatTime(nextSession.horario.hora_inicio)} - {formatTime(nextSession.horario.hora_fin)}
                                        </div>

                                        <div className="space-y-3 pt-4 border-t border-slate-800">
                                            <div className="flex justify-between text-sm">
                                                <span className="text-slate-500">Profesor:</span>
                                                <span className="text-white">{nextSession.horario.profesor_nombre || 'Sin asignar'}</span>
                                            </div>
                                            <div className="flex justify-between text-sm">
                                                <span className="text-slate-500">Inscriptos:</span>
                                                <span className="text-white">
                                                    {nextSession.inscripciones.length} / {nextSession.horario.cupo || '∞'}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="text-slate-500 italic">No hay próximas sesiones programadas.</div>
                                )}
                            </div>

                            <div className="col-span-1 lg:col-span-2 space-y-4">
                                <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider">
                                    Asistentes ({nextSession?.inscripciones.length || 0})
                                </h3>
                                {loadingNext ? (
                                    <div className="text-sm text-slate-500">Cargando asistentes...</div>
                                ) : nextSession?.inscripciones.length ? (
                                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                                        {nextSession.inscripciones.map(i => (
                                            <div key={i.id} className="flex items-center gap-3 p-3 rounded-lg bg-slate-800/40 border border-slate-700/50">
                                                <div className="w-8 h-8 rounded-full bg-primary-500/20 text-primary-300 flex items-center justify-center font-bold text-xs">
                                                    {(i.usuario_nombre || 'U').charAt(0)}
                                                </div>
                                                <div className="min-w-0">
                                                    <div className="text-sm font-medium text-white truncate">{i.usuario_nombre || 'Usuario sin nombre'}</div>
                                                    {i.usuario_telefono && <div className="text-xs text-slate-500">{i.usuario_telefono}</div>}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="p-8 text-center border-2 border-dashed border-slate-800 rounded-xl">
                                        <Users className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                                        <p className="text-slate-500">Sin inscriptos aun</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {activeTab === 'estructura' && (
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider">Bloques de Trabajo</h3>
                                <div className="text-xs text-slate-500">Solo lectura</div>
                            </div>

                            <div className="space-y-3">
                                {bloques.length === 0 ? (
                                    <div className="text-center py-12 text-slate-500 bg-slate-950/30 rounded-xl">
                                        No hay bloques definidos para esta clase.
                                    </div>
                                ) : (
                                    bloques.map((bloque) => {
                                        const items = bloqueItems[bloque.id];
                                        return (
                                            <div key={bloque.id} className="border border-slate-800 rounded-lg overflow-hidden bg-slate-950/20">
                                                <button
                                                    onClick={() => toggleBloque(bloque.id)}
                                                    className="w-full flex items-center justify-between p-4 hover:bg-slate-800/50 transition-colors"
                                                >
                                                    <span className="font-medium text-white">{bloque.nombre}</span>
                                                    <ChevronRight className={cn("w-4 h-4 text-slate-500 transition-transform", items ? "rotate-90" : "")} />
                                                </button>

                                                {items && (
                                                    <div className="border-t border-slate-800 bg-slate-900/50 p-4">
                                                        {items.length === 0 ? (
                                                            <div className="text-sm text-slate-500 italic">Sin ejercicios</div>
                                                        ) : (
                                                            <div className="overflow-x-auto">
                                                                <table className="w-full text-sm text-left">
                                                                    <thead className="text-xs text-slate-500 uppercase bg-slate-800/50">
                                                                        <tr>
                                                                            <th className="px-3 py-2">Ejercicio</th>
                                                                            <th className="px-3 py-2">Series</th>
                                                                            <th className="px-3 py-2">Reps</th>
                                                                            <th className="px-3 py-2">Descanso</th>
                                                                            <th className="px-3 py-2">Notas</th>
                                                                        </tr>
                                                                    </thead>
                                                                    <tbody className="divide-y divide-slate-800">
                                                                        {items.map(it => (
                                                                            <tr key={it.id}>
                                                                                <td className="px-3 py-2 font-medium text-slate-300">{it.nombre_ejercicio}</td>
                                                                                <td className="px-3 py-2 text-slate-400">{it.series}</td>
                                                                                <td className="px-3 py-2 text-slate-400">{it.repeticiones || '-'}</td>
                                                                                <td className="px-3 py-2 text-slate-400">{it.descanso_segundos ? `${it.descanso_segundos}s` : '-'}</td>
                                                                                <td className="px-3 py-2 text-slate-500 italic">{it.notas || '-'}</td>
                                                                            </tr>
                                                                        ))}
                                                                    </tbody>
                                                                </table>
                                                            </div>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })
                                )}
                            </div>
                        </div>
                    )}

                    {activeTab === 'horarios' && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                            {horarios.map(h => (
                                <div key={h.id} className="p-4 rounded-lg bg-slate-800/40 border border-slate-700/50 flex flex-col gap-2">
                                    <div className="flex items-center gap-2 text-primary-400 mb-1">
                                        <Calendar className="w-4 h-4" />
                                        <span className="font-bold">{h.dia}</span>
                                    </div>
                                    <div className="text-2xl text-white font-mono">
                                        {formatTime(h.hora_inicio)}
                                    </div>
                                    <div className="text-sm text-slate-500 flex justify-between pt-2 border-t border-slate-700/50 mt-1">
                                        <span>{h.profesor_nombre || 'Sin profe'}</span>
                                        <span>Cupo: {h.cupo || '∞'}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </motion.div>
    );
}
