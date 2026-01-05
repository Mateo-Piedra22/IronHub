'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Dumbbell, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { api, type Rutina } from '@/lib/api';

export default function RoutinesPage() {
    const { user } = useAuth();
    const [routines, setRoutines] = useState<Rutina[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedDay, setExpandedDay] = useState<number | null>(0);

    const loadRoutines = useCallback(async () => {
        if (!user?.id) return;
        setLoading(true);
        try {
            const res = await api.getRutinas({ usuario_id: user.id });
            if (res.ok && res.data) {
                setRoutines(res.data.rutinas || []);
            }
        } catch (error) {
            console.error('Error loading routines:', error);
        } finally {
            setLoading(false);
        }
    }, [user?.id]);

    useEffect(() => {
        loadRoutines();
    }, [loadRoutines]);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-iron-400" />
            </div>
        );
    }

    const routine = routines[0];

    if (!routine) {
        return (
            <div className="space-y-6 py-6">
                <div>
                    <h1 className="text-2xl font-display font-bold text-white">Mi Rutina</h1>
                    <p className="text-neutral-400 mt-1">Plan de entrenamiento asignado</p>
                </div>
                <div className="glass-card p-8 text-center">
                    <Dumbbell className="w-12 h-12 text-neutral-600 mx-auto mb-4" />
                    <p className="text-neutral-400">No tenés una rutina asignada</p>
                    <p className="text-neutral-500 text-sm mt-2">Consultá con un profesor para que te asignen un plan de entrenamiento</p>
                </div>
            </div>
        );
    }

    const days = routine.dias || [];

    return (
        <div className="space-y-6 py-6">
            <div>
                <h1 className="text-2xl font-display font-bold text-white">Mi Rutina</h1>
                <p className="text-neutral-400 mt-1">Plan de entrenamiento asignado</p>
            </div>

            {/* Routine Info */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-card p-6"
            >
                <div className="flex items-start gap-4">
                    <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-iron-500 to-iron-700 flex items-center justify-center shadow-glow-sm">
                        <Dumbbell className="w-7 h-7 text-white" />
                    </div>
                    <div className="flex-1">
                        <h2 className="text-lg font-semibold text-white">{routine.nombre}</h2>
                        <p className="text-sm text-neutral-400 mt-1">
                            {days.length} días de entrenamiento
                        </p>
                        {routine.descripcion && (
                            <p className="text-xs text-neutral-500 mt-2">{routine.descripcion}</p>
                        )}
                    </div>
                </div>
            </motion.div>

            {/* Days */}
            <div className="space-y-4">
                {days.map((day, dayIndex) => (
                    <motion.div
                        key={dayIndex}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 + dayIndex * 0.1 }}
                        className="glass-card overflow-hidden"
                    >
                        <button
                            onClick={() => setExpandedDay(expandedDay === dayIndex ? null : dayIndex)}
                            className="w-full p-4 flex items-center justify-between hover:bg-neutral-800/30 transition-colors"
                        >
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-xl bg-iron-500/20 flex items-center justify-center">
                                    <span className="text-iron-400 font-bold">{dayIndex + 1}</span>
                                </div>
                                <div className="text-left">
                                    <h3 className="font-medium text-white">{day.nombre || `Día ${dayIndex + 1}`}</h3>
                                    <p className="text-xs text-neutral-500">{(day.ejercicios || []).length} ejercicios</p>
                                </div>
                            </div>
                            {expandedDay === dayIndex ? (
                                <ChevronUp className="w-5 h-5 text-neutral-400" />
                            ) : (
                                <ChevronDown className="w-5 h-5 text-neutral-400" />
                            )}
                        </button>

                        <AnimatePresence>
                            {expandedDay === dayIndex && (
                                <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    transition={{ duration: 0.2 }}
                                    className="overflow-hidden"
                                >
                                    <div className="border-t border-neutral-800/50 divide-y divide-neutral-800/50">
                                        {(day.ejercicios || []).map((exercise, exIndex) => (
                                            <div key={exIndex} className="p-4">
                                                <div className="flex items-start justify-between gap-4">
                                                    <div className="flex-1">
                                                        <h4 className="font-medium text-white">
                                                            {exercise.ejercicio_nombre || 'Ejercicio'}
                                                        </h4>
                                                        {exercise.notas && (
                                                            <p className="text-xs text-neutral-500 mt-1">{exercise.notas}</p>
                                                        )}
                                                    </div>
                                                    <div className="flex items-center gap-4 text-sm">
                                                        <div className="text-center">
                                                            <div className="text-white font-medium">{exercise.series || '-'}</div>
                                                            <div className="text-xs text-neutral-500">series</div>
                                                        </div>
                                                        <div className="text-center">
                                                            <div className="text-white font-medium">{exercise.repeticiones || '-'}</div>
                                                            <div className="text-xs text-neutral-500">reps</div>
                                                        </div>
                                                        <div className="text-center">
                                                            <div className="text-white font-medium">{exercise.descanso || '-'}</div>
                                                            <div className="text-xs text-neutral-500">descanso</div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </motion.div>
                ))}
            </div>
        </div>
    );
}
