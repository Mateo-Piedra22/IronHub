'use client';

import { useState, useEffect, useCallback, Suspense } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Dumbbell, ChevronDown, ChevronUp, Loader2, QrCode, Lock, Info, PlayCircle } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { api, type Rutina, type EjercicioRutina } from '@/lib/api';
import { QRScannerModal } from '@/components/QrScannerModal';
import { UserExerciseModal } from '@/components/UserExerciseModal';
import { Button, useToast } from '@/components/ui';

function RoutinesContent() {
    const { user } = useAuth();
    const router = useRouter();
    const searchParams = useSearchParams();
    const [routines, setRoutines] = useState<Rutina[]>([]);
    const [routine, setRoutine] = useState<Rutina | null>(null);
    const [loading, setLoading] = useState(true);
    const [expandedDay, setExpandedDay] = useState<number | null>(0);

    // Strict QR Logic
    const [isBlocked, setIsBlocked] = useState(true);
    const [showScanner, setShowScanner] = useState(false);
    const [selectedExercise, setSelectedExercise] = useState<EjercicioRutina | null>(null);
    const { success, error } = useToast();

    // Check routine unlock status (Client-side persistence)
    const checkUnlockStatus = useCallback((uuid: string) => {
        if (!uuid) return false;
        try {
            const unlocked = localStorage.getItem(`unlocked_routine_${uuid}`);
            if (unlocked) {
                const timestamp = parseInt(unlocked, 10);
                const now = Date.now();
                // 24 hours = 86400000 ms
                if (now - timestamp < 86400000) {
                    return true;
                } else {
                    localStorage.removeItem(`unlocked_routine_${uuid}`);
                }
            }
        } catch (e) {
            // ignore
        }
        return false;
    }, []);

    const verifyAndUnlock = useCallback(async (uuid: string) => {
        try {
            const res = await api.verifyRoutineQR(uuid);
            if (res.ok && res.data) {
                // Determine if this is the routine we should show
                setRoutine(res.data.rutina); // Use the returned full routine
                setIsBlocked(false);
                // Persist locally
                localStorage.setItem(`unlocked_routine_${uuid}`, Date.now().toString());
                success('¡Rutina desbloqueada!');

                // Clear param to clean URL? optional
                // router.replace('/dashboard/routines'); 
            } else {
                error('Rutina no válida o no encontrada');
            }
        } catch (e) {
            console.error(e);
            error('Error al verificar rutina');
        }
    }, [success, error]);

    const loadRoutines = useCallback(async () => {
        if (!user?.id) return;
        setLoading(true);
        try {
            const res = await api.getRutinas({ usuario_id: user.id });
            if (res.ok && res.data) {
                const list = res.data.rutinas || [];
                setRoutines(list);

                // If we haven't set a specific routine yet (e.g. from QR param), pick the first one
                setRoutine((prev) => {
                    if (prev) return prev; // Already set by effect?
                    return list.length > 0 ? list[0] : null;
                });
            }
        } catch (error) {
            console.error('Error loading routines:', error);
        } finally {
            setLoading(false);
        }
    }, [user?.id]);

    useEffect(() => {
        loadRoutines().then(() => {
            // After loading defaults, check params or local storage for the *current* routine
            const paramUuid = searchParams.get('uuid');
            if (paramUuid) {
                verifyAndUnlock(paramUuid);
            }
        });
    }, [loadRoutines, searchParams, verifyAndUnlock]);

    // Update block status when routine changes
    useEffect(() => {
        if (routine?.uuid_rutina) {
            const isUnlocked = checkUnlockStatus(routine.uuid_rutina);
            // Only set blocked if not already unlocked (to avoid locking if just unlocked)
            // Actually, state isBlocked defaults to true.
            if (isUnlocked) {
                setIsBlocked(false);
            } else {
                // If explicitly switching routines, we might want to lock? 
                // But for now we only support 1 routine view basically.
                // If paramUuid verified, isBlocked became false.
            }
        }
    }, [routine, checkUnlockStatus]);

    if (loading && !routine) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
            </div>
        );
    }

    // Verify scan
    const handleScan = (decodedText: string) => {
        try {
            let scannedUuid = decodedText;
            // Handle URL format
            if (decodedText.includes('/qr_scan/')) {
                const parts = decodedText.split('/qr_scan/');
                if (parts.length > 1) {
                    scannedUuid = parts[1];
                }
            } else if (decodedText.includes('uuid=')) {
                try {
                    const urlObj = new URL(decodedText);
                    const u = urlObj.searchParams.get('uuid');
                    if (u) scannedUuid = u;
                } catch (e) { }
            }
            // Clean params
            scannedUuid = scannedUuid.split('?')[0].split('&')[0];

            if (scannedUuid) {
                verifyAndUnlock(scannedUuid);
                setShowScanner(false);
            } else {
                error('Código inválido');
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
                        {(routine.creada_por_nombre || routine.fecha_creacion || routine.sucursal_nombre) && (
                            <div className="text-xs text-slate-500 mt-2 space-y-1">
                                {routine.creada_por_nombre && <div>Creada por {routine.creada_por_nombre}</div>}
                                {routine.fecha_creacion && (
                                    <div>Creación: {new Date(routine.fecha_creacion).toLocaleDateString('es-AR')}</div>
                                )}
                                {routine.sucursal_nombre && <div>Sucursal: {routine.sucursal_nombre}</div>}
                            </div>
                        )}
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
                                                            {/* Video Link if available */}
                                                            {exercise.ejercicio_video_url && (
                                                                <a
                                                                    href={exercise.ejercicio_video_url}
                                                                    target="_blank"
                                                                    rel="noopener noreferrer"
                                                                    className="inline-flex items-center gap-1.5 mt-2 text-primary-400 hover:text-primary-300 text-xs font-medium bg-primary-500/10 hover:bg-primary-500/20 px-2.5 py-1.5 rounded-lg transition-colors group"
                                                                >
                                                                    <PlayCircle className="w-3.5 h-3.5" />
                                                                    Ver video explicativo
                                                                </a>
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

            <QRScannerModal
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

export default function RoutinesPage() {
    return (
        <Suspense
            fallback={
                <div className="flex items-center justify-center h-64">
                    <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
                </div>
            }
        >
            <RoutinesContent />
        </Suspense>
    );
}

