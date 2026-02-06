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
        } catch (e: unknown) {
            setCameras([]);
            setScanError(
                e instanceof Error ? e.message : 'No se pudo acceder a cámaras. Verifica permisos del navegador.'
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
                        if (typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function') {
                            navigator.vibrate([40, 30, 40]);
                        }
                    } catch {
                    }
                    try {
                        const w = window as Window & { webkitAudioContext?: typeof AudioContext };
                        const AudioCtx = window.AudioContext || w.webkitAudioContext;
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
        } catch (e: unknown) {
            setRunning(false);
            setScanError(
                e instanceof Error ? e.message : 'No se pudo iniciar la cámara. Verifica permisos y que estés en HTTPS.'
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
                className="fixed inset-0 z-50 bg-slate-950/90 backdrop-blur-md"
            >
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(59,130,246,0.12),transparent_55%)]" />
                <div className="relative z-10 flex flex-col h-full">
                    <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
                        <div>
                            <div className="text-white font-semibold">Escanear QR</div>
                            <div className="text-xs text-slate-400">{description || 'Apuntá tu cámara al código QR de la rutina'}</div>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-2 rounded-xl bg-white/5 border border-white/10 text-slate-200 hover:bg-white/10"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    <div className="flex-1 flex flex-col items-center justify-center gap-4 px-5 py-6">
                        <div className="w-full max-w-md">
                            <div className="relative w-full aspect-square rounded-3xl overflow-hidden border border-slate-800 bg-black shadow-elevated">
                                <div id={readerId} className="absolute inset-0" />
                                <div className="absolute inset-0 pointer-events-none">
                                    <div className="absolute inset-0 bg-gradient-to-b from-black/30 via-transparent to-black/40" />
                                    <div className="absolute left-1/2 top-1/2 w-[80%] h-[80%] -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-white/20" />
                                    <div className="absolute left-1/2 top-1/2 w-[80%] h-[80%] -translate-x-1/2 -translate-y-1/2">
                                        <div className="absolute -left-1 -top-1 w-8 h-8 border-l-2 border-t-2 border-primary-400 rounded-tl-2xl" />
                                        <div className="absolute -right-1 -top-1 w-8 h-8 border-r-2 border-t-2 border-primary-400 rounded-tr-2xl" />
                                        <div className="absolute -left-1 -bottom-1 w-8 h-8 border-l-2 border-b-2 border-primary-400 rounded-bl-2xl" />
                                        <div className="absolute -right-1 -bottom-1 w-8 h-8 border-r-2 border-b-2 border-primary-400 rounded-br-2xl" />
                                        <motion.div
                                            className="absolute left-3 right-3 h-px bg-gradient-to-r from-transparent via-primary-300 to-transparent opacity-80"
                                            animate={{ top: ['16%', '84%', '16%'] }}
                                            transition={{ duration: 2.1, repeat: Infinity, ease: 'easeInOut' }}
                                        />
                                    </div>
                                    {pulse ? (
                                        <div className="absolute inset-0 bg-emerald-500/10" />
                                    ) : null}
                                </div>
                            </div>

                            {scanError ? (
                                <div className="mt-3 text-xs text-red-200 bg-red-500/10 border border-red-500/20 rounded-xl p-3">
                                    {scanError}
                                </div>
                            ) : (
                                <div className="mt-3 text-xs text-slate-400">
                                    El escaneo es automático. Si no inicia, seleccioná la cámara e iniciá.
                                </div>
                            )}
                        </div>

                        <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/60 p-4 space-y-3">
                            {cameras.length > 0 ? (
                                <div className="flex items-center gap-2">
                                    <span className="text-xs text-slate-500 w-14">Cámara</span>
                                    <select
                                        className="bg-slate-950/30 border border-slate-800 text-slate-200 text-xs rounded-xl px-3 py-2 flex-1"
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
                            ) : null}

                            <div className="flex items-center justify-between gap-2">
                                {!running ? (
                                    <Button onClick={start} isLoading={starting} className="w-full">
                                        Iniciar cámara
                                    </Button>
                                ) : (
                                    <Button variant="secondary" onClick={stop} className="w-full">
                                        Detener
                                    </Button>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </motion.div>
        </AnimatePresence>
    );
}
