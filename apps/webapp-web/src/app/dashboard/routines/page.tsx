'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Dumbbell, ChevronDown, ChevronUp, Loader2, QrCode, Lock, Info, PlayCircle } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { api, type Rutina, type EjercicioRutina } from '@/lib/api';
import { QrScannerModal } from '@/components/QrScannerModal';
import { UserExerciseModal } from '@/components/UserExerciseModal';
import { Button, useToast } from '@/components/ui';

export default function RoutinesPage() {
    const { user } = useAuth();
    const [routines, setRoutines] = useState<Rutina[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedDay, setExpandedDay] = useState<number | null>(0);

    // Strict QR Logic
    const [isBlocked, setIsBlocked] = useState(true);
    const [showScanner, setShowScanner] = useState(false);
    const [selectedExercise, setSelectedExercise] = useState<EjercicioRutina | null>(null);
    const { success, error } = useToast();

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
                <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
            </div>
        );
    }

    const routine = routines[0];

    // Verify scan
    const handleScan = (decodedText: string) => {
        try {
            // Decoded text should be the UUID or a JSON containing it? 
            // Legacy usually just encoded the UUID string.
            // Let's assume it's the uuid string or a URL ending with it.
            // But strict check: matching uuid_rutina.

            // Clean the scanned text just in case (urls etc)
            // If it's a URL like /rutina/UUID, extract UUID.
            let scannedUuid = decodedText;
            if (decodedText.includes('/')) {
                const parts = decodedText.split('/');
                scannedUuid = parts[parts.length - 1];
            }

            if (!routine.uuid_rutina) {
                // Fallback if routine has no UUID for some reason (legacy data?)
                // Allow matching ID? No, safer to fail or warn.
                error('Esta rutina no tiene código QR asociado. Pedile a tu profe que la actualice.');
                setShowScanner(false);
                return;
            }

            if (scannedUuid === routine.uuid_rutina) {
                setIsBlocked(false);
                setShowScanner(false);
                success('¡Rutina desbloqueada!');
            } else {
                error('El código QR no coincide con tu rutina asignada.');
                setShowScanner(false);
            }
        } catch (e) {
            console.error(e);
            error('Error al procesar el código QR');
            setShowScanner(false);
        }
    };

    if (!routine) {
        return (
            <div className="space-y-6 py-6">
                <div>
                    <h1 className="text-2xl font-display font-bold text-white">Mi Rutina</h1>
                    <p className="text-slate-400 mt-1">Plan de entrenamiento asignado</p>
                </div>
                <div className="card p-8 text-center">
                    <Dumbbell className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                    <p className="text-slate-400">No tenés una rutina asignada</p>
                    <p className="text-slate-500 text-sm mt-2">Consultá con un profesor para que te asignen un plan de entrenamiento</p>
                </div>
            </div>
        );
    }

    const days = routine.dias || [];

    return (
        <div className="space-y-6 py-6">
            <div>
                <h1 className="text-2xl font-display font-bold text-white">Mi Rutina</h1>
                <p className="text-slate-400 mt-1">Plan de entrenamiento asignado</p>
            </div>

            {/* Routine Info */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="card p-6"
            >
                <div className="flex items-start gap-4">
                    <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-sm">
                        <Dumbbell className="w-7 h-7 text-white" />
                    </div>
                    <div className="flex-1">
                        <h2 className="text-lg font-semibold text-white">{routine.nombre}</h2>
                        <p className="text-sm text-slate-400 mt-1">
                            {days.length} días de entrenamiento
                        </p>
                        {routine.descripcion && (
                            <p className="text-xs text-slate-500 mt-2">{routine.descripcion}</p>
                        )}
                    </div>
                </div>
            </motion.div>

            {/* Locked State / Days */}
            {isBlocked ? (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="card p-8 text-center space-y-4"
                >
                    <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center mx-auto mb-4">
                        <Lock className="w-8 h-8 text-slate-500" />
                    </div>
                    <div>
                        <h3 className="text-lg font-semibold text-white">Rutina Bloqueada</h3>
                        <p className="text-slate-400 text-sm mt-1 max-w-xs mx-auto">
                            Para ver los ejercicios, escaneá el código QR presente en tu planilla de entrenamiento.
                        </p>
                    </div>
                    <Button
                        onClick={() => setShowScanner(true)}
                        className="bg-primary-500 hover:bg-primary-600 text-white"
                    >
                        <QrCode className="w-4 h-4 mr-2" />
                        Escanear QR
                    </Button>
                </motion.div>
            ) : (
                /* Days List */
                <div className="space-y-4">
                    {days.map((day, dayIndex) => (
                        <motion.div
                            key={dayIndex}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.1 + dayIndex * 0.1 }}
                            className="card overflow-hidden"
                        >
                            <button
                                onClick={() => setExpandedDay(expandedDay === dayIndex ? null : dayIndex)}
                                className="w-full p-4 flex items-center justify-between hover:bg-slate-800/30 transition-colors"
                            >
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-xl bg-primary-500/20 flex items-center justify-center">
                                        <span className="text-primary-400 font-bold">{dayIndex + 1}</span>
                                    </div>
                                    <div className="text-left">
                                        <h3 className="font-medium text-white">{day.nombre || `Día ${dayIndex + 1}`}</h3>
                                        <p className="text-xs text-slate-500">{(day.ejercicios || []).length} ejercicios</p>
                                    </div>
                                </div>
                                {expandedDay === dayIndex ? (
                                    <ChevronUp className="w-5 h-5 text-slate-400" />
                                ) : (
                                    <ChevronDown className="w-5 h-5 text-slate-400" />
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
                                        <div className="border-t border-slate-800/50 divide-y divide-neutral-800/50">
                                            {(day.ejercicios || []).map((exercise, exIndex) => (
                                                <div key={exIndex} className="p-4">
                                                    <div className="flex items-start justify-between gap-4">
                                                        <div className="flex-1">
                                                            <h4 className="font-medium text-white">
                                                                {exercise.ejercicio_nombre || 'Ejercicio'}
                                                            </h4>
                                                            {exercise.notas && (
                                                                <p className="text-xs text-slate-500 mt-1">{exercise.notas}</p>
                                                            )}
                                                        </div>
                                                        <div className="flex items-center gap-4 text-sm">
                                                            <div className="text-center hidden sm:block">
                                                                <div className="text-white font-medium">{exercise.series || '-'}</div>
                                                                <div className="text-xs text-slate-500">series</div>
                                                            </div>
                                                            <div className="text-center hidden sm:block">
                                                                <div className="text-white font-medium">{exercise.repeticiones || '-'}</div>
                                                                <div className="text-xs text-slate-500">reps</div>
                                                            </div>
                                                            <button
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    setSelectedExercise(exercise);
                                                                }}
                                                                className="p-2 hover:bg-slate-800 rounded-lg text-primary-400 transition-colors"
                                                            >
                                                                <Info className="w-5 h-5" />
                                                            </button>
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
            )}

            <QrScannerModal
                isOpen={showScanner}
                onClose={() => setShowScanner(false)}
                onScan={handleScan}
                description="Apuntá tu cámara al código QR de la rutina"
            />

            <UserExerciseModal
                isOpen={!!selectedExercise}
                onClose={() => setSelectedExercise(null)}
                exercise={selectedExercise}
            />
        </div >
    );
}

