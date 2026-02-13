"use client";

import { useCallback, useEffect, useState, type ChangeEvent } from "react";
import { Grid, Plus, RefreshCw, Star, Users, Upload } from "lucide-react";
import { Button, Select, useToast, Card, Modal, Input, Toggle } from "@/components/ui";
import { api, type Gym, type Template, type TemplateStats } from "@/lib/api";
import { TemplateGallery } from "@/components/TemplateGallery";
import { TemplateEditor } from "@/components/TemplateEditor";
import { TemplatePreview } from "@/components/TemplatePreview";

type TimeRange = "7d" | "30d" | "90d" | "1y" | "all";

export default function TemplatesPage() {
  const [gyms, setGyms] = useState<Gym[]>([]);
  const [selectedGymId, setSelectedGymId] = useState<number | null>(null);
  const [stats, setStats] = useState<TemplateStats | null>(null);
  const [timeRange, setTimeRange] = useState<TimeRange>("30d");
  const [galleryKey, setGalleryKey] = useState(0);

  // Modal states
  const [showEditor, setShowEditor] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [showImportExcel, setShowImportExcel] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [isCreatingNew, setIsCreatingNew] = useState(false);
  const [excelFile, setExcelFile] = useState<File | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [importNombre, setImportNombre] = useState("");
  const [importDescripcion, setImportDescripcion] = useState("");
  const [importCategoria, setImportCategoria] = useState("");
  const [importTags, setImportTags] = useState("");
  const [importPublica, setImportPublica] = useState(false);
  const [importActiva, setImportActiva] = useState(true);
  const [replaceDefaults, setReplaceDefaults] = useState(true);
  const [importLoading, setImportLoading] = useState(false);

  const { success, error } = useToast();

  const loadGyms = useCallback(async () => {
    try {
      const pageSize = 100;
      let page = 1;
      let all: Gym[] = [];
      let total = 0;
      while (true) {
        const res = await api.getGyms({ page, page_size: pageSize });
        if (!res.ok || !res.data?.gyms) {
          error(res.error || "Error al cargar gimnasios");
          return;
        }
        const items = Array.isArray(res.data.gyms) ? res.data.gyms : [];
        total = Number(res.data.total || total);
        all = [...all, ...items];
        if (!items.length) break;
        if (total && all.length >= total) break;
        if (items.length < pageSize) break;
        page += 1;
      }
      setGyms(all);

      const stored = typeof window !== "undefined" ? window.localStorage.getItem("ironhub_admin_selected_gym_id") : null;
      const storedId = stored ? Number(stored) : 0;
      const fallbackId = all[0]?.id ? Number(all[0].id) : 0;
      const effectiveId = (storedId && all.some((g) => g.id === storedId)) ? storedId : fallbackId;
      if (effectiveId) {
        setSelectedGymId(effectiveId);
        if (typeof window !== "undefined") window.localStorage.setItem("ironhub_admin_selected_gym_id", String(effectiveId));
      } else {
        setSelectedGymId(null);
      }
    } catch {
      error("Error al cargar gimnasios");
    }
  }, [error]);

  const loadStats = useCallback(async () => {
    try {
      if (!selectedGymId) return;
      const response = await api.getTemplateStats(timeRange);
      if (response.ok && response.data?.success) {
        setStats(response.data.stats);
      }
    } catch {}
  }, [timeRange, selectedGymId]);

  useEffect(() => {
    loadGyms();
  }, [loadGyms]);

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

  const resetImportForm = () => {
    setExcelFile(null);
    setImageFile(null);
    setImportNombre("");
    setImportDescripcion("");
    setImportCategoria("");
    setImportTags("");
    setImportPublica(false);
    setImportActiva(true);
    setReplaceDefaults(true);
  };

  const handleImportExcel = async () => {
    if (!selectedGymId) return;
    if (!excelFile) {
      error("Seleccioná un archivo Excel");
      return;
    }
    setImportLoading(true);
    try {
      const res = await api.importExcelTemplate({
        excel_file: excelFile,
        image_file: imageFile || undefined,
        nombre: importNombre || undefined,
        descripcion: importDescripcion || undefined,
        categoria: importCategoria || undefined,
        tags: importTags || undefined,
        publica: importPublica,
        activa: importActiva,
        replace_defaults: replaceDefaults,
      });
      if (!res.ok || !res.data?.success) {
        error(res.error || "No se pudo importar el Excel");
        return;
      }
      success("Template importado correctamente");
      setShowImportExcel(false);
      resetImportForm();
      setGalleryKey((prev) => prev + 1);
      loadStats();
    } catch {
      error("No se pudo importar el Excel");
    } finally {
      setImportLoading(false);
    }
  };

  const handleOpenImport = () => {
    resetImportForm();
    setShowImportExcel(true);
  };

  const handleTemplateSave = (_template: Template) => {
    success(`Template ${isCreatingNew ? "creado" : "actualizado"} exitosamente`);
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
            Administra y personaliza templates de exportación de rutinas
          </p>
        </div>

        <div className="flex gap-3">
          <Select
            value={selectedGymId ? String(selectedGymId) : ""}
            onChange={(e: ChangeEvent<HTMLSelectElement>) => {
              const next = Number(e.target.value) || 0;
              if (!next) return;
              setSelectedGymId(next);
              if (typeof window !== "undefined") window.localStorage.setItem("ironhub_admin_selected_gym_id", String(next));
              setStats(null);
              loadStats();
            }}
            placeholder="Gimnasio"
            className="w-60"
            options={[
              { value: "", label: gyms.length ? "Seleccionar gimnasio…" : "Sin gimnasios" },
              ...gyms.map((g) => ({ value: String(g.id), label: `${g.nombre} (ID: ${g.id})` })),
            ]}
          />
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
            disabled={!selectedGymId}
          >
            Actualizar
          </Button>
          <Button
            onClick={handleOpenImport}
            variant="secondary"
            leftIcon={<Upload className="w-4 h-4" />}
            disabled={!selectedGymId}
          >
            Importar Excel
          </Button>
          <Button
            onClick={handleTemplateCreate}
            leftIcon={<Plus className="w-4 h-4" />}
            disabled={!selectedGymId}
          >
            Nuevo Template
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

      {selectedGymId ? (
        <TemplateGallery
          key={galleryKey}
          onTemplateSelect={handleTemplateSelect}
          onTemplateEdit={handleTemplateEdit}
          onTemplateCreate={handleTemplateCreate}
        />
      ) : (
        <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-6 text-slate-300">
          Seleccioná un gimnasio para administrar sus templates.
        </div>
      )}

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

      <Modal
        isOpen={showImportExcel}
        onClose={() => setShowImportExcel(false)}
        title="Importar plantilla desde Excel"
        description="Subí el archivo Excel y opcionalmente una imagen de logo."
        size="lg"
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => setShowImportExcel(false)}
              disabled={importLoading}
            >
              Cancelar
            </Button>
            <Button onClick={handleImportExcel} disabled={importLoading || !excelFile}>
              {importLoading ? "Importando..." : "Importar"}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="space-y-2">
            <div className="text-sm text-slate-300">Archivo Excel</div>
            <input
              type="file"
              accept=".xlsx,.xls"
              className="block w-full text-sm text-slate-300 file:mr-4 file:rounded-lg file:border-0 file:bg-slate-800 file:px-4 file:py-2 file:text-sm file:text-white hover:file:bg-slate-700"
              onChange={(e) => setExcelFile(e.target.files?.[0] || null)}
            />
          </div>
          <div className="space-y-2">
            <div className="text-sm text-slate-300">Logo (opcional)</div>
            <input
              type="file"
              accept="image/*"
              className="block w-full text-sm text-slate-300 file:mr-4 file:rounded-lg file:border-0 file:bg-slate-800 file:px-4 file:py-2 file:text-sm file:text-white hover:file:bg-slate-700"
              onChange={(e) => setImageFile(e.target.files?.[0] || null)}
            />
          </div>
          <Input
            label="Nombre"
            value={importNombre}
            onChange={(e) => setImportNombre(e.target.value)}
            placeholder="Plantilla Excel Importada"
          />
          <Input
            label="Descripción"
            value={importDescripcion}
            onChange={(e) => setImportDescripcion(e.target.value)}
            placeholder="Descripción opcional"
          />
          <Input
            label="Categoría"
            value={importCategoria}
            onChange={(e) => setImportCategoria(e.target.value)}
            placeholder="general"
          />
          <Input
            label="Tags"
            value={importTags}
            onChange={(e) => setImportTags(e.target.value)}
            placeholder="fuerza, hipertrofia"
          />
          <div className="flex flex-wrap gap-6">
            <Toggle checked={importPublica} onChange={setImportPublica} label="Pública" />
            <Toggle checked={importActiva} onChange={setImportActiva} label="Activa" />
            <Toggle checked={replaceDefaults} onChange={setReplaceDefaults} label="Reemplazar plantillas por defecto" />
          </div>
        </div>
      </Modal>
    </div>
  );
}
