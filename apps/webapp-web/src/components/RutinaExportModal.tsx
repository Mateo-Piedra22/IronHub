"use client";

import { useState, useCallback } from "react";
import { FileSpreadsheet, Download, QrCode, Loader2 } from "lucide-react";
import { Modal, Button, Input, Select, useToast } from "@/components/ui";
import type { Rutina } from "@/lib/api";

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
    const { success, error } = useToast();

    // Set default filename when modal opens
    useState(() => {
        if (rutina) {
            const safeName = (rutina.nombre || "rutina").replace(/[^a-zA-Z0-9]/g, "_");
            setFilename(`${safeName}.xlsx`);
        }
    });

    const handleExport = useCallback(async () => {
        if (!rutina) return;

        setLoading(true);
        try {
            const res = await fetch(`/api/rutinas/${rutina.id}/export`, {
                method: "POST",
                credentials: "include",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    filename: filename || `rutina_${rutina.id}.xlsx`,
                    weeks: parseInt(weeks),
                    qr_placement: qrPlacement,
                    usuario_nombre: rutina.usuario_nombre,
                }),
            });

            if (res.ok) {
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = filename || `rutina_${rutina.id}.xlsx`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                success("Excel exportado correctamente");
                onClose();
            } else {
                const data = await res.json().catch(() => ({}));
                error(data.detail || "Error al exportar");
            }
        } catch {
            error("Error de conexión");
        } finally {
            setLoading(false);
        }
    }, [rutina, filename, weeks, qrPlacement, success, error, onClose]);

    if (!rutina) return null;

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title="Exportar Rutina a Excel"
            size="md"
            footer={
                <>
                    <Button variant="secondary" onClick={onClose} disabled={loading}>
                        Cancelar
                    </Button>
                    <Button
                        leftIcon={loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                        onClick={handleExport}
                        disabled={loading}
                    >
                        Descargar Excel
                    </Button>
                </>
            }
        >
            <div className="space-y-4">
                {/* Preview info */}
                <div className="p-4 bg-neutral-900 rounded-xl border border-neutral-800">
                    <div className="flex items-center gap-3">
                        <FileSpreadsheet className="w-10 h-10 text-success-400" />
                        <div>
                            <div className="font-medium text-white">{rutina.nombre}</div>
                            <div className="text-sm text-neutral-400">
                                {rutina.dias?.length || 0} días • {rutina.categoria || "General"}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Filename */}
                <Input
                    label="Nombre del archivo"
                    value={filename}
                    onChange={(e) => setFilename(e.target.value)}
                    placeholder="rutina.xlsx"
                />

                {/* Weeks */}
                <div>
                    <label className="block text-sm font-medium text-neutral-300 mb-2">
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
                    <label className="block text-sm font-medium text-neutral-300 mb-2">
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
                    <p className="mt-1 text-xs text-neutral-500">
                        El código QR permite al usuario escanear y ver su rutina en la app.
                    </p>
                </div>
            </div>
        </Modal>
    );
}

export default RutinaExportModal;
