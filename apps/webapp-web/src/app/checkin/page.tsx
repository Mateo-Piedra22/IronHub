'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import {
    ScanLine,
    CheckCircle2,
    XCircle,
    User,
    Clock,
    LogOut,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import { Html5Qrcode } from 'html5-qrcode';

interface CheckinResult {
    success: boolean;
    message: string;
    userName?: string;
    userDni?: string;
    timestamp?: string;
}

export default function CheckinPage() {
    // Auth state
    const [authenticated, setAuthenticated] = useState(false);
    const [authDni, setAuthDni] = useState('');
    const [authLoading, setAuthLoading] = useState(false);
    const [authError, setAuthError] = useState('');

    // User info
    const [userInfo, setUserInfo] = useState<{
        cuotasVencidas?: number;
        diasRestantes?: number;
        fechaVencimiento?: string;
        exento?: boolean;
        activo?: boolean;
    } | null>(null);

    // Scanner state
    const [scanning, setScanning] = useState(false);
    const [lastResult, setLastResult] = useState<CheckinResult | null>(null);
    const [recentCheckins, setRecentCheckins] = useState<Array<{ name: string; dni: string; time: string }>>([]);

    const scannerRef = useRef<Html5Qrcode | null>(null);
    const autoSubmitAttempted = useRef(false);
    const logoutInProgress = useRef(false);
    const startScanningRef = useRef<(() => void) | null>(null);

    const makeIdempotencyKey = useCallback(() => {
        try {
            const id = globalThis.crypto?.randomUUID?.();
            if (id) return id;
        } catch {}
        return `${Date.now()}-${Math.random().toString(16).slice(2)}-${Math.random().toString(16).slice(2)}`;
    }, []);

    // Restore saved credentials
    useEffect(() => {
        try {
            const saved = localStorage.getItem('checkin_saved_user');
            if (saved) {
                const data = JSON.parse(saved);
                if (data.dni) setAuthDni(data.dni);
            }
        } catch {}
    }, []);

    // Auth submit with DNI only
    const handleAuth = useCallback(async (e: React.FormEvent) => {
        e.preventDefault();
        setAuthError('');

        const dni = authDni.replace(/\D/g, '');

        if (!dni) {
            setAuthError('Ingresá un DNI válido');
            return;
        }

        setAuthLoading(true);

        try {
            const res = await api.checkinAuth({ dni });

            if (res.ok && res.data?.success) {
                // Save for future use
                try {
                    localStorage.setItem('checkin_saved_user', JSON.stringify({
                        dni,
                        usuario_id: res.data.usuario_id || null,
                    }));
                } catch { }

                // Store user info for quota warnings
                setUserInfo({
                    cuotasVencidas: res.data.cuotas_vencidas,
                    diasRestantes: res.data.dias_restantes,
                    fechaVencimiento: res.data.fecha_proximo_vencimiento,
                    exento: res.data.exento,
                    activo: res.data.activo,
                });

                setAuthenticated(true);
            } else {
                setAuthError(res.error || res.data?.message || 'DNI no encontrado');
            }
        } catch {
            setAuthError('Error de conexión');
        } finally {
            setAuthLoading(false);
        }
    }, [authDni]);

    // Auto-submit support - hardened to prevent loops
    useEffect(() => {
        if (autoSubmitAttempted.current || logoutInProgress.current || authenticated || authLoading) {
            return;
        }

        const query = new URLSearchParams(window.location.search);
        const isAutoMode = query.get('auto') === 'true';

        if (!isAutoMode) return;

        const cleanDni = authDni.replace(/\D/g, '');
        if (!cleanDni || cleanDni.length < 6) {
            return;
        }

        autoSubmitAttempted.current = true;

        const url = new URL(window.location.href);
        url.searchParams.delete('auto');
        window.history.replaceState({}, '', url.toString());

        const fakeEvent = { preventDefault: () => {} } as React.FormEvent;
        void handleAuth(fakeEvent);
    }, [authDni, authenticated, authLoading, handleAuth]);

    const asRecord = (v: unknown): Record<string, unknown> | null => {
        if (!v || typeof v !== 'object') return null;
        return v as Record<string, unknown>;
    };

    const getString = (obj: Record<string, unknown> | null, key: string): string | null => {
        if (!obj) return null;
        const v = obj[key];
        return typeof v === 'string' ? v : null;
    };

    const playSuccessSound = useCallback(() => {
        try {
            const WebkitAudioContext = (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
            const AudioContextCtor = window.AudioContext || WebkitAudioContext;
            if (!AudioContextCtor) return;
            const ctx = new AudioContextCtor();
            const oscillator = ctx.createOscillator();
            const gainNode = ctx.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(ctx.destination);

            oscillator.frequency.value = 880;
            oscillator.type = 'sine';
            gainNode.gain.setValueAtTime(0.3, ctx.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);

            oscillator.start(ctx.currentTime);
            oscillator.stop(ctx.currentTime + 0.3);
        } catch {}
    }, []);

    const handleQRScanned = useCallback(
        async (token: string) => {
            const idemKey = makeIdempotencyKey();
            let raw = String(token || '').trim();
            try {
                if (raw.includes('token=')) {
                    const qsPart = raw.includes('?') ? raw.split('?', 2)[1] : raw;
                    const params = new URLSearchParams(qsPart);
                    const t = params.get('token');
                    if (t) raw = t.trim();
                }
            } catch {}

            if (scannerRef.current) {
                await scannerRef.current.stop().catch(() => {});
                setScanning(false);
            }

            try {
                const resCheckin = await api.checkIn(raw, idemKey);

                if (resCheckin.ok && resCheckin.data?.ok) {
                    const branch = getString(asRecord(resCheckin.data), 'sucursal_nombre');
                    setLastResult({
                        success: true,
                        message: `${resCheckin.data?.mensaje || 'OK'}${branch ? ` • ${branch}` : ''}`,
                    });
                    playSuccessSound();
                } else {
                    const res = await api.scanStationQR(raw, idemKey);

                    if (res.ok && res.data?.ok) {
                        const timestamp = new Date().toLocaleTimeString('es-AR');
                        const result: CheckinResult = {
                            success: true,
                            message: res.data.mensaje || '¡Check-in exitoso!',
                            userName: res.data.usuario?.nombre || 'Usuario',
                            userDni: res.data.usuario?.dni || '',
                            timestamp,
                        };
                        setLastResult(result);

                        setRecentCheckins((prev) => [
                            { name: result.userName || 'Usuario', dni: result.userDni || '', time: timestamp },
                            ...prev.slice(0, 4),
                        ]);

                        playSuccessSound();
                    } else {
                        setLastResult({
                            success: false,
                            message: res.data?.mensaje || res.error || resCheckin.error || 'Error al escanear',
                        });
                    }
                }
            } catch {
                setLastResult({
                    success: false,
                    message: 'Error de conexión',
                });
            }

            setTimeout(() => {
                setLastResult(null);
                startScanningRef.current?.();
            }, 3000);
        },
        [makeIdempotencyKey, playSuccessSound]
    );

    const startScanning = useCallback(async () => {
        if (!scannerRef.current || scanning) return;

        try {
            setScanning(true);
            await scannerRef.current.start(
                { facingMode: 'environment' },
                {
                    fps: 10,
                    qrbox: { width: 250, height: 250 },
                    aspectRatio: 1,
                },
                async (decodedText) => {
                    await handleQRScanned(decodedText);
                },
                () => {}
            );
        } catch {
            setScanning(false);
        }
    }, [handleQRScanned, scanning]);

    startScanningRef.current = () => {
        void startScanning();
    };

    useEffect(() => {
        if (!authenticated) return;

        const initScanner = async () => {
            try {
                scannerRef.current = new Html5Qrcode('qr-scanner-container');
                await startScanning();
            } catch {}
        };

        const timer = setTimeout(() => {
            void initScanner();
        }, 500);

        return () => {
            clearTimeout(timer);
            if (scannerRef.current && scanning) {
                scannerRef.current.stop().catch(() => {});
            }
        };
    }, [authenticated, scanning, startScanning]);

    // Logout
    const handleLogout = async () => {
        // Prevent re-entry and block auto-submit
        if (logoutInProgress.current) return;
        logoutInProgress.current = true;

        // Stop scanner first
        if (scannerRef.current && scanning) {
            await scannerRef.current.stop().catch(() => { });
        }

        // Clear session on backend
        await api.logout();

        // Remove 'auto' param to prevent immediate re-login loop
        const url = new URL(window.location.href);
        if (url.searchParams.get('auto')) {
            url.searchParams.delete('auto');
            window.history.replaceState({}, '', url.toString());
        }

        // Clear saved credentials to prevent auto re-login on reload
        try {
            localStorage.removeItem('checkin_saved_user');
        } catch { }

        // Reset all auth state
        setAuthDni('');
        setAuthenticated(false);
        setUserInfo(null);
        setScanning(false);

        // Reset refs
        autoSubmitAttempted.current = false;
        logoutInProgress.current = false;

        // Redirect to home page to fully exit check-in flow
        window.location.href = '/';
    };

    // Get quota warning message
    const getQuotaWarning = () => {
        if (!userInfo || userInfo.exento) return null;

        const { cuotasVencidas, diasRestantes, fechaVencimiento } = userInfo;

        if (cuotasVencidas && cuotasVencidas > 0) {
            return { type: 'error', message: 'Tu cuota está vencida. Regularizá el pago para entrenar.' };
        }

        if (diasRestantes !== undefined && diasRestantes <= 3) {
            const dMsg = diasRestantes < 0
                ? 'vencida'
                : (diasRestantes === 0 ? 'vence hoy' : `vence en ${diasRestantes} día${diasRestantes === 1 ? '' : 's'}`);
            return {
                type: 'warning',
                message: `Atención: tu cuota ${dMsg}${fechaVencimiento ? ` (${fechaVencimiento})` : ''}.`
            };
        }

        return null;
    };

    const quotaWarning = getQuotaWarning();

    // Auth screen
    if (!authenticated) {
        return (
            <div className="min-h-screen flex items-center justify-center p-4 bg-slate-950">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="w-full max-w-md"
                >
                    <div className="text-center mb-8">
                        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-success-500 to-success-600 shadow-md mb-4">
                            <ScanLine className="w-8 h-8 text-white" />
                        </div>
                        <h1 className="text-2xl font-display font-bold text-white">Check-in</h1>
                        <p className="text-slate-400 mt-1">Ingresá tu DNI para escanear el QR</p>
                    </div>

                    <div className="card p-8">
                        <form onSubmit={handleAuth} className="space-y-4">
                            {/* DNI */}
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">DNI</label>
                                <div className="relative">
                                    <input
                                        type="text"
                                        inputMode="numeric"
                                        value={authDni}
                                        onChange={(e) => setAuthDni(e.target.value)}
                                        className="w-full px-4 py-3 pl-11 rounded-xl bg-slate-900 border border-slate-800 text-white focus:ring-2 focus:ring-success-500/50 focus:border-success-500 transition-all"
                                        placeholder="Ingresá tu DNI"
                                        autoComplete="off"
                                        autoFocus
                                    />
                                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                                </div>
                            </div>

                            {authError && (
                                <div className="p-3 rounded-xl bg-danger-500/10 border border-danger-500/30 text-danger-400 text-sm">
                                    {authError}
                                </div>
                            )}

                            <button
                                type="submit"
                                disabled={authLoading}
                                className="w-full py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-success-500 to-success-600 hover:shadow-md transition-all disabled:opacity-50"
                            >
                                {authLoading ? 'Verificando...' : 'Continuar'}
                            </button>

                            {/* Back button */}
                            <Link href="/" className="block w-full py-3 rounded-xl font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 text-center transition-all">
                                ← Volver al inicio
                            </Link>
                        </form>
                    </div>
                </motion.div>
            </div>
        );
    }

    // Main scanner screen
    return (
        <div className="min-h-screen bg-slate-950 flex flex-col">
            {/* Header */}
            <header className="flex items-center justify-between p-4 border-b border-slate-800">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-success-500 to-success-600 flex items-center justify-center">
                        <ScanLine className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h1 className="text-lg font-display font-bold text-white">Check-in</h1>
                        <p className="text-xs text-slate-500">Escanea el código QR</p>
                    </div>
                </div>
                <button
                    onClick={handleLogout}
                    className="p-2 rounded-lg text-slate-400 hover:text-danger-400 hover:bg-danger-500/10 transition-colors"
                >
                    <LogOut className="w-5 h-5" />
                </button>
            </header>

            {/* Quota warning toast */}
            {quotaWarning && (
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={cn(
                        'mx-4 mt-4 p-3 rounded-xl text-sm',
                        quotaWarning.type === 'error'
                            ? 'bg-danger-500/10 border border-danger-500/30 text-danger-400'
                            : 'bg-warning-500/10 border border-warning-500/30 text-warning-400'
                    )}
                >
                    {quotaWarning.message}
                </motion.div>
            )}

            {/* Scanner area */}
            <main className="flex-1 flex flex-col items-center justify-center p-4">
                <div className="relative w-full max-w-sm">
                    {/* Scanner container */}
                    <div className="relative aspect-square rounded-2xl overflow-hidden bg-slate-900 border-2 border-slate-700">
                        <div id="qr-scanner-container" className="w-full h-full" />

                        {/* Scanning indicator */}
                        {scanning && !lastResult && (
                            <div className="absolute inset-0 pointer-events-none">
                                <div className="absolute inset-4 border-2 border-success-400 rounded-xl">
                                    <motion.div
                                        className="absolute left-0 right-0 h-0.5 bg-success-400"
                                        animate={{ top: ['0%', '100%', '0%'] }}
                                        transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                                    />
                                </div>
                            </div>
                        )}

                        {/* Result overlay */}
                        <AnimatePresence>
                            {lastResult && (
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                    className={cn(
                                        'absolute inset-0 flex flex-col items-center justify-center p-6',
                                        lastResult.success ? 'bg-success-500' : 'bg-danger-500'
                                    )}
                                >
                                    <motion.div
                                        initial={{ scale: 0 }}
                                        animate={{ scale: 1 }}
                                        transition={{ type: 'spring', damping: 15 }}
                                    >
                                        {lastResult.success ? (
                                            <CheckCircle2 className="w-20 h-20 text-white" />
                                        ) : (
                                            <XCircle className="w-20 h-20 text-white" />
                                        )}
                                    </motion.div>

                                    <p className="text-white text-xl font-bold mt-4 text-center">
                                        {lastResult.success ? '¡Check-in exitoso!' : lastResult.message}
                                    </p>

                                    {lastResult.success && lastResult.userName && (
                                        <div className="mt-4 text-center">
                                            <p className="text-white/90 text-2xl font-semibold">{lastResult.userName}</p>
                                            {lastResult.userDni && (
                                                <p className="text-white/70 text-lg mt-1">DNI: {lastResult.userDni}</p>
                                            )}
                                            {lastResult.timestamp && (
                                                <p className="text-white/60 text-sm mt-2 flex items-center justify-center gap-2">
                                                    <Clock className="w-4 h-4" />
                                                    {lastResult.timestamp}
                                                </p>
                                            )}
                                        </div>
                                    )}
                                </motion.div>
                            )}
                        </AnimatePresence>

                        {/* Loading state */}
                        {!scanning && !lastResult && (
                            <div className="absolute inset-0 flex items-center justify-center bg-slate-900">
                                <div className="text-center">
                                    <ScanLine className="w-12 h-12 text-slate-600 mx-auto mb-4 animate-pulse" />
                                    <p className="text-slate-500">Iniciando cámara...</p>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Instructions */}
                    <p className="text-center text-slate-400 text-sm mt-4">
                        Apunta la cámara al código QR que se muestra en la pantalla del gimnasio
                    </p>
                </div>

                {/* Recent check-ins */}
                {recentCheckins.length > 0 && (
                    <div className="w-full max-w-sm mt-8">
                        <h2 className="text-sm font-medium text-slate-400 mb-3 flex items-center gap-2">
                            <Clock className="w-4 h-4" />
                            Últimos Check-ins
                        </h2>
                        <div className="space-y-2">
                            {recentCheckins.map((c, i) => (
                                <div
                                    key={i}
                                    className="flex items-center justify-between p-3 rounded-xl bg-slate-900/50 border border-slate-800"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-full bg-success-500/20 flex items-center justify-center">
                                            <User className="w-4 h-4 text-success-400" />
                                        </div>
                                        <div>
                                            <span className="text-white text-sm">{c.name}</span>
                                            <p className="text-xs text-slate-500">DNI: {c.dni}</p>
                                        </div>
                                    </div>
                                    <span className="text-xs text-slate-500">{c.time}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}
