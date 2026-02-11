'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { 
  Search, Filter, Grid, List, Star, Download, Eye, Heart, 
  Clock, TrendingUp, Users, Calendar, Award, Palette,
  ChevronDown, RefreshCw, X, Check, AlertTriangle
} from 'lucide-react';
import { api, type Template, type TemplateAnalytics } from '@/lib/api';
import { Button, Card, Badge, Input, Select, Modal, useToast } from '@/components/ui';
import { useRouter } from 'next/navigation';

interface TemplateGalleryProps {
  onTemplateSelect?: (template: Template) => void;
  onTemplatePreview?: (template: Template) => void;
}

type ViewMode = "grid" | "list";
type SortOption = "nombre" | "fecha_creacion" | "uso_count" | "rating" | "categoria";
type FilterCategory = "all" | string;

export default function TemplatesPage() {
  const router = useRouter();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<FilterCategory>("all");
  const [sortBy, setSortBy] = useState<SortOption>("uso_count");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [categories, setCategories] = useState<string[]>([]);
  const [analytics, setAnalytics] = useState<{ [key: number]: TemplateAnalytics }>({});
  const [favorites, setFavorites] = useState<number[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  
  const { success, error } = useToast();

  // Load categories and initial templates
  useEffect(() => {
    loadCategories();
    loadTemplates();
    loadFavorites();
  }, []);

  // Reset and load templates when filters change
  useEffect(() => {
    setPage(0);
    loadTemplates(true);
  }, [searchQuery, selectedCategory, sortBy, sortOrder]);

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
        categoria: selectedCategory === "all" ? undefined : selectedCategory,
        sort_by: sortBy,
        sort_order: sortOrder,
        activa: true, // Only show active templates
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
  }, [searchQuery, selectedCategory, sortBy, sortOrder, page, error]);

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

  const loadFavorites = async () => {
    try {
      const response = await api.getTemplateFavorites();
      if (response.ok && response.data?.success) {
        setFavorites(response.data.templates.map(t => t.id));
      }
    } catch (err) {
      console.error("Error loading favorites:", err);
    }
  };

  // Load more templates
  const loadMore = () => {
    if (!loading && hasMore) {
      setPage(prev => prev + 1);
      loadTemplates(false);
    }
  };

  // Handle template actions
  const handleTemplateSelect = (template: Template) => {
    setSelectedTemplate(template);
    setShowPreviewModal(true);
  };

  const handleTemplatePreview = (template: Template) => {
    setSelectedTemplate(template);
    setShowPreviewModal(true);
  };

  const handleTemplateFavorite = async (template: Template) => {
    try {
      const response = await api.toggleTemplateFavorite(template.id);
      if (response.ok && response.data?.success) {
        setFavorites(prev => 
          prev.includes(template.id) 
            ? prev.filter(id => id !== template.id)
            : [...prev, template.id]
        );
        success(response.data.favorite ? "Añadido a favoritos" : "Eliminado de favoritos");
      }
    } catch (err) {
      console.error("Error toggling favorite:", err);
      error("Error al actualizar favoritos");
    }
  };

  const handleTemplateUse = async (template: Template) => {
    try {
      // Navigate to routines page with template selected
      router.push(`/usuario/routines?template=${template.id}`);
    } catch (err) {
      console.error("Error navigating to routines:", err);
      error("Error al navegar a rutinas");
    }
  };

  const handleTemplateRate = async (template: Template, rating: number) => {
    try {
      const response = await api.rateTemplate(template.id, rating);
      if (response.ok && response.data?.success) {
        success("Gracias por tu calificación");
        // Refresh templates to update rating
        loadTemplates(true);
      }
    } catch (err) {
      console.error("Error rating template:", err);
      error("Error al calificar plantilla");
    }
  };

  const handleRefresh = () => {
    loadTemplates(true);
    loadFavorites();
  };

  const getRatingStars = (rating: number) => {
    return Array.from({ length: 5 }, (_, i) => (
      <Star
        key={i}
        className={`w-3 h-3 ${
          i < Math.floor(rating) ? 'fill-yellow-400 text-yellow-400' : 'text-slate-600'
        }`}
      />
    ));
  };

  const getUsageLevel = (usos: number) => {
    if (usos > 100) return { level: "Alto", color: "text-green-400", icon: TrendingUp };
    if (usos > 50) return { level: "Medio", color: "text-yellow-400", icon: Users };
    return { level: "Bajo", color: "text-slate-400", icon: Clock };
  };

  const filteredTemplates = templates;

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <div className="bg-slate-900/50 backdrop-blur-sm border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Palette className="w-8 h-8 text-primary-500" />
              <div>
                <h1 className="text-xl font-bold text-white">Plantillas de Rutina</h1>
                <p className="text-sm text-slate-400">
                  Descubre y usa plantillas profesionales para tus entrenamientos
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRefresh}
                disabled={loading}
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
              
              <div className="flex gap-2">
                <Button
                  variant={viewMode === "grid" ? "primary" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode("grid")}
                >
                  <Grid className="w-4 h-4" />
                </Button>
                <Button
                  variant={viewMode === "list" ? "primary" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode("list")}
                >
                  <List className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="bg-slate-900/30 backdrop-blur-sm border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
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
                  { value: "all", label: "Todas las categorías" },
                  ...categories.map(cat => ({ value: cat, label: cat }))
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
                  { value: "uso_count-desc", label: "Más usadas" },
                  { value: "rating-desc", label: "Mejor evaluadas" },
                  { value: "fecha_creacion-desc", label: "Más recientes" },
                  { value: "nombre-asc", label: "Nombre A-Z" },
                  { value: "categoria-asc", label: "Categoría" }
                ]}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Results Header */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex items-center justify-between">
          <p className="text-slate-400">
            {total} plantilla{total !== 1 ? 's' : ''} encontrada{total !== 1 ? 's' : ''}
            {searchQuery && ` para "${searchQuery}"`}
          </p>
          
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-400">Favoritos:</span>
            <Badge variant="outline">{favorites.length}</Badge>
          </div>
        </div>
      </div>

      {/* Templates Grid/List */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-8">
        {loading && templates.length === 0 ? (
          <div className="flex justify-center py-12">
            <div className="text-center">
              <div className="w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
              <p className="text-slate-400">Cargando plantillas...</p>
            </div>
          </div>
        ) : filteredTemplates.length === 0 ? (
          <div className="text-center py-12">
            <Palette className="w-16 h-16 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-400 mb-4">
              {searchQuery || selectedCategory !== "all"
                ? "No se encontraron plantillas con los filtros seleccionados"
                : "No hay plantillas disponibles"}
            </p>
            <Button onClick={handleRefresh} leftIcon={<RefreshCw className="w-4 h-4" />}>
              Actualizar
            </Button>
          </div>
        ) : (
          <>
            {viewMode === "grid" ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {filteredTemplates.map((template, index) => (
                  <motion.div
                    key={template.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                  >
                    <TemplateCard
                      template={template}
                      analytics={analytics[template.id]}
                      isFavorite={favorites.includes(template.id)}
                      onSelect={() => handleTemplateSelect(template)}
                      onPreview={() => handleTemplatePreview(template)}
                      onFavorite={() => handleTemplateFavorite(template)}
                      onUse={() => handleTemplateUse(template)}
                      onRate={(rating) => handleTemplateRate(template, rating)}
                    />
                  </motion.div>
                ))}
              </div>
            ) : (
              <div className="space-y-4">
                {filteredTemplates.map((template, index) => (
                  <motion.div
                    key={template.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                  >
                    <TemplateListItem
                      template={template}
                      analytics={analytics[template.id]}
                      isFavorite={favorites.includes(template.id)}
                      onSelect={() => handleTemplateSelect(template)}
                      onPreview={() => handleTemplatePreview(template)}
                      onFavorite={() => handleTemplateFavorite(template)}
                      onUse={() => handleTemplateUse(template)}
                      onRate={(rating) => handleTemplateRate(template, rating)}
                    />
                  </motion.div>
                ))}
              </div>
            )}

            {/* Load More */}
            {hasMore && (
              <div className="flex justify-center pt-8">
                <Button
                  variant="outline"
                  onClick={loadMore}
                  disabled={loading}
                  leftIcon={loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <ChevronDown className="w-4 h-4" />}
                >
                  {loading ? "Cargando..." : "Cargar Más"}
                </Button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Preview Modal */}
      {showPreviewModal && selectedTemplate && (
        <TemplatePreviewModal
          template={selectedTemplate}
          isOpen={showPreviewModal}
          onClose={() => setShowPreviewModal(false)}
          onUse={() => handleTemplateUse(selectedTemplate)}
        />
      )}
    </div>
  );
}

// Template Card Component
interface TemplateCardProps {
  template: Template;
  analytics?: TemplateAnalytics;
  isFavorite: boolean;
  onSelect: () => void;
  onPreview: () => void;
  onFavorite: () => void;
  onUse: () => void;
  onRate: (rating: number) => void;
}

function TemplateCard({ 
  template, 
  analytics, 
  isFavorite, 
  onSelect, 
  onPreview, 
  onFavorite, 
  onUse, 
  onRate 
}: TemplateCardProps) {
  const [rating, setRating] = useState(0);
  const [showRating, setShowRating] = useState(false);

  const handleRating = (newRating: number) => {
    setRating(newRating);
    onRate(newRating);
    setShowRating(false);
  };

  const usageLevel = getUsageLevel(analytics?.usos_totales || 0);
  const UsageIcon = usageLevel.icon;

  return (
    <Card className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-all duration-200 group cursor-pointer">
      <div className="relative">
        {/* Preview Image */}
        <div className="relative h-48 bg-slate-800 overflow-hidden">
          {template.preview_url ? (
            <img
              src={template.preview_url}
              alt={template.nombre}
              className="w-full h-full object-cover transition-transform duration-200 group-hover:scale-105"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-slate-800 to-slate-900">
              <Palette className="w-12 h-12 text-slate-600" />
            </div>
          )}
          
          {/* Status Badge */}
          <div className="absolute top-3 right-3">
            <Badge variant="success" size="sm">
              <Check className="w-3 h-3 mr-1" />
              Activa
            </Badge>
          </div>

          {/* Quick Actions */}
          <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-center gap-3">
            <Button
              variant="secondary"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onPreview();
              }}
              className="bg-white/10 backdrop-blur-sm border-white/20"
            >
              <Eye className="w-4 h-4 mr-2" />
              Vista Previa
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onUse();
              }}
            >
              Usar Plantilla
            </Button>
          </div>
        </div>

        {/* Content */}
        <div className="p-4">
          <div className="space-y-3">
            {/* Header */}
            <div>
              <h3 className="font-semibold text-white mb-2 group-hover:text-primary-400 transition-colors">
                {template.nombre}
              </h3>
              {template.descripcion && (
                <p className="text-sm text-slate-400 line-clamp-2">{template.descripcion}</p>
              )}
            </div>

            {/* Tags and Metadata */}
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline" size="sm">{template.categoria}</Badge>
              {template.dias_semana && (
                <span className="text-xs text-slate-400">{template.dias_semana} días</span>
              )}
              <span className="text-xs text-slate-400">v{template.version_actual}</span>
            </div>

            {/* Analytics */}
            {analytics && (
              <div className="flex items-center justify-between text-xs text-slate-400">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1">
                    <Download className="w-3 h-3" />
                    <span>{analytics.usos_totales || 0}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Users className="w-3 h-3" />
                    <span>{analytics.usuarios_unicos || 0}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <UsageIcon className={`w-3 h-3 ${usageLevel.color}`} />
                    <span>{usageLevel.level}</span>
                  </div>
                </div>
                
                {template.rating_promedio && (
                  <div className="flex items-center gap-1">
                    {getRatingStars(Number(template.rating_promedio))}
                  </div>
                )}
              </div>
            )}

            {/* Rating Section */}
            <div className="flex items-center justify-between pt-3 border-t border-slate-700">
              <div className="flex items-center gap-2">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRating(star);
                    }}
                    className="transition-colors"
                  >
                    <Star
                      className={`w-4 h-4 ${
                        star <= rating
                          ? 'fill-yellow-400 text-yellow-400'
                          : 'text-slate-600 hover:text-yellow-300'
                      }`}
                    />
                  </button>
                ))}
              </div>

              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    onFavorite();
                  }}
                  className={isFavorite ? "text-red-400 hover:text-red-300" : "text-slate-400 hover:text-white"}
                >
                  <Heart className={`w-4 h-4 ${isFavorite ? 'fill-current' : ''}`} />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelect();
                  }}
                >
                  <Eye className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

// Template List Item Component
interface TemplateListItemProps {
  template: Template;
  analytics?: TemplateAnalytics;
  isFavorite: boolean;
  onSelect: () => void;
  onPreview: () => void;
  onFavorite: () => void;
  onUse: () => void;
  onRate: (rating: number) => void;
}

function TemplateListItem({ 
  template, 
  analytics, 
  isFavorite, 
  onSelect, 
  onPreview, 
  onFavorite, 
  onUse, 
  onRate 
}: TemplateListItemProps) {
  const [rating, setRating] = useState(0);

  const handleRating = (newRating: number) => {
    setRating(newRating);
    onRate(newRating);
  };

  return (
    <Card className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-all duration-200">
      <div className="p-6">
        <div className="flex items-start gap-4">
          {/* Preview Thumbnail */}
          <div className="w-20 h-20 bg-slate-800 rounded-lg overflow-hidden flex-shrink-0">
            {template.preview_url ? (
              <img
                src={template.preview_url}
                alt={template.nombre}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <Palette className="w-8 h-8 text-slate-600" />
              </div>
            )}
          </div>

          {/* Template Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                <h3 className="font-semibold text-white text-lg mb-2">{template.nombre}</h3>
                {template.descripcion && (
                  <p className="text-slate-400 mb-3">{template.descripcion}</p>
                )}
                
                <div className="flex items-center gap-4 text-sm text-slate-400">
                  <Badge variant="outline">{template.categoria}</Badge>
                  {template.dias_semana && (
                    <span>{template.dias_semana} días</span>
                  )}
                  <span>v{template.version_actual}</span>
                  <Badge variant="success">
                    <Check className="w-3 h-3 mr-1" />
                    Activa
                  </Badge>
                </div>
              </div>

              {/* Analytics */}
              {analytics && (
                <div className="flex items-center gap-6 text-sm text-slate-400">
                  <div className="text-center">
                    <div className="font-semibold text-white">{analytics.usos_totales || 0}</div>
                    <div className="text-xs">Usos</div>
                  </div>
                  <div className="text-center">
                    <div className="font-semibold text-white">{analytics.usuarios_unicos || 0}</div>
                    <div className="text-xs">Usuarios</div>
                  </div>
                  {template.rating_promedio && (
                    <div className="text-center">
                      <div className="font-semibold text-white">
                        {Number(template.rating_promedio).toFixed(1)}
                      </div>
                      <div className="text-xs">Rating</div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-col gap-2">
            <Button onClick={onUse} className="whitespace-nowrap">
              Usar Plantilla
            </Button>
            <div className="flex gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={onPreview}
              >
                <Eye className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={onFavorite}
                className={isFavorite ? "text-red-400 hover:text-red-300" : "text-slate-400 hover:text-white"}
              >
                <Heart className={`w-4 h-4 ${isFavorite ? 'fill-current' : ''}`} />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

// Template Preview Modal
interface TemplatePreviewModalProps {
  template: Template;
  isOpen: boolean;
  onClose: () => void;
  onUse: () => void;
}

function TemplatePreviewModal({ template, isOpen, onClose, onUse }: TemplatePreviewModalProps) {
  if (!isOpen) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={template.nombre}
      size="lg"
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>
            Cerrar
          </Button>
          <Button onClick={onUse}>
            Usar Plantilla
          </Button>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Preview Image */}
        {template.preview_url && (
          <div className="bg-slate-800 rounded-lg p-4">
            <img
              src={template.preview_url}
              alt={template.nombre}
              className="w-full rounded-lg"
            />
          </div>
        )}

        {/* Template Info */}
        <div className="space-y-4">
          <div>
            <h3 className="font-semibold text-white mb-2">Descripción</h3>
            <p className="text-slate-400">{template.descripcion || "Sin descripción disponible"}</p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <h4 className="font-medium text-white mb-2">Detalles</h4>
              <div className="space-y-1 text-sm text-slate-400">
                <div>Categoría: {template.categoria}</div>
                <div>Días: {template.dias_semana || "No especificado"}</div>
                <div>Versión: {template.version_actual}</div>
              </div>
            </div>
            
            <div>
              <h4 className="font-medium text-white mb-2">Estadísticas</h4>
              <div className="space-y-1 text-sm text-slate-400">
                <div>Usos totales: {template.uso_count}</div>
                <div>Rating: {template.rating_promedio ? Number(template.rating_promedio).toFixed(1) : "N/A"}</div>
                <div>Estado: {template.activa ? "Activa" : "Inactiva"}</div>
              </div>
            </div>
          </div>

          {template.tags && template.tags.length > 0 && (
            <div>
              <h4 className="font-medium text-white mb-2">Etiquetas</h4>
              <div className="flex flex-wrap gap-2">
                {template.tags.map((tag, index) => (
                  <Badge key={index} variant="outline" size="sm">
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}
