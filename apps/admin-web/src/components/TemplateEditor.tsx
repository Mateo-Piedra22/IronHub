"use client";

import { useState, useEffect, useCallback, useRef, type ChangeEvent } from "react";
import dynamic from "next/dynamic";
import Image from "next/image";
import { 
  Save, Eye, Download, Upload, RefreshCw, 
  FileText, Code, Check, AlertTriangle,
  RotateCcw, ZoomIn, ZoomOut, Maximize2
} from "lucide-react";
import { Badge, Button, Input, Modal, Select, Toggle, useToast } from "@/components/ui";
import { api, type Template, type TemplateConfig, type TemplateValidation, type TemplateVersion } from "@/lib/api";
import type * as Monaco from "monaco-editor";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

interface TemplateEditorProps {
  template?: Template;
  isOpen: boolean;
  onClose: () => void;
  onSave: (template: Template) => void;
  isNew?: boolean;
}

export function TemplateEditor({ template, isOpen, onClose, onSave, isNew = false }: TemplateEditorProps) {
  const [activeTab, setActiveTab] = useState<"config" | "preview" | "validation" | "versions">("config");
  const [saving, setSaving] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [validation, setValidation] = useState<TemplateValidation | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string>("");
  const [previewScale, setPreviewScale] = useState(1);
  const monacoRef = useRef<typeof import("monaco-editor") | null>(null);
  const editorRef = useRef<Monaco.editor.IStandaloneCodeEditor | null>(null);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [versions, setVersions] = useState<TemplateVersion[]>([]);
  const [newVersionLabel, setNewVersionLabel] = useState("");
  const [newVersionDesc, setNewVersionDesc] = useState("");
  
  // Template data
  const [templateData, setTemplateData] = useState<Partial<Template>>({
    nombre: "",
    descripcion: "",
    categoria: "general",
    dias_semana: undefined,
    configuracion: getDefaultTemplateConfig(),
    activa: true,
    publica: false,
    tags: []
  });

  // Editor states
  const [configJson, setConfigJson] = useState<string>("");
  const [autoSave, setAutoSave] = useState(false);
  
  const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);
  const { success, error } = useToast();

  // Initialize template data
  useEffect(() => {
    if (template && !isNew) {
      setTemplateData({
        nombre: template.nombre,
        descripcion: template.descripcion || "",
        categoria: template.categoria || "general",
        dias_semana: template.dias_semana,
        configuracion: template.configuracion,
        activa: template.activa,
        publica: template.publica,
        tags: template.tags || []
      });
      setConfigJson(JSON.stringify(template.configuracion, null, 2));
    } else if (isNew) {
      const defaultConfig = getDefaultTemplateConfig();
      setTemplateData(prev => ({ ...prev, configuracion: defaultConfig }));
      setConfigJson(JSON.stringify(defaultConfig, null, 2));
    }
  }, [template, isNew]);

  const handleAutoSave = useCallback(async () => {
    if (!template || isNew) return;

    try {
      const updatedConfig = JSON.parse(configJson);
      const response = await api.updateTemplate(template.id, {
        ...templateData,
        configuracion: updatedConfig
      });

      if (response.ok && response.data?.success) {
        return;
      }
    } catch {
      return;
    }
  }, [configJson, isNew, template, templateData]);

  // Auto-save functionality
  useEffect(() => {
    if (autoSave && !isNew && configJson) {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
      
      autoSaveTimerRef.current = setTimeout(() => {
        handleAutoSave();
      }, 2000); // Auto-save after 2 seconds of inactivity
    }

    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
  }, [autoSave, configJson, handleAutoSave, isNew]);

  const validateTemplate = useCallback(async (config?: TemplateConfig) => {
    const configToValidate = config || templateData.configuracion;
    if (!configToValidate) return;

    try {
      const response = await api.validateTemplate(configToValidate);
      if (response.ok && response.data?.success) {
        setValidation(response.data.validation);
      }
    } catch {}
  }, [templateData.configuracion]);

  const setEditorMarkers = useCallback((markers: Monaco.editor.IMarkerData[]) => {
    const monaco = monacoRef.current;
    const editor = editorRef.current;
    if (!monaco || !editor) return;
    const model = editor.getModel?.();
    if (!model) return;
    monaco.editor.setModelMarkers(model, "template-config", markers);
  }, []);

  const showJsonParseError = useCallback((err: unknown) => {
    const message = err instanceof Error ? err.message : "JSON inválido";
    setValidation({ is_valid: false, errors: [{ message }], warnings: [] });
    const editor = editorRef.current;
    if (!editor) {
      return;
    }
    const model = editor.getModel?.();
    if (!model) {
      return;
    }
    let start = { lineNumber: 1, column: 1 };
    const m = message.match(/position\s+(\d+)/i);
    if (m?.[1]) {
      const pos = Number(m[1]);
      if (Number.isFinite(pos) && pos >= 0) {
        start = model.getPositionAt(pos);
      }
    }
    setEditorMarkers([
      {
        severity: monacoRef.current?.MarkerSeverity?.Error ?? 8,
        message,
        startLineNumber: start.lineNumber,
        startColumn: start.column,
        endLineNumber: start.lineNumber,
        endColumn: Math.max(start.column + 1, start.column),
      },
    ]);
  }, [setEditorMarkers]);

  const handleConfigChange = useCallback((value: string | undefined) => {
    if (value !== undefined) {
      setConfigJson(value);
      try {
        const parsed = JSON.parse(value);
        setEditorMarkers([]);
        setTemplateData(prev => ({ ...prev, configuracion: parsed }));
        validateTemplate(parsed);
      } catch (e) {
        showJsonParseError(e);
      }
    }
  }, [setEditorMarkers, showJsonParseError, validateTemplate]);

  const handleSave = async () => {
    if (!templateData.nombre?.trim()) {
      error("El nombre de la plantilla es requerido");
      return;
    }

    try {
      const finalConfig = JSON.parse(configJson);
      const validationRes = await api.validateTemplate(finalConfig);
      if (validationRes.ok && validationRes.data?.success) {
        setValidation(validationRes.data.validation);
        if (!validationRes.data.validation.is_valid) {
          error("La configuración tiene errores de validación");
          setActiveTab("validation");
          return;
        }
      } else {
        error("Error al validar la configuración");
        return;
      }
      setSaving(true);

      const payload = {
        ...templateData,
        configuracion: finalConfig
      };

      let response;
      if (isNew) {
        response = await api.createTemplate(payload);
      } else {
        response = await api.updateTemplate(template!.id, payload);
      }

      if (response.ok && response.data?.success) {
        success(`Plantilla ${isNew ? "creada" : "actualizada"} exitosamente`);
        onSave(response.data.template);
        onClose();
      } else {
        error(`Error al ${isNew ? "crear" : "actualizar"} plantilla`);
      }
    } catch (err) {
      console.error("Save failed:", err);
      error("Error al guardar plantilla");
    } finally {
      setSaving(false);
    }
  };

  const handlePreview = async () => {
    if (!templateData.configuracion) return;

    try {
      setPreviewLoading(true);
      const previewRequest = {
        format: "pdf",
        quality: "medium",
        page_number: 1,
      } as const;
      const response = await api.getTemplatePreviewFromConfig(templateData.configuracion, previewRequest);
      
      if (response.ok && response.data?.success) {
        setPreviewUrl(response.data.preview_url || "");
        setActiveTab("preview");
      } else {
        error("Error al generar vista previa");
      }
    } catch (err) {
      console.error("Preview generation failed:", err);
      error("Error al generar vista previa");
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleExportTemplate = () => {
    const dataStr = JSON.stringify(templateData, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `${templateData.nombre || 'template'}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  const handleImportTemplate = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const content = e.target?.result as string;
        const imported = JSON.parse(content);
        
        setTemplateData({
          nombre: imported.nombre || "",
          descripcion: imported.descripcion || "",
          categoria: imported.categoria || "general",
          dias_semana: imported.dias_semana || undefined,
          configuracion: imported.configuracion || getDefaultTemplateConfig(),
          activa: imported.activa !== false,
          publica: imported.publica || false,
          tags: imported.tags || []
        });
        
        setConfigJson(JSON.stringify(imported.configuracion || getDefaultTemplateConfig(), null, 2));
        success("Plantilla importada exitosamente");
      } catch {
        error("Error al importar plantilla: formato inválido");
      }
    };
    reader.readAsText(file);
  };

  const handleResetToDefault = () => {
    if (!confirm("¿Estás seguro de restablecer la configuración a los valores por defecto?")) {
      return;
    }

    const defaultConfig = getDefaultTemplateConfig();
    setConfigJson(JSON.stringify(defaultConfig, null, 2));
    setTemplateData(prev => ({ ...prev, configuracion: defaultConfig }));
  };

  const loadVersions = useCallback(async () => {
    if (!template || isNew) return;
    setVersionsLoading(true);
    try {
      const res = await api.getTemplateVersions(template.id);
      if (res.ok && res.data?.success) {
        setVersions(res.data.versions || []);
      }
    } catch {
    } finally {
      setVersionsLoading(false);
    }
  }, [isNew, template]);

  useEffect(() => {
    if (!isOpen) return;
    if (activeTab !== "versions") return;
    loadVersions();
  }, [activeTab, isOpen, loadVersions]);

  const handleCreateVersion = async () => {
    if (!template || isNew) return;
    try {
      const cfg = JSON.parse(configJson) as TemplateConfig;
      const res = await api.createTemplateVersion(template.id, {
        version: newVersionLabel || undefined,
        descripcion: newVersionDesc || undefined,
        configuracion: cfg,
      });
      if (res.ok && res.data?.success) {
        success("Versión creada");
        setNewVersionLabel("");
        setNewVersionDesc("");
        await loadVersions();
      } else {
        error("Error creando versión");
      }
    } catch (e) {
      showJsonParseError(e);
    }
  };

  const handleRestoreVersion = async (version: string) => {
    if (!template || isNew) return;
    if (!confirm(`¿Restaurar a la versión ${version}?`)) return;
    try {
      const res = await api.restoreTemplateVersion(template.id, version);
      if (res.ok && res.data?.success) {
        success(`Restaurada a ${version}`);
        const refreshed = await api.getTemplate(template.id);
        if (refreshed.ok && refreshed.data?.success) {
          setTemplateData({
            nombre: refreshed.data.template.nombre,
            descripcion: refreshed.data.template.descripcion || "",
            categoria: refreshed.data.template.categoria || "general",
            dias_semana: refreshed.data.template.dias_semana,
            configuracion: refreshed.data.template.configuracion,
            activa: refreshed.data.template.activa,
            publica: refreshed.data.template.publica,
            tags: refreshed.data.template.tags || [],
          });
          setConfigJson(JSON.stringify(refreshed.data.template.configuracion, null, 2));
        }
        await loadVersions();
      } else {
        error("Error restaurando versión");
      }
    } catch {
      error("Error restaurando versión");
    }
  };

  const getCategoryOptions = () => [
    { value: "general", label: "General" },
    { value: "fuerza", label: "Fuerza" },
    { value: "cardio", label: "Cardio" },
    { value: "hiit", label: "HIIT" },
    { value: "funcional", label: "Funcional" },
    { value: "yoga", label: "Yoga" },
    { value: "pilates", label: "Pilates" },
    { value: "crossfit", label: "CrossFit" },
    { value: "rehabilitacion", label: "Rehabilitación" },
    { value: "deportivo", label: "Deportivo" }
  ];

  const getValidationStatus = (): { type: "error" | "warning" | "success"; message: string } | null => {
    if (!validation) return null;
    
    if (validation.errors.length > 0) {
      return { type: "error", message: `${validation.errors.length} error(es)` };
    } else if (validation.warnings.length > 0) {
      return { type: "warning", message: `${validation.warnings.length} advertencia(s)` };
    } else {
      return { type: "success", message: "Configuración válida" };
    }
  };

  const validationStatus = getValidationStatus();

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isNew ? "Nueva Plantilla" : "Editar Plantilla"}
      size="full"
      className="template-editor-modal"
      footer={
        <div className="flex justify-between items-center w-full">
          <div className="flex gap-3">
            {validationStatus && (
              <Badge variant={validationStatus.type}>
                {validationStatus.type === "error" && <AlertTriangle className="w-3 h-3 mr-1" />}
                {validationStatus.type === "warning" && <AlertTriangle className="w-3 h-3 mr-1" />}
                {validationStatus.type === "success" && <Check className="w-3 h-3 mr-1" />}
                {validationStatus.message}
              </Badge>
            )}
            {autoSave && !isNew && (
              <Badge variant="secondary">
                <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                Auto-guardado
              </Badge>
            )}
          </div>
          
          <div className="flex gap-3">
            <Button variant="secondary" onClick={onClose}>
              Cancelar
            </Button>
            <Button
              onClick={handleSave}
              disabled={saving || !templateData.nombre?.trim() || (validation?.errors?.length ?? 0) > 0}
              leftIcon={saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            >
              {saving ? "Guardando..." : (isNew ? "Crear" : "Guardar")}
            </Button>
          </div>
        </div>
      }
    >
      <div className="flex flex-col h-full">
        {/* Header Actions */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <div className="flex gap-3">
            <Button
              variant={activeTab === "config" ? "primary" : "secondary"}
              size="sm"
              onClick={() => setActiveTab("config")}
            >
              <Code className="w-4 h-4 mr-2" />
              Configuración
            </Button>
            <Button
              variant={activeTab === "preview" ? "primary" : "secondary"}
              size="sm"
              onClick={() => setActiveTab("preview")}
            >
              <Eye className="w-4 h-4 mr-2" />
              Vista Previa
            </Button>
            <Button
              variant={activeTab === "validation" ? "primary" : "secondary"}
              size="sm"
              onClick={() => setActiveTab("validation")}
            >
              <Check className="w-4 h-4 mr-2" />
              Validación
            </Button>
            <Button
              variant={activeTab === "versions" ? "primary" : "secondary"}
              size="sm"
              onClick={() => setActiveTab("versions")}
              disabled={!template || isNew}
            >
              <FileText className="w-4 h-4 mr-2" />
              Versiones
            </Button>
          </div>

          <div className="flex gap-2">
            {/* Editor Settings */}
            <div className="flex items-center gap-3 px-3 border-l border-r border-slate-700">
              <Toggle
                checked={autoSave}
                onChange={setAutoSave}
                disabled={isNew}
                label="Auto-guardar"
              />
            </div>

            {/* Template Actions */}
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={handlePreview}
                disabled={previewLoading}
                leftIcon={previewLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />}
              >
                Vista Previa
              </Button>
              
              <Button
                variant="secondary"
                size="sm"
                onClick={handleExportTemplate}
              >
                <Download className="w-4 h-4" />
              </Button>

              <label className="cursor-pointer">
                <Button variant="secondary" size="sm" asChild>
                  <span>
                    <Upload className="w-4 h-4" />
                  </span>
                </Button>
                <input
                  type="file"
                  accept=".json"
                  onChange={handleImportTemplate}
                  className="hidden"
                />
              </label>

              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  editorRef.current?.getAction?.("editor.action.formatDocument")?.run?.();
                }}
              >
                <Code className="w-4 h-4" />
              </Button>

              <Button
                variant="secondary"
                size="sm"
                onClick={handleResetToDefault}
              >
                <RotateCcw className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {activeTab === "config" && (
            <div className="grid grid-cols-1 lg:grid-cols-4 h-full">
              {/* Template Metadata */}
              <div className="lg:col-span-1 p-6 border-r border-slate-700 space-y-4 overflow-y-auto">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Nombre *
                  </label>
                  <Input
                    value={templateData.nombre || ""}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => setTemplateData(prev => ({ ...prev, nombre: e.target.value }))}
                    placeholder="Nombre de la plantilla"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Descripción
                  </label>
                  <textarea
                    className="w-full px-4 py-3 rounded-xl bg-slate-900 border border-slate-800 text-white focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 resize-none"
                    rows={3}
                    value={templateData.descripcion || ""}
                    onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setTemplateData(prev => ({ ...prev, descripcion: e.target.value }))}
                    placeholder="Descripción de la plantilla"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Categoría
                  </label>
                  <Select
                    value={templateData.categoria || "general"}
                    onChange={(e: ChangeEvent<HTMLSelectElement>) => setTemplateData(prev => ({ ...prev, categoria: e.target.value }))}
                    options={getCategoryOptions()}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Días de la semana
                  </label>
                  <Select
                    value={templateData.dias_semana?.toString() || ""}
                    onChange={(e: ChangeEvent<HTMLSelectElement>) => setTemplateData(prev => ({ 
                      ...prev, 
                      dias_semana: e.target.value ? parseInt(e.target.value) : undefined 
                    }))}
                    placeholder="Opcional"
                    options={[
                      { value: "", label: "Sin especificar" },
                      { value: "1", label: "1 día" },
                      { value: "2", label: "2 días" },
                      { value: "3", label: "3 días" },
                      { value: "4", label: "4 días" },
                      { value: "5", label: "5 días" },
                      { value: "6", label: "6 días" },
                      { value: "7", label: "7 días" }
                    ]}
                  />
                </div>

                <div className="space-y-3">
                  <Toggle
                    checked={Boolean(templateData.activa)}
                    onChange={(checked: boolean) => setTemplateData(prev => ({ ...prev, activa: checked }))}
                    label="Plantilla activa"
                  />
                  
                  <Toggle
                    checked={Boolean(templateData.publica)}
                    onChange={(checked: boolean) => setTemplateData(prev => ({ ...prev, publica: checked }))}
                    label="Plantilla pública"
                  />
                </div>

                {/* Tags */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Etiquetas
                  </label>
                  <Input
                    value={templateData.tags?.join(", ") || ""}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => setTemplateData(prev => ({ 
                      ...prev, 
                      tags: e.target.value.split(",").map((tag: string) => tag.trim()).filter(Boolean)
                    }))}
                    placeholder="etiqueta1, etiqueta2, etiqueta3"
                  />
                </div>
              </div>

              {/* JSON Editor */}
              <div className="lg:col-span-3 flex flex-col">
                <div className="flex-1 relative">
                  <div className="absolute inset-0 border border-slate-800 rounded-xl overflow-hidden">
                    <MonacoEditor
                      value={configJson}
                      onChange={handleConfigChange}
                      language="json"
                      theme="vs-dark"
                      height="100%"
                      options={{
                        minimap: { enabled: false },
                        fontSize: 13,
                        wordWrap: "on",
                        scrollBeyondLastLine: false,
                        automaticLayout: true,
                      }}
                      onMount={(editor, monaco) => {
                        editorRef.current = editor;
                        monacoRef.current = monaco;
                      }}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "preview" && (
            <div className="h-full flex flex-col">
              <div className="flex items-center justify-between p-4 border-b border-slate-700">
                <div className="flex items-center gap-3">
                  <span className="text-sm text-slate-400">Zoom:</span>
                  <div className="flex gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setPreviewScale(Math.max(0.25, previewScale - 0.25))}
                    >
                      <ZoomOut className="w-4 h-4" />
                    </Button>
                    <span className="text-sm text-white px-2">{Math.round(previewScale * 100)}%</span>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setPreviewScale(Math.min(2, previewScale + 0.25))}
                    >
                      <ZoomIn className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setPreviewScale(1)}
                    >
                      <Maximize2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handlePreview}
                  disabled={previewLoading}
                  leftIcon={previewLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                >
                  Actualizar Vista Previa
                </Button>
              </div>

              <div className="flex-1 overflow-auto p-8 flex items-center justify-center bg-slate-900">
                {previewLoading ? (
                  <div className="flex flex-col items-center gap-4">
                    <RefreshCw className="w-8 h-8 animate-spin text-primary-500" />
                    <span className="text-slate-400">Generando vista previa...</span>
                  </div>
                ) : previewUrl ? (
                  <div 
                    className="bg-white shadow-2xl transition-transform duration-200"
                    style={{ transform: `scale(${previewScale})` }}
                  >
                    {previewUrl.startsWith("data:application/pdf") ? (
                      <iframe
                        src={previewUrl}
                        title="Template Preview PDF"
                        className="w-[900px] h-[1100px]"
                      />
                    ) : (
                      <Image
                        src={previewUrl}
                        alt="Template Preview"
                        width={900}
                        height={1100}
                        unoptimized
                        className="max-w-none"
                      />
                    )}
                  </div>
                ) : (
                  <div className="text-center">
                    <FileText className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                    <p className="text-slate-400 mb-4">No hay vista previa disponible</p>
                    <Button onClick={handlePreview} leftIcon={<Eye className="w-4 h-4" />}>
                      Generar Vista Previa
                    </Button>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === "validation" && (
            <div className="h-full overflow-y-auto p-6">
              {validation ? (
                <div className="max-w-4xl mx-auto space-y-6">
                  {/* Validation Summary */}
                  <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
                    <h3 className="text-lg font-semibold text-white mb-4">Resumen de Validación</h3>
                    
                    <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                      <div className="text-center">
                        <div className={`text-2xl font-bold ${
                          validation.errors.length > 0 ? 'text-red-400' :
                          validation.warnings.length > 0 ? 'text-yellow-400' : 
                          'text-green-400'
                        }`}>
                          {validation.errors.length === 0 && validation.warnings.length === 0 ? '✓' :
                           validation.errors.length > 0 ? validation.errors.length : 
                           validation.warnings.length}
                        </div>
                        <div className="text-sm text-slate-400">
                          {validation.errors.length > 0 ? 'Errores' : 
                           validation.warnings.length > 0 ? 'Advertencias' : 
                           'Válido'}
                        </div>
                      </div>
                      
                      <div className="text-center">
                        <div className="text-2xl font-bold text-blue-400">
                          {templateData.configuracion?.pages?.reduce((acc, p) => acc + (p.sections?.length || 0), 0) || 0}
                        </div>
                        <div className="text-sm text-slate-400">Secciones</div>
                      </div>
                      
                      <div className="text-center">
                        <div className="text-2xl font-bold text-purple-400">
                          {Object.keys(templateData.configuracion?.variables || {}).length}
                        </div>
                        <div className="text-sm text-slate-400">Variables</div>
                      </div>

                      <div className="text-center">
                        <div className={`text-2xl font-bold ${
                          validation.performance_score == null ? 'text-slate-400' :
                          validation.performance_score >= 80 ? 'text-green-400' :
                          validation.performance_score >= 60 ? 'text-yellow-400' :
                          'text-red-400'
                        }`}>
                          {validation.performance_score == null ? '—' : Math.round(validation.performance_score)}
                        </div>
                        <div className="text-sm text-slate-400">Performance</div>
                      </div>

                      <div className="text-center">
                        <div className={`text-2xl font-bold ${
                          validation.security_score == null ? 'text-slate-400' :
                          validation.security_score >= 80 ? 'text-green-400' :
                          validation.security_score >= 60 ? 'text-yellow-400' :
                          'text-red-400'
                        }`}>
                          {validation.security_score == null ? '—' : Math.round(validation.security_score)}
                        </div>
                        <div className="text-sm text-slate-400">Seguridad</div>
                      </div>
                    </div>
                  </div>

                  {/* Errors */}
                  {validation.errors.length > 0 && (
                    <div className="bg-red-900/20 border border-red-800 rounded-xl p-6">
                      <h4 className="text-red-400 font-semibold mb-4 flex items-center gap-2">
                        <AlertTriangle className="w-5 h-5" />
                        Errores ({validation.errors.length})
                      </h4>
                      <div className="space-y-3">
                        {validation.errors.map((error, index) => (
                          <div key={index} className="bg-red-900/40 rounded-lg p-4">
                            <div className="font-medium text-red-300">{error.message}</div>
                            {error.path && (
                              <div className="text-sm text-red-400 mt-1">Ruta: {error.path}</div>
                            )}
                            {error.suggestion && (
                              <div className="text-sm text-red-200 mt-2">Sugerencia: {error.suggestion}</div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Warnings */}
                  {validation.warnings.length > 0 && (
                    <div className="bg-yellow-900/20 border border-yellow-800 rounded-xl p-6">
                      <h4 className="text-yellow-400 font-semibold mb-4 flex items-center gap-2">
                        <AlertTriangle className="w-5 h-5" />
                        Advertencias ({validation.warnings.length})
                      </h4>
                      <div className="space-y-3">
                        {validation.warnings.map((warning, index) => (
                          <div key={index} className="bg-yellow-900/40 rounded-lg p-4">
                            <div className="font-medium text-yellow-300">{warning.message}</div>
                            {warning.path && (
                              <div className="text-sm text-yellow-400 mt-1">Ruta: {warning.path}</div>
                            )}
                            {warning.suggestion && (
                              <div className="text-sm text-yellow-200 mt-2">Sugerencia: {warning.suggestion}</div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full">
                  <AlertTriangle className="w-16 h-16 text-slate-600 mb-4" />
                  <p className="text-slate-400 mb-4">No hay resultados de validación</p>
                  <Button onClick={() => validateTemplate()} leftIcon={<Check className="w-4 h-4" />}>
                    Validar Configuración
                  </Button>
                </div>
              )}
            </div>
          )}

          {activeTab === "versions" && (
            <div className="h-full overflow-y-auto p-6">
              <div className="max-w-4xl mx-auto space-y-6">
                <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
                  <div className="flex items-center justify-between gap-3 mb-4">
                    <h3 className="text-lg font-semibold text-white">Historial de Versiones</h3>
                    <Button variant="secondary" size="sm" onClick={loadVersions} disabled={versionsLoading}>
                      <RefreshCw className={versionsLoading ? "w-4 h-4 animate-spin" : "w-4 h-4"} />
                    </Button>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <Input
                      label="Versión"
                      value={newVersionLabel}
                      onChange={(e) => setNewVersionLabel(e.target.value)}
                      placeholder="1.0.1"
                    />
                    <div className="md:col-span-2">
                      <Input
                        label="Descripción"
                        value={newVersionDesc}
                        onChange={(e) => setNewVersionDesc(e.target.value)}
                        placeholder="Cambios realizados..."
                      />
                    </div>
                  </div>
                  <div className="mt-4 flex justify-end">
                    <Button onClick={handleCreateVersion} disabled={versionsLoading}>
                      Crear versión
                    </Button>
                  </div>
                </div>

                <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
                  {versionsLoading ? (
                    <div className="p-8 text-center text-slate-400">
                      <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-3" />
                      Cargando versiones...
                    </div>
                  ) : versions.length > 0 ? (
                    <div className="divide-y divide-slate-700">
                      {versions.map((v) => (
                        <div key={`${v.id}-${v.version}`} className="p-4 flex items-center justify-between gap-3">
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <div className="font-semibold text-white truncate">{v.version}</div>
                              {v.es_actual && <Badge variant="success">Actual</Badge>}
                            </div>
                            <div className="text-xs text-slate-400 mt-1">
                              {String(v.fecha_creacion || "").slice(0, 19).replace("T", " ")}
                            </div>
                            {v.descripcion && (
                              <div className="text-sm text-slate-300 mt-2">
                                {v.descripcion}
                              </div>
                            )}
                          </div>
                          <div className="flex gap-2">
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => handleRestoreVersion(v.version)}
                              disabled={Boolean(v.es_actual)}
                            >
                              Restaurar
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-8 text-center text-slate-400">
                      No hay versiones registradas.
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}

// Helper function to get default template configuration
function getDefaultTemplateConfig(): TemplateConfig {
  return {
    metadata: {
      name: "Plantilla Básica",
      version: "1.0.0",
      description: "Plantilla pública por defecto para exportar rutinas en PDF",
      author: "system",
      category: "general",
      difficulty: "beginner",
      tags: ["classic", "system"],
      estimated_duration: 45,
    },
    layout: {
      page_size: "A4",
      orientation: "portrait",
      margins: {
        top: 20,
        right: 20,
        bottom: 20,
        left: 20
      }
    },
    pages: [
      {
        name: "Rutina",
        sections: [
          {
            type: "header",
            content: {
              title: "{{gym_name}}",
              subtitle: "{{nombre_rutina}} - {{usuario_nombre}}",
            },
          },
          { type: "spacing", content: { height: 8 } },
          { type: "exercise_table", content: {} },
          { type: "spacing", content: { height: 12 } },
          { type: "qr_code", content: { size: 90 } },
        ],
      },
    ],
    variables: {
      gym_name: {
        type: "string",
        default: "Gym",
        description: "Nombre del gimnasio"
      },
      client_name: {
        type: "string", 
        default: "Cliente",
        description: "Nombre del cliente"
      },
      nombre_rutina: {
        type: "string",
        default: "Rutina",
        description: "Nombre de la rutina"
      },
      usuario_nombre: {
        type: "string",
        default: "Usuario",
        description: "Nombre del usuario"
      }
    },
    qr_code: { enabled: true, position: "inline", data_source: "routine_uuid" },
    styling: {
      fonts: {
        title: { family: "Helvetica-Bold", size: 18, color: "#000000" },
        body: { family: "Helvetica", size: 10, color: "#111827" }
      },
      colors: { primary: "#111827", accent: "#3B82F6" }
    },
  };
}
