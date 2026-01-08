'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
    DndContext,
    DragEndEvent,
    DragOverEvent,
    DragStartEvent,
    DragOverlay,
    closestCorners,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
    useDroppable,
} from '@dnd-kit/core';
import {
    arrayMove,
    SortableContext,
    sortableKeyboardCoordinates,
    useSortable,
    verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, Plus, Trash2, ChevronDown, ChevronRight, FileSpreadsheet } from 'lucide-react';
import { Button, Modal, Select, Input, useToast } from '@/components/ui';
import { api, type Ejercicio, type EjercicioRutina } from '@/lib/api';
import { cn } from '@/lib/utils';
import { ExcelPreviewViewer } from '@/components/ExcelPreviewViewer';

// Types
type DraggableExercise = EjercicioRutina & { dragId: string };

interface DayExercises {
    dayNumber: number;
    dayName: string;
    exercises: EjercicioRutina[];
}

interface DayWithIds {
    dayNumber: number;
    dayName: string;
    exercises: DraggableExercise[];
}

interface RoutineExerciseEditorProps {
    rutinaId: number;
    initialDays: DayExercises[];
    availableExercises: Ejercicio[];
    onSave: (days: DayExercises[]) => Promise<void>;
    onClose: () => void;
}

// Droppable Day Column
function DroppableDay({
    day,
    children,
    onAddExercise
}: {
    day: DayExercises;
    children: React.ReactNode;
    onAddExercise: () => void;
}) {
    const { setNodeRef, isOver } = useDroppable({
        id: `day-${day.dayNumber}`,
    });

    return (
        <div
            ref={setNodeRef}
            className={cn(
                'card overflow-hidden transition-all',
                isOver && 'ring-2 ring-primary-500 ring-offset-2 ring-offset-neutral-950'
            )}
        >
            <div className="p-3 bg-slate-900/80 border-b border-slate-800 flex items-center justify-between">
                <h3 className="font-semibold text-white">
                    Día {day.dayNumber}: {day.dayName || 'Sin nombre'}
                </h3>
                <button
                    onClick={onAddExercise}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                >
                    <Plus className="w-4 h-4" />
                </button>
            </div>
            <div className="p-3 min-h-[150px] space-y-2">
                {children}
            </div>
        </div>
    );
}

// Sortable Exercise Item
function SortableExercise({
    exercise,
    onEdit,
    onDelete,
}: {
    exercise: DraggableExercise;
    onEdit: () => void;
    onDelete: () => void;
}) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
    } = useSortable({ id: exercise.dragId });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
    };

    return (
        <div
            ref={setNodeRef}
            style={style}
            className={cn(
                'p-3 rounded-xl border border-slate-800 bg-slate-900/50 group',
                'hover:border-slate-700 transition-colors',
                isDragging && 'opacity-50 shadow-lg'
            )}
        >
            <div className="flex items-center gap-3">
                <div
                    {...attributes}
                    {...listeners}
                    className="cursor-grab text-slate-600 hover:text-slate-400 transition-colors"
                >
                    <GripVertical className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0" onClick={onEdit}>
                    <div className="font-medium text-white text-sm truncate cursor-pointer hover:text-primary-300">
                        {exercise.ejercicio_nombre || `Ejercicio #${exercise.ejercicio_id}`}
                    </div>
                    <div className="text-xs text-slate-500">
                        {exercise.series} series x {exercise.repeticiones} reps
                        {exercise.descanso && ` • ${exercise.descanso}s`}
                    </div>
                </div>
                <button
                    onClick={onDelete}
                    className="p-1.5 rounded text-slate-500 hover:text-danger-400 opacity-0 group-hover:opacity-100 transition-all"
                >
                    <Trash2 className="w-4 h-4" />
                </button>
            </div>
        </div>
    );
}

// Exercise Form Modal
interface ExerciseFormModalProps {
    isOpen: boolean;
    onClose: () => void;
    exercise?: EjercicioRutina | null;
    availableExercises: Ejercicio[];
    onSave: (data: Partial<EjercicioRutina>) => void;
}

function ExerciseFormModal({
    isOpen,
    onClose,
    exercise,
    availableExercises,
    onSave,
}: ExerciseFormModalProps) {
    const [formData, setFormData] = useState({
        ejercicio_id: 0,
        series: 3,
        repeticiones: '10',
        descanso: 60,
        notas: '',
    });

    useEffect(() => {
        if (isOpen) {
            if (exercise) {
                setFormData({
                    ejercicio_id: exercise.ejercicio_id,
                    series: typeof exercise.series === 'number' ? exercise.series : Number(exercise.series) || 3,
                    repeticiones: exercise.repeticiones || '10',
                    descanso: exercise.descanso || 60,
                    notas: exercise.notas || '',
                });
            } else {
                setFormData({
                    ejercicio_id: 0,
                    series: 3,
                    repeticiones: '10',
                    descanso: 60,
                    notas: '',
                });
            }
        }
    }, [isOpen, exercise]);

    const handleSubmit = () => {
        if (!formData.ejercicio_id) return;
        const ej = availableExercises.find(e => e.id === formData.ejercicio_id);
        onSave({
            ...formData,
            ejercicio_nombre: ej?.nombre,
        });
        onClose();
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={exercise ? 'Editar Ejercicio' : 'Agregar Ejercicio'}
            size="md"
            footer={
                <>
                    <Button variant="secondary" onClick={onClose}>
                        Cancelar
                    </Button>
                    <Button onClick={handleSubmit} disabled={!formData.ejercicio_id}>
                        {exercise ? 'Guardar' : 'Agregar'}
                    </Button>
                </>
            }
        >
            <div className="space-y-4">
                <Select
                    label="Ejercicio"
                    value={formData.ejercicio_id?.toString() || ''}
                    onChange={(e) => setFormData({ ...formData, ejercicio_id: Number(e.target.value) })}
                    options={availableExercises.map((e) => ({ value: e.id.toString(), label: e.nombre }))}
                    placeholder="Seleccionar ejercicio"
                />
                <div className="grid grid-cols-3 gap-4">
                    <Input
                        label="Series"
                        type="number"
                        min={1}
                        value={formData.series}
                        onChange={(e) => setFormData({ ...formData, series: Number(e.target.value) })}
                    />
                    <Input
                        label="Repeticiones"
                        value={formData.repeticiones}
                        onChange={(e) => setFormData({ ...formData, repeticiones: e.target.value })}
                        placeholder="10 o 8-12"
                    />
                    <Input
                        label="Descanso (seg)"
                        type="number"
                        min={0}
                        value={formData.descanso}
                        onChange={(e) => setFormData({ ...formData, descanso: Number(e.target.value) })}
                    />
                </div>
                <Input
                    label="Notas"
                    value={formData.notas}
                    onChange={(e) => setFormData({ ...formData, notas: e.target.value })}
                    placeholder="Instrucciones adicionales..."
                />
            </div>
        </Modal>
    );
}

// Main Editor Component
export function RoutineExerciseEditor({
    rutinaId,
    initialDays,
    availableExercises,
    onSave,
    onClose,
}: RoutineExerciseEditorProps) {
    const { success, error } = useToast();
    const [days, setDays] = useState<DayExercises[]>(initialDays);
    const [saving, setSaving] = useState(false);
    const [activeExercise, setActiveExercise] = useState<DraggableExercise | null>(null);

    // Exercise form modal state
    const [exerciseModalOpen, setExerciseModalOpen] = useState(false);
    const [editingExercise, setEditingExercise] = useState<EjercicioRutina | null>(null);
    const [targetDayNumber, setTargetDayNumber] = useState<number>(1);

    // Excel preview state
    const [showPreview, setShowPreview] = useState(false);

    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: { distance: 8 },
        }),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    // Generate unique IDs for exercises
    const getDaysWithIds = useCallback((): DayWithIds[] => {
        return days.map((day) => ({
            ...day,
            exercises: day.exercises.map((ex, idx): DraggableExercise => ({
                ...ex,
                dragId: `day${day.dayNumber}-ex${idx}-${ex.ejercicio_id}`,
            })),
        }));
    }, [days]);

    const daysWithIds: DayWithIds[] = getDaysWithIds();

    // Find which day an exercise belongs to
    const findDayOfExercise = (exerciseId: string): number | null => {
        for (const day of daysWithIds) {
            if (day.exercises.some((ex) => ex.dragId === exerciseId)) {
                return day.dayNumber;
            }
        }
        return null;
    };

    const handleDragStart = (event: DragStartEvent) => {
        const exerciseId = event.active.id as string;
        for (const day of daysWithIds) {
            const ex = day.exercises.find((e) => e.dragId === exerciseId);
            if (ex) {
                setActiveExercise(ex);
                break;
            }
        }
    };

    const handleDragOver = (event: DragOverEvent) => {
        const { active, over } = event;
        if (!over) return;

        const activeId = active.id as string;
        const overId = over.id as string;

        const activeDay = findDayOfExercise(activeId);

        // Check if dropping on a day column
        if (overId.startsWith('day-')) {
            const targetDay = parseInt(overId.replace('day-', ''));
            if (activeDay !== null && activeDay !== targetDay) {
                // Move to new day
                setDays((prev) => {
                    const newDays = prev.map((d) => ({
                        ...d,
                        exercises: [...d.exercises],
                    }));

                    const sourceDayIdx = newDays.findIndex((d) => d.dayNumber === activeDay);
                    const targetDayIdx = newDays.findIndex((d) => d.dayNumber === targetDay);

                    const sourceExIdx = newDays[sourceDayIdx].exercises.findIndex(
                        (_, idx) => daysWithIds[sourceDayIdx].exercises[idx]?.dragId === activeId
                    );

                    if (sourceExIdx >= 0) {
                        const [moved] = newDays[sourceDayIdx].exercises.splice(sourceExIdx, 1);
                        newDays[targetDayIdx].exercises.push(moved);
                    }

                    return newDays;
                });
            }
            return;
        }

        // Dropping on another exercise
        const overDay = findDayOfExercise(overId);
        if (activeDay !== null && overDay !== null && activeDay !== overDay) {
            // Move between days at specific position
            setDays((prev) => {
                const newDays = prev.map((d) => ({
                    ...d,
                    exercises: [...d.exercises],
                }));

                const sourceDayIdx = newDays.findIndex((d) => d.dayNumber === activeDay);
                const targetDayIdx = newDays.findIndex((d) => d.dayNumber === overDay);

                const sourceExIdx = newDays[sourceDayIdx].exercises.findIndex(
                    (_, idx) => daysWithIds[sourceDayIdx].exercises[idx]?.dragId === activeId
                );
                const targetExIdx = newDays[targetDayIdx].exercises.findIndex(
                    (_, idx) => daysWithIds[targetDayIdx].exercises[idx]?.dragId === overId
                );

                if (sourceExIdx >= 0) {
                    const [moved] = newDays[sourceDayIdx].exercises.splice(sourceExIdx, 1);
                    newDays[targetDayIdx].exercises.splice(targetExIdx, 0, moved);
                }

                return newDays;
            });
        }
    };

    const handleDragEnd = (event: DragEndEvent) => {
        const { active, over } = event;
        setActiveExercise(null);

        if (!over || active.id === over.id) return;

        const activeId = active.id as string;
        const overId = over.id as string;

        const activeDay = findDayOfExercise(activeId);
        const overDay = findDayOfExercise(overId);

        // Same-day reorder
        if (activeDay !== null && overDay !== null && activeDay === overDay) {
            setDays((prev) => {
                const newDays = prev.map((d) => ({
                    ...d,
                    exercises: [...d.exercises],
                }));

                const dayIdx = newDays.findIndex((d) => d.dayNumber === activeDay);
                const oldIndex = newDays[dayIdx].exercises.findIndex(
                    (_, idx) => daysWithIds[dayIdx].exercises[idx]?.dragId === activeId
                );
                const newIndex = newDays[dayIdx].exercises.findIndex(
                    (_, idx) => daysWithIds[dayIdx].exercises[idx]?.dragId === overId
                );

                newDays[dayIdx].exercises = arrayMove(newDays[dayIdx].exercises, oldIndex, newIndex);
                return newDays;
            });
        }
    };

    // Add exercise to day
    const handleAddExercise = (dayNumber: number) => {
        setTargetDayNumber(dayNumber);
        setEditingExercise(null);
        setExerciseModalOpen(true);
    };

    // Edit exercise
    const handleEditExercise = (dayNumber: number, exercise: EjercicioRutina) => {
        setTargetDayNumber(dayNumber);
        setEditingExercise(exercise);
        setExerciseModalOpen(true);
    };

    // Delete exercise
    const handleDeleteExercise = (dayNumber: number, exerciseIndex: number) => {
        setDays((prev) =>
            prev.map((d) =>
                d.dayNumber === dayNumber
                    ? { ...d, exercises: d.exercises.filter((_, i) => i !== exerciseIndex) }
                    : d
            )
        );
    };

    // Save exercise from modal
    const handleSaveExercise = (data: Partial<EjercicioRutina>) => {
        setDays((prev) =>
            prev.map((d) => {
                if (d.dayNumber !== targetDayNumber) return d;

                if (editingExercise) {
                    // Update existing
                    return {
                        ...d,
                        exercises: d.exercises.map((ex) =>
                            ex === editingExercise ? { ...ex, ...data } : ex
                        ),
                    };
                } else {
                    // Add new
                    return {
                        ...d,
                        exercises: [
                            ...d.exercises,
                            {
                                ejercicio_id: data.ejercicio_id!,
                                ejercicio_nombre: data.ejercicio_nombre,
                                series: data.series || 3,
                                repeticiones: data.repeticiones || '10',
                                descanso: data.descanso || 60,
                                notas: data.notas || '',
                                orden: d.exercises.length,
                            } as EjercicioRutina,
                        ],
                    };
                }
            })
        );
    };

    // Save all changes
    const handleSaveAll = async () => {
        setSaving(true);
        try {
            await onSave(days);
            success('Rutina guardada correctamente');
        } catch (e) {
            error('Error al guardar la rutina');
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h2 className="text-xl font-display font-bold text-white">
                    Configurar Ejercicios
                </h2>
                <div className="flex items-center gap-2">
                    <Button
                        variant={showPreview ? 'primary' : 'secondary'}
                        leftIcon={<FileSpreadsheet className="w-4 h-4" />}
                        onClick={() => setShowPreview(!showPreview)}
                    >
                        {showPreview ? 'Ocultar Preview' : 'Ver Excel'}
                    </Button>
                    <Button variant="secondary" onClick={onClose} disabled={saving}>
                        Cancelar
                    </Button>
                    <Button onClick={handleSaveAll} isLoading={saving}>
                        Guardar Cambios
                    </Button>
                </div>
            </div>

            {/* Days Grid with Drag & Drop */}
            <DndContext
                sensors={sensors}
                collisionDetection={closestCorners}
                onDragStart={handleDragStart}
                onDragOver={handleDragOver}
                onDragEnd={handleDragEnd}
            >
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                    {daysWithIds.map((day) => (
                        <DroppableDay
                            key={day.dayNumber}
                            day={day}
                            onAddExercise={() => handleAddExercise(day.dayNumber)}
                        >
                            <SortableContext
                                items={day.exercises.map((e) => e.dragId)}
                                strategy={verticalListSortingStrategy}
                            >
                                {day.exercises.length === 0 ? (
                                    <div className="text-center text-slate-600 text-sm py-8">
                                        Arrastra ejercicios aquí
                                    </div>
                                ) : (
                                    day.exercises.map((exercise, idx) => (
                                        <SortableExercise
                                            key={exercise.dragId}
                                            exercise={exercise}
                                            onEdit={() => handleEditExercise(day.dayNumber, days[days.findIndex(d => d.dayNumber === day.dayNumber)].exercises[idx])}
                                            onDelete={() => handleDeleteExercise(day.dayNumber, idx)}
                                        />
                                    ))
                                )}
                            </SortableContext>
                        </DroppableDay>
                    ))}
                </div>

                <DragOverlay>
                    {activeExercise && (
                        <div className="p-3 rounded-xl border border-primary-500 bg-slate-900 shadow-lg rotate-2">
                            <div className="font-medium text-white text-sm">
                                {activeExercise.ejercicio_nombre}
                            </div>
                            <div className="text-xs text-slate-500">
                                {activeExercise.series} x {activeExercise.repeticiones}
                            </div>
                        </div>
                    )}
                </DragOverlay>
            </DndContext>

            {/* Exercise Form Modal */}
            <ExerciseFormModal
                isOpen={exerciseModalOpen}
                onClose={() => setExerciseModalOpen(false)}
                exercise={editingExercise}
                availableExercises={availableExercises}
                onSave={handleSaveExercise}
            />

            {/* Excel Preview */}
            <ExcelPreviewViewer
                excelUrl={api.getRutinaExcelUrl(rutinaId)}
                isOpen={showPreview}
                onMinimize={() => setShowPreview(false)}
            />
        </div>
    );
}

