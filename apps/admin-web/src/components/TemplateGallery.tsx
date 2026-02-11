"use client";

import { useState, useEffect, useCallback } from "react";
import Image from "next/image";
import { 
  Plus, Search, Download, Eye, Edit, Trash2, 
  Star, Users, Copy,
  ChevronDown, Grid, List, Loader2, Check, X, RefreshCw, FileText
} from "lucide-react";
import { Button, Input, Select, useToast, Badge } from "@/components/ui";
import { api, type Template, type TemplateAnalytics } from "@/lib/api";

interface TemplateGalleryProps {
  onTemplateSelect: (template: Template) => void;
  onTemplateEdit: (template: Template) => void;
  onTemplateCreate: () => void;
}

type ViewMode = "grid" | "list";
type SortOption = "nombre" | "fecha_creacion" | "uso_count" | "rating" | "categoria";
type FilterStatus = "all" | "active" | "inactive" | "draft";

export function TemplateGallery({ onTemplateSelect, onTemplateEdit, onTemplateCreate }: TemplateGalleryProps) {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [selectedStatus, setSelectedStatus] = useState<FilterStatus>("all");
  const [sortBy, setSortBy] = useState<SortOption>("fecha_creacion");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedTemplates, setSelectedTemplates] = useState<number[]>([]);
  const [analytics, setAnalytics] = useState<{ [key: number]: TemplateAnalytics }>({});
  const [showBulkActions, setShowBulkActions] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  
  const { success, error } = useToast();

  const loadCategories = useCallback(async () => {
    try {
      const response = await api.getTemplateCategories();
      if (response.ok && response.data?.success && response.data.categories) {
        setCategories(response.data.categories);
      }
    } catch (err) {
      console.error("Error loading categories:", err);
    }
  }, []);

  const loadTemplates = useCallback(async (resetPage = false) => {
    setLoading(true);
    try {
      const currentPage = resetPage ? 0 : page;
      const params = {
        query: searchQuery || undefined,
        categoria: selectedCategory || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        activa: selectedStatus === "all" ? undefined : selectedStatus === "active",
        limit: 20,
        offset: currentPage * 20
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
        
        // Load analytics for visible templates
        loadAnalytics(response.data.templates);
      }
    } catch (err) {
      console.error("Error loading templates:", err);
      error("Error al cargar plantillas");
    } finally {
      setLoading(false);
    }
  }, [searchQuery, selectedCategory, selectedStatus, sortBy, sortOrder, page, error]);

  // Load categories on mount
  useEffect(() => {
    loadCategories();
    loadTemplates();
  }, [loadCategories, loadTemplates]);

  // Reset and load templates when filters change
  useEffect(() => {
    setPage(0);
    loadTemplates(true);
  }, [searchQuery, selectedCategory, selectedStatus, sortBy, sortOrder, loadTemplates]);

  const loadAnalytics = async (templateList: Template[]) => {
    try {
      const analyticsPromises = templateList.map(template => 
        api.getTemplateAnalytics(template.id)
      );
      
      const responses = await Promise.all(analyticsPromises);
      const newAnalytics: { [key: number]: TemplateAnalytics } = {};
      
      responses.forEach((response, index) => {
        if (response.ok && response.data?.success) {
          newAnalytics[templateList[index].id] = response.data.analytics;
        }
      });
      
      setAnalytics(prev => ({ ...prev, ...newAnalytics }));
    } catch (err) {
      console.error("Error loading analytics:", err);
    }
  };

  // Load more templates
  const loadMore = () => {
    if (!loading && hasMore) {
      setPage(prev => prev + 1);
      loadTemplates(false);
    }
  };

  // Handle template selection
  const handleTemplateSelect = (templateId: number) => {
    setSelectedTemplates(prev => {
      const newSelection = prev.includes(templateId)
        ? prev.filter(id => id !== templateId)
        : [...prev, templateId];
      
      setShowBulkActions(newSelection.length > 0);
      return newSelection;
    });
  };

  // Handle template actions
  const handleTemplateEdit = (template: Template) => {
    onTemplateEdit(template);
  };

  const handleTemplateDuplicate = async (template: Template) => {
    try {
      const response = await api.duplicateTemplate(template.id);
      if (response.ok && response.data?.success) {
        success("Plantilla duplicada exitosamente");
        loadTemplates(true);
      } else {
        error("Error al duplicar plantilla");
      }
    } catch (err) {
      console.error("Error duplicating template:", err);
      error("Error al duplicar plantilla");
    }
  };

  const handleTemplateDelete = async (template: Template) => {
    if (!confirm(`¿Estás seguro de eliminar la plantilla "${template.nombre}"?`)) {
      return;
    }

    try {
      const response = await api.deleteTemplate(template.id);
      if (response.ok && response.data?.success) {
        success("Plantilla eliminada exitosamente");
        loadTemplates(true);
      } else {
        error("Error al eliminar plantilla");
      }
    } catch (err) {
      console.error("Error deleting template:", err);
      error("Error al eliminar plantilla");
    }
  };

  const handleBulkAction = async (action: "activate" | "deactivate" | "delete") => {
    if (selectedTemplates.length === 0) return;

    const confirmMessage = action === "delete" 
      ? `¿Estás seguro de eliminar ${selectedTemplates.length} plantillas?`
      : `¿Estás seguro de ${action === "activate" ? "activar" : "desactivar"} ${selectedTemplates.length} plantillas?`;

    if (!confirm(confirmMessage)) return;

    try {
      const response = await api.bulkUpdateTemplates(selectedTemplates, {
        activa: action === "activate" ? true : action === "deactivate" ? false : undefined
      });

      if (response.ok && response.data?.success) {
        success(`${action === "delete" ? "Eliminadas" : action === "activate" ? "Activadas" : "Desactivadas"} ${selectedTemplates.length} plantillas`);
        setSelectedTemplates([]);
        setShowBulkActions(false);
        loadTemplates(true);
      } else {
        error(`Error al realizar acción bulk ${action}`);
      }
    } catch (err) {
      console.error(`Error in bulk ${action}:`, err);
      error(`Error al realizar acción bulk ${action}`);
    }
  };

  const handleRefresh = () => {
    loadTemplates(true);
  };

  const filteredTemplates = templates;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white">Galería de Plantillas</h2>
          <p className="text-slate-400 mt-1">
            {total} plantilla{total !== 1 ? 's' : ''} encontrada{total !== 1 ? 's' : ''}
          </p>
        </div>
        
        <div className="flex gap-3">
          <Button
            onClick={handleRefresh}
            variant="secondary"
            size="sm"
            leftIcon={<RefreshCw className="w-4 h-4" />}
          >
            Actualizar
          </Button>
          <Button
            onClick={onTemplateCreate}
            leftIcon={<Plus className="w-4 h-4" />}
          >
            Nueva Plantilla
          </Button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Buscar plantillas..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>

          {/* Filters */}
          <div className="flex flex-wrap gap-3">
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
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value as FilterStatus)}
              placeholder="Estado"
              className="w-full sm:w-36"
              options={[
                { value: "all", label: "Todos" },
                { value: "active", label: "Activas" },
                { value: "inactive", label: "Inactivas" },
                { value: "draft", label: "Borradores" }
              ]}
            />

            <Select
              value={`${sortBy}-${sortOrder}`}
              onChange={(e) => {
                const [sort, order] = e.target.value.split('-');
                setSortBy(sort as SortOption);
                setSortOrder(order as "asc" | "desc");
              }}
              className="w-full sm:w-48"
              options={[
                { value: "fecha_creacion-desc", label: "Más recientes" },
                { value: "fecha_creacion-asc", label: "Más antiguos" },
                { value: "nombre-asc", label: "Nombre A-Z" },
                { value: "nombre-desc", label: "Nombre Z-A" },
                { value: "uso_count-desc", label: "Más usadas" },
                { value: "rating-desc", label: "Mejor evaluadas" }
              ]}
            />
          </div>

          {/* View Mode */}
          <div className="flex gap-2">
            <Button
              variant={viewMode === "grid" ? "primary" : "secondary"}
              size="sm"
              onClick={() => setViewMode("grid")}
            >
              <Grid className="w-4 h-4" />
            </Button>
            <Button
              variant={viewMode === "list" ? "primary" : "secondary"}
              size="sm"
              onClick={() => setViewMode("list")}
            >
              <List className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Bulk Actions */}
      {showBulkActions && (
        <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-sm text-white">
                {selectedTemplates.length} plantilla{selectedTemplates.length !== 1 ? 's' : ''} seleccionada{selectedTemplates.length !== 1 ? 's' : ''}
              </span>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setSelectedTemplates([]);
                  setShowBulkActions(false);
                }}
              >
                Limpiar selección
              </Button>
            </div>
            
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleBulkAction("activate")}
              >
                <Check className="w-4 h-4 mr-2" />
                Activar
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleBulkAction("deactivate")}
              >
                <X className="w-4 h-4 mr-2" />
                Desactivar
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={() => handleBulkAction("delete")}
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Eliminar
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Templates Grid/List */}
      <div className="space-y-4">
        {loading && templates.length === 0 ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
          </div>
        ) : filteredTemplates.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-slate-400 mb-4">
              {searchQuery || selectedCategory || selectedStatus !== "all"
                ? "No se encontraron plantillas con los filtros seleccionados"
                : "No hay plantillas creadas aún"}
            </div>
            {!searchQuery && !selectedCategory && selectedStatus === "all" && (
              <Button onClick={onTemplateCreate} leftIcon={<Plus className="w-4 h-4" />}>
                Crear Primera Plantilla
              </Button>
            )}
          </div>
        ) : (
          <>
            {viewMode === "grid" ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {filteredTemplates.map(template => (
                  <TemplateCard
                    key={template.id}
                    template={template}
                    analytics={analytics[template.id]}
                    isSelected={selectedTemplates.includes(template.id)}
                    onSelect={() => handleTemplateSelect(template.id)}
                    onEdit={() => handleTemplateEdit(template)}
                    onDuplicate={() => handleTemplateDuplicate(template)}
                    onDelete={() => handleTemplateDelete(template)}
                    onView={() => onTemplateSelect(template)}
                  />
                ))}
              </div>
            ) : (
              <div className="space-y-3">
                {filteredTemplates.map(template => (
                  <TemplateListItem
                    key={template.id}
                    template={template}
                    analytics={analytics[template.id]}
                    isSelected={selectedTemplates.includes(template.id)}
                    onSelect={() => handleTemplateSelect(template.id)}
                    onEdit={() => handleTemplateEdit(template)}
                    onDuplicate={() => handleTemplateDuplicate(template)}
                    onDelete={() => handleTemplateDelete(template)}
                    onView={() => onTemplateSelect(template)}
                  />
                ))}
              </div>
            )}

            {/* Load More */}
            {hasMore && (
              <div className="flex justify-center pt-6">
                <Button
                  variant="secondary"
                  onClick={loadMore}
                  disabled={loading}
                  leftIcon={loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ChevronDown className="w-4 h-4" />}
                >
                  {loading ? "Cargando..." : "Cargar Más"}
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// Template Card Component
interface TemplateCardProps {
  template: Template;
  analytics?: TemplateAnalytics;
  isSelected: boolean;
  onSelect: () => void;
  onEdit: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
  onView: () => void;
}

function TemplateCard({ 
  template, 
  analytics, 
  isSelected, 
  onSelect, 
  onEdit, 
  onDuplicate, 
  onDelete, 
  onView 
}: TemplateCardProps) {
  return (
    <div className={`bg-slate-800 rounded-xl border overflow-hidden transition-all duration-200 hover:border-slate-600 ${
      isSelected ? 'border-primary-500 ring-2 ring-primary-500/50' : 'border-slate-700'
    }`}>
      {/* Selection Checkbox */}
      <div className="absolute top-3 left-3 z-10">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onSelect}
          className="w-4 h-4 rounded border-slate-600 bg-slate-900 text-primary-500 focus:ring-primary-500/50"
        />
      </div>

      {/* Preview Image */}
      <div className="relative h-32 bg-slate-900">
        {template.preview_url ? (
          <Image
            src={template.preview_url}
            alt={template.nombre}
            fill
            unoptimized
            className="object-cover"
            sizes="(max-width: 1024px) 100vw, 33vw"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <FileText className="w-8 h-8 text-slate-600" />
          </div>
        )}
        
        {/* Status Badge */}
        <div className="absolute top-3 right-3">
          <Badge variant={template.activa ? "success" : "secondary"}>
            {template.activa ? "Activa" : "Inactiva"}
          </Badge>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        <div className="space-y-2">
          <div>
            <h3 className="font-semibold text-white truncate">{template.nombre}</h3>
            {template.descripcion && (
              <p className="text-sm text-slate-400 line-clamp-2">{template.descripcion}</p>
            )}
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-400">
            {template.categoria && (
              <Badge variant="outline" size="sm">{template.categoria}</Badge>
            )}
            {template.dias_semana && (
              <span>{template.dias_semana} días</span>
            )}
            <span>v{template.version_actual}</span>
          </div>

          {/* Analytics */}
          {analytics && (
            <div className="flex items-center gap-4 text-xs text-slate-400">
              <div className="flex items-center gap-1">
                <Download className="w-3 h-3" />
                <span>{analytics.usos_totales || 0}</span>
              </div>
              <div className="flex items-center gap-1">
                <Star className="w-3 h-3" />
                <span>{template.rating_promedio ? Number(template.rating_promedio).toFixed(1) : "N/A"}</span>
              </div>
              <div className="flex items-center gap-1">
                <Users className="w-3 h-3" />
                <span>{analytics.usuarios_unicos || 0}</span>
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2 mt-4">
          <Button
            variant="secondary"
            size="sm"
            onClick={onView}
            className="flex-1"
          >
            <Eye className="w-3 h-3 mr-1" />
            Ver
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={onEdit}
          >
            <Edit className="w-3 h-3" />
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={onDuplicate}
          >
            <Copy className="w-3 h-3" />
          </Button>
          <Button
            variant="danger"
            size="sm"
            onClick={onDelete}
          >
            <Trash2 className="w-3 h-3" />
          </Button>
        </div>
      </div>
    </div>
  );
}

// Template List Item Component
interface TemplateListItemProps {
  template: Template;
  analytics?: TemplateAnalytics;
  isSelected: boolean;
  onSelect: () => void;
  onEdit: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
  onView: () => void;
}

function TemplateListItem({ 
  template, 
  analytics, 
  isSelected, 
  onSelect, 
  onEdit, 
  onDuplicate, 
  onDelete, 
  onView 
}: TemplateListItemProps) {
  return (
    <div className={`bg-slate-800 rounded-xl border p-4 transition-all duration-200 hover:border-slate-600 ${
      isSelected ? 'border-primary-500 ring-2 ring-primary-500/50' : 'border-slate-700'
    }`}>
      <div className="flex items-center gap-4">
        {/* Selection Checkbox */}
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onSelect}
          className="w-4 h-4 rounded border-slate-600 bg-slate-900 text-primary-500 focus:ring-primary-500/50"
        />

        {/* Preview Thumbnail */}
        <div className="w-16 h-16 bg-slate-900 rounded-lg overflow-hidden flex-shrink-0">
          {template.preview_url ? (
            <Image
              src={template.preview_url}
              alt={template.nombre}
              width={64}
              height={64}
              unoptimized
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <FileText className="w-6 h-6 text-slate-600" />
            </div>
          )}
        </div>

        {/* Template Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <h3 className="font-semibold text-white truncate">{template.nombre}</h3>
              {template.descripcion && (
                <p className="text-sm text-slate-400 line-clamp-1">{template.descripcion}</p>
              )}
              <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
                {template.categoria && (
                  <Badge variant="outline" size="sm">{template.categoria}</Badge>
                )}
                {template.dias_semana && (
                  <span>{template.dias_semana} días</span>
                )}
                <span>v{template.version_actual}</span>
                <Badge variant={template.activa ? "success" : "secondary"} size="sm">
                  {template.activa ? "Activa" : "Inactiva"}
                </Badge>
              </div>
            </div>

            {/* Analytics */}
            {analytics && (
              <div className="flex items-center gap-4 text-sm text-slate-400">
                <div className="flex items-center gap-1">
                  <Download className="w-4 h-4" />
                  <span>{analytics.usos_totales || 0}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Star className="w-4 h-4" />
                  <span>{template.rating_promedio ? Number(template.rating_promedio).toFixed(1) : "N/A"}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Users className="w-4 h-4" />
                  <span>{analytics.usuarios_unicos || 0}</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={onView}
          >
            <Eye className="w-4 h-4" />
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={onEdit}
          >
            <Edit className="w-4 h-4" />
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={onDuplicate}
          >
            <Copy className="w-4 h-4" />
          </Button>
          <Button
            variant="danger"
            size="sm"
            onClick={onDelete}
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
