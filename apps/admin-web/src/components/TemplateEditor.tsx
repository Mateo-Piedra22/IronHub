"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { 
  Save, Eye, Download, Upload, Settings, RefreshCw, 
  FileText, Code, Check, X, AlertTriangle, Info,
  Play, Pause, RotateCcw, ZoomIn, ZoomOut, Maximize2
} from "lucide-react";
import { Button, Input, Select, Modal, useToast, Badge, Toggle } from "@/components/ui";
import { api, type Template, type TemplateConfig, type TemplateValidation } from "@/lib/api";

// Monaco Editor import (will be loaded dynamically)
interface MonacoEditorProps {
  value: string;
  onChange: (value: string) => void;
  language?: string;
  theme?: string;
  onMount?: (editor: any) => void;
}

// Dynamic import for Monaco Editor to avoid SSR issues
const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false });

interface TemplateEditorProps {
  template?: Template;
  isOpen: boolean;
  onClose: () => void;
  onSave: (template: Template) => void;
  isNew?: boolean;
}

export function TemplateEditor({ template, isOpen, onClose, onSave, isNew = false }: TemplateEditorProps) {
  const [activeTab, setActiveTab] = useState<"config" | "preview" | "validation">("config");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [validation, setValidation] = useState<TemplateValidation | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string>("");
  const [previewScale, setPreviewScale] = useState(1);
  
  // Template data
  const [templateData, setTemplateData] = useState<Partial<Template>>({
    nombre: "",
    descripcion: "",
    categoria: "general",
    dias_semana: null,
    configuracion: getDefaultTemplateConfig(),
    activa: true,
    publica: false,
    tags: []
  });

  // Editor states
  const [configJson, setConfigJson] = useState<string>("");
  const [editorTheme, setEditorTheme] = useState<"vs-dark" | "light">("vs-dark");
  const [autoSave, setAutoSave] = useState(false);
  const [showLineNumbers, setShowLineNumbers] = useState(true);
  const [wordWrap, setWordWrap] = useState(true);
  
  const editorRef = useRef<any>(null);
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
  }, [configJson, autoSave, templateData, isNew]);

  const handleAutoSave = async () => {
    if (!template || isNew) return;

    try {
      const updatedConfig = JSON.parse(configJson);
      const response = await api.updateTemplate(template.id, {
        ...templateData,
        configuracion: updatedConfig
      });

      if (response.ok && response.data?.success) {
        // Silent auto-save success
        console.log("Template auto-saved");
      }
    } catch (err) {
      console.error("Auto-save failed:", err);
    }
  };

  const handleConfigChange = useCallback((value: string | undefined) => {
    if (value !== undefined) {
      setConfigJson(value);
      try {
        const parsed = JSON.parse(value);
        setTemplateData(prev => ({ ...prev, configuracion: parsed }));
        validateTemplate(parsed);
      } catch (err) {
        // Invalid JSON, don't update template data
      }
    }
  }, []);

  const validateTemplate = useCallback(async (config?: TemplateConfig) => {
    const configToValidate = config || templateData.configuracion;
    if (!configToValidate) return;

    try {
      const response = await api.validateTemplate(configToValidate);
      if (response.ok && response.data?.success) {
        setValidation(response.data.validation);
      }
    } catch (err) {
      console.error("Template validation failed:", err);
    }
  }, [templateData.configuracion]);

  const handleSave = async () => {
    if (!templateData.nombre?.trim()) {
      error("El nombre de la plantilla es requerido");
      return;
    }

    try {
      const finalConfig = JSON.parse(configJson);
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
      const response = await api.generateTemplatePreview(templateData.configuracion);
      
      if (response.ok && response.data?.success) {
        setPreviewUrl(response.data.preview_url);
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
          dias_semana: imported.dias_semana || null,
          configuracion: imported.configuracion || getDefaultTemplateConfig(),
          activa: imported.activa !== false,
          publica: imported.publica || false,
          tags: imported.tags || []
        });
        
        setConfigJson(JSON.stringify(imported.configuracion || getDefaultTemplateConfig(), null, 2));
        success("Plantilla importada exitosamente");
      } catch (err) {
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

  const handleEditorDidMount = (editor: any, monaco: any) => {
    editorRef.current = editor;
    
    // Configure editor options
    editor.updateOptions({
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      fontSize: 14,
      lineNumbers: showLineNumbers ? 'on' : 'off',
      wordWrap: wordWrap ? 'on' : 'off',
      automaticLayout: true,
    });

    // Add custom validation
    editor.onDidChangeModelContent(() => {
      const value = editor.getValue();
      handleConfigChange(value);
    });
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

  const getValidationStatus = () => {
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
              <Badge variant={validationStatus.type as any}>
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
              disabled={saving || !templateData.nombre?.trim()}
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
              
              <Select
                value={editorTheme}
                onChange={(e) => setEditorTheme(e.target.value as "vs-dark" | "light")}
                className="w-32"
                options={[
                  { value: "vs-dark", label: "Oscuro" },
                  { value: "light", label: "Claro" }
                ]}
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
                    onChange={(e) => setTemplateData(prev => ({ ...prev, nombre: e.target.value }))}
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
                    onChange={(e) => setTemplateData(prev => ({ ...prev, descripcion: e.target.value }))}
                    placeholder="Descripción de la plantilla"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Categoría
                  </label>
                  <Select
                    value={templateData.categoria || "general"}
                    onChange={(e) => setTemplateData(prev => ({ ...prev, categoria: e.target.value }))}
                    options={getCategoryOptions()}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Días de la semana
                  </label>
                  <Select
                    value={templateData.dias_semana?.toString() || ""}
                    onChange={(e) => setTemplateData(prev => ({ 
                      ...prev, 
                      dias_semana: e.target.value ? parseInt(e.target.value) : null 
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
                    checked={templateData.activa}
                    onChange={(checked) => setTemplateData(prev => ({ ...prev, activa: checked }))}
                    label="Plantilla activa"
                  />
                  
                  <Toggle
                    checked={templateData.publica}
                    onChange={(checked) => setTemplateData(prev => ({ ...prev, publica: checked }))}
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
                    onChange={(e) => setTemplateData(prev => ({ 
                      ...prev, 
                      tags: e.target.value.split(",").map(tag => tag.trim()).filter(Boolean)
                    }))}
                    placeholder="etiqueta1, etiqueta2, etiqueta3"
                  />
                </div>
              </div>

              {/* JSON Editor */}
              <div className="lg:col-span-3 flex flex-col">
                <div className="flex-1 relative">
                  <MonacoEditor
                    height="100%"
                    language="json"
                    theme={editorTheme}
                    value={configJson}
                    onChange={handleConfigChange}
                    onMount={handleEditorDidMount}
                    options={{
                      minimap: { enabled: false },
                      scrollBeyondLastLine: false,
                      fontSize: 14,
                      lineNumbers: showLineNumbers ? 'on' : 'off',
                      wordWrap: wordWrap ? 'on' : 'off',
                      automaticLayout: true,
                      formatOnPaste: true,
                      formatOnType: true,
                    }}
                  />
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
                    <img
                      src={previewUrl}
                      alt="Template Preview"
                      className="max-w-none"
                    />
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
                    
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                          {validation.sections?.length || 0}
                        </div>
                        <div className="text-sm text-slate-400">Secciones</div>
                      </div>
                      
                      <div className="text-center">
                        <div className="text-2xl font-bold text-purple-400">
                          {validation.variables?.length || 0}
                        </div>
                        <div className="text-sm text-slate-400">Variables</div>
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

                  {/* Sections */}
                  {validation.sections && validation.sections.length > 0 && (
                    <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
                      <h4 className="text-white font-semibold mb-4">Secciones Detectadas</h4>
                      <div className="space-y-3">
                        {validation.sections.map((section, index) => (
                          <div key={index} className="bg-slate-900 rounded-lg p-4">
                            <div className="font-medium text-white">{section.name}</div>
                            <div className="text-sm text-slate-400 mt-1">
                              Tipo: {section.type} | Ejercicios: {section.exercises?.length || 0}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Variables */}
                  {validation.variables && validation.variables.length > 0 && (
                    <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
                      <h4 className="text-white font-semibold mb-4">Variables Detectadas</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {validation.variables.map((variable, index) => (
                          <div key={index} className="bg-slate-900 rounded-lg p-3">
                            <div className="font-medium text-white">{variable.name}</div>
                            <div className="text-sm text-slate-400">
                              Tipo: {variable.type} {variable.required && "| Requerido"}
                            </div>
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
        </div>
      </div>
    </Modal>
  );
}

// Helper function to get default template configuration
function getDefaultTemplateConfig(): TemplateConfig {
  return {
    version: "1.0.0",
    metadata: {
      name: "Plantilla Básica",
      description: "Plantilla de rutina básica",
      author: "System",
      created_at: new Date().toISOString(),
      tags: []
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
    sections: [
      {
        id: "header",
        type: "header",
        content: {
          title: "{{gym_name}}",
          subtitle: "Rutina de Entrenamiento",
          show_logo: true,
          show_date: true
        }
      },
      {
        id: "exercises",
        type: "exercise_table",
        content: {
          columns: ["dia", "ejercicio", "series", "repeticiones", "descanso"],
          show_day_separator: true,
          group_by_day: true
        }
      }
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
      }
    },
    styling: {
      primary_color: "#000000",
      secondary_color: "#666666",
      font_family: "Arial",
      font_size: 12
    }
  };
}

// Dynamic import fix for Next.js
import dynamic from 'next/dynamic';
