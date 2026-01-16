'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Minimize2,
    Maximize2,
    ZoomIn,
    ZoomOut,
    FileSpreadsheet,
    RefreshCw,
    X,
    Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui';
import { cn } from '@/lib/utils';

interface ExcelPreviewViewerProps {
    /** URL to the Excel file to preview */
    excelUrl: string | null;
    /** Whether the preview is open/visible */
    isOpen: boolean;
    /** Callback when user closes/minimizes the preview */
    onMinimize: () => void;
    /** Class name for positioning */
    className?: string;
}

/**
 * Excel Preview Viewer component that shows an Excel file in a preview panel.
 * Uses Office Online Viewer for rendering the Excel file.
 * 
 * Features:
 * - Zoom in/out (50% - 200%)
 * - Minimize/Maximize
 * - Refresh preview
 */
export function ExcelPreviewViewer({
    excelUrl,
    isOpen,
    onMinimize,
    className,
}: ExcelPreviewViewerProps) {
    const [zoom, setZoom] = useState(100);
    const [isLoading, setIsLoading] = useState(false);
    const [isMaximized, setIsMaximized] = useState(false);
    const [refreshKey, setRefreshKey] = useState(0);

    // Reset loading when URL changes
    useEffect(() => {
        if (excelUrl) {
            setIsLoading(true);
        }
    }, [excelUrl, refreshKey]);

    const handleZoomIn = useCallback(() => {
        setZoom((prev) => Math.min(prev + 25, 200));
    }, []);

    const handleZoomOut = useCallback(() => {
        setZoom((prev) => Math.max(prev - 25, 50));
    }, []);

    const handleRefresh = useCallback(() => {
        setRefreshKey((prev) => prev + 1);
        setIsLoading(true);
    }, []);

    const handleIframeLoad = useCallback(() => {
        setIsLoading(false);
    }, []);

    const toggleMaximize = useCallback(() => {
        setIsMaximized((prev) => !prev);
    }, []);

    if (!isOpen || !excelUrl) {
        return null;
    }

    const urlLower = excelUrl.toLowerCase();
    const isPdf =
        urlLower.includes('.pdf') ||
        urlLower.includes('/pdf_view.pdf') ||
        urlLower.includes('/render_draft.pdf');

    const looksLocal =
        excelUrl.includes('localhost') ||
        excelUrl.includes('127.0.0.1') ||
        excelUrl.includes('0.0.0.0') ||
        excelUrl.startsWith('http://192.168.') ||
        excelUrl.startsWith('http://10.') ||
        excelUrl.startsWith('http://172.16.') ||
        excelUrl.startsWith('http://172.17.') ||
        excelUrl.startsWith('http://172.18.') ||
        excelUrl.startsWith('http://172.19.') ||
        excelUrl.startsWith('http://172.2') ||
        excelUrl.startsWith('http://172.30.') ||
        excelUrl.startsWith('http://172.31.');

    // Office Online Viewer requires the Excel file to be reachable from the public internet.
    // If the URL is local/private, fall back to a download CTA instead of showing "file not found".
    const useOfficeViewer = !isPdf && excelUrl.startsWith('http') && !looksLocal;
    const viewerUrl = useOfficeViewer
        ? `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(excelUrl)}`
        : excelUrl;
    const officeTabUrl = useOfficeViewer
        ? `https://view.officeapps.live.com/op/view.aspx?src=${encodeURIComponent(excelUrl)}`
        : excelUrl;

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0, y: 50, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 50, scale: 0.95 }}
                    transition={{ duration: 0.2 }}
                    className={cn(
                        'bg-slate-900 rounded-lg border border-slate-700 shadow-2xl overflow-hidden',
                        isMaximized
                            ? 'fixed inset-4 z-50'
                            : 'absolute bottom-4 right-4 w-[600px] h-[400px] z-40',
                        className
                    )}
                >
                    {/* Header */}
                    <div className="flex items-center justify-between px-3 py-2 bg-slate-800 border-b border-slate-700">
                        <div className="flex items-center gap-2">
                            <FileSpreadsheet className="w-4 h-4 text-green-500" />
                            <span className="text-sm font-medium text-slate-200">
                                Vista Previa Excel
                            </span>
                            {isLoading && (
                                <Loader2 className="w-4 h-4 animate-spin text-slate-400" />
                            )}
                        </div>

                        {/* Controls */}
                        <div className="flex items-center gap-1">
                            {/* Zoom Controls */}
                            <Button
                                size="sm"
                                variant="ghost"
                                onClick={handleZoomOut}
                                disabled={zoom <= 50}
                                className="p-1 h-7 w-7"
                                title="Zoom Out"
                            >
                                <ZoomOut className="w-3.5 h-3.5" />
                            </Button>
                            <span className="text-xs text-slate-400 w-10 text-center">
                                {zoom}%
                            </span>
                            <Button
                                size="sm"
                                variant="ghost"
                                onClick={handleZoomIn}
                                disabled={zoom >= 200}
                                className="p-1 h-7 w-7"
                                title="Zoom In"
                            >
                                <ZoomIn className="w-3.5 h-3.5" />
                            </Button>

                            <div className="w-px h-4 bg-slate-700 mx-1" />

                            {/* Refresh */}
                            <Button
                                size="sm"
                                variant="ghost"
                                onClick={handleRefresh}
                                className="p-1 h-7 w-7"
                                title="Actualizar"
                            >
                                <RefreshCw className="w-3.5 h-3.5" />
                            </Button>

                            {/* Maximize/Minimize */}
                            <Button
                                size="sm"
                                variant="ghost"
                                onClick={toggleMaximize}
                                className="p-1 h-7 w-7"
                                title={isMaximized ? 'Restaurar' : 'Maximizar'}
                            >
                                {isMaximized ? (
                                    <Minimize2 className="w-3.5 h-3.5" />
                                ) : (
                                    <Maximize2 className="w-3.5 h-3.5" />
                                )}
                            </Button>

                            {/* Close */}
                            <Button
                                size="sm"
                                variant="ghost"
                                onClick={onMinimize}
                                className="p-1 h-7 w-7 hover:bg-red-500/20 hover:text-red-400"
                                title="Minimizar"
                            >
                                <X className="w-3.5 h-3.5" />
                            </Button>
                        </div>
                    </div>

                    {/* Content */}
                    <div
                        className="relative w-full h-[calc(100%-40px)] overflow-auto bg-slate-950"
                        style={{
                            transform: `scale(${zoom / 100})`,
                            transformOrigin: 'top left',
                        }}
                    >
                        {isPdf ? (
                            <iframe
                                key={refreshKey}
                                src={excelUrl}
                                className="w-full h-full border-0"
                                onLoad={handleIframeLoad}
                                title="PDF Preview"
                            />
                        ) : !useOfficeViewer ? (
                            <div className="flex flex-col items-center justify-center h-full gap-4 text-slate-400">
                                <FileSpreadsheet className="w-16 h-16 text-slate-600" />
                                <div className="text-center">
                                    <p className="font-medium">{isPdf ? 'Vista Previa Generada' : 'Archivo Excel Generado'}</p>
                                    <p className="text-sm text-slate-500">
                                        {isPdf ? 'La previsualización se muestra como PDF dentro del panel' : 'Usa el botón \"Descargar Excel\" para ver el archivo'}
                                    </p>
                                </div>
                                <Button
                                    variant="secondary"
                                    onClick={() => window.open(excelUrl, '_blank')}
                                >
                                    {isPdf ? 'Abrir PDF' : 'Descargar Excel'}
                                </Button>
                            </div>
                        ) : (
                            <div className="w-full h-full flex flex-col">
                                <div className="px-3 py-2 border-b border-slate-800 flex items-center justify-end gap-2">
                                    <Button
                                        size="sm"
                                        variant="secondary"
                                        onClick={() => window.open(officeTabUrl, '_blank', 'noopener,noreferrer')}
                                    >
                                        Abrir en Office
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="secondary"
                                        onClick={() => window.open(excelUrl, '_blank', 'noopener,noreferrer')}
                                    >
                                        Abrir XLSX
                                    </Button>
                                </div>
                                <iframe
                                    key={refreshKey}
                                    src={viewerUrl}
                                    className="w-full flex-1 border-0"
                                    onLoad={handleIframeLoad}
                                    title="Excel Preview"
                                    sandbox="allow-scripts allow-same-origin allow-popups allow-forms allow-downloads allow-top-navigation-by-user-activation"
                                />
                            </div>
                        )}
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}

export default ExcelPreviewViewer;

