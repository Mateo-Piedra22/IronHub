"use client";

import { useState, useEffect, useCallback, useRef, type ChangeEvent } from "react";
import NextImage from "next/image";
import { 
  Eye,
  Download,
  Share2,
  Settings,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Loader2,
  FileText,
  ChevronLeft,
  ChevronRight,
  Grid,
  RefreshCw,
  Minimize2,
  Camera,
  RotateCcw,
} from "lucide-react";
import { Button, Modal, useToast, Badge, Toggle, Select, Input } from "@/components/ui";
import { api, type Template, type TemplatePreviewRequest, type Rutina } from "@/lib/api";

interface TemplatePreviewProps {
  template: Template;
  rutina?: Rutina;
  isOpen: boolean;
  onClose: () => void;
}

type PreviewQuality = "low" | "medium" | "high";
type PreviewFormat = "pdf" | "image" | "thumbnail" | "html" | "json";

export function TemplatePreview({ template, rutina, isOpen, onClose }: TemplatePreviewProps) {
  const [loading, setLoading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string>("");
  const [previewPages, setPreviewPages] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState(0);
  const [scale, setScale] = useState(1);
  const [previewQuality, setPreviewQuality] = useState<PreviewQuality>("medium");
  const [previewFormat, setPreviewFormat] = useState<PreviewFormat>("pdf");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [showGrid, setShowGrid] = useState(false);
  const [showRulers, setShowRulers] = useState(false);
  
  // Preview settings
  const [qrMode, setQrMode] = useState<"header" | "footer" | "inline" | "sheet" | "none">("inline");
  
  const previewRef = useRef<HTMLDivElement>(null);
  const autoRefreshTimerRef = useRef<NodeJS.Timeout | null>(null);
  const { success, error } = useToast();
  const [pageInput, setPageInput] = useState(1);

  const handleFitWidth = useCallback(() => {
    const width = previewRef.current?.clientWidth;
    if (!width) return;
    const next = Math.max(0.3, Math.min(2, (width - 64) / 900));
    setScale(next);
  }, []);

  const loadPreview = useCallback(async () => {
    if (!template) return;

    setLoading(true);
    try {
      const request: TemplatePreviewRequest = {
        format: previewFormat,
        quality: previewQuality,
        page_number: currentPage + 1,
        sample_data: null,
      };
      if (rutina) request.qr_mode = qrMode;

      const response = rutina
        ? await api.getRutinaPreviewWithTemplate(rutina.id, template.id, request)
        : await api.getTemplatePreview(template.id, request);

      if (response.ok && response.data?.success) {
        const url = response.data.preview_url;
        if (url) {
          setPreviewUrl(url);
          setPreviewPages([url]);
        } else {
          error("Error al generar vista previa");
        }
      } else {
        error("Error al generar vista previa");
      }
    } catch {
      error("Error al generar vista previa");
    } finally {
      setLoading(false);
    }
  }, [currentPage, error, previewFormat, previewQuality, qrMode, rutina, template]);

  // Load preview when modal opens or settings change
  useEffect(() => {
    if (isOpen) loadPreview();
  }, [isOpen, loadPreview]);

  useEffect(() => {
    setPageInput(currentPage + 1);
  }, [currentPage]);

  // Auto-refresh functionality
  useEffect(() => {
    if (autoRefresh && isOpen) {
      autoRefreshTimerRef.current = setInterval(() => {
        loadPreview();
      }, 30000); // Refresh every 30 seconds
    }

    return () => {
      if (autoRefreshTimerRef.current) {
        clearInterval(autoRefreshTimerRef.current);
      }
    };
  }, [autoRefresh, isOpen, loadPreview]);

  const handleDownload = async () => {
    if (!previewUrl) return;

    try {
      const link = document.createElement('a');
      link.href = previewUrl;
      link.download = `${template.nombre}_preview.${previewFormat}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      success("Vista previa descargada");
    } catch (err) {
      console.error("Download failed:", err);
      error("Error al descargar vista previa");
    }
  };

  const handleShare = async () => {
    if (!previewUrl) return;

    try {
      if (navigator.share) {
        await navigator.share({
          title: `Vista previa: ${template.nombre}`,
          text: `Echa un vistazo a esta plantilla: ${template.nombre}`,
          url: previewUrl
        });
      } else {
        // Fallback: copy to clipboard
        await navigator.clipboard.writeText(previewUrl);
        success("Enlace copiado al portapapeles");
      }
    } catch (err) {
      console.error("Share failed:", err);
      error("Error al compartir vista previa");
    }
  };

  const handleScreenshot = async () => {
    if (!previewRef.current) return;

    try {
      // Use html2canvas or similar library for screenshot
      // For now, we'll use a simple implementation
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const img = new Image();
      img.onload = () => {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);
        
        canvas.toBlob((blob) => {
          if (blob) {
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `${template.nombre}_screenshot.png`;
            link.click();
            URL.revokeObjectURL(url);
            success("Captura de pantalla guardada");
          }
        });
      };
      img.src = previewUrl;
    } catch (err) {
      console.error("Screenshot failed:", err);
      error("Error al tomar captura de pantalla");
    }
  };

  const handlePrint = () => {
    if (!previewUrl) return;

    const printWindow = window.open(previewUrl, '_blank');
    if (printWindow) {
      printWindow.onload = () => {
        printWindow.print();
      };
    }
  };

  const handleScaleChange = (newScale: number) => {
    setScale(Math.max(0.25, Math.min(3, newScale)));
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const toggleFullscreen = () => {
    if (!isFullscreen) {
      if (previewRef.current?.requestFullscreen) {
        previewRef.current.requestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
    setIsFullscreen(!isFullscreen);
  };

  const getQualityLabel = (quality: PreviewQuality) => {
    switch (quality) {
      case "low": return "Baja";
      case "medium": return "Media";
      case "high": return "Alta";
    }
  };

  const getFormatLabel = (format: PreviewFormat) => {
    switch (format) {
      case "pdf": return "PDF";
      case "image": return "Imagen";
      case "thumbnail": return "Miniatura";
      case "html": return "HTML";
      case "json": return "JSON";
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Vista Previa: ${template.nombre}`}
      size="full"
      className="template-preview-modal"
      footer={
        <div className="flex justify-between items-center w-full">
          <div className="flex gap-3">
            <Badge variant="outline">
              Página {currentPage + 1} de {previewPages.length}
            </Badge>
            <Badge variant="outline">
              {getQualityLabel(previewQuality)} calidad
            </Badge>
            <Badge variant="outline">
              {getFormatLabel(previewFormat)}
            </Badge>
            {autoRefresh && (
              <Badge variant="secondary">
                <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                Auto-refresh
              </Badge>
            )}
          </div>
          
          <div className="flex gap-3">
            <Button variant="secondary" onClick={onClose}>
              Cerrar
            </Button>
            <Button onClick={handleDownload} leftIcon={<Download className="w-4 h-4" />}>
              Descargar
            </Button>
          </div>
        </div>
      }
    >
      <div className="flex flex-col h-full">
        {/* Toolbar */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <div className="flex gap-3">
            {/* Settings */}
            <div className="flex items-center gap-3 px-3 border-l border-r border-slate-700">
              <Select
                value={previewQuality}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setPreviewQuality(e.target.value as PreviewQuality)}
                className="w-24"
                options={[
                  { value: "low", label: "Baja" },
                  { value: "medium", label: "Media" },
                  { value: "high", label: "Alta" }
                ]}
              />

              <Select
                value={previewFormat}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setPreviewFormat(e.target.value as PreviewFormat)}
                className="w-20"
                options={[
                  { value: "pdf", label: "PDF" },
                  { value: "image", label: "Imagen" },
                  { value: "thumbnail", label: "Miniatura" }
                ]}
              />

              <Select
                value={qrMode}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setQrMode(e.target.value as "header" | "footer" | "inline" | "sheet" | "none")}
                className="w-32"
                options={[
                  { value: "header", label: "QR Header" },
                  { value: "footer", label: "QR Footer" },
                  { value: "inline", label: "QR Inline" },
                  { value: "sheet", label: "QR Hoja" },
                  { value: "none", label: "Sin QR" }
                ]}
              />
            </div>

            {/* Toggles */}
            <div className="flex items-center gap-3">
              <Toggle
                checked={autoRefresh}
                onChange={setAutoRefresh}
                label="Auto"
              />
              <Toggle
                checked={showGrid}
                onChange={setShowGrid}
                label="Cuadrícula"
              />
            </div>
          </div>

          <div className="flex gap-2">
            {/* Actions */}
            <Button
              variant="secondary"
              size="sm"
              onClick={handleShare}
            >
              <Share2 className="w-4 h-4" />
            </Button>
            
            <Button
              variant="secondary"
              size="sm"
              onClick={handleScreenshot}
            >
              <Camera className="w-4 h-4" />
            </Button>

            <Button
              variant="secondary"
              size="sm"
              onClick={handlePrint}
            >
              <FileText className="w-4 h-4" />
            </Button>

            <Button
              variant="secondary"
              size="sm"
              onClick={toggleFullscreen}
            >
              {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </Button>

            <Button
              variant="secondary"
              size="sm"
              onClick={loadPreview}
              disabled={loading}
              leftIcon={loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            >
              Actualizar
            </Button>
          </div>
        </div>

        {/* Preview Controls */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <div className="flex items-center gap-4">
            {/* Page Navigation */}
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handlePageChange(Math.max(0, currentPage - 1))}
                disabled={currentPage === 0}
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <Input
                type="number"
                min={1}
                value={pageInput}
                onChange={(e) => setPageInput(Math.max(1, Number(e.target.value) || 1))}
                onBlur={() => {
                  const maxPage = Math.max(1, previewPages.length);
                  const next = Math.min(maxPage, Math.max(1, Number(pageInput) || 1));
                  handlePageChange(next - 1);
                }}
                className="w-20"
              />
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handlePageChange(Math.min(previewPages.length - 1, currentPage + 1))}
                disabled={currentPage >= previewPages.length - 1}
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
              <span className="text-sm text-slate-400">Página</span>
            </div>

            {/* Zoom Controls */}
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleScaleChange(scale - 0.25)}
              >
                <ZoomOut className="w-4 h-4" />
              </Button>
              <span className="text-sm text-white min-w-[60px] text-center">
                {Math.round(scale * 100)}%
              </span>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleScaleChange(scale + 0.25)}
              >
                <ZoomIn className="w-4 h-4" />
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleScaleChange(1)}
              >
                <RotateCcw className="w-4 h-4" />
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={handleFitWidth}
              >
                <Maximize2 className="w-4 h-4" />
              </Button>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowGrid(!showGrid)}
            >
              <Grid className="w-4 h-4" />
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowRulers(!showRulers)}
            >
              <Settings className="w-4 h-4" />
            </Button>
            {previewPages[currentPage] && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => window.open(previewPages[currentPage], "_blank", "noopener,noreferrer")}
              >
                <Share2 className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>

        {/* Preview Area */}
        <div className="flex-1 overflow-auto bg-slate-900 p-8" ref={previewRef}>
          {loading ? (
            <div className="flex flex-col items-center justify-center h-full">
              <Loader2 className="w-12 h-12 animate-spin text-primary-500 mb-4" />
              <span className="text-slate-400">Generando vista previa...</span>
            </div>
          ) : previewPages.length > 0 ? (
            <div className="flex flex-col items-center">
              {/* Rulers */}
              {showRulers && (
                <div className="mb-4 text-xs text-slate-500">
                  <div className="flex gap-8">
                    <span>Ancho: 210mm (A4)</span>
                    <span>Alto: 297mm (A4)</span>
                    <span>Escala: {Math.round(scale * 100)}%</span>
                  </div>
                </div>
              )}

              {/* Preview Container */}
              <div 
                className={`relative bg-white shadow-2xl transition-transform duration-200 ${
                  showGrid ? 'outline-dotted outline-2 outline-slate-600' : ''
                }`}
                style={{ 
                  transform: `scale(${scale})`,
                  transformOrigin: 'top center'
                }}
              >
                {/* Grid Overlay */}
                {showGrid && (
                  <div className="absolute inset-0 pointer-events-none">
                    <div className="w-full h-full" style={{
                      backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 19px, rgba(0,0,0,0.1) 19px, rgba(0,0,0,0.1) 20px), repeating-linear-gradient(90deg, transparent, transparent 19px, rgba(0,0,0,0.1) 19px, rgba(0,0,0,0.1) 20px)',
                      backgroundSize: '20px 20px'
                    }} />
                  </div>
                )}

                {/* Preview Content */}
                {previewPages[currentPage]?.startsWith("data:application/pdf") ? (
                  <iframe
                    src={previewPages[currentPage]}
                    title={`Preview page ${currentPage + 1}`}
                    className="w-[900px] h-[1100px]"
                  />
                ) : (
                  <NextImage
                    src={previewPages[currentPage]}
                    alt={`Preview page ${currentPage + 1}`}
                    width={900}
                    height={1100}
                    unoptimized
                    className="max-w-none"
                  />
                )}
              </div>

              {/* Metadata */}
              <div className="mt-6 text-center text-sm text-slate-400">
                <div>Plantilla: {template.nombre}</div>
                <div>Versión: {template.version_actual}</div>
                <div>Categoría: {template.categoria}</div>
                {rutina && <div>Rutina: {rutina.nombre}</div>}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full">
              <FileText className="w-16 h-16 text-slate-600 mb-4" />
              <p className="text-slate-400 mb-4">No hay vista previa disponible</p>
              <Button onClick={loadPreview} leftIcon={<Eye className="w-4 h-4" />}>
                Generar Vista Previa
              </Button>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}
