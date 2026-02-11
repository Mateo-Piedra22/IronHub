'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Plus,
    Search,
    Filter,
    Grid,
    List,
    Star,
    Download,
    Eye,
    Heart,
    Settings,
    TrendingUp,
    Calendar,
    Users,
    ChevronDown,
    ChevronUp,
    Edit,
    Trash2,
    Copy,
    BarChart3,
    Target,
    Zap,
    CheckCircle,
    AlertCircle,
    X,
    Save,
    RefreshCw
} from 'lucide-react';
import { api, type Template, type GymTemplateAssignment } from '@/lib/api';
import { 
    Button, 
    Card, 
    Badge, 
    Input, 
    Select, 
    Modal, 
    useToast, 
    Tabs,
    TabsList,
    TabsTrigger,
    TabsContent,
    DataTable,
    type Column
} from '@/components/ui';

interface GymTemplateManagerProps {
    gymId: number;
    gymName: string;
}

type ViewMode = "grid" | "list";
type SortOption = "priority" | "name" | "category" | "usage" | "assigned_date";
type FilterCategory = "all" | string;

export function GymTemplateManager({ gymId, gymName }: GymTemplateManagerProps) {
    const [activeTab, setActiveTab] = useState("assigned");
    const [assignedTemplates, setAssignedTemplates] = useState<GymTemplateAssignment[]>([]);
    const [availableTemplates, setAvailableTemplates] = useState<Template[]>([]);
    const [recommendedTemplates, setRecommendedTemplates] = useState<Template[]>([]);
    const [loading, setLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const [selectedCategory, setSelectedCategory] = useState<FilterCategory>("all");
    const [sortBy, setSortBy] = useState<SortOption>("priority");
    const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");
    const [viewMode, setViewMode] = useState<ViewMode>("grid");
    const [categories, setCategories] = useState<string[]>([]);
    
    // Modal states
    const [showAssignModal, setShowAssignModal] = useState(false);
    const [showCustomizeModal, setShowCustomizeModal] = useState(false);
    const [showAnalyticsModal, setShowAnalyticsModal] = useState(false);
    const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
    const [selectedAssignment, setSelectedAssignment] = useState<GymTemplateAssignment | null>(null);
    
    // Analytics data
    const [analytics, setAnalytics] = useState<any>(null);
    const [popularTemplates, setPopularTemplates] = useState<any[]>([]);
    
    const { success, error } = useToast();

    // Load data on mount and tab change
    useEffect(() => {
        if (gymId) {
            loadData();
        }
    }, [gymId, activeTab]);

    // Load data based on active tab
    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            if (activeTab === "assigned") {
                await loadAssignedTemplates();
            } else if (activeTab === "available") {
                await loadAvailableTemplates();
            } else if (activeTab === "recommended") {
                await loadRecommendedTemplates();
            }
        } catch (err) {
            console.error("Error loading data:", err);
            error("Error al cargar datos");
        } finally {
            setLoading(false);
        }
    }, [activeTab, gymId, error]);

    const loadAssignedTemplates = async () => {
        try {
            const response = await api.get(`/api/v1/gyms/${gymId}/templates?include_analytics=true`);
            if (response.ok && (response.data as any)?.success) {
                setAssignedTemplates((response.data as any).templates);
            }
        } catch (err) {
            console.error("Error loading assigned templates:", err);
        }
    };

    const loadAvailableTemplates = async () => {
        try {
            const response = await api.get(`/api/v1/gyms/${gymId}/templates/available`, {
                params: {
                    category: selectedCategory === "all" ? undefined : selectedCategory,
                    search_query: searchQuery || undefined
                }
            });
            if (response.ok && (response.data as any)?.success) {
                setAvailableTemplates((response.data as any).templates);
            }
        } catch (err) {
            console.error("Error loading available templates:", err);
        }
    };

    const loadRecommendedTemplates = async () => {
        try {
            const response = await api.get(`/api/v1/gyms/${gymId}/templates/recommended`);
            if (response.ok && (response.data as any)?.success) {
                setRecommendedTemplates((response.data as any).recommended_templates);
            }
        } catch (err) {
            console.error("Error loading recommended templates:", err);
        }
    };

    const loadAnalytics = async () => {
        try {
            const [analyticsRes, popularRes] = await Promise.all([
                api.get(`/api/v1/gyms/${gymId}/templates/analytics`),
                api.get(`/api/v1/gyms/${gymId}/templates/popular`)
            ]);

            if (analyticsRes.ok && (analyticsRes.data as any)?.success) {
                setAnalytics((analyticsRes.data as any).analytics);
            }

            if (popularRes.ok && (popularRes.data as any)?.success) {
                setPopularTemplates((popularRes.data as any).popular_templates);
            }
        } catch (err) {
            console.error("Error loading analytics:", err);
        }
    };

    // Handle template assignment
    const handleAssignTemplate = async (template: Template) => {
        try {
            const response = await api.post(`/api/v1/gyms/${gymId}/templates/assign`, {
                template_id: template.id,
                priority: assignedTemplates.length
            });

            if (response.ok && (response.data as any)?.success) {
                success(`Plantilla "${template.nombre}" asignada exitosamente`);
                setShowAssignModal(false);
                if (activeTab === "assigned") {
                    await loadAssignedTemplates();
                }
            } else {
                error("Error al asignar plantilla");
            }
        } catch (err) {
            console.error("Error assigning template:", err);
            error("Error al asignar plantilla");
        }
    };

    // Handle template customization
    const handleCustomizeTemplate = async (assignment: GymTemplateAssignment, customConfig: any) => {
        try {
            const response = await api.post(`/api/v1/gyms/${gymId}/templates/${assignment.assignment_id}/customize`, {
                custom_config: customConfig
            });

            if (response.ok && (response.data as any)?.success) {
                success("Plantilla personalizada exitosamente");
                setShowCustomizeModal(false);
                await loadAssignedTemplates();
            } else {
                error("Error al personalizar plantilla");
            }
        } catch (err) {
            console.error("Error customizing template:", err);
            error("Error al personalizar plantilla");
        }
    };

    // Handle template removal
    const handleRemoveTemplate = async (assignment: GymTemplateAssignment) => {
        try {
            const response = await api.delete(`/api/v1/gyms/${gymId}/templates/${assignment.assignment_id}`);

            if (response.ok && (response.data as any)?.success) {
                success("Plantilla eliminada del gimnasio");
                await loadAssignedTemplates();
            } else {
                error("Error al eliminar plantilla");
            }
        } catch (err) {
            console.error("Error removing template:", err);
            error("Error al eliminar plantilla");
        }
    };

    // Handle priority update
    const handleUpdatePriority = async (assignment: GymTemplateAssignment, newPriority: number) => {
        try {
            const response = await api.put(`/api/v1/gyms/${gymId}/templates/${assignment.assignment_id}`, {
                priority: newPriority
            });

            if (response.ok && (response.data as any)?.success) {
                success("Prioridad actualizada");
                await loadAssignedTemplates();
            } else {
                error("Error al actualizar prioridad");
            }
        } catch (err) {
            console.error("Error updating priority:", err);
            error("Error al actualizar prioridad");
        }
    };

    const getPriorityColor = (priority: number) => {
        if (priority === 0) return "text-red-400";
        if (priority <= 2) return "text-yellow-400";
        return "text-green-400";
    };

    const getPriorityLabel = (priority: number) => {
        if (priority === 0) return "Alta";
        if (priority <= 2) return "Media";
        return "Baja";
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="bg-slate-900/50 backdrop-blur-sm border-b border-slate-800">
                <div className="p-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                                <Target className="w-8 h-8 text-primary-500" />
                                Gestión de Plantillas
                            </h1>
                            <p className="text-slate-400 mt-1">
                                {gymName} - Administra las plantillas disponibles para este gimnasio
                            </p>
                        </div>
                        
                        <div className="flex items-center gap-3">
                            <Button
                                variant="secondary"
                                onClick={() => setShowAnalyticsModal(true)}
                                leftIcon={<BarChart3 className="w-4 h-4" />}
                            >
                                Analytics
                            </Button>
                            <Button
                                onClick={() => setShowAssignModal(true)}
                                leftIcon={<Plus className="w-4 h-4" />}
                            >
                                Asignar Plantilla
                            </Button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Tabs */}
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                <div className="bg-slate-900/30 border-b border-slate-800">
                    <div className="px-6">
                        <TabsList className="bg-transparent border-0">
                            <TabsTrigger 
                                value="assigned" 
                                className="data-[state=active]:bg-primary-500 data-[state=active]:text-white"
                            >
                                <div className="flex items-center gap-2">
                                    <CheckCircle className="w-4 h-4" />
                                    Asignadas ({assignedTemplates.length})
                                </div>
                            </TabsTrigger>
                            <TabsTrigger 
                                value="available"
                                className="data-[state=active]:bg-primary-500 data-[state=active]:text-white"
                            >
                                <div className="flex items-center gap-2">
                                    <Grid className="w-4 h-4" />
                                    Disponibles
                                </div>
                            </TabsTrigger>
                            <TabsTrigger 
                                value="recommended"
                                className="data-[state=active]:bg-primary-500 data-[state=active]:text-white"
                            >
                                <div className="flex items-center gap-2">
                                    <TrendingUp className="w-4 h-4" />
                                    Recomendadas
                                </div>
                            </TabsTrigger>
                        </TabsList>
                    </div>
                </div>

                {/* Tab Content */}
                <div className="p-6">
                    {/* Assigned Templates Tab */}
                    {activeTab === "assigned" && (
                        <div className="space-y-4">
                            {loading ? (
                                <div className="flex justify-center py-12">
                                    <div className="w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
                                </div>
                            ) : assignedTemplates.length === 0 ? (
                                <div className="text-center py-12">
                                    <Target className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                                    <h3 className="text-lg font-medium text-white mb-2">No hay plantillas asignadas</h3>
                                    <p className="text-slate-400 mb-4">Comienza asignando plantillas a este gimnasio</p>
                                    <Button onClick={() => setShowAssignModal(true)}>
                                        Asignar Primera Plantilla
                                    </Button>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    {assignedTemplates.map((assignment, index) => (
                                        <motion.div
                                            key={assignment.assignment_id}
                                            initial={{ opacity: 0, y: 20 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: index * 0.1 }}
                                        >
                                            <Card className="bg-slate-900 border-slate-800">
                                                <div className="p-6">
                                                    <div className="flex items-start justify-between">
                                                        <div className="flex-1">
                                                            <div className="flex items-center gap-3 mb-3">
                                                                <h3 className="text-lg font-semibold text-white">
                                                                    {assignment.template_name}
                                                                </h3>
                                                                <Badge variant="outline">
                                                                    {assignment.template_category}
                                                                </Badge>
                                                                {assignment.dias_semana && (
                                                                    <Badge variant="secondary">
                                                                        {assignment.dias_semana} días
                                                                    </Badge>
                                                                )}
                                                                <div className="flex items-center gap-1">
                                                                    <Target className={`w-4 h-4 ${getPriorityColor(assignment.priority)}`} />
                                                                    <span className={`text-sm ${getPriorityColor(assignment.priority)}`}>
                                                                        {getPriorityLabel(assignment.priority)}
                                                                    </span>
                                                                </div>
                                                            </div>
                                                            
                                                            <p className="text-slate-400 mb-4">
                                                                {assignment.template_description}
                                                            </p>
                                                            
                                                            <div className="flex flex-wrap items-center gap-4 text-sm text-slate-400">
                                                                <div className="flex items-center gap-1">
                                                                    <Users className="w-4 h-4" />
                                                                    <span>Usos: {assignment.gym_usage_count}</span>
                                                                </div>
                                                                {assignment.rating_promedio && (
                                                                    <div className="flex items-center gap-1">
                                                                        <Star className="w-4 h-4 text-yellow-400" />
                                                                        <span>{assignment.rating_promedio.toFixed(1)}</span>
                                                                    </div>
                                                                )}
                                                                <div className="flex items-center gap-1">
                                                                    <Calendar className="w-4 h-4" />
                                                                    <span>Asignada: {new Date(assignment.fecha_asignacion).toLocaleDateString()}</span>
                                                                </div>
                                                                {assignment.assigned_by_name && (
                                                                    <div className="flex items-center gap-1">
                                                                        <Users className="w-4 h-4" />
                                                                        <span>Por: {assignment.assigned_by_name}</span>
                                                                    </div>
                                                                )}
                                                            </div>
                                                            
                                                            {assignment.custom_config && (
                                                                <div className="mt-4 p-3 bg-slate-800 rounded-lg">
                                                                    <div className="flex items-center gap-2 mb-2">
                                                                        <Settings className="w-4 h-4 text-primary-400" />
                                                                        <span className="text-sm font-medium text-primary-400">Configuración Personalizada</span>
                                                                    </div>
                                                                    <p className="text-xs text-slate-400">
                                                                        Esta plantilla tiene ajustes específicos para este gimnasio
                                                                    </p>
                                                                </div>
                                                            )}
                                                        </div>
                                                        
                                                        <div className="flex items-center gap-2">
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                onClick={() => {
                                                                    setSelectedAssignment(assignment);
                                                                    setShowCustomizeModal(true);
                                                                }}
                                                                leftIcon={<Settings className="w-4 h-4" />}
                                                            >
                                                                Personalizar
                                                            </Button>
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                onClick={() => handleUpdatePriority(assignment, Math.max(0, assignment.priority - 1))}
                                                                leftIcon={<ChevronUp className="w-4 h-4" />}
                                                            >
                                                                Prioridad
                                                            </Button>
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                onClick={() => handleRemoveTemplate(assignment)}
                                                                leftIcon={<Trash2 className="w-4 h-4" />}
                                                                className="text-red-400 hover:text-red-300"
                                                            >
                                                                Eliminar
                                                            </Button>
                                                        </div>
                                                    </div>
                                                </div>
                                            </Card>
                                        </motion.div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Available Templates Tab */}
                    {activeTab === "available" && (
                        <div className="space-y-4">
                            {/* Search and Filters */}
                            <div className="flex flex-col sm:flex-row gap-4">
                                <div className="flex-1 relative">
                                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
                                    <Input
                                        placeholder="Buscar plantillas..."
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        className="pl-10"
                                    />
                                </div>
                                
                                <Select
                                    value={selectedCategory}
                                    onChange={(e) => setSelectedCategory(e.target.value)}
                                    placeholder="Categoría"
                                    className="w-full sm:w-48"
                                    options={[
                                        { value: "all", label: "Todas las categorías" },
                                        { value: "fuerza", label: "Fuerza" },
                                        { value: "hipertrofia", label: "Hipertrofia" },
                                        { value: "funcional", label: "Funcional" },
                                        { value: "cardio", label: "Cardio" },
                                        { value: "rehab", label: "Rehabilitación" }
                                    ]}
                                />
                                
                                <Button onClick={loadAvailableTemplates} leftIcon={<RefreshCw className="w-4 h-4" />}>
                                    Actualizar
                                </Button>
                            </div>

                            {/* Available Templates Grid */}
                            {loading ? (
                                <div className="flex justify-center py-12">
                                    <div className="w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
                                </div>
                            ) : availableTemplates.length === 0 ? (
                                <div className="text-center py-12">
                                    <Grid className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                                    <h3 className="text-lg font-medium text-white mb-2">No hay plantillas disponibles</h3>
                                    <p className="text-slate-400">No se encontraron plantillas que coincidan con los filtros</p>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                    {availableTemplates.map((template, index) => (
                                        <motion.div
                                            key={template.id}
                                            initial={{ opacity: 0, y: 20 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: index * 0.1 }}
                                        >
                                            <Card className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-all">
                                                <div className="p-6">
                                                    <div className="space-y-4">
                                                        <div>
                                                            <h3 className="font-semibold text-white mb-2">
                                                                {template.nombre}
                                                            </h3>
                                                            <p className="text-sm text-slate-400 line-clamp-2">
                                                                {template.descripcion}
                                                            </p>
                                                        </div>
                                                        
                                                        <div className="flex flex-wrap gap-2">
                                                            <Badge variant="outline">{template.categoria}</Badge>
                                                            {template.dias_semana && (
                                                                <Badge variant="secondary">
                                                                    {template.dias_semana} días
                                                                </Badge>
                                                            )}
                                                        </div>
                                                        
                                                        <div className="flex items-center justify-between text-sm text-slate-400">
                                                            <div className="flex items-center gap-1">
                                                                <Download className="w-4 h-4" />
                                                                <span>{template.uso_count}</span>
                                                            </div>
                                                            {template.rating_promedio && (
                                                                <div className="flex items-center gap-1">
                                                                    <Star className="w-4 h-4 text-yellow-400" />
                                                                    <span>{template.rating_promedio.toFixed(1)}</span>
                                                                </div>
                                                            )}
                                                        </div>
                                                        
                                                        <Button
                                                            onClick={() => handleAssignTemplate(template)}
                                                            className="w-full"
                                                            leftIcon={<Plus className="w-4 h-4" />}
                                                        >
                                                            Asignar
                                                        </Button>
                                                    </div>
                                                </div>
                                            </Card>
                                        </motion.div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Recommended Templates Tab */}
                    {activeTab === "recommended" && (
                        <div className="space-y-4">
                            {loading ? (
                                <div className="flex justify-center py-12">
                                    <div className="w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
                                </div>
                            ) : recommendedTemplates.length === 0 ? (
                                <div className="text-center py-12">
                                    <TrendingUp className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                                    <h3 className="text-lg font-medium text-white mb-2">Sin recomendaciones</h3>
                                    <p className="text-slate-400">Usa más plantillas para obtener recomendaciones personalizadas</p>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                    {recommendedTemplates.map((template, index) => (
                                        <motion.div
                                            key={template.id}
                                            initial={{ opacity: 0, y: 20 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: index * 0.1 }}
                                        >
                                            <Card className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-all">
                                                <div className="p-6">
                                                    <div className="space-y-4">
                                                        <div className="flex items-start justify-between">
                                                            <div className="flex-1">
                                                                <h3 className="font-semibold text-white mb-2">
                                                                    {template.nombre}
                                                                </h3>
                                                                <p className="text-sm text-slate-400 line-clamp-2">
                                                                    {template.descripcion}
                                                                </p>
                                                            </div>
                                                            <Badge className="bg-yellow-500 text-black text-xs">
                                                                <TrendingUp className="w-3 h-3 mr-1" />
                                                                Recomendada
                                                            </Badge>
                                                        </div>
                                                        
                                                        {template.recommendation_reason && (
                                                            <div className="p-2 bg-yellow-500/10 rounded-lg">
                                                                <p className="text-xs text-yellow-400">
                                                                    {template.recommendation_reason}
                                                                </p>
                                                            </div>
                                                        )}
                                                        
                                                        <div className="flex flex-wrap gap-2">
                                                            <Badge variant="outline">{template.categoria}</Badge>
                                                            {template.dias_semana && (
                                                                <Badge variant="secondary">
                                                                    {template.dias_semana} días
                                                                </Badge>
                                                            )}
                                                        </div>
                                                        
                                                        <Button
                                                            onClick={() => handleAssignTemplate(template)}
                                                            className="w-full"
                                                            leftIcon={<Plus className="w-4 h-4" />}
                                                        >
                                                            Asignar
                                                        </Button>
                                                    </div>
                                                </div>
                                            </Card>
                                        </motion.div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </Tabs>

            {/* Assign Template Modal */}
            <Modal
                isOpen={showAssignModal}
                onClose={() => setShowAssignModal(false)}
                title="Asignar Nueva Plantilla"
                size="lg"
            >
                <div className="space-y-4">
                    <p className="text-slate-400">
                        Selecciona una plantilla de la biblioteca para asignarla a {gymName}
                    </p>
                    
                    {/* Template selection would go here */}
                    <div className="text-center py-8">
                        <AlertCircle className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                        <p className="text-slate-400">
                            Usa la pestaña "Disponibles" para explorar y asignar plantillas
                        </p>
                    </div>
                    
                    <div className="flex justify-end">
                        <Button onClick={() => setShowAssignModal(false)}>
                            Cerrar
                        </Button>
                    </div>
                </div>
            </Modal>

            {/* Customize Template Modal */}
            <Modal
                isOpen={showCustomizeModal}
                onClose={() => setShowCustomizeModal(false)}
                title="Personalizar Plantilla"
                size="xl"
            >
                {selectedAssignment && (
                    <div className="space-y-6">
                        <div>
                            <h3 className="font-semibold text-white mb-2">
                                {selectedAssignment.template_name}
                            </h3>
                            <p className="text-slate-400">
                                Ajusta la configuración para adaptarla mejor a las necesidades de {gymName}
                            </p>
                        </div>
                        
                        {/* Customization form would go here */}
                        <div className="p-4 bg-slate-800 rounded-lg">
                            <p className="text-slate-400 text-center">
                                Formulario de personalización en desarrollo...
                            </p>
                        </div>
                        
                        <div className="flex justify-end gap-3">
                            <Button variant="secondary" onClick={() => setShowCustomizeModal(false)}>
                                Cancelar
                            </Button>
                            <Button onClick={() => setShowCustomizeModal(false)}>
                                Guardar Cambios
                            </Button>
                        </div>
                    </div>
                )}
            </Modal>

            {/* Analytics Modal */}
            <Modal
                isOpen={showAnalyticsModal}
                onClose={() => setShowAnalyticsModal(false)}
                title="Analytics de Plantillas"
                size="xl"
            >
                <div className="space-y-6">
                    {analytics ? (
                        <>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <Card className="bg-slate-800 border-slate-700">
                                    <div className="p-4 text-center">
                                        <div className="text-2xl font-bold text-white">{analytics.total_events}</div>
                                        <div className="text-sm text-slate-400">Eventos Totales</div>
                                    </div>
                                </Card>
                                <Card className="bg-slate-800 border-slate-700">
                                    <div className="p-4 text-center">
                                        <div className="text-2xl font-bold text-white">{analytics.unique_users}</div>
                                        <div className="text-sm text-slate-400">Usuarios Únicos</div>
                                    </div>
                                </Card>
                                <Card className="bg-slate-800 border-slate-700">
                                    <div className="p-4 text-center">
                                        <div className="text-2xl font-bold text-white">{analytics.success_rate.toFixed(1)}%</div>
                                        <div className="text-sm text-slate-400">Tasa de Éxito</div>
                                    </div>
                                </Card>
                            </div>
                            
                            <div>
                                <h4 className="font-semibold text-white mb-3">Plantillas Populares</h4>
                                <div className="space-y-2">
                                    {popularTemplates.map((template, index) => (
                                        <div key={index} className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                                            <div>
                                                <div className="font-medium text-white">{template.template_name}</div>
                                                <div className="text-sm text-slate-400">{template.template_category}</div>
                                            </div>
                                            <div className="text-right">
                                                <div className="font-medium text-white">{template.usage_count}</div>
                                                <div className="text-sm text-slate-400">usos</div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </>
                    ) : (
                        <div className="text-center py-8">
                            <BarChart3 className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                            <p className="text-slate-400">Cargando analytics...</p>
                        </div>
                    )}
                    
                    <div className="flex justify-end">
                        <Button onClick={() => setShowAnalyticsModal(false)}>
                            Cerrar
                        </Button>
                    </div>
                </div>
            </Modal>
        </div>
    );
}

export default GymTemplateManager;
