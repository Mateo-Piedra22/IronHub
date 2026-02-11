"use client";

import { useState } from "react";
import { 
  Star, Download, Users, Calendar, Eye, Edit, Trash2, Copy, 
  Heart, Share2, MoreVertical, ChevronRight, TrendingUp,
  Award, Zap, Clock, CheckCircle, AlertCircle, Play
} from "lucide-react";
import { Button, Badge, Dropdown, useToast } from "@/components/ui";
import { api, type Template, type TemplateAnalytics } from "@/lib/api";

interface TemplateCardProps {
  template: Template;
  analytics?: TemplateAnalytics;
  isSelected?: boolean;
  onSelect?: () => void;
  onEdit?: () => void;
  onDuplicate?: () => void;
  onDelete?: () => void;
  onView?: () => void;
  onPreview?: () => void;
  onFavorite?: () => void;
  onShare?: () => void;
  showActions?: boolean;
  compact?: boolean;
  variant?: "default" | "featured" | "minimal";
}

export function TemplateCard({
  template,
  analytics,
  isSelected = false,
  onSelect,
  onEdit,
  onDuplicate,
  onDelete,
  onView,
  onPreview,
  onFavorite,
  onShare,
  showActions = true,
  compact = false,
  variant = "default"
}: TemplateCardProps) {
  const [isFavorite, setIsFavorite] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const { success, error } = useToast();

  const handleFavorite = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsFavorite(!isFavorite);
    onFavorite?.();
    
    // Here you would typically call an API to update favorite status
    try {
      await api.toggleTemplateFavorite(template.id);
      success(isFavorite ? "Eliminado de favoritos" : "Añadido a favoritos");
    } catch (err) {
      console.error("Failed to toggle favorite:", err);
    }
  };

  const handleShare = async (e: React.MouseEvent) => {
    e.stopPropagation();
    onShare?.();
    
    try {
      const shareUrl = `${window.location.origin}/templates/${template.id}`;
      if (navigator.share) {
        await navigator.share({
          title: template.nombre,
          text: template.descripcion,
          url: shareUrl
        });
      } else {
        await navigator.clipboard.writeText(shareUrl);
        success("Enlace copiado al portapapeles");
      }
    } catch (err) {
      console.error("Share failed:", err);
      error("Error al compartir plantilla");
    }
  };

  const handleQuickPreview = (e: React.MouseEvent) => {
    e.stopPropagation();
    onPreview?.();
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

  getUsageLevel = (usos: number) => {
    if (usos > 100) return { level: "Alto", color: "text-green-400", icon: TrendingUp };
    if (usos > 50) return { level: "Medio", color: "text-yellow-400", icon: Users };
    return { level: "Bajo", color: "text-slate-400", icon: Clock };
  };

  const usageLevel = getUsageLevel(analytics?.usos_totales || 0);
  const UsageIcon = usageLevel.icon;

  if (variant === "minimal") {
    return (
      <div
        className={`bg-slate-800 rounded-lg border p-3 transition-all duration-200 hover:border-slate-600 cursor-pointer ${
          isSelected ? 'border-primary-500 ring-2 ring-primary-500/50' : 'border-slate-700'
        }`}
        onClick={onView}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-slate-900 rounded-lg overflow-hidden flex-shrink-0">
            {template.preview_url && !imageError ? (
              <img
                src={template.preview_url}
                alt={template.nombre}
                className="w-full h-full object-cover"
                onLoad={() => setImageLoaded(true)}
                onError={() => setImageError(true)}
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <div className="w-6 h-6 bg-slate-700 rounded" />
              </div>
            )}
          </div>
          
          <div className="flex-1 min-w-0">
            <h3 className="font-medium text-white truncate">{template.nombre}</h3>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="outline" size="sm">{template.categoria}</Badge>
              {template.dias_semana && (
                <span className="text-xs text-slate-400">{template.dias_semana} días</span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {analytics?.usos_totales && (
              <div className="flex items-center gap-1 text-xs text-slate-400">
                <Download className="w-3 h-3" />
                <span>{analytics.usos_totales}</span>
              </div>
            )}
            
            {showActions && (
              <Dropdown
                trigger={
                  <Button variant="ghost" size="sm">
                    <MoreVertical className="w-4 h-4" />
                  </Button>
                }
                items={[
                  { label: "Ver detalles", onClick: onView, icon: Eye },
                  { label: "Editar", onClick: onEdit, icon: Edit },
                  { label: "Duplicar", onClick: onDuplicate, icon: Copy },
                  { label: "Eliminar", onClick: onDelete, icon: Trash2, variant: "danger" }
                ]}
              />
            )}
          </div>
        </div>
      </div>
    );
  }

  if (variant === "featured") {
    return (
      <div
        className={`relative bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl border overflow-hidden transition-all duration-300 hover:border-slate-600 hover:shadow-xl hover:shadow-primary-500/10 cursor-pointer group ${
          isSelected ? 'border-primary-500 ring-2 ring-primary-500/50' : 'border-slate-700'
        }`}
        onClick={onView}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        {/* Featured Badge */}
        <div className="absolute top-3 left-3 z-10">
          <Badge variant="warning" className="bg-gradient-to-r from-yellow-500 to-orange-500">
            <Award className="w-3 h-3 mr-1" />
            Destacada
          </Badge>
        </div>

        {/* Selection Checkbox */}
        {onSelect && (
          <div className="absolute top-3 right-3 z-10">
            <input
              type="checkbox"
              checked={isSelected}
              onChange={onSelect}
              className="w-4 h-4 rounded border-slate-600 bg-slate-900 text-primary-500 focus:ring-primary-500/50"
            />
          </div>
        )}

        {/* Preview Image */}
        <div className="relative h-48 bg-slate-900 overflow-hidden">
          {template.preview_url && !imageError ? (
            <>
              <img
                src={template.preview_url}
                alt={template.nombre}
                className={`w-full h-full object-cover transition-transform duration-300 ${
                  isHovered ? 'scale-105' : 'scale-100'
                }`}
                onLoad={() => setImageLoaded(true)}
                onError={() => setImageError(true)}
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent" />
            </>
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-slate-800 to-slate-900">
              <div className="text-center">
                <div className="w-16 h-16 bg-slate-700 rounded-xl mx-auto mb-2 flex items-center justify-center">
                  <div className="w-8 h-8 bg-slate-600 rounded" />
                </div>
                <span className="text-slate-500 text-sm">Sin vista previa</span>
              </div>
            </div>
          )}

          {/* Quick Actions Overlay */}
          {showActions && isHovered && (
            <div className="absolute inset-0 bg-black/60 flex items-center justify-center gap-3">
              <Button
                variant="secondary"
                size="sm"
                onClick={handleQuickPreview}
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
                  onEdit?.();
                }}
              >
                <Edit className="w-4 h-4 mr-2" />
                Editar
              </Button>
            </div>
          )}
        </div>

        {/* Content */}
        <div className="p-6">
          <div className="space-y-4">
            {/* Header */}
            <div>
              <h3 className="font-bold text-xl text-white mb-2 group-hover:text-primary-400 transition-colors">
                {template.nombre}
              </h3>
              {template.descripcion && (
                <p className="text-slate-300 line-clamp-2">{template.descripcion}</p>
              )}
            </div>

            {/* Tags and Metadata */}
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline">{template.categoria}</Badge>
              {template.dias_semana && (
                <Badge variant="secondary">{template.dias_semana} días</Badge>
              )}
              <Badge variant="outline">v{template.version_actual}</Badge>
              {template.activa ? (
                <Badge variant="success">
                  <CheckCircle className="w-3 h-3 mr-1" />
                  Activa
                </Badge>
              ) : (
                <Badge variant="secondary">
                  <AlertCircle className="w-3 h-3 mr-1" />
                  Inactiva
                </Badge>
              )}
            </div>

            {/* Analytics Bar */}
            {analytics && (
              <div className="bg-slate-800/50 rounded-lg p-4">
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <div className="flex items-center justify-center gap-1 text-lg font-semibold text-white">
                      <Download className="w-4 h-4 text-blue-400" />
                      {analytics.usos_totales || 0}
                    </div>
                    <div className="text-xs text-slate-400">Usos</div>
                  </div>
                  <div>
                    <div className="flex items-center justify-center gap-1 text-lg font-semibold text-white">
                      <Users className="w-4 h-4 text-green-400" />
                      {analytics.usuarios_unicos || 0}
                    </div>
                    <div className="text-xs text-slate-400">Usuarios</div>
                  </div>
                  <div>
                    <div className="flex items-center justify-center gap-1">
                      {getRatingStars(Number(template.rating_promedio) || 0)}
                    </div>
                    <div className="text-xs text-slate-400">
                      {template.rating_promedio ? Number(template.rating_promedio).toFixed(1) : "N/A"}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Action Bar */}
            {showActions && (
              <div className="flex items-center justify-between pt-4 border-t border-slate-700">
                <div className="flex gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleFavorite}
                    className={isFavorite ? "text-red-400 hover:text-red-300" : "text-slate-400 hover:text-white"}
                  >
                    <Heart className={`w-4 h-4 ${isFavorite ? 'fill-current' : ''}`} />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleShare}
                    className="text-slate-400 hover:text-white"
                  >
                    <Share2 className="w-4 h-4" />
                  </Button>
                </div>

                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDuplicate?.();
                    }}
                  >
                    <Copy className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      onView?.();
                    }}
                  >
                    Ver Detalles
                    <ChevronRight className="w-4 h-4 ml-1" />
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Default variant
  return (
    <div
      className={`bg-slate-800 rounded-xl border overflow-hidden transition-all duration-200 hover:border-slate-600 hover:shadow-lg cursor-pointer ${
        isSelected ? 'border-primary-500 ring-2 ring-primary-500/50' : 'border-slate-700'
      } ${compact ? 'p-4' : ''}`}
      onClick={onView}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Selection Checkbox */}
      {onSelect && (
        <div className="absolute top-3 left-3 z-10">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={onSelect}
            className="w-4 h-4 rounded border-slate-600 bg-slate-900 text-primary-500 focus:ring-primary-500/50"
          />
        </div>
      )}

      {/* Preview Image */}
      <div className="relative h-32 bg-slate-900">
        {template.preview_url && !imageError ? (
          <>
            <img
              src={template.preview_url}
              alt={template.nombre}
              className={`w-full h-full object-cover transition-transform duration-200 ${
                isHovered ? 'scale-105' : 'scale-100'
              }`}
              onLoad={() => setImageLoaded(true)}
              onError={() => setImageError(true)}
            />
            
            {/* Status Badge */}
            <div className="absolute top-3 right-3">
              <Badge variant={template.activa ? "success" : "secondary"} size="sm">
                {template.activa ? "Activa" : "Inactiva"}
              </Badge>
            </div>

            {/* Quick Preview Button */}
            {showActions && isHovered && onPreview && (
              <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleQuickPreview}
                  className="bg-white/10 backdrop-blur-sm border-white/20"
                >
                  <Eye className="w-4 h-4 mr-2" />
                  Vista Previa
                </Button>
              </div>
            )}
          </>
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <div className="text-center">
              <div className="w-12 h-12 bg-slate-700 rounded-lg mx-auto mb-2 flex items-center justify-center">
                <div className="w-6 h-6 bg-slate-600 rounded" />
              </div>
              <span className="text-slate-500 text-xs">Sin vista previa</span>
            </div>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        <div className="space-y-3">
          {/* Header */}
          <div>
            <h3 className="font-semibold text-white truncate mb-1">{template.nombre}</h3>
            {template.descripcion && !compact && (
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
          {analytics && !compact && (
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

          {/* Actions */}
          {showActions && (
            <div className="flex gap-2 pt-2 border-t border-slate-700">
              <Button
                variant="secondary"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onView?.();
                }}
                className="flex-1"
              >
                <Eye className="w-3 h-3 mr-1" />
                Ver
              </Button>
              
              {!compact && (
                <>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      onEdit?.();
                    }}
                  >
                    <Edit className="w-3 h-3" />
                  </Button>
                  
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDuplicate?.();
                    }}
                  >
                    <Copy className="w-3 h-3" />
                  </Button>
                  
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete?.();
                    }}
                  >
                    <Trash2 className="w-3 h-3" />
                  </Button>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
