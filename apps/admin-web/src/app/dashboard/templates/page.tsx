"use client";

import { useCallback, useEffect, useState, type ChangeEvent } from "react";
import { Grid, Plus, RefreshCw, Star, Users } from "lucide-react";
import { Button, Select, useToast, Card } from "@/components/ui";
import { api, type Template, type TemplateStats } from "@/lib/api";
import { TemplateGallery } from "@/components/TemplateGallery";
import { TemplateEditor } from "@/components/TemplateEditor";
import { TemplatePreview } from "@/components/TemplatePreview";

type TimeRange = "7d" | "30d" | "90d" | "1y" | "all";

export default function TemplatesPage() {
  const [stats, setStats] = useState<TemplateStats | null>(null);
  const [timeRange, setTimeRange] = useState<TimeRange>("30d");

  // Modal states
  const [showEditor, setShowEditor] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [isCreatingNew, setIsCreatingNew] = useState(false);

  const { success } = useToast();

  const loadStats = useCallback(async () => {
    try {
      const response = await api.getTemplateStats(timeRange);
      if (response.ok && response.data?.success) {
        setStats(response.data.stats);
      }
    } catch {}
  }, [timeRange]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  const handleRefresh = () => {
    loadStats();
  };

  const handleTemplateSelect = (template: Template) => {
    setSelectedTemplate(template);
    setShowPreview(true);
  };

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

  const handleTemplateSave = (_template: Template) => {
    success(`Plantilla ${isCreatingNew ? "creada" : "actualizada"} exitosamente`);
    setShowEditor(false);
    loadStats();
  };

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
          <Select
            value={timeRange}
            onChange={(e: ChangeEvent<HTMLSelectElement>) => setTimeRange(e.target.value as TimeRange)}
            placeholder="Período"
            className="w-36"
            options={[
              { value: "7d", label: "7 días" },
              { value: "30d", label: "30 días" },
              { value: "90d", label: "90 días" },
              { value: "1y", label: "1 año" },
              { value: "all", label: "Todo" }
            ]}
          />
          <Button
            onClick={handleRefresh}
            variant="secondary"
            size="sm"
            leftIcon={<RefreshCw className="w-4 h-4" />}
          >
            Actualizar
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
              <div className="w-12 h-12 bg-green-500/20 rounded-lg flex items-center justify-center" />
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

      {/* Templates Gallery — component manages its own data loading, filtering, pagination */}
      <TemplateGallery
        onTemplateSelect={handleTemplateSelect}
        onTemplateEdit={handleTemplateEdit}
        onTemplateCreate={handleTemplateCreate}
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
