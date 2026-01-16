import { useEffect, useMemo, useRef, useState } from 'react';
import { Html5Qrcode, type CameraDevice } from 'html5-qrcode';
import { X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui';

interface QRScannerModalProps {
    isOpen: boolean;
    onClose: () => void;
    onScan: (decodedText: string) => void;
    description?: string;
}

export function QRScannerModal({ isOpen, onClose, onScan, description }: QRScannerModalProps) {
    const readerId = useMemo(() => `qr-reader-${Math.random().toString(36).slice(2)}`, []);
    const qrRef = useRef<Html5Qrcode | null>(null);
    const [cameras, setCameras] = useState<CameraDevice[]>([]);
    const [selectedCameraId, setSelectedCameraId] = useState<string>('');
    const [starting, setStarting] = useState(false);
    const [running, setRunning] = useState(false);
    const [scanError, setScanError] = useState<string>('');
    const [pulse, setPulse] = useState(false);

    useEffect(() => {
        if (!isOpen) return;
        setScanError('');
        setStarting(false);
        setRunning(false);

        if (!qrRef.current) {
            qrRef.current = new Html5Qrcode(readerId, false);
        }

        return () => {
            const qr = qrRef.current;
            qrRef.current = null;
            setCameras([]);
            setSelectedCameraId('');
            setStarting(false);
            setRunning(false);
            setScanError('');

            if (!qr) return;
            const stop = async () => {
                try {
                    if (qr.isScanning) {
                        await qr.stop();
                    }
                } catch {
                }
                try {
                    await qr.clear();
                } catch {
                }
            };
            void stop();
        };
    }, [isOpen, readerId]);

    const loadCameras = async () => {
        try {
            const list = await Html5Qrcode.getCameras();
            setCameras(list || []);
            if (!selectedCameraId && list && list.length > 0) {
                setSelectedCameraId(list[list.length - 1].id);
            }
        } catch (e: any) {
            setCameras([]);
            setScanError(
                typeof e?.message === 'string'
                    ? e.message
                    : 'No se pudo acceder a cámaras. Verifica permisos del navegador.'
            );
        }
    };

    const start = async () => {
        const qr = qrRef.current;
        if (!qr) return;
        setScanError('');
        setStarting(true);
        try {
            if (cameras.length === 0) {
                await loadCameras();
            }

            const config = {
                fps: 12,
                qrbox: { width: 260, height: 260 },
                aspectRatio: 1.0,
                disableFlip: false,
            };

            const onSuccess = (decodedText: string) => {
                try {
                    try {
                        if (typeof navigator !== 'undefined' && 'vibrate' in navigator) {
                            (navigator as any).vibrate?.([40, 30, 40]);
                        }
                    } catch {
                    }
                    try {
                        const AudioCtx = (window as any).AudioContext || (window as any).webkitAudioContext;
                        if (AudioCtx) {
                            const ctx = new AudioCtx();
                            const o = ctx.createOscillator();
                            const g = ctx.createGain();
                            o.type = 'sine';
                            o.frequency.value = 880;
                            g.gain.setValueAtTime(0.0001, ctx.currentTime);
                            g.gain.exponentialRampToValueAtTime(0.15, ctx.currentTime + 0.02);
                            g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.18);
                            o.connect(g);
                            g.connect(ctx.destination);
                            o.start();
                            o.stop(ctx.currentTime + 0.2);
                            o.onended = () => {
                                try { ctx.close(); } catch { }
                            };
                        }
                    } catch {
                    }
                    setPulse(true);
                    window.setTimeout(() => setPulse(false), 450);
                    onScan(decodedText);
                } finally {
                    onClose();
                }
            };

            const onError = () => {
            };

            if (selectedCameraId) {
                await qr.start({ deviceId: { exact: selectedCameraId } }, config, onSuccess, onError);
            } else {
                await qr.start({ facingMode: 'environment' }, config, onSuccess, onError);
            }
            setRunning(true);
        } catch (e: any) {
            setRunning(false);
            setScanError(
                typeof e?.message === 'string'
                    ? e.message
                    : 'No se pudo iniciar la cámara. Verifica permisos y que estés en HTTPS.'
            );
        } finally {
            setStarting(false);
        }
    };

    const stop = async () => {
        const qr = qrRef.current;
        if (!qr) return;
        try {
            if (qr.isScanning) {
                await qr.stop();
            }
        } catch {
        } finally {
            setRunning(false);
        }
    };

    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
            >
                <motion.div
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="bg-slate-900 rounded-2xl w-full max-w-md overflow-hidden border border-slate-800"
                >
                    <div className="p-4 border-b border-slate-800 flex justify-between items-center">
                        <h3 className="font-semibold text-white">Escanear Rutina</h3>
                        <button onClick={onClose} className="p-2 hover:bg-slate-800 rounded-full text-slate-400 hover:text-white">
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    <div className="p-4 bg-black space-y-3">
                        <div className="flex items-center justify-between gap-2">
                            <div className="text-xs text-slate-400">
                                {description || 'Apuntá tu cámara al código QR de la rutina'}
                            </div>
                            <div className="flex items-center gap-2">
                                {!running ? (
                                    <Button size="sm" onClick={start} isLoading={starting}>
                                        Iniciar cámara
                                    </Button>
                                ) : (
                                    <Button size="sm" variant="secondary" onClick={stop}>
                                        Detener
                                    </Button>
                                )}
                            </div>
                        </div>

                        {cameras.length > 0 && (
                            <div className="flex items-center gap-2">
                                <span className="text-xs text-slate-500">Cámara</span>
                                <select
                                    className="bg-slate-900 border border-slate-800 text-slate-200 text-xs rounded-lg px-2 py-1 flex-1"
                                    value={selectedCameraId}
                                    onChange={(e) => setSelectedCameraId(e.target.value)}
                                    disabled={running}
                                >
                                    {cameras.map((c) => (
                                        <option key={c.id} value={c.id}>
                                            {c.label || c.id}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        )}

                        <div className="rounded-xl overflow-hidden border border-slate-800 bg-black">
                            <div className="relative w-full">
                                <div id={readerId} className="w-full" />
                                <div className="pointer-events-none absolute inset-0">
                                    <div className="absolute inset-0 qr-mask" />
                                    <div className="absolute inset-0 flex items-center justify-center">
                                        <div className={`qr-frame ${pulse ? 'qr-pulse' : ''}`}>
                                            <span className="qr-corner tl" />
                                            <span className="qr-corner tr" />
                                            <span className="qr-corner bl" />
                                            <span className="qr-corner br" />
                                            <span className="qr-line" />
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {scanError && (
                            <div className="text-xs text-red-300 bg-red-500/10 border border-red-500/20 rounded-lg p-2">
                                {scanError}
                            </div>
                        )}
                    </div>
                </motion.div>
            </motion.div>
            <style jsx>{`
                .qr-mask {
                    background:
                        radial-gradient(circle at center,
                            rgba(0,0,0,0) 0,
                            rgba(0,0,0,0) 34%,
                            rgba(0,0,0,0.55) 35%,
                            rgba(0,0,0,0.72) 100%);
                }
                .qr-frame {
                    position: relative;
                    width: 78%;
                    max-width: 320px;
                    aspect-ratio: 1 / 1;
                    border-radius: 18px;
                    border: 1px solid rgba(148, 163, 184, 0.35);
                    box-shadow: 0 0 0 1px rgba(2, 132, 199, 0.15) inset, 0 0 30px rgba(2, 132, 199, 0.08);
                }
                .qr-corner {
                    position: absolute;
                    width: 34px;
                    height: 34px;
                    border-color: rgba(34, 211, 238, 0.95);
                }
                .qr-corner.tl { top: -1px; left: -1px; border-top: 3px solid; border-left: 3px solid; border-top-left-radius: 18px; }
                .qr-corner.tr { top: -1px; right: -1px; border-top: 3px solid; border-right: 3px solid; border-top-right-radius: 18px; }
                .qr-corner.bl { bottom: -1px; left: -1px; border-bottom: 3px solid; border-left: 3px solid; border-bottom-left-radius: 18px; }
                .qr-corner.br { bottom: -1px; right: -1px; border-bottom: 3px solid; border-right: 3px solid; border-bottom-right-radius: 18px; }
                .qr-line {
                    position: absolute;
                    left: 12px;
                    right: 12px;
                    top: 18%;
                    height: 2px;
                    background: linear-gradient(90deg, rgba(34,211,238,0), rgba(34,211,238,0.9), rgba(34,211,238,0));
                    filter: drop-shadow(0 0 8px rgba(34,211,238,0.55));
                    animation: qr-scan 1.55s ease-in-out infinite;
                }
                .qr-pulse {
                    box-shadow:
                        0 0 0 2px rgba(34, 197, 94, 0.45) inset,
                        0 0 0 1px rgba(34, 197, 94, 0.35),
                        0 0 42px rgba(34, 197, 94, 0.22);
                    border-color: rgba(34, 197, 94, 0.55);
                    animation: qr-pulse 0.45s ease-out 1;
                }
                @keyframes qr-scan {
                    0% { transform: translateY(0); opacity: 0.75; }
                    50% { opacity: 1; }
                    100% { transform: translateY(260%); opacity: 0.75; }
                }
                @keyframes qr-pulse {
                    0% { transform: scale(1); }
                    50% { transform: scale(1.02); }
                    100% { transform: scale(1); }
                }
            `}</style>
        </AnimatePresence>
    );
}
