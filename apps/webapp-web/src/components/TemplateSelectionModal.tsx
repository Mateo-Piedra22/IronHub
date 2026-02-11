"use client";

import { useState, useEffect, useCallback } from "react";
import { Star, Download, Search, ChevronRight, Loader2, FileText, Users, Eye, Palette } from "lucide-react";
import { Modal, Button, Input, Select, useToast, Badge } from "@/components/ui";
import { api, type Template, type Rutina, type TemplatePreviewRequest } from "@/lib/api";

interface TemplateSelectionModalProps {
    isOpen: boolean;
    onClose: () => void;
    onTemplateSelect: (template: Template) => void;
    rutina: Rutina | null;
    gymId?: number;
}

type SortOption = "nombre" | "fecha_creacion" | "uso_count" | "categoria";
type SortOrder = "asc" | "desc";

export function TemplateSelectionModal({ isOpen, onClose, onTemplateSelect, rutina, gymId: _gymId }: TemplateSelectionModalProps) {
    const [templates, setTemplates] = useState<Template[]>([]);
    const [loading, setLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const [selectedCategory, setSelectedCategory] = useState<string>("");
    const [selectedDays, setSelectedDays] = useState<string>("");
    const [sortBy, setSortBy] = useState<SortOption>("fecha_creacion");
    const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
    const [categories, setCategories] = useState<string[]>([]);
    const [previewTemplate, setPreviewTemplate] = useState<Template | null>(null);
    const [previewLoading, setPreviewLoading] = useState(false);
    const [previewUrl, setPreviewUrl] = useState<string>("");
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(0);
    const [hasMore, setHasMore] = useState(false);
    
    const { success, error } = useToast();

    // Load categories on mount
    useEffect(() => {
        if (isOpen) {
            loadCategories();
            loadTemplates();
        }
    }, [isOpen]);

    // Reset state when modal closes
    useEffect(() => {
        if (!isOpen) {
            setTemplates([]);
            setSearchQuery("");
            setSelectedCategory("");
            setSelectedDays("");
            setPreviewTemplate(null);
            setPreviewUrl("");
            setPage(0);
        }
    }, [isOpen]);

    const loadCategories = async () => {
        try {
            const response = await api.getTemplateCategories();
            if (response.ok && response.data?.success && response.data.categories) {
                setCategories(response.data.categories);
            }
        } catch (err) {
            console.error("Error loading categories:", err);
        }
    };

    const loadTemplates = useCallback(async (resetPage = false) => {
        if (!rutina) return;

        setLoading(true);
        try {
            const currentPage = resetPage ? 0 : page;
            const params = {
                query: searchQuery || undefined,
                categoria: selectedCategory || undefined,
                dias_semana: selectedDays ? parseInt(selectedDays) : undefined,
                sort_by: sortBy,
                sort_order: sortOrder,
                limit: 12,
                offset: currentPage * 12
            };

            const response = await api.getTemplates(params);
            
            if (response.ok && response.data?.success && response.data.templates) {
                if (resetPage) {
                    setTemplates(response.data.templates);
                    setPage(0);
                } else {
                    setTemplates(prev => [...prev, ...(response.data?.templates || [])]);
                }
                setTotal(response.data.total || 0);
                setHasMore(response.data.has_more || false);
            }
        } catch (err) {
            console.error("Error loading templates:", err);
            error("Error al cargar plantillas");
        } finally {
            setLoading(false);
        }
    }, [rutina, searchQuery, selectedCategory, selectedDays, sortBy, sortOrder, page]);

    // Load more templates
    const loadMore = () => {
        if (!loading && hasMore) {
            setPage(prev => prev + 1);
            loadTemplates(false);
        }
    };

    // Handle search with debounce
    useEffect(() => {
        const timer = setTimeout(() => {
            loadTemplates(true);
        }, 300);

        return () => clearTimeout(timer);
    }, [searchQuery, selectedCategory, selectedDays, sortBy, sortOrder]);

    // Generate preview for template
    const generatePreview = async (template: Template) => {
        if (!rutina) return;

        setPreviewTemplate(template);
        setPreviewLoading(true);
        try {
            const request: TemplatePreviewRequest = {
                format: 'pdf',
                quality: 'medium',
                page_number: 1
            };

            const response = await api.getRutinaPreviewWithTemplate(rutina.id, template.id, request);
            
            if (response.ok && response.data?.success && response.data.preview_url) {
                setPreviewUrl(response.data.preview_url);
            } else {
                // Fallback to template preview
                const templateResponse = await api.getTemplatePreview(template.id, request);
                if (templateResponse.ok && templateResponse.data?.success && templateResponse.data.preview_url) {
                    setPreviewUrl(templateResponse.data.preview_url);
                }
            }
        } catch (err) {
            console.error("Error generating preview:", err);
            error("Error al generar vista previa");
        } finally {
            setPreviewLoading(false);
        }
    };

    // Handle template selection
    const handleTemplateSelect = (template: Template) => {
        onTemplateSelect(template);
        onClose();
        success(`Plantilla "${template.nombre}" seleccionada`);
    };

    // Filter templates based on routine days
    const getRecommendedTemplates = () => {
        if (!rutina) return templates;
        const routineDays = rutina.dias?.length || 0;
        return templates.filter(template => 
            !template.dias_semana || template.dias_semana === routineDays
        );
    };

    const recommendedTemplates = getRecommendedTemplates();

    return (
        <>
            <Modal
                isOpen={isOpen && !previewTemplate}
                onClose={onClose}
                title="Seleccionar Plantilla"
                size="xl"
                footer={
                    <div className="flex justify-between items-center w-full">
                        <div className="text-sm text-slate-400">
                            {total} plantilla{total !== 1 ? 's' : ''} encontrada{total !== 1 ? 's' : ''}
                        </div>
                        <div className="flex gap-2">
                            <Button variant="secondary" onClick={onClose}>
                                Cancelar
                            </Button>
                        </div>
                    </div>
                }
            >
                <div className="space-y-4">
                    {/* Search and Filters */}
                    <div className="flex flex-col sm:flex-row gap-3">
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
                                { value: "", label: "Todas las categorías" },
                                ...categories.map(cat => ({ value: cat, label: cat }))
                            ]}
                        />

                        <Select
                            value={selectedDays}
                            onChange={(e) => setSelectedDays(e.target.value)}
                            placeholder="Días"
                            className="w-full sm:w-32"
                            options={[
                                { value: "", label: "Todos los días" },
                                { value: "1", label: "1 día" },
                                { value: "2", label: "2 días" },
                                { value: "3", label: "3 días" },
                                { value: "4", label: "4 días" },
                                { value: "5", label: "5 días" },
                                { value: "6", label: "6 días" },
                                { value: "7", label: "7 días" }
                            ]}
                        />

                        <Select
                            value={`${sortBy}-${sortOrder}`}
                            onChange={(e) => {
                                const [sort, order] = e.target.value.split('-');
                                setSortBy(sort as SortOption);
                                setSortOrder(order as SortOrder);
                            }}
                            className="w-full sm:w-40"
                            options={[
                                { value: "fecha_creacion-desc", label: "Más recientes" },
                                { value: "fecha_creacion-asc", label: "Más antiguos" },
                                { value: "nombre-asc", label: "Nombre A-Z" },
                                { value: "nombre-desc", label: "Nombre Z-A" },
                                { value: "uso_count-desc", label: "Más usadas" },
                                { value: "uso_count-asc", label: "Menos usadas" }
                            ]}
                        />
                    </div>

                    {/* Recommended Templates */}
                    {recommendedTemplates.length > 0 && (
                        <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                            <div className="flex items-center gap-2 mb-3">
                                <Star className="w-4 h-4 text-yellow-400" />
                                <span className="text-sm font-medium text-white">Recomendadas para esta rutina</span>
                                <Badge variant="secondary">{rutina?.dias?.length || 0} días</Badge>
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                                {recommendedTemplates.slice(0, 3).map(template => (
                                    <TemplateCard
                                        key={template.id}
                                        template={template}
                                        onSelect={() => handleTemplateSelect(template)}
                                        onPreview={() => generatePreview(template)}
                                        isRecommended={true}
                                    />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Templates Grid */}
                    <div className="space-y-3">
                        {loading && templates.length === 0 ? (
                            <div className="flex justify-center py-8">
                                <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
                            </div>
                        ) : templates.length === 0 ? (
                            <div className="text-center py-8 text-slate-400">
                                <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                                <p>No se encontraron plantillas</p>
                                <p className="text-sm mt-1">Intenta ajustar los filtros de búsqueda</p>
                            </div>
                        ) : (
                            <>
                                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                                    {templates.map(template => (
                                        <TemplateCard
                                            key={template.id}
                                            template={template}
                                            onSelect={() => handleTemplateSelect(template)}
                                            onPreview={() => generatePreview(template)}
                                            isRecommended={recommendedTemplates.includes(template)}
                                        />
                                    ))}
                                </div>

                                {/* Load More */}
                                {hasMore && (
                                    <div className="flex justify-center pt-4">
                                        <Button
                                            variant="secondary"
                                            onClick={loadMore}
                                            disabled={loading}
                                            leftIcon={loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ChevronRight className="w-4 h-4" />}
                                        >
                                            Cargar más
                                        </Button>
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                </div>
            </Modal>

            {/* Preview Modal */}
            <Modal
                isOpen={!!previewTemplate}
                onClose={() => setPreviewTemplate(null)}
                title={`Vista previa: ${previewTemplate?.nombre}`}
                size="lg"
                footer={
                    <div className="flex justify-between items-center w-full">
                        <Button variant="secondary" onClick={() => setPreviewTemplate(null)}>
                            Cerrar vista previa
                        </Button>
                        {previewTemplate && (
                            <Button
                                onClick={() => handleTemplateSelect(previewTemplate)}
                                leftIcon={<Download className="w-4 h-4" />}
                            >
                                Usar esta plantilla
                            </Button>
                        )}
                    </div>
                }
            >
                <div className="space-y-4">
                    {/* Template Info */}
                    {previewTemplate && (
                        <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                            <div className="flex items-start justify-between">
                                <div>
                                    <h3 className="font-medium text-white">{previewTemplate.nombre}</h3>
                                    <p className="text-sm text-slate-400 mt-1">{previewTemplate.descripcion}</p>
                                    <div className="flex items-center gap-4 mt-2">
                                        <Badge variant="secondary">{previewTemplate.categoria}</Badge>
                                        {previewTemplate.dias_semana && (
                                            <Badge variant="outline">{previewTemplate.dias_semana} días</Badge>
                                        )}
                                        <div className="flex items-center gap-1 text-xs text-slate-400">
                                            <Users className="w-3 h-3" />
                                            {previewTemplate.uso_count} usos
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Preview */}
                    <div className="bg-white rounded-lg overflow-hidden" style={{ minHeight: '400px' }}>
                        {previewLoading ? (
                            <div className="flex items-center justify-center h-96">
                                <div className="text-center">
                                    <Loader2 className="w-8 h-8 animate-spin text-slate-600 mx-auto mb-2" />
                                    <p className="text-slate-600">Generando vista previa...</p>
                                </div>
                            </div>
                        ) : previewUrl ? (
                            <iframe
                                src={previewUrl}
                                className="w-full h-96 border-0"
                                title="Template Preview"
                            />
                        ) : (
                            <div className="flex items-center justify-center h-96">
                                <div className="text-center text-slate-500">
                                    <Eye className="w-12 h-12 mx-auto mb-2 opacity-50" />
                                    <p>No se pudo generar la vista previa</p>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </Modal>
        </>
    );
}

interface TemplateCardProps {
    template: Template;
    onSelect: () => void;
    onPreview: () => void;
    isRecommended: boolean;
}

function TemplateCard({ template, onSelect, onPreview, isRecommended }: TemplateCardProps) {
    return (
        <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden hover:border-slate-600 transition-colors">
            {/* Preview Thumbnail */}
            <div className="relative h-32 bg-slate-900">
                {template.preview_url ? (
                    <img
                        src={template.preview_url}
                        alt={template.nombre}
                        className="w-full h-full object-cover"
                    />
                ) : (
                    <div className="flex items-center justify-center h-full">
                        <Palette className="w-8 h-8 text-slate-600" />
                    </div>
                )}
                
                {isRecommended && (
                    <div className="absolute top-2 left-2">
                        <Badge className="bg-yellow-500 text-black text-xs">
                            <Star className="w-3 h-3 mr-1" />
                            Recomendada
                        </Badge>
                    </div>
                )}

                <div className="absolute bottom-2 right-2 flex gap-1">
                    <button
                        onClick={onPreview}
                        className="p-1.5 bg-black/50 rounded-md hover:bg-black/70 transition-colors"
                        title="Vista previa"
                    >
                        <Eye className="w-3 h-3 text-white" />
                    </button>
                </div>
            </div>

            {/* Template Info */}
            <div className="p-3">
                <h3 className="font-medium text-white text-sm truncate">{template.nombre}</h3>
                <p className="text-xs text-slate-400 mt-1 line-clamp-2">{template.descripcion}</p>
                
                <div className="flex items-center justify-between mt-3">
                    <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="text-xs">
                            {template.categoria}
                        </Badge>
                        {template.dias_semana && (
                            <Badge variant="outline" className="text-xs">
                                {template.dias_semana}d
                            </Badge>
                        )}
                    </div>
                    
                    <div className="flex items-center gap-1 text-xs text-slate-400">
                        <Users className="w-3 h-3" />
                        {template.uso_count}
                    </div>
                </div>

                <Button
                    onClick={onSelect}
                    className="w-full mt-3"
                    size="sm"
                    leftIcon={<Download className="w-3 h-3" />}
                >
                    Seleccionar
                </Button>
            </div>
        </div>
    );
}

export default TemplateSelectionModal;
