'use client';

import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, X, Film, Loader2, Play } from 'lucide-react';
import { cn } from '@/lib/utils';

interface VideoDropzoneProps {
    value?: string;
    onUpload: (file: File) => Promise<string>;
    onClear: () => void;
    className?: string;
}

export function VideoDropzone({ value, onUpload, onClear, className }: VideoDropzoneProps) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const onDrop = useCallback(async (acceptedFiles: File[]) => {
        const file = acceptedFiles[0];
        if (!file) return;

        if (file.size > 50 * 1024 * 1024) {
            setError('El archivo es demasiado grande (máx 50MB)');
            return;
        }

        setLoading(true);
        setError(null);
        try {
            await onUpload(file);
        } catch (e) {
            setError('Error al subir el video');
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, [onUpload]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'video/*': ['.mp4', '.webm', '.mov'],
            'image/gif': ['.gif']
        },
        maxFiles: 1,
        disabled: loading || !!value
    });

    if (value) {
        return (
            <div className={cn("relative rounded-xl overflow-hidden bg-slate-900 border border-slate-800 group", className)}>
                <video
                    src={value}
                    className="w-full h-full object-cover max-h-[300px]"
                    controls
                />
                <button
                    onClick={(e) => {
                        e.preventDefault();
                        onClear();
                    }}
                    className="absolute top-2 right-2 p-1.5 bg-slate-900/80 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-danger-500"
                >
                    <X className="w-4 h-4" />
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-2">
            <div
                {...getRootProps()}
                className={cn(
                    "border-2 border-dashed rounded-xl p-8 transition-colors cursor-pointer flex flex-col items-center justify-center min-h-[200px] text-center",
                    isDragActive ? "border-primary-500 bg-primary-500/10" : "border-slate-800 bg-slate-900/50 hover:border-slate-700 hover:bg-slate-900",
                    error && "border-danger-500/50 bg-danger-500/5",
                    className
                )}
            >
                <input {...getInputProps()} />
                {loading ? (
                    <div className="flex flex-col items-center gap-3 text-slate-400">
                        <Loader2 className="w-10 h-10 animate-spin text-primary-500" />
                        <p className="text-sm font-medium">Subiendo video...</p>
                    </div>
                ) : (
                    <>
                        <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mb-4 group-hover:bg-slate-700 transition-colors">
                            <UploadCloud className="w-6 h-6 text-slate-400 group-hover:text-primary-400 transition-colors" />
                        </div>
                        <p className="text-sm font-medium text-white mb-1">
                            {isDragActive ? "Suelta el video aquí" : "Arrastra un video o haz clic"}
                        </p>
                        <p className="text-xs text-slate-500 max-w-[200px]">
                            MP4, WebM o GIF (máx. 50MB). Formato horizontal recomendado.
                        </p>
                    </>
                )}
            </div>
            {error && (
                <p className="text-xs text-danger-400 text-center animate-in fade-in slide-in-from-top-1">
                    {error}
                </p>
            )}
        </div>
    );
}

