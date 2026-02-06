'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
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
import {
    GripVertical,
    Plus,
    Trash2,
    ChevronDown,
    ChevronRight,
    FileSpreadsheet,
    Save,
    X,
    Search,
    Copy,
    ArrowUp,
    ArrowDown,
    Minimize2,
    Maximize2,
    RefreshCw,
} from 'lucide-react';
import { Button, Modal, Select, Input, Textarea, useToast } from '@/components/ui';
import { ExcelPreviewViewer } from './ExcelPreviewViewer';
import { api, type Ejercicio, type EjercicioRutina, type Rutina } from '@/lib/api';
import { cn } from '@/lib/utils';

// ============================
// Types
// ============================

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

type DraftRutinaExportPayload = {
    rutina: {
        nombre: string;
        descripcion: string;
        dias_semana: number;
        objetivo: string;
        notas: string;
    };
    usuario: { nombre: string };
    ejercicios: Array<{
        dia: number;
        orden: number;
        nombre_ejercicio?: string;
        series?: EjercicioRutina['series'];
        repeticiones?: EjercicioRutina['repeticiones'];
        descanso?: EjercicioRutina['descanso'];
        notas?: EjercicioRutina['notas'];
    }>;
    weeks: number;
};

interface UnifiedRutinaEditorProps {
    isOpen: boolean;
    onClose: () => void;
    rutina?: Rutina | null;
    isPlantilla: boolean;
    onSuccess: () => void;
}

// ============================
// Subcomponents
// ============================

// Droppable Day Column
function DroppableDay({
    day,
    children,
    isCollapsed,
    onToggleCollapse,
    onAddExercise,
}: {
    day: DayExercises;
    children: React.ReactNode;
    isCollapsed: boolean;
    onToggleCollapse: () => void;
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
            <button
                onClick={onToggleCollapse}
                className="w-full p-3 bg-slate-900/80 border-b border-slate-800 flex items-center justify-between hover:bg-slate-800/80 transition-colors"
            >
                <div className="flex items-center gap-2">
                    {isCollapsed ? (
                        <ChevronRight className="w-4 h-4 text-slate-400" />
                    ) : (
                        <ChevronDown className="w-4 h-4 text-slate-400" />
                    )}
                    <h3 className="font-semibold text-white">
                        Día {day.dayNumber}
                    </h3>
                    <span className="text-xs text-slate-500">
                        ({day.exercises.length} ejercicios)
                    </span>
                </div>
                <button
                    onClick={(e) => { e.stopPropagation(); onAddExercise(); }}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
                >
                    <Plus className="w-4 h-4" />
                </button>
            </button>
            <AnimatePresence>
                {!isCollapsed && (
                    <motion.div
                        initial={{ height: 0 }}
                        animate={{ height: 'auto' }}
                        exit={{ height: 0 }}
                        className="overflow-hidden"
                    >
                        <div className="p-3 min-h-[80px] space-y-2">
                            {children}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
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
                'p-2.5 rounded-xl border border-slate-800 bg-slate-900/50 group',
                'hover:border-slate-700 transition-colors cursor-pointer',
                isDragging && 'opacity-50 shadow-lg'
            )}
            onClick={onEdit}
        >
            <div className="flex items-center gap-2">
                <div
                    {...attributes}
                    {...listeners}
                    className="cursor-grab text-slate-600 hover:text-slate-400 transition-colors"
                    onClick={(e) => e.stopPropagation()}
                >
                    <GripVertical className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                    <div className="font-medium text-white text-sm truncate">
                        {exercise.ejercicio_nombre || `Ejercicio #${exercise.ejercicio_id}`}
                    </div>
                    <div className="text-xs text-slate-500">
                        {exercise.series || 3}×{exercise.repeticiones || '10'}
                    </div>
                </div>
                <button
                    onClick={(e) => { e.stopPropagation(); onDelete(); }}
                    className="p-1 rounded text-slate-500 hover:text-danger-400 opacity-0 group-hover:opacity-100 transition-all"
                >
                    <Trash2 className="w-3.5 h-3.5" />
                </button>
            </div>
        </div>
    );
}

// Floating Exercise Editor Panel
interface ExerciseEditorPanelProps {
    isOpen: boolean;
    onClose: () => void;
    exercise: EjercicioRutina | null;
    weeks: number;
    maxDays: number;
    onSave: (data: Partial<EjercicioRutina>) => void;
    onDelete: () => void;
    onMoveUp: () => void;
    onMoveDown: () => void;
    onDuplicate: () => void;
}

function ExerciseEditorPanel({
    isOpen,
    onClose,
    exercise,
    weeks,
    maxDays,
    onSave,
    onDelete,
    onMoveUp,
    onMoveDown,
    onDuplicate,
}: ExerciseEditorPanelProps) {
    const [formData, setFormData] = useState({
        series: ['', '', '', ''],
        repeticiones: ['', '', '', ''],
        orden: 1,
        dia: 1,
    });

    useEffect(() => {
        if (exercise) {
            const seriesArr = (exercise.series?.toString() || '3').split(',').map(s => s.trim());
            const repsArr = (exercise.repeticiones?.toString() || '10').split(',').map(s => s.trim());
            // Pad arrays to 4 elements
            while (seriesArr.length < 4) seriesArr.push(seriesArr[seriesArr.length - 1] || '');
            while (repsArr.length < 4) repsArr.push(repsArr[repsArr.length - 1] || '');
            setFormData({
                series: seriesArr.slice(0, 4),
                repeticiones: repsArr.slice(0, 4),
                orden: exercise.orden || 1,
                dia: exercise.dia || 1,
            });
        }
    }, [exercise]);

    const handleSave = () => {
        // Only include weeks that are needed
        const series = formData.series.slice(0, weeks).join(',');
        const repeticiones = formData.repeticiones.slice(0, weeks).join(',');
        onSave({
            series: series || 3,
            repeticiones: repeticiones || '10',
            orden: formData.orden,
            dia: formData.dia,
        });
        onClose();
    };

    if (!isOpen || !exercise) return null;

    return (
        <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            className="fixed inset-x-4 bottom-4 md:inset-auto md:bottom-6 md:right-6 md:w-[480px] z-50 bg-slate-900 rounded-xl border border-slate-700 shadow-2xl overflow-hidden"
        >
            <div className="p-3 bg-slate-800 border-b border-slate-700 flex items-center justify-between">
                <h4 className="font-semibold text-white text-sm">
                    {exercise.ejercicio_nombre || 'Editar ejercicio'}
                </h4>
                <button onClick={onClose} className="p-1 text-slate-400 hover:text-white">
                    <X className="w-4 h-4" />
                </button>
            </div>

            <div className="p-4 space-y-4">
                {/* Series/Reps per week table */}
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="text-slate-400 text-xs">
                                <th className="text-left p-2"></th>
                                {Array.from({ length: weeks }, (_, i) => (
                                    <th key={i} className="p-2 text-center">S{i + 1}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td className="p-2 text-slate-400">Series</td>
                                {Array.from({ length: weeks }, (_, i) => (
                                    <td key={i} className="p-1">
                                        <input
                                            type="text"
                                            value={formData.series[i]}
                                            onChange={(e) => {
                                                const newSeries = [...formData.series];
                                                newSeries[i] = e.target.value;
                                                setFormData({ ...formData, series: newSeries });
                                            }}
                                            className="w-14 px-2 py-1 text-center bg-slate-800 border border-slate-700 rounded text-white text-sm"
                                        />
                                    </td>
                                ))}
                            </tr>
                            <tr>
                                <td className="p-2 text-slate-400">Reps</td>
                                {Array.from({ length: weeks }, (_, i) => (
                                    <td key={i} className="p-1">
                                        <input
                                            type="text"
                                            value={formData.repeticiones[i]}
                                            onChange={(e) => {
                                                const newReps = [...formData.repeticiones];
                                                newReps[i] = e.target.value;
                                                setFormData({ ...formData, repeticiones: newReps });
                                            }}
                                            className="w-14 px-2 py-1 text-center bg-slate-800 border border-slate-700 rounded text-white text-sm"
                                        />
                                    </td>
                                ))}
                            </tr>
                        </tbody>
                    </table>
                </div>

                {/* Orden and Día */}
                <div className="flex gap-4">
                    <div className="flex-1">
                        <label className="text-xs text-slate-400 mb-1 block">Orden</label>
                        <input
                            type="number"
                            min={1}
                            max={8}
                            value={formData.orden}
                            onChange={(e) => setFormData({ ...formData, orden: Number(e.target.value) })}
                            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white"
                        />
                    </div>
                    <div className="flex-1">
                        <label className="text-xs text-slate-400 mb-1 block">Día</label>
                        <select
                            value={formData.dia}
                            onChange={(e) => setFormData({ ...formData, dia: Number(e.target.value) })}
                            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white"
                        >
                            {Array.from({ length: maxDays }, (_, i) => (
                                <option key={i + 1} value={i + 1}>Día {i + 1}</option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Actions */}
                <div className="flex flex-wrap gap-2">
                    <Button size="sm" variant="secondary" onClick={onMoveUp}>
                        <ArrowUp className="w-3.5 h-3.5" />
                    </Button>
                    <Button size="sm" variant="secondary" onClick={onMoveDown}>
                        <ArrowDown className="w-3.5 h-3.5" />
                    </Button>
                    <Button size="sm" variant="secondary" onClick={onDuplicate}>
                        <Copy className="w-3.5 h-3.5 mr-1" /> Duplicar
                    </Button>
                    <div className="flex-1" />
                    <Button size="sm" variant="danger" onClick={onDelete}>
                        <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                    <Button size="sm" onClick={handleSave}>
                        <Save className="w-3.5 h-3.5 mr-1" /> Aplicar
                    </Button>
                </div>
            </div>
        </motion.div>
    );
}

// Excel Preview Panel
interface ExcelPreviewPanelProps {
    rutinaId: number | null;
    isVisible: boolean;
    draftData: DraftRutinaExportPayload | null;
    weeks: number;
}

function ExcelPreviewPanel({ rutinaId, isVisible, draftData, weeks }: ExcelPreviewPanelProps) {
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [isMaximized, setIsMaximized] = useState(false);
    const [refreshKey, setRefreshKey] = useState(0);
    const [isLoading, setIsLoading] = useState(false);

    // Export Options
    const [qrMode, setQrMode] = useState<'inline' | 'sheet' | 'none'>('sheet');
    const [sheetName] = useState('');

    useEffect(() => {
        if (!isVisible) return;

        const loadUrl = async () => {
            setIsLoading(true);
            try {
                let url: string | null = null;

                if (draftData) {
                    // Draft mode
                    const res = await api.getRutinaDraftPdfViewUrl({
                        ...draftData,
                        weeks, // Ensure weeks is explicit in draft data (though already in draftData object)
                        qr_mode: qrMode,
                        sheet_name: sheetName
                    });
                    if (res.ok && res.data) {
                        url = res.data.url;
                    }
                } else if (rutinaId) {
                    // Saved mode
                    const res = await api.getRutinaPdfViewUrl(rutinaId, {
                        weeks,
                        qr_mode: qrMode,
                        sheet_name: sheetName || undefined
                    });
                    if (res.ok && res.data) {
                        url = res.data.url;
                    }
                }
                setPreviewUrl(url);
            } catch (error) {
                console.error("Error loading preview:", error);
            } finally {
                setIsLoading(false);
            }
        };

        const timer = setTimeout(loadUrl, 500); // Debounce
        return () => clearTimeout(timer);
    }, [isVisible, rutinaId, draftData, weeks, refreshKey, qrMode, sheetName]);


    if (!isVisible) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-slate-500 gap-3 p-6">
                <FileSpreadsheet className="w-12 h-12 text-slate-600" />
                <p className="text-sm text-center">
                    Abre la vista previa para ver el Excel en tiempo real
                </p>
            </div>
        );
    }

    return (
        <div className={cn(
            "flex flex-col h-full relative",
            isMaximized && "fixed inset-4 z-50 bg-slate-900 rounded-xl border border-slate-700 shadow-2xl"
        )}>
            {/* Controls */}
            <div className="flex items-center justify-between px-3 py-2 bg-slate-800/50 border-b border-slate-700">
                <span className="text-xs text-slate-400">Vista previa Excel</span>
                <div className="flex items-center gap-1">
                    <button
                        onClick={() => { setRefreshKey(k => k + 1); setIsLoading(true); }}
                        className="p-1.5 text-slate-400 hover:text-white"
                        title="Actualizar"
                    >
                        <RefreshCw className={cn("w-3.5 h-3.5", isLoading && "animate-spin")} />
                    </button>
                    <button
                        onClick={() => setIsMaximized(!isMaximized)}
                        className="p-1.5 text-slate-400 hover:text-white"
                        title="Maximizar"
                    >
                        {isMaximized ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
                    </button>
                </div>
            </div>

            {/* Export Settings */}
            <div className="px-3 py-2 bg-slate-900 border-b border-slate-800 flex flex-wrap gap-3 items-center text-xs">
                <div className="flex items-center gap-2">
                    <span className="text-slate-500">QR:</span>
                    <select
                        value={qrMode}
                        onChange={(e) => setQrMode(e.target.value as 'inline' | 'sheet' | 'none')}
                        className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-300 focus:outline-none focus:border-primary-500"
                    >
                        <option value="inline">Incluido</option>
                        <option value="sheet">Hoja aparte</option>
                        <option value="none">Sin QR</option>
                    </select>
                </div>
                <Button
                    size="sm"
                    variant="ghost"
                    className="ml-auto h-7 px-2 text-xs"
                    onClick={() => { setRefreshKey(k => k + 1); setIsLoading(true); }}
                >
                    Actualizar
                </Button>
            </div>

            {/* Viewer */}
            <div className="flex-1 relative bg-slate-950 overflow-hidden">
                <ExcelPreviewViewer
                    excelUrl={previewUrl}
                    isOpen={true}
                    onMinimize={() => { }}
                    className="absolute inset-0 w-full h-full border-0 shadow-none rounded-none"
                />
            </div>
        </div>
    );
}

// ============================
// Main Component
// ============================

export function UnifiedRutinaEditor({
    isOpen,
    onClose,
    rutina,
    isPlantilla,
    onSuccess,
}: UnifiedRutinaEditorProps) {
    const { success, error } = useToast();

    // Metadata
    const [nombre, setNombre] = useState('');
    const [descripcion, setDescripcion] = useState('');
    const [categoria, setCategoria] = useState('general');
    const [diasSemana, setDiasSemana] = useState(3);
    const [semanas, setSemanas] = useState(4);

    // Days and exercises
    const [days, setDays] = useState<DayExercises[]>([]);
    const [collapsedDays, setCollapsedDays] = useState<Set<number>>(new Set());
    const [activeExercise, setActiveExercise] = useState<DraggableExercise | null>(null);

    // Exercise selector
    const [ejercicios, setEjercicios] = useState<Ejercicio[]>([]);
    const [ejercicioSearch, setEjercicioSearch] = useState('');
    const [grupoFilter, setGrupoFilter] = useState('');
    const [objetivoFilter, setObjetivoFilter] = useState('');
    const [selectedEjercicioId, setSelectedEjercicioId] = useState<number>(0);
    const [selectedDayForAdd, setSelectedDayForAdd] = useState(1);

    // Editor panel
    const [editingExercise, setEditingExercise] = useState<EjercicioRutina | null>(null);
    const [editingDayNumber, setEditingDayNumber] = useState(1);
    const [editingIndex, setEditingIndex] = useState(-1);

    // State
    const [saving, setSaving] = useState(false);
    const [showPreview, setShowPreview] = useState(true);

    // Sensors for drag & drop
    const sensors = useSensors(
        useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
        useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
    );

    // Calc draft data for preview
    const draftData = useMemo(() => {
        const flatExercises: DraftRutinaExportPayload["ejercicios"] = [];
        days.forEach(d => {
            d.exercises.forEach(e => {
                flatExercises.push({
                    dia: d.dayNumber,
                    orden: e.orden || 0,
                    nombre_ejercicio: e.ejercicio_nombre,
                    series: e.series,
                    repeticiones: e.repeticiones,
                    descanso: e.descanso,
                    notas: e.notas,
                    // Additional fields if available
                });
            });
        });

        return {
            rutina: {
                nombre,
                descripcion,
                dias_semana: diasSemana,
                objetivo: categoria,
                notas: ''
            },
            usuario: { nombre: 'Vista Previa' },
            ejercicios: flatExercises,
            weeks: semanas // Include weeks for template generation
        };
    }, [days, nombre, descripcion, diasSemana, categoria, semanas]);

    const loadEjercicios = useCallback(async () => {
        const res = await api.getEjercicios({ search: ejercicioSearch, grupo: grupoFilter, objetivo: objetivoFilter });
        if (res.ok && res.data) {
            setEjercicios(res.data.ejercicios);
        }
    }, [ejercicioSearch, grupoFilter, objetivoFilter]);

    // Initialize data
    useEffect(() => {
        if (isOpen) {
            loadEjercicios();
            if (rutina) {
                setNombre(rutina.nombre || '');
                setDescripcion(rutina.descripcion || '');
                setCategoria(rutina.categoria || 'general');
                setDiasSemana(rutina.dias?.length || 3);
                setSemanas(4); // Default

                // Convert rutina.dias to DayExercises[]
                const daysData: DayExercises[] = (rutina.dias || []).map((d) => {
                    const legacyDay = d as Rutina["dias"][number] & { dayNumber?: number; nombre?: string };
                    const dayNumber = Number(legacyDay.numero || legacyDay.dayNumber || 1);
                    const exercises = (legacyDay.ejercicios || []).map((e) => {
                        const legacyEx = e as EjercicioRutina & { id?: number; nombre?: string };
                        const ejercicio_id = Number(legacyEx.ejercicio_id || legacyEx.id || 0);
                        const ejercicio_nombre = legacyEx.ejercicio_nombre || legacyEx.nombre || '';
                        return { ...legacyEx, ejercicio_id, ejercicio_nombre };
                    });
                    return {
                        dayNumber,
                        dayName: legacyDay.nombre || '',
                        exercises,
                    };
                });

                // Ensure we have all days
                for (let i = 1; i <= (rutina.dias?.length || diasSemana); i++) {
                    if (!daysData.find(d => d.dayNumber === i)) {
                        daysData.push({ dayNumber: i, dayName: '', exercises: [] });
                    }
                }
                daysData.sort((a, b) => a.dayNumber - b.dayNumber);
                setDays(daysData);
            } else {
                // New rutina
                setNombre('');
                setDescripcion('');
                setCategoria('general');
                setDiasSemana(3);
                setSemanas(4);
                setDays([
                    { dayNumber: 1, dayName: '', exercises: [] },
                    { dayNumber: 2, dayName: '', exercises: [] },
                    { dayNumber: 3, dayName: '', exercises: [] },
                ]);
            }
        }
    }, [isOpen, rutina, diasSemana, loadEjercicios]);

    // Update days when diasSemana changes
    useEffect(() => {
        setDays(prevDays => {
            const newDays = [...prevDays];
            // Add missing days
            for (let i = 1; i <= diasSemana; i++) {
                if (!newDays.find(d => d.dayNumber === i)) {
                    newDays.push({ dayNumber: i, dayName: '', exercises: [] });
                }
            }
            // Remove extra days
            return newDays.filter(d => d.dayNumber <= diasSemana).sort((a, b) => a.dayNumber - b.dayNumber);
        });
    }, [diasSemana]);

    useEffect(() => {
        if (isOpen) loadEjercicios();
    }, [isOpen, loadEjercicios]);

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

    const daysWithIds = getDaysWithIds();

    // Find which day an exercise belongs to
    const findDayOfExercise = (exerciseId: string): number | null => {
        for (const day of daysWithIds) {
            if (day.exercises.some((ex) => ex.dragId === exerciseId)) {
                return day.dayNumber;
            }
        }
        return null;
    };

    // Drag handlers
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

        if (overId.startsWith('day-')) {
            const targetDay = parseInt(overId.replace('day-', ''));
            if (activeDay !== null && activeDay !== targetDay) {
                setDays((prev) => {
                    const newDays = prev.map((d) => ({ ...d, exercises: [...d.exercises] }));
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

        if (activeDay !== null && overDay !== null && activeDay === overDay) {
            setDays((prev) => {
                const newDays = prev.map((d) => ({ ...d, exercises: [...d.exercises] }));
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

    // Add exercise
    const handleAddExercise = () => {
        if (!selectedEjercicioId) return;
        const ej = ejercicios.find(e => e.id === selectedEjercicioId);
        if (!ej) return;

        setDays(prev => prev.map(d => {
            if (d.dayNumber !== selectedDayForAdd) return d;
            return {
                ...d,
                exercises: [
                    ...d.exercises,
                    {
                        ejercicio_id: ej.id,
                        ejercicio_nombre: ej.nombre,
                        series: 3,
                        repeticiones: '10',
                        descanso: 60,
                        notas: '',
                        orden: d.exercises.length + 1,
                        dia: d.dayNumber,
                    } as EjercicioRutina,
                ],
            };
        }));
        setSelectedEjercicioId(0);
        success(`${ej.nombre} añadido al Día ${selectedDayForAdd}`);
    };

    // Edit exercise handlers
    const handleEditExercise = (dayNumber: number, exercise: EjercicioRutina, index: number) => {
        setEditingExercise(exercise);
        setEditingDayNumber(dayNumber);
        setEditingIndex(index);
    };

    const handleSaveExercise = (data: Partial<EjercicioRutina>) => {
        if (!editingExercise) return;

        // Handle day change
        const newDia = data.dia || editingDayNumber;

        setDays(prev => {
            const newDays = prev.map(d => ({ ...d, exercises: [...d.exercises] }));

            if (newDia !== editingDayNumber) {
                // Move to different day
                const sourceDayIdx = newDays.findIndex(d => d.dayNumber === editingDayNumber);
                const targetDayIdx = newDays.findIndex(d => d.dayNumber === newDia);
                if (sourceDayIdx >= 0 && targetDayIdx >= 0 && editingIndex >= 0) {
                    const [moved] = newDays[sourceDayIdx].exercises.splice(editingIndex, 1);
                    newDays[targetDayIdx].exercises.push({ ...moved, ...data, dia: newDia });
                }
            } else {
                // Update in place
                const dayIdx = newDays.findIndex(d => d.dayNumber === editingDayNumber);
                if (dayIdx >= 0 && editingIndex >= 0) {
                    newDays[dayIdx].exercises[editingIndex] = {
                        ...newDays[dayIdx].exercises[editingIndex],
                        ...data,
                    };
                }
            }

            return newDays;
        });

        setEditingExercise(null);
    };

    const handleDeleteExercise = () => {
        if (editingIndex < 0) return;
        setDays(prev => prev.map(d => {
            if (d.dayNumber !== editingDayNumber) return d;
            return {
                ...d,
                exercises: d.exercises.filter((_, i) => i !== editingIndex),
            };
        }));
        setEditingExercise(null);
    };

    const handleMoveUp = () => {
        if (editingIndex <= 0) return;
        setDays(prev => prev.map(d => {
            if (d.dayNumber !== editingDayNumber) return d;
            const newExercises = [...d.exercises];
            [newExercises[editingIndex - 1], newExercises[editingIndex]] = [newExercises[editingIndex], newExercises[editingIndex - 1]];
            return { ...d, exercises: newExercises };
        }));
        setEditingIndex(editingIndex - 1);
    };

    const handleMoveDown = () => {
        const dayExercises = days.find(d => d.dayNumber === editingDayNumber)?.exercises || [];
        if (editingIndex >= dayExercises.length - 1) return;
        setDays(prev => prev.map(d => {
            if (d.dayNumber !== editingDayNumber) return d;
            const newExercises = [...d.exercises];
            [newExercises[editingIndex], newExercises[editingIndex + 1]] = [newExercises[editingIndex + 1], newExercises[editingIndex]];
            return { ...d, exercises: newExercises };
        }));
        setEditingIndex(editingIndex + 1);
    };

    const handleDuplicate = () => {
        if (!editingExercise) return;
        setDays(prev => prev.map(d => {
            if (d.dayNumber !== editingDayNumber) return d;
            const newExercises = [...d.exercises];
            newExercises.splice(editingIndex + 1, 0, { ...editingExercise });
            return { ...d, exercises: newExercises };
        }));
        success('Ejercicio duplicado');
    };

    // Save rutina
    const handleSave = async () => {
        if (!nombre.trim()) {
            error('El nombre es requerido');
            return;
        }

        setSaving(true);
        try {
            // Prepare data
            const rutinaData = {
                nombre_rutina: nombre,
                nombre,
                descripcion,
                categoria,
                dias_semana: diasSemana,
                es_plantilla: isPlantilla,
                activa: true,
                dias: days.map(d => ({
                    numero: d.dayNumber,
                    nombre: d.dayName || `Día ${d.dayNumber}`,
                    ejercicios: d.exercises.map((e, idx) => ({
                        ejercicio_id: e.ejercicio_id,
                        series: e.series,
                        repeticiones: e.repeticiones,
                        descanso: e.descanso || 60,
                        notas: e.notas || '',
                        orden: idx + 1,
                    })),
                })),
            };

            let res;
            if (rutina?.id) {
                res = await api.updateRutina(rutina.id, rutinaData);
            } else {
                res = await api.createRutina(rutinaData);
            }

            if (res.ok) {
                success(rutina ? 'Rutina actualizada' : 'Rutina creada');
                onSuccess();
                onClose();
            } else {
                error(res.error || 'Error al guardar');
            }
        } catch {
            error('Error de conexión');
        } finally {
            setSaving(false);
        }
    };

    // Get unique groups and objetivos
    const grupos = useMemo(() => [...new Set(ejercicios.map(e => e.grupo_muscular).filter(Boolean))], [ejercicios]);
    const objetivos = useMemo(() => [...new Set(ejercicios.map(e => e.objetivo).filter(Boolean))], [ejercicios]);

    return (
        <>
            <Modal
                isOpen={isOpen}
                onClose={onClose}
                title={rutina ? 'Editar Rutina' : (isPlantilla ? 'Nueva Plantilla' : 'Nueva Rutina')}
                size="xl"
                className="!max-w-[95vw] !max-h-[95vh]"
                footer={
                    <div className="flex items-center justify-between w-full">
                        <Button
                            variant="secondary"
                            leftIcon={<FileSpreadsheet className="w-4 h-4" />}
                            onClick={() => setShowPreview(!showPreview)}
                        >
                            {showPreview ? 'Ocultar Preview' : 'Ver Preview'}
                        </Button>
                        <div className="flex gap-2">
                            <Button variant="secondary" onClick={onClose} disabled={saving}>
                                Cancelar
                            </Button>
                            <Button onClick={handleSave} isLoading={saving}>
                                <Save className="w-4 h-4 mr-2" />
                                Guardar
                            </Button>
                        </div>
                    </div>
                }
            >
                <div className="flex gap-4 h-[calc(90vh-160px)] overflow-hidden min-h-0">
                    {/* Left: Editor */}
                    <div className={cn("flex flex-col gap-4 min-h-0 overflow-y-auto", showPreview ? "w-2/3" : "w-full")}>
                        {/* Metadata */}
                        <div className="card p-4 space-y-3">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                <Input
                                    label="Nombre"
                                    value={nombre}
                                    onChange={(e) => setNombre(e.target.value)}
                                    placeholder="Ej: Rutina Full Body"
                                />
                                <div className="grid grid-cols-2 gap-3">
                                    <Select
                                        label="Días"
                                        value={diasSemana.toString()}
                                        onChange={(e) => setDiasSemana(Number(e.target.value))}
                                        options={[
                                            { value: '2', label: '2 días' },
                                            { value: '3', label: '3 días' },
                                            { value: '4', label: '4 días' },
                                            { value: '5', label: '5 días' },
                                        ]}
                                    />
                                    <Select
                                        label="Semanas"
                                        value={semanas.toString()}
                                        onChange={(e) => setSemanas(Number(e.target.value))}
                                        options={[
                                            { value: '1', label: '1 semana' },
                                            { value: '2', label: '2 semanas' },
                                            { value: '3', label: '3 semanas' },
                                            { value: '4', label: '4 semanas' },
                                        ]}
                                    />
                                </div>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                <div className="md:col-span-2">
                                    <Textarea
                                        label="Descripción"
                                        value={descripcion}
                                        onChange={(e) => setDescripcion(e.target.value)}
                                        placeholder="Objetivos y estructura..."
                                        rows={2}
                                    />
                                </div>
                                <Select
                                    label="Categoría"
                                    value={categoria}
                                    onChange={(e) => setCategoria(e.target.value)}
                                    options={[
                                        { value: 'general', label: 'General' },
                                        { value: 'fuerza', label: 'Fuerza' },
                                        { value: 'hipertrofia', label: 'Hipertrofia' },
                                        { value: 'resistencia', label: 'Resistencia' },
                                        { value: 'fullbody', label: 'Full Body' },
                                    ]}
                                />
                            </div>
                        </div>

                        {/* Add Exercise */}
                        <div className="card p-4">
                            <h4 className="text-sm font-medium text-slate-400 mb-3">Agregar ejercicio</h4>
                            <div className="flex flex-wrap gap-2">
                                <div className="relative flex-1 min-w-[200px]">
                                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                    <input
                                        type="text"
                                        value={ejercicioSearch}
                                        onChange={(e) => setEjercicioSearch(e.target.value)}
                                        placeholder="Buscar ejercicio..."
                                        className="w-full pl-9 pr-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm"
                                    />
                                </div>
                                <select
                                    value={grupoFilter}
                                    onChange={(e) => setGrupoFilter(e.target.value)}
                                    className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm min-w-[140px]"
                                >
                                    <option value="">Grupo: Todos</option>
                                    {grupos.map(g => <option key={g} value={g}>{g}</option>)}
                                </select>
                                <select
                                    value={objetivoFilter}
                                    onChange={(e) => setObjetivoFilter(e.target.value)}
                                    className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm min-w-[140px]"
                                >
                                    <option value="">Objetivo: Todos</option>
                                    {objetivos.map(o => <option key={o} value={o}>{o}</option>)}
                                </select>
                            </div>
                            <div className="flex gap-2 mt-2">
                                <select
                                    value={selectedEjercicioId}
                                    onChange={(e) => setSelectedEjercicioId(Number(e.target.value))}
                                    className="flex-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm"
                                >
                                    <option value={0}>Seleccionar ejercicio...</option>
                                    {ejercicios.map(e => (
                                        <option key={e.id} value={e.id}>{e.nombre}</option>
                                    ))}
                                </select>
                                <select
                                    value={selectedDayForAdd}
                                    onChange={(e) => setSelectedDayForAdd(Number(e.target.value))}
                                    className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm"
                                >
                                    {Array.from({ length: diasSemana }, (_, i) => (
                                        <option key={i + 1} value={i + 1}>Día {i + 1}</option>
                                    ))}
                                </select>
                                <Button onClick={handleAddExercise} disabled={!selectedEjercicioId}>
                                    <Plus className="w-4 h-4 mr-1" /> Agregar
                                </Button>
                            </div>
                        </div>

                        {/* Days Grid */}
                        <DndContext
                            sensors={sensors}
                            collisionDetection={closestCorners}
                            onDragStart={handleDragStart}
                            onDragOver={handleDragOver}
                            onDragEnd={handleDragEnd}
                        >
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                {daysWithIds.map((day) => (
                                    <DroppableDay
                                        key={day.dayNumber}
                                        day={day}
                                        isCollapsed={collapsedDays.has(day.dayNumber)}
                                        onToggleCollapse={() => {
                                            setCollapsedDays(prev => {
                                                const next = new Set(prev);
                                                if (next.has(day.dayNumber)) next.delete(day.dayNumber);
                                                else next.add(day.dayNumber);
                                                return next;
                                            });
                                        }}
                                        onAddExercise={() => {
                                            setSelectedDayForAdd(day.dayNumber);
                                        }}
                                    >
                                        <SortableContext
                                            items={day.exercises.map((e) => e.dragId)}
                                            strategy={verticalListSortingStrategy}
                                        >
                                            {day.exercises.length === 0 ? (
                                                <div className="text-center text-slate-600 text-xs py-4">
                                                    Arrastra ejercicios aquí
                                                </div>
                                            ) : (
                                                day.exercises.map((exercise, idx) => (
                                                    <SortableExercise
                                                        key={exercise.dragId}
                                                        exercise={exercise}
                                                        onEdit={() => handleEditExercise(
                                                            day.dayNumber,
                                                            days[days.findIndex(d => d.dayNumber === day.dayNumber)].exercises[idx],
                                                            idx
                                                        )}
                                                        onDelete={() => {
                                                            setDays(prev => prev.map(d => {
                                                                if (d.dayNumber !== day.dayNumber) return d;
                                                                return {
                                                                    ...d,
                                                                    exercises: d.exercises.filter((_, i) => i !== idx),
                                                                };
                                                            }));
                                                        }}
                                                    />
                                                ))
                                            )}
                                        </SortableContext>
                                    </DroppableDay>
                                ))}
                            </div>

                            <DragOverlay>
                                {activeExercise && (
                                    <div className="p-2.5 rounded-xl border border-primary-500 bg-slate-900 shadow-lg rotate-2">
                                        <div className="font-medium text-white text-sm">{activeExercise.ejercicio_nombre}</div>
                                        <div className="text-xs text-slate-500">{activeExercise.series} × {activeExercise.repeticiones}</div>
                                    </div>
                                )}
                            </DragOverlay>
                        </DndContext>
                    </div>

                    {/* Right: Preview */}
                    {showPreview && (
                        <div className="w-1/3 card overflow-hidden flex flex-col min-h-0">
                            <ExcelPreviewPanel
                                rutinaId={rutina?.id || null}
                                isVisible={showPreview}
                                draftData={draftData}
                                weeks={semanas}
                            />
                        </div>
                    )}
                </div>
            </Modal>

            {/* Floating Exercise Editor */}
            <AnimatePresence>
                {editingExercise && (
                    <ExerciseEditorPanel
                        isOpen={!!editingExercise}
                        onClose={() => setEditingExercise(null)}
                        exercise={editingExercise}
                        weeks={semanas}
                        maxDays={diasSemana}
                        onSave={handleSaveExercise}
                        onDelete={handleDeleteExercise}
                        onMoveUp={handleMoveUp}
                        onMoveDown={handleMoveDown}
                        onDuplicate={handleDuplicate}
                    />
                )}
            </AnimatePresence>
        </>
    );
}

export default UnifiedRutinaEditor;

