"use client";

import { useState, useCallback, useEffect } from "react";
import { FileSpreadsheet, Download, QrCode, Loader2, FileText, Palette } from "lucide-react";
import { Modal, Button, Input, Select, useToast, Toggle } from "@/components/ui";
import { api, type Rutina, type Template } from "@/lib/api";
import TemplateSelectionModal from "./TemplateSelectionModal";

interface RutinaExportModalProps {
    isOpen: boolean;
    onClose: () => void;
    rutina: Rutina | null;
}

type QRPlacement = "inline" | "sheet" | "none";

export function RutinaExportModal({ isOpen, onClose, rutina }: RutinaExportModalProps) {
    const [filename, setFilename] = useState("");
    const [weeks, setWeeks] = useState("4");
    const [qrPlacement, setQrPlacement] = useState<QRPlacement>("inline");
    const [loading, setLoading] = useState(false);
    const [useTemplate, setUseTemplate] = useState(false);
    const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
    const [showTemplateSelection, setShowTemplateSelection] = useState(false);
    const [exportFormat, setExportFormat] = useState<"excel" | "pdf">("excel");
    const { success, error } = useToast();

    // Set default filename when modal opens
    useEffect(() => {
        if (!isOpen) return;
        if (!rutina) return;
        const extension = exportFormat === "pdf" ? "pdf" : "xlsx";
        const safeName = (rutina.nombre || "rutina").replace(/[^a-zA-Z0-9]/g, "_");
        setFilename((prev) => prev || `${safeName}.${extension}`);
    }, [isOpen, rutina, exportFormat]);

    // Reset template selection when format changes
    useEffect(() => {
        if (exportFormat === "excel") {
            setUseTemplate(false);
            setSelectedTemplate(null);
        }
    }, [exportFormat]);

    const handleExport = useCallback(async () => {
        if (!rutina) return;

        setLoading(true);
        try {
            let url: string;
            
            if (exportFormat === "pdf" && useTemplate && selectedTemplate) {
                // Export with template
                url = api.getRutinaPdfUrlWithTemplate(rutina.id, selectedTemplate.id, {
                    weeks: Number.parseInt(weeks, 10) || 1,
                    qr_mode: qrPlacement,
                    user_override: rutina.usuario_nombre || undefined,
                    filename: filename || undefined,
                });
            } else if (exportFormat === "excel") {
                // Traditional Excel export
                url = api.getRutinaExcelUrl(rutina.id, {
                    weeks: Number.parseInt(weeks, 10) || 1,
                    qr_mode: qrPlacement,
                    user_override: rutina.usuario_nombre || undefined,
                    filename: filename || undefined,
                });
            } else {
                // PDF without template
                url = api.getRutinaPdfUrl(rutina.id, {
                    weeks: Number.parseInt(weeks, 10) || 1,
                    qr_mode: qrPlacement,
                    user_override: rutina.usuario_nombre || undefined,
                    filename: filename || undefined,
                });
            }

            window.open(url, "_blank", "noopener,noreferrer");
            success("Descarga iniciada");
            onClose();
        } catch {
            error("Error de conexión");
        } finally {
            setLoading(false);
        }
    }, [rutina, filename, weeks, qrPlacement, exportFormat, useTemplate, selectedTemplate, success, error, onClose]);

    const handleTemplateSelect = (template: Template) => {
        setSelectedTemplate(template);
        setShowTemplateSelection(false);
    };

    if (!rutina) return null;

    return (
        <>
            <Modal
                isOpen={isOpen}
                onClose={onClose}
                title={`Exportar Rutina a ${exportFormat === "excel" ? "Excel" : "PDF"}`}
                size="md"
                footer={
                    <>
                        <Button variant="secondary" onClick={onClose} disabled={loading}>
                            Cancelar
                        </Button>
                        <Button
                            leftIcon={loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                            onClick={handleExport}
                            disabled={loading || (exportFormat === "pdf" && useTemplate && !selectedTemplate)}
                        >
                            Descargar {exportFormat === "excel" ? "Excel" : "PDF"}
                        </Button>
                    </>
                }
            >
                <div className="space-y-4">
                    {/* Preview info */}
                    <div className="p-4 bg-slate-900 rounded-xl border border-slate-800">
                        <div className="flex items-center gap-3">
                            {exportFormat === "excel" ? (
                                <FileSpreadsheet className="w-10 h-10 text-success-400" />
                            ) : (
                                <FileText className="w-10 h-10 text-blue-400" />
                            )}
                            <div>
                                <div className="font-medium text-white">{rutina.nombre}</div>
                                <div className="text-sm text-slate-400">
                                    {rutina.dias?.length || 0} días • {rutina.categoria || "General"}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Export Format */}
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                            Formato de exportación
                        </label>
                        <div className="grid grid-cols-2 gap-2">
                            <button
                                onClick={() => setExportFormat("excel")}
                                className={`p-3 rounded-lg border-2 transition-all ${
                                    exportFormat === "excel"
                                        ? "border-blue-500 bg-blue-500/10 text-blue-400"
                                        : "border-slate-700 text-slate-400 hover:border-slate-600"
                                }`}
                            >
                                <FileSpreadsheet className="w-5 h-5 mx-auto mb-1" />
                                <div className="text-sm font-medium">Excel</div>
                                <div className="text-xs opacity-75">Tradicional</div>
                            </button>
                            <button
                                onClick={() => setExportFormat("pdf")}
                                className={`p-3 rounded-lg border-2 transition-all ${
                                    exportFormat === "pdf"
                                        ? "border-blue-500 bg-blue-500/10 text-blue-400"
                                        : "border-slate-700 text-slate-400 hover:border-slate-600"
                                }`}
                            >
                                <FileText className="w-5 h-5 mx-auto mb-1" />
                                <div className="text-sm font-medium">PDF</div>
                                <div className="text-xs opacity-75">Con plantillas</div>
                            </button>
                        </div>
                    </div>

                    {/* Template Selection (PDF only) */}
                    {exportFormat === "pdf" && (
                        <div className="space-y-3">
                            <div className="flex items-center justify-between">
                                <label className="text-sm font-medium text-slate-300">
                                    <Palette className="w-4 h-4 inline mr-2" />
                                    Usar plantilla personalizada
                                </label>
                                <Toggle
                                    checked={useTemplate}
                                    onCheckedChange={setUseTemplate}
                                />
                            </div>

                            {useTemplate && (
                                <div className="bg-slate-800 rounded-lg border border-slate-700 p-3">
                                    {selectedTemplate ? (
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-3">
                                                {selectedTemplate.preview_url ? (
                                                    <img
                                                        src={selectedTemplate.preview_url}
                                                        alt={selectedTemplate.nombre}
                                                        className="w-12 h-12 rounded object-cover"
                                                    />
                                                ) : (
                                                    <div className="w-12 h-12 rounded bg-slate-700 flex items-center justify-center">
                                                        <Palette className="w-5 h-5 text-slate-400" />
                                                    </div>
                                                )}
                                                <div>
                                                    <div className="text-sm font-medium text-white">
                                                        {selectedTemplate.nombre}
                                                    </div>
                                                    <div className="text-xs text-slate-400">
                                                        {selectedTemplate.categoria}
                                                        {selectedTemplate.dias_semana && ` • ${selectedTemplate.dias_semana} días`}
                                                    </div>
                                                </div>
                                            </div>
                                            <Button
                                                variant="secondary"
                                                size="sm"
                                                onClick={() => setShowTemplateSelection(true)}
                                            >
                                                Cambiar
                                            </Button>
                                        </div>
                                    ) : (
                                        <button
                                            onClick={() => setShowTemplateSelection(true)}
                                            className="w-full p-3 border-2 border-dashed border-slate-600 rounded-lg text-slate-400 hover:border-slate-500 hover:text-slate-300 transition-colors"
                                        >
                                            <div className="flex items-center justify-center gap-2">
                                                <Palette className="w-4 h-4" />
                                                <span>Seleccionar plantilla</span>
                                            </div>
                                        </button>
                                    )}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Filename */}
                    <Input
                        label="Nombre del archivo"
                        value={filename}
                        onChange={(e) => setFilename(e.target.value)}
                        placeholder={`rutina.${exportFormat === "excel" ? "xlsx" : "pdf"}`}
                    />

                    {/* Weeks */}
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                            Semanas a exportar
                        </label>
                        <Select
                            value={weeks}
                            onChange={(e) => setWeeks(e.target.value)}
                            options={[
                                { value: "1", label: "1 semana" },
                                { value: "2", label: "2 semanas" },
                                { value: "3", label: "3 semanas" },
                                { value: "4", label: "4 semanas" },
                            ]}
                        />
                    </div>

                    {/* QR Placement */}
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                            <QrCode className="w-4 h-4 inline mr-2" />
                            Ubicación del QR
                        </label>
                        <Select
                            value={qrPlacement}
                            onChange={(e) => setQrPlacement(e.target.value as QRPlacement)}
                            options={[
                                { value: "inline", label: "Debajo de la rutina" },
                                { value: "sheet", label: "Segunda hoja (QR)" },
                                { value: "none", label: "Sin QR" },
                            ]}
                        />
                        <p className="mt-1 text-xs text-slate-500">
                            El código QR permite al usuario escanear y ver su rutina en la app.
                        </p>
                    </div>
                </div>
            </Modal>

            {/* Template Selection Modal */}
            <TemplateSelectionModal
                isOpen={showTemplateSelection}
                onClose={() => setShowTemplateSelection(false)}
                onTemplateSelect={handleTemplateSelect}
                rutina={rutina}
            />
        </>
    );
}

export default RutinaExportModal;

