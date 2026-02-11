'use client';

import { useState, useEffect, useCallback, Suspense } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Dumbbell, ChevronDown, ChevronUp, Loader2, QrCode, Lock, Info, PlayCircle,
  Download, FileText, Palette, Star, Eye, Settings, Calendar, TrendingUp,
  Clock, Users, Award, Zap, BarChart3, Share2, Heart, Filter, Search
} from 'lucide-react';
import { useSearchParams } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { api, type Rutina, type EjercicioRutina, type Template } from '@/lib/api';
import { QRScannerModal } from '@/components/QrScannerModal';
import { UserExerciseModal } from '@/components/UserExerciseModal';
import { RutinaExportModal } from '@/components/RutinaExportModal';
import { TemplateSelectionModal } from '@/components/TemplateSelectionModal';
import { Button, useToast, Badge, Card, Select, Input } from '@/components/ui';

function RoutinesContent() {
    const { user } = useAuth();
    const searchParams = useSearchParams();
    const [routine, setRoutine] = useState<Rutina | null>(null);
    const [routines, setRoutines] = useState<Rutina[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedDay, setExpandedDay] = useState<number | null>(0);
    const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);

    // Enhanced UI States
    const [viewMode, setViewMode] = useState<'list' | 'grid' | 'analytics'>('list');
    const [showExportModal, setShowExportModal] = useState(false);
    const [showTemplateModal, setShowTemplateModal] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [sortBy, setSortBy] = useState<'name' | 'date' | 'usage'>('date');
    const [filterStatus, setFilterStatus] = useState<'all' | 'active' | 'completed'>('all');
    
    // Analytics data
    const [routineStats, setRoutineStats] = useState<any>(null);
    const [recentTemplates, setRecentTemplates] = useState<Template[]>([]);

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
        } catch {
        }
        return false;
    }, []);

    const verifyAndUnlock = useCallback(async (uuid: string) => {
        try {
            const res = await api.verifyRoutineQR(uuid);
            if (res.ok && res.data) {
                setRoutine(res.data.rutina);
                setIsBlocked(false);
                localStorage.setItem(`unlocked_routine_${uuid}`, Date.now().toString());
                success('¡Rutina desbloqueada!');
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
                setRoutine((prev) => {
                    if (prev) return prev;
                    return list.length > 0 ? list[0] : null;
                });
            }
        } catch (error) {
            console.error('Error loading routines:', error);
        } finally {
            setLoading(false);
        }
    }, [user?.id]);

    const loadRoutineStats = useCallback(async () => {
        if (!routine?.id) return;
        try {
            const res = await api.getRoutineStats(routine.id);
            if (res.ok && res.data) {
                setRoutineStats(res.data);
            }
        } catch (err) {
            console.error('Error loading routine stats:', err);
        }
    }, [routine?.id]);

    const loadRecentTemplates = useCallback(async () => {
        try {
            const res = await api.getTemplates({ 
                limit: 6, 
                sort_by: 'uso_count', 
                sort_order: 'desc' 
            });
            if (res.ok && res.data?.templates) {
                setRecentTemplates(res.data.templates);
            }
        } catch (err) {
            console.error('Error loading recent templates:', err);
        }
    }, []);

    useEffect(() => {
        loadRoutines().then(() => {
            const paramUuid = searchParams.get('uuid');
            if (paramUuid) {
                verifyAndUnlock(paramUuid);
            }
        });
        loadRecentTemplates();
    }, [loadRoutines, searchParams, verifyAndUnlock, loadRecentTemplates]);

    useEffect(() => {
        if (routine?.uuid_rutina) {
            const isUnlocked = checkUnlockStatus(routine.uuid_rutina);
            setIsBlocked(!isUnlocked);
        }
    }, [routine, checkUnlockStatus]);

    useEffect(() => {
        if (routine && !isBlocked) {
            loadRoutineStats();
        }
    }, [routine, isBlocked, loadRoutineStats]);

    const handleTemplateSelect = (template: Template) => {
        setSelectedTemplate(template);
        setShowTemplateModal(false);
        success(`Plantilla "${template.nombre}" seleccionada`);
    };

    const handleExport = () => {
        if (!routine) return;
        setShowExportModal(true);
    };

    const handleRoutineSelect = (selectedRoutine: Rutina) => {
        setRoutine(selectedRoutine);
        setExpandedDay(0);
    };

    const filteredRoutines = routines.filter(routine => {
        const matchesSearch = routine.nombre.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesStatus = filterStatus === 'all' || 
            (filterStatus === 'active' && !isBlocked) ||
            (filterStatus === 'completed' && isBlocked);
        return matchesSearch && matchesStatus;
    }).sort((a, b) => {
        switch (sortBy) {
            case 'name':
                return a.nombre.localeCompare(b.nombre);
            case 'date':
                return new Date(b.fecha_creacion || 0).getTime() - new Date(a.fecha_creacion || 0).getTime();
            case 'usage':
                return (b.uso_count || 0) - (a.uso_count || 0);
            default:
                return 0;
        }
    });

    const getUsageLevel = (usage: number) => {
        if (usage > 50) return { level: 'Alto', color: 'text-green-400' };
        if (usage > 20) return { level: 'Medio', color: 'text-yellow-400' };
        return { level: 'Bajo', color: 'text-slate-400' };
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-slate-950 flex items-center justify-center">
                <div className="text-center">
                    <Loader2 className="w-12 h-12 animate-spin text-primary-500 mx-auto mb-4" />
                    <p className="text-slate-400">Cargando rutinas...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-950">
            {/* Header */}
            <div className="bg-slate-900/50 backdrop-blur-sm border-b border-slate-800">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        <div className="flex items-center gap-4">
                            <Dumbbell className="w-8 h-8 text-primary-500" />
                            <h1 className="text-xl font-bold text-white">Mis Rutinas</h1>
                            {routine && (
                                <Badge variant="outline" className="ml-2">
                                    {routine.dias?.length || 0} días
                                </Badge>
                            )}
                        </div>
                        
                        <div className="flex items-center gap-3">
                            <div className="flex gap-2">
                                <Button
                                    variant={viewMode === 'list' ? 'primary' : 'ghost'}
                                    size="sm"
                                    onClick={() => setViewMode('list')}
                                >
                                    <FileText className="w-4 h-4" />
                                </Button>
                                <Button
                                    variant={viewMode === 'grid' ? 'primary' : 'ghost'}
                                    size="sm"
                                    onClick={() => setViewMode('grid')}
                                >
                                    <div className="grid grid-cols-2 gap-0.5 w-4 h-4">
                                        <div className="bg-current rounded-sm"></div>
                                        <div className="bg-current rounded-sm"></div>
                                        <div className="bg-current rounded-sm"></div>
                                        <div className="bg-current rounded-sm"></div>
                                    </div>
                                </Button>
                                <Button
                                    variant={viewMode === 'analytics' ? 'primary' : 'ghost'}
                                    size="sm"
                                    onClick={() => setViewMode('analytics')}
                                >
                                    <BarChart3 className="w-4 h-4" />
                                </Button>
                            </div>
                            
                            {routine && !isBlocked && (
                                <Button onClick={handleExport} leftIcon={<Download className="w-4 h-4" />}>
                                    Exportar
                                </Button>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Search and Filters */}
            <div className="bg-slate-900/30 backdrop-blur-sm border-b border-slate-800">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                    <div className="flex flex-col lg:flex-row gap-4">
                        <div className="flex-1 relative">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
                            <Input
                                placeholder="Buscar rutinas..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="pl-10"
                            />
                        </div>
                        
                        <div className="flex gap-3">
                            <Select
                                value={filterStatus}
                                onChange={(e) => setFilterStatus(e.target.value as any)}
                                className="w-40"
                                options={[
                                    { value: 'all', label: 'Todas' },
                                    { value: 'active', label: 'Activas' },
                                    { value: 'completed', label: 'Completadas' }
                                ]}
                            />
                            
                            <Select
                                value={sortBy}
                                onChange={(e) => setSortBy(e.target.value as any)}
                                className="w-40"
                                options={[
                                    { value: 'date', label: 'Más recientes' },
                                    { value: 'name', label: 'Nombre' },
                                    { value: 'usage', label: 'Más usadas' }
                                ]}
                            />
                        </div>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Analytics View */}
                {viewMode === 'analytics' && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="space-y-6"
                    >
                        {/* Stats Cards */}
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                            <Card className="bg-slate-900 border-slate-800">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-slate-400 text-sm">Total Rutinas</p>
                                        <p className="text-2xl font-bold text-white">{routines.length}</p>
                                    </div>
                                    <div className="w-12 h-12 bg-blue-500/20 rounded-lg flex items-center justify-center">
                                        <FileText className="w-6 h-6 text-blue-400" />
                                    </div>
                                </div>
                            </Card>

                            <Card className="bg-slate-900 border-slate-800">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-slate-400 text-sm">Total Usos</p>
                                        <p className="text-2xl font-bold text-white">
                                            {routines.reduce((sum, r) => sum + (r.uso_count || 0), 0)}
                                        </p>
                                    </div>
                                    <div className="w-12 h-12 bg-green-500/20 rounded-lg flex items-center justify-center">
                                        <TrendingUp className="w-6 h-6 text-green-400" />
                                    </div>
                                </div>
                            </Card>

                            <Card className="bg-slate-900 border-slate-800">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-slate-400 text-sm">Días Totales</p>
                                        <p className="text-2xl font-bold text-white">
                                            {routines.reduce((sum, r) => sum + (r.dias?.length || 0), 0)}
                                        </p>
                                    </div>
                                    <div className="w-12 h-12 bg-purple-500/20 rounded-lg flex items-center justify-center">
                                        <Calendar className="w-6 h-6 text-purple-400" />
                                    </div>
                                </div>
                            </Card>

                            <Card className="bg-slate-900 border-slate-800">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-slate-400 text-sm">Plantillas</p>
                                        <p className="text-2xl font-bold text-white">{recentTemplates.length}</p>
                                    </div>
                                    <div className="w-12 h-12 bg-yellow-500/20 rounded-lg flex items-center justify-center">
                                        <Palette className="w-6 h-6 text-yellow-400" />
                                    </div>
                                </div>
                            </Card>
                        </div>

                        {/* Recent Templates */}
                        <div>
                            <h3 className="text-lg font-semibold text-white mb-4">Plantillas Populares</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {recentTemplates.map((template) => (
                                    <Card key={template.id} className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-colors">
                                        <div className="p-4">
                                            <div className="flex items-start justify-between mb-3">
                                                <div>
                                                    <h4 className="font-medium text-white">{template.nombre}</h4>
                                                    <p className="text-sm text-slate-400 line-clamp-2">{template.descripcion}</p>
                                                </div>
                                                <Badge variant="outline" size="sm">{template.categoria}</Badge>
                                            </div>
                                            
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-2 text-sm text-slate-400">
                                                    <Star className="w-3 h-3" />
                                                    <span>{template.rating_promedio?.toFixed(1) || 'N/A'}</span>
                                                    <Download className="w-3 h-3 ml-2" />
                                                    <span>{template.uso_count}</span>
                                                </div>
                                                
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => {
                                                        setSelectedTemplate(template);
                                                        setShowTemplateModal(true);
                                                    }}
                                                >
                                                    <Eye className="w-3 h-3" />
                                                </Button>
                                            </div>
                                        </div>
                                    </Card>
                                ))}
                            </div>
                        </div>
                    </motion.div>
                )}

                {/* List/Grid View */}
                {viewMode !== 'analytics' && (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        {/* Routines List */}
                        <div className={`${viewMode === 'grid' ? 'lg:col-span-2' : 'lg:col-span-1'}`}>
                            <div className="space-y-4">
                                {filteredRoutines.length === 0 ? (
                                    <Card className="bg-slate-900 border-slate-800">
                                        <div className="text-center py-12">
                                            <FileText className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                                            <p className="text-slate-400 mb-4">
                                                {searchQuery ? 'No se encontraron rutinas' : 'No hay rutinas disponibles'}
                                            </p>
                                        </div>
                                    </Card>
                                ) : (
                                    filteredRoutines.map((routineItem) => (
                                        <motion.div
                                            key={routineItem.id}
                                            initial={{ opacity: 0, y: 20 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ duration: 0.3 }}
                                        >
                                            <Card 
                                                className={`bg-slate-900 border-slate-800 hover:border-slate-700 transition-all cursor-pointer ${
                                                    routine?.id === routineItem.id ? 'border-primary-500 ring-2 ring-primary-500/50' : ''
                                                }`}
                                                onClick={() => handleRoutineSelect(routineItem)}
                                            >
                                                <div className="p-6">
                                                    <div className="flex items-start justify-between mb-4">
                                                        <div className="flex-1">
                                                            <h3 className="text-lg font-semibold text-white mb-2">
                                                                {routineItem.nombre}
                                                            </h3>
                                                            <div className="flex items-center gap-3 text-sm text-slate-400">
                                                                <Badge variant="outline">
                                                                    {routineItem.dias?.length || 0} días
                                                                </Badge>
                                                                <span className="flex items-center gap-1">
                                                                    <Clock className="w-3 h-3" />
                                                                    {new Date(routineItem.fecha_creacion || '').toLocaleDateString()}
                                                                </span>
                                                                {routineItem.uso_count && (
                                                                    <span className="flex items-center gap-1">
                                                                        <TrendingUp className="w-3 h-3" />
                                                                        {routineItem.uso_count} usos
                                                                    </span>
                                                                )}
                                                            </div>
                                                        </div>
                                                        
                                                        <div className="flex gap-2">
                                                            {routineItem.uuid_rutina && !checkUnlockStatus(routineItem.uuid_rutina) && (
                                                                <Badge variant="warning">
                                                                    <Lock className="w-3 h-3 mr-1" />
                                                                    Bloqueada
                                                                </Badge>
                                                            )}
                                                        </div>
                                                    </div>

                                                    {viewMode === 'grid' && routine?.id === routineItem.id && !isBlocked && (
                                                        <div className="mt-4 pt-4 border-t border-slate-700">
                                                            <div className="flex gap-2">
                                                                <Button
                                                                    variant="secondary"
                                                                    size="sm"
                                                                    onClick={(e) => {
                                                                        e.stopPropagation();
                                                                        setShowTemplateModal(true);
                                                                    }}
                                                                    leftIcon={<Palette className="w-4 h-4" />}
                                                                >
                                                                    Plantillas
                                                                </Button>
                                                                <Button
                                                                    variant="secondary"
                                                                    size="sm"
                                                                    onClick={(e) => {
                                                                        e.stopPropagation();
                                                                        handleExport();
                                                                    }}
                                                                    leftIcon={<Download className="w-4 h-4" />}
                                                                >
                                                                    Exportar
                                                                </Button>
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            </Card>
                                        </motion.div>
                                    ))
                                )}
                            </div>
                        </div>

                        {/* Routine Details */}
                        {routine && viewMode === 'list' && (
                            <motion.div
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                className="lg:col-span-2"
                            >
                                <Card className="bg-slate-900 border-slate-800">
                                    <div className="p-6">
                                        <div className="flex items-center justify-between mb-6">
                                            <div>
                                                <h2 className="text-2xl font-bold text-white mb-2">
                                                    {routine.nombre}
                                                </h2>
                                                <div className="flex items-center gap-3 text-sm text-slate-400">
                                                    <Badge variant="outline">
                                                        {routine.dias?.length || 0} días
                                                    </Badge>
                                                    <span>{new Date(routine.fecha_creacion || '').toLocaleDateString()}</span>
                                                    {routine.uso_count && (
                                                        <span>{routine.uso_count} usos</span>
                                                    )}
                                                </div>
                                            </div>

                                            <div className="flex gap-2">
                                                {isBlocked ? (
                                                    <Button
                                                        onClick={() => setShowScanner(true)}
                                                        leftIcon={<QrCode className="w-4 h-4" />}
                                                    >
                                                        Desbloquear
                                                    </Button>
                                                ) : (
                                                    <>
                                                        <Button
                                                            variant="secondary"
                                                            onClick={() => setShowTemplateModal(true)}
                                                            leftIcon={<Palette className="w-4 h-4" />}
                                                        >
                                                            Plantillas
                                                        </Button>
                                                        <Button
                                                            onClick={handleExport}
                                                            leftIcon={<Download className="w-4 h-4" />}
                                                        >
                                                            Exportar
                                                        </Button>
                                                    </>
                                                )}
                                            </div>
                                        </div>

                                        {isBlocked ? (
                                            <div className="text-center py-12">
                                                <Lock className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                                                <p className="text-slate-400 mb-4">
                                                    Esta rutina está bloqueada. Escanea el código QR para desbloquearla.
                                                </p>
                                                <Button onClick={() => setShowScanner(true)} leftIcon={<QrCode className="w-4 h-4" />}>
                                                    Escanear QR
                                                </Button>
                                            </div>
                                        ) : (
                                            <div className="space-y-4">
                                                {routine.dias?.map((day, index) => (
                                                    <motion.div
                                                        key={index}
                                                        initial={{ opacity: 0, y: 10 }}
                                                        animate={{ opacity: 1, y: 0 }}
                                                        transition={{ delay: index * 0.1 }}
                                                    >
                                                        <Card className="bg-slate-800 border-slate-700">
                                                            <div
                                                                className="p-4 cursor-pointer"
                                                                onClick={() => setExpandedDay(expandedDay === index ? null : index)}
                                                            >
                                                                <div className="flex items-center justify-between">
                                                                    <div className="flex items-center gap-3">
                                                                        <div className="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center text-white font-bold">
                                                                            {index + 1}
                                                                        </div>
                                                                        <h3 className="font-semibold text-white">
                                                                            Día {index + 1}
                                                                        </h3>
                                                                        <Badge variant="outline">
                                                                            {day.ejercicios?.length || 0} ejercicios
                                                                        </Badge>
                                                                    </div>
                                                                    {expandedDay === index ? (
                                                                        <ChevronUp className="w-5 h-5 text-slate-400" />
                                                                    ) : (
                                                                        <ChevronDown className="w-5 h-5 text-slate-400" />
                                                                    )}
                                                                </div>

                                                                <AnimatePresence>
                                                                    {expandedDay === index && (
                                                                        <motion.div
                                                                            initial={{ height: 0, opacity: 0 }}
                                                                            animate={{ height: 'auto', opacity: 1 }}
                                                                            exit={{ height: 0, opacity: 0 }}
                                                                            transition={{ duration: 0.3 }}
                                                                            className="overflow-hidden"
                                                                        >
                                                                            <div className="pt-4 mt-4 border-t border-slate-600 space-y-3">
                                                                                {day.ejercicios?.map((ejercicio: any, ejIndex: number) => (
                                                                                    <div
                                                                                        key={ejIndex}
                                                                                        className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg"
                                                                                        onClick={(e) => {
                                                                                            e.stopPropagation();
                                                                                            setSelectedExercise(ejercicio);
                                                                                        }}
                                                                                    >
                                                                                        <div className="flex-1">
                                                                                            <h4 className="font-medium text-white">
                                                                                                {ejercicio.ejercicio?.nombre}
                                                                                            </h4>
                                                                                            <div className="flex items-center gap-4 text-sm text-slate-400 mt-1">
                                                                                                <span>{ejercicio.series} series</span>
                                                                                                <span>{ejercicio.repeticiones} reps</span>
                                                                                                {ejercicio.descanso && (
                                                                                                    <span>Descanso: {ejercicio.descanso}s</span>
                                                                                                )}
                                                                                            </div>
                                                                                        </div>
                                                                                        <PlayCircle className="w-5 h-5 text-primary-400" />
                                                                                    </div>
                                                                                ))}
                                                                            </div>
                                                                        </motion.div>
                                                                    )}
                                                                </AnimatePresence>
                                                            </div>
                                                        </Card>
                                                    </motion.div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </Card>
                            </motion.div>
                        )}
                    </div>
                )}
            </div>

            {/* Modals */}
            {showScanner && (
                <QRScannerModal
                    isOpen={showScanner}
                    onClose={() => setShowScanner(false)}
                    onScan={(uuid) => {
                        verifyAndUnlock(uuid);
                        setShowScanner(false);
                    }}
                />
            )}

            {selectedExercise && (
                <UserExerciseModal
                    isOpen={!!selectedExercise}
                    onClose={() => setSelectedExercise(null)}
                    exercise={selectedExercise}
                />
            )}

            {showExportModal && routine && (
                <RutinaExportModal
                    isOpen={showExportModal}
                    onClose={() => setShowExportModal(false)}
                    rutina={routine}
                    selectedTemplate={selectedTemplate}
                />
            )}

            {showTemplateModal && routine && (
                <TemplateSelectionModal
                    isOpen={showTemplateModal}
                    onClose={() => setShowTemplateModal(false)}
                    onTemplateSelect={handleTemplateSelect}
                    rutina={routine}
                />
            )}
        </div>
    );
}

export default function RoutinesPage() {
    return (
        <Suspense fallback={
            <div className="min-h-screen bg-slate-950 flex items-center justify-center">
                <Loader2 className="w-12 h-12 animate-spin text-primary-500" />
            </div>
        }>
            <RoutinesContent />
        </Suspense>
    );
}
