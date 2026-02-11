"use client";

import { useState, useEffect, useCallback } from "react";
import { 
  Plus, Search, Filter, Download, Eye, Edit, Trash2, 
  Star, Users, Calendar, TrendingUp, Copy, Settings,
  ChevronDown, Grid, List, Loader2, Check, X, RefreshCw,
  BarChart3, PieChart, Activity, Zap, Award, Clock
} from "lucide-react";
import { Button, Input, Select, Modal, useToast, Badge, Card } from "@/components/ui";
import { api, type Template, type TemplateAnalytics, type TemplateStats } from "@/lib/api";
import TemplateGallery from "@/components/TemplateGallery";
import TemplateEditor from "@/components/TemplateEditor";
import TemplatePreview from "@/components/TemplatePreview";

type ViewMode = "grid" | "list";
type SortOption = "nombre" | "fecha_creacion" | "uso_count" | "rating" | "categoria";
type FilterStatus = "all" | "active" | "inactive" | "draft";
type TimeRange = "7d" | "30d" | "90d" | "1y" | "all";

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<TemplateStats | null>(null);
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
  const [timeRange, setTimeRange] = useState<TimeRange>("30d");
  
  // Modal states
  const [showEditor, setShowEditor] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [isCreatingNew, setIsCreatingNew] = useState(false);
  
  const { success, error } = useToast();

  // Load initial data
  useEffect(() => {
    loadStats();
    loadCategories();
    loadTemplates();
  }, []);

  // Reset and load templates when filters change
  useEffect(() => {
    setPage(0);
    loadTemplates(true);
  }, [searchQuery, selectedCategory, selectedStatus, sortBy, sortOrder]);

  // Load stats when time range changes
  useEffect(() => {
    loadStats();
  }, [timeRange]);

  const loadStats = async () => {
    try {
      const response = await api.getTemplateStats(timeRange);
      if (response.ok && response.data?.success) {
        setStats(response.data.stats);
      }
    } catch (err) {
      console.error("Error loading stats:", err);
    }
  };

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
    setSelectedTemplate(template);
    setIsCreatingNew(false);
    setShowEditor(true);
  };

  const handleTemplateCreate = () => {
    setSelectedTemplate(null);
    setIsCreatingNew(true);
    setShowEditor(true);
  };

  const handleTemplatePreview = (template: Template) => {
    setSelectedTemplate(template);
    setShowPreview(true);
  };

  const handleTemplateDuplicate = async (template: Template) => {
    try {
      const response = await api.duplicateTemplate(template.id);
      if (response.ok && response.data?.success) {
        success("Plantilla duplicada exitosamente");
        loadTemplates(true);
        loadStats();
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
        loadStats();
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
        loadStats();
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
    loadStats();
  };

  const handleExportTemplates = async () => {
    try {
      const response = await api.exportTemplates(selectedTemplates.length > 0 ? selectedTemplates : undefined);
      if (response.ok && response.data?.success) {
        // Create download link
        const link = document.createElement('a');
        link.href = response.data.download_url;
        link.download = `templates_export_${new Date().toISOString().split('T')[0]}.json`;
        link.click();
        success("Plantillas exportadas exitosamente");
      } else {
        error("Error al exportar plantillas");
      }
    } catch (err) {
      console.error("Error exporting templates:", err);
      error("Error al exportar plantillas");
    }
  };

  const handleTemplateSave = (template: Template) => {
    success(`Plantilla ${isCreatingNew ? "creada" : "actualizada"} exitosamente`);
    setShowEditor(false);
    loadTemplates(true);
    loadStats();
  };

  const filteredTemplates = templates;

  const getTimeRangeLabel = (range: TimeRange) => {
    switch (range) {
      case "7d": return "Últimos 7 días";
      case "30d": return "Últimos 30 días";
      case "90d": return "Últimos 90 días";
      case "1y": return "Último año";
      case "all": return "Todo el tiempo";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">Gestión de Plantillas</h1>
          <p className="text-slate-400 mt-1">
            Administra y personaliza las plantillas de rutinas del sistema
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
            onClick={handleExportTemplates}
            variant="secondary"
            size="sm"
            leftIcon={<Download className="w-4 h-4" />}
          >
            Exportar
          </Button>
          <Button
            onClick={handleTemplateCreate}
            leftIcon={<Plus className="w-4 h-4" />}
          >
            Nueva Plantilla
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="bg-slate-800 border-slate-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">Total Plantillas</p>
                <p className="text-2xl font-bold text-white">{stats.total_templates}</p>
                <p className="text-xs text-slate-500 mt-1">
                  {stats.active_templates} activas
                </p>
              </div>
              <div className="w-12 h-12 bg-blue-500/20 rounded-lg flex items-center justify-center">
                <Grid className="w-6 h-6 text-blue-400" />
              </div>
            </div>
          </Card>

          <Card className="bg-slate-800 border-slate-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">Usos Totales</p>
                <p className="text-2xl font-bold text-white">{stats.total_usos}</p>
                <p className="text-xs text-slate-500 mt-1">
                  {getTimeRangeLabel(timeRange)}
                </p>
              </div>
              <div className="w-12 h-12 bg-green-500/20 rounded-lg flex items-center justify-center">
                <Download className="w-6 h-6 text-green-400" />
              </div>
            </div>
          </Card>

          <Card className="bg-slate-800 border-slate-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">Usuarios Únicos</p>
                <p className="text-2xl font-bold text-white">{stats.usuarios_unicos}</p>
                <p className="text-xs text-slate-500 mt-1">
                  {getTimeRangeLabel(timeRange)}
                </p>
              </div>
              <div className="w-12 h-12 bg-purple-500/20 rounded-lg flex items-center justify-center">
                <Users className="w-6 h-6 text-purple-400" />
              </div>
            </div>
          </Card>

          <Card className="bg-slate-800 border-slate-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">Rating Promedio</p>
                <p className="text-2xl font-bold text-white">
                  {stats.rating_promedio ? Number(stats.rating_promedio).toFixed(1) : "N/A"}
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  {stats.total_ratings} evaluaciones
                </p>
              </div>
              <div className="w-12 h-12 bg-yellow-500/20 rounded-lg flex items-center justify-center">
                <Star className="w-6 h-6 text-yellow-400" />
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Search and Filters */}
      <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
        <div className="flex flex-col xl:flex-row gap-4">
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
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortOption)}
              placeholder="Ordenar por"
              className="w-full sm:w-40"
              options={[
                { value: "nombre", label: "Nombre" },
                { value: "fecha_creacion", label: "Fecha" },
                { value: "uso_count", label: "Usos" },
                { value: "rating", label: "Rating" },
                { value: "categoria", label: "Categoría" }
              ]}
            />

            <Select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value as TimeRange)}
              placeholder="Período"
              className="w-full sm:w-36"
              options={[
                { value: "7d", label: "7 días" },
                { value: "30d", label: "30 días" },
                { value: "90d", label: "90 días" },
                { value: "1y", label: "1 año" },
                { value: "all", label: "Todo" }
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

      {/* Templates Gallery */}
      <TemplateGallery
        templates={filteredTemplates}
        analytics={analytics}
        loading={loading}
        viewMode={viewMode}
        selectedTemplates={selectedTemplates}
        total={total}
        hasMore={hasMore}
        onTemplateSelect={handleTemplateSelect}
        onTemplateEdit={handleTemplateEdit}
        onTemplatePreview={handleTemplatePreview}
        onTemplateDuplicate={handleTemplateDuplicate}
        onTemplateDelete={handleTemplateDelete}
        onLoadMore={loadMore}
      />

      {/* Template Editor Modal */}
      {showEditor && (
        <TemplateEditor
          template={selectedTemplate || undefined}
          isOpen={showEditor}
          onClose={() => setShowEditor(false)}
          onSave={handleTemplateSave}
          isNew={isCreatingNew}
        />
      )}

      {/* Template Preview Modal */}
      {showPreview && selectedTemplate && (
        <TemplatePreview
          template={selectedTemplate}
          isOpen={showPreview}
          onClose={() => setShowPreview(false)}
        />
      )}
    </div>
  );
}
