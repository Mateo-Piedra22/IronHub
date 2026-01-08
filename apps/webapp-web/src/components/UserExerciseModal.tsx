'use client';

import { X, PlayCircle, Dumbbell, AlertCircle } from 'lucide-react';
import { Modal } from '@/components/ui';
import { type EjercicioRutina } from '@/lib/api';

interface UserExerciseModalProps {
    isOpen: boolean;
    onClose: () => void;
    exercise: EjercicioRutina | null;
}

export function UserExerciseModal({ isOpen, onClose, exercise }: UserExerciseModalProps) {
    if (!exercise) return null;

    // Helper to determine if video is playable directly
    const isVideo = exercise.video_url?.match(/\.(mp4|webm|ogg)$/i);
    const isYoutube = exercise.video_url?.match(/(youtube\.com|youtu\.be)/i);
    const isGif = exercise.video_url?.match(/\.(gif)$/i);

    const renderMedia = () => {
        if (!exercise.video_url) {
            return (
                <div className="w-full aspect-video bg-slate-900 rounded-lg flex flex-col items-center justify-center text-slate-500 gap-2">
                    <PlayCircle className="w-12 h-12 opacity-20" />
                    <span className="text-sm">Sin video disponible</span>
                </div>
            );
        }

        if (isVideo) {
            return (
                <video
                    src={exercise.video_url}
                    controls
                    className="w-full rounded-lg bg-black aspect-video object-contain"
                />
            );
        }

        if (isGif) {
            // eslint-disable-next-line @next/next/no-img-element
            return <img src={exercise.video_url} alt={exercise.ejercicio_nombre} className="w-full rounded-lg bg-black aspect-video object-contain" />;
        }

        if (isYoutube) {
            // Basic embed attempt (fragile without proper ID extraction, but matches legacy)
            // Using a generic link button if embed fails is safer, but let's try link first.
            return (
                <div className="w-full aspect-video bg-slate-900 rounded-lg flex flex-col items-center justify-center gap-4">
                    <p className="text-slate-400">Ver demostración en YouTube</p>
                    <a
                        href={exercise.video_url}
                        target="_blank"
                        rel="noreferrer"
                        className="px-4 py-2 bg-red-600 text-white rounded-full text-sm font-medium hover:bg-red-700 transition-colors"
                    >
                        Abrir Video
                    </a>
                </div>
            );
        }

        // Fallback for unknown URLs
        return (
            <div className="w-full aspect-video bg-slate-900 rounded-lg flex flex-col items-center justify-center gap-4">
                <p className="text-slate-400">Ver demostración</p>
                <a
                    href={exercise.video_url}
                    target="_blank"
                    rel="noreferrer"
                    className="px-4 py-2 bg-primary-600 text-white rounded-full text-sm font-medium hover:bg-primary-700 transition-colors"
                >
                    Abrir Enlace
                </a>
            </div>
        );
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={exercise.ejercicio_nombre || 'Detalle del Ejercicio'}
            size="lg"
        >
            <div className="space-y-6">
                {/* Media Player */}
                {renderMedia()}

                {/* Info Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-slate-900/50 p-4 rounded-lg space-y-2 text-white">
                        <div className="flex items-center gap-2 text-slate-400 mb-2">
                            <Dumbbell className="w-4 h-4" />
                            <span className="text-xs font-bold uppercase tracking-wider">Detalles</span>
                        </div>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                                <span className="block text-slate-500 text-xs">Series</span>
                                <span className="font-medium">{exercise.series || '-'}</span>
                            </div>
                            <div>
                                <span className="block text-slate-500 text-xs">Repeticiones</span>
                                <span className="font-medium">{exercise.repeticiones || '-'}</span>
                            </div>
                            <div>
                                <span className="block text-slate-500 text-xs">Descanso</span>
                                <span className="font-medium">{exercise.descanso ? `${exercise.descanso}"` : '-'}</span>
                            </div>
                            <div>
                                <span className="block text-slate-500 text-xs">Equipamiento</span>
                                <span className="font-medium">{exercise.equipamiento || '-'}</span>
                            </div>
                        </div>
                    </div>

                    <div className="bg-slate-900/50 p-4 rounded-lg text-white">
                        <div className="flex items-center gap-2 text-slate-400 mb-2">
                            <AlertCircle className="w-4 h-4" />
                            <span className="text-xs font-bold uppercase tracking-wider">Notas / Descripción</span>
                        </div>
                        <div className="text-sm space-y-3">
                            {exercise.notas && (
                                <div className="p-2 bg-yellow-500/10 border border-yellow-500/20 rounded text-yellow-200">
                                    <span className="font-bold text-xs uppercase block mb-1">Nota:</span>
                                    {exercise.notas}
                                </div>
                            )}
                            {exercise.descripcion ? (
                                <p className="text-slate-300 leading-relaxed text-xs">
                                    {exercise.descripcion}
                                </p>
                            ) : (
                                <p className="text-slate-500 italic text-xs">Sin descripción disponible</p>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </Modal>
    );
}

