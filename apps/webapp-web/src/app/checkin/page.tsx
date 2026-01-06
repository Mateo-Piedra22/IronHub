'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    ScanLine,
    CheckCircle2,
    XCircle,
    Camera,
    Keyboard,
    User,
    Clock,
    LogOut,
    Phone,
    ChevronDown,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

type ScanStatus = 'idle' | 'scanning' | 'processing' | 'success' | 'error';

interface CheckinResult {
    success: boolean;
    message: string;
    userName?: string;
    timestamp?: string;
}

const COUNTRY_PREFIXES = [
    { code: '+54', country: 'Argentina' },
    { code: '+598', country: 'Uruguay' },
    { code: '+56', country: 'Chile' },
    { code: '+595', country: 'Paraguay' },
    { code: '+55', country: 'Brasil' },
    { code: '+1', country: 'Estados Unidos' },
    { code: '+34', country: 'España' },
];

export default function CheckinPage() {
    // Auth state
    const [authenticated, setAuthenticated] = useState(false);
    const [authDni, setAuthDni] = useState('');
    const [authPhone, setAuthPhone] = useState('');
    const [countryPrefix, setCountryPrefix] = useState('+54');
    const [showPrefixSelector, setShowPrefixSelector] = useState(false);
    const [authLoading, setAuthLoading] = useState(false);
    const [authError, setAuthError] = useState('');

    // User quota info
    const [userInfo, setUserInfo] = useState<{
        cuotasVencidas?: number;
        diasRestantes?: number;
        fechaVencimiento?: string;
        exento?: boolean;
        activo?: boolean;
    } | null>(null);

    // Scanner state
    const [mode, setMode] = useState<'camera' | 'manual'>('manual');
    const [scanStatus, setScanStatus] = useState<ScanStatus>('idle');
    const [lastResult, setLastResult] = useState<CheckinResult | null>(null);
    const [manualToken, setManualToken] = useState('');
    const [recentCheckins, setRecentCheckins] = useState<Array<{ name: string; time: string }>>([]);

    const videoRef = useRef<HTMLVideoElement>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    // Restore saved credentials
    useEffect(() => {
        try {
            const saved = localStorage.getItem('checkin_saved_user');
            if (saved) {
                const data = JSON.parse(saved);
                if (data.dni) setAuthDni(data.dni);
                if (data.telefono) setAuthPhone(data.telefono);
            }
        } catch { }
    }, []);

    // Auth submit with DNI + phone
    const handleAuth = async (e: React.FormEvent) => {
        e.preventDefault();
        setAuthError('');

        const dni = authDni.replace(/\D/g, '');
        const telefono = authPhone.replace(/\D/g, '');

        if (!dni || !telefono) {
            setAuthError('Ingresá DNI y teléfono válidos');
            return;
        }

        setAuthLoading(true);

        try {
            const res = await api.checkinAuth({ dni, telefono });

            if (res.ok && res.data?.success) {
                // Save for future use
                try {
                    localStorage.setItem('checkin_saved_user', JSON.stringify({
                        dni,
                        telefono,
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
                setAuthError(res.error || res.data?.message || 'Credenciales inválidas');
            }
        } catch {
            setAuthError('Error de conexión');
        } finally {
            setAuthLoading(false);
        }
    };

    // Start camera
    const startCamera = useCallback(async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment' },
            });
            streamRef.current = stream;
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
            }
            setScanStatus('scanning');
        } catch (err) {
            console.error('Camera error:', err);
            setMode('manual');
        }
    }, []);

    // Stop camera
    const stopCamera = useCallback(() => {
        if (streamRef.current) {
            streamRef.current.getTracks().forEach((track) => track.stop());
            streamRef.current = null;
        }
    }, []);

    // Handle mode change
    useEffect(() => {
        if (authenticated && mode === 'camera') {
            startCamera();
        } else {
            stopCamera();
        }
        return () => stopCamera();
    }, [authenticated, mode, startCamera, stopCamera]);

    // Focus input on mount and mode change
    useEffect(() => {
        if (authenticated && mode === 'manual' && inputRef.current) {
            inputRef.current.focus();
        }
    }, [authenticated, mode, scanStatus]);

    // Process token (from QR or manual - using DNI)
    const processToken = useCallback(async (token: string) => {
        if (!token.trim()) return;

        // Check if user is inactive
        if (userInfo && !userInfo.exento && userInfo.activo === false) {
            setLastResult({
                success: false,
                message: 'Cuenta desactivada. No podés registrar asistencia.',
            });
            setScanStatus('error');
            setTimeout(() => {
                setScanStatus('idle');
                setLastResult(null);
            }, 3000);
            return;
        }

        setScanStatus('processing');
        try {
            const res = await api.checkInByDni(token);

            if (res.ok && res.data?.ok) {
                const timestamp = new Date().toLocaleTimeString('es-AR');
                const result: CheckinResult = {
                    success: true,
                    message: res.data.mensaje || 'Check-in exitoso',
                    userName: res.data.usuario_nombre || 'Usuario',
                    timestamp,
                };
                setLastResult(result);
                setScanStatus('success');
                setRecentCheckins((prev) => [
                    { name: result.userName!, time: timestamp },
                    ...prev.slice(0, 9),
                ]);
            } else {
                setLastResult({
                    success: false,
                    message: res.error || res.data?.mensaje || 'Usuario no encontrado o inactivo',
                });
                setScanStatus('error');
            }
        } catch {
            setLastResult({
                success: false,
                message: 'Error de conexión',
            });
            setScanStatus('error');
        }

        // Reset after delay
        setTimeout(() => {
            setScanStatus('idle');
            setManualToken('');
            setLastResult(null);
            if (inputRef.current) {
                inputRef.current.focus();
            }
        }, 2500);
    }, [userInfo]);

    // Manual submit
    const handleManualSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        processToken(manualToken);
    };

    // Logout
    const handleLogout = async () => {
        stopCamera();
        await api.logout();
        setAuthenticated(false);
        setUserInfo(null);
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
            <div className="min-h-screen flex items-center justify-center p-4 bg-neutral-950">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="w-full max-w-md"
                >
                    <div className="text-center mb-8">
                        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-success-500 to-success-600 shadow-glow-md mb-4">
                            <ScanLine className="w-8 h-8 text-white" />
                        </div>
                        <h1 className="text-2xl font-display font-bold text-white">Check-in</h1>
                        <p className="text-neutral-400 mt-1">Ingresá tus datos para habilitar el lector</p>
                    </div>

                    <div className="glass-card p-8">
                        <form onSubmit={handleAuth} className="space-y-4">
                            {/* DNI */}
                            <div>
                                <label className="block text-sm font-medium text-neutral-300 mb-2">DNI</label>
                                <div className="relative">
                                    <input
                                        type="text"
                                        inputMode="numeric"
                                        value={authDni}
                                        onChange={(e) => setAuthDni(e.target.value)}
                                        className="w-full px-4 py-3 pl-11 rounded-xl bg-neutral-900 border border-neutral-800 text-white focus:ring-2 focus:ring-success-500/50 focus:border-success-500 transition-all"
                                        placeholder="Solo números"
                                        autoComplete="off"
                                    />
                                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-500" />
                                </div>
                            </div>

                            {/* Phone with country prefix */}
                            <div>
                                <label className="block text-sm font-medium text-neutral-300 mb-2">Teléfono</label>
                                <div className="flex gap-2">
                                    {/* Prefix selector */}
                                    <div className="relative">
                                        <button
                                            type="button"
                                            onClick={() => setShowPrefixSelector(!showPrefixSelector)}
                                            className="flex items-center gap-1 px-3 py-3 rounded-xl bg-neutral-900 border border-neutral-800 text-white hover:bg-neutral-800 transition-all"
                                        >
                                            {countryPrefix}
                                            <ChevronDown className="w-4 h-4 text-neutral-500" />
                                        </button>

                                        <AnimatePresence>
                                            {showPrefixSelector && (
                                                <motion.div
                                                    initial={{ opacity: 0, y: -10 }}
                                                    animate={{ opacity: 1, y: 0 }}
                                                    exit={{ opacity: 0, y: -10 }}
                                                    className="absolute top-full left-0 mt-2 w-48 bg-neutral-900 border border-neutral-800 rounded-xl shadow-lg z-10 overflow-hidden"
                                                >
                                                    {COUNTRY_PREFIXES.map((p) => (
                                                        <button
                                                            key={p.code}
                                                            type="button"
                                                            onClick={() => {
                                                                setCountryPrefix(p.code);
                                                                setShowPrefixSelector(false);
                                                            }}
                                                            className={cn(
                                                                'w-full px-4 py-2 text-left text-sm hover:bg-neutral-800 transition-colors',
                                                                countryPrefix === p.code ? 'text-success-400' : 'text-white'
                                                            )}
                                                        >
                                                            {p.country} ({p.code})
                                                        </button>
                                                    ))}
                                                </motion.div>
                                            )}
                                        </AnimatePresence>
                                    </div>

                                    {/* Phone input */}
                                    <div className="relative flex-1">
                                        <input
                                            type="text"
                                            inputMode="numeric"
                                            value={authPhone}
                                            onChange={(e) => setAuthPhone(e.target.value)}
                                            className="w-full px-4 py-3 pl-11 rounded-xl bg-neutral-900 border border-neutral-800 text-white focus:ring-2 focus:ring-success-500/50 focus:border-success-500 transition-all"
                                            placeholder="Ej: 3434473599"
                                            autoComplete="off"
                                        />
                                        <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-500" />
                                    </div>
                                </div>
                                <p className="text-xs text-neutral-500 mt-1">Elegí el prefijo. Ingresá solo dígitos.</p>
                            </div>

                            {authError && (
                                <div className="p-3 rounded-xl bg-danger-500/10 border border-danger-500/30 text-danger-400 text-sm">
                                    {authError}
                                </div>
                            )}

                            <button
                                type="submit"
                                disabled={authLoading}
                                className="w-full py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-success-500 to-success-600 hover:shadow-glow-md transition-all disabled:opacity-50"
                            >
                                {authLoading ? 'Verificando...' : 'Continuar'}
                            </button>
                        </form>
                    </div>
                </motion.div>
            </div>
        );
    }

    // Main check-in screen
    return (
        <div className="min-h-screen bg-neutral-950 p-4">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-success-500 to-success-600 flex items-center justify-center">
                        <ScanLine className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h1 className="text-lg font-display font-bold text-white">Check-in</h1>
                        <p className="text-xs text-neutral-500">Ingresa el DNI del socio</p>
                    </div>
                </div>
                <button
                    onClick={handleLogout}
                    className="p-2 rounded-lg text-neutral-400 hover:text-danger-400 hover:bg-danger-500/10 transition-colors"
                >
                    <LogOut className="w-5 h-5" />
                </button>
            </div>

            {/* Quota warning toast */}
            {quotaWarning && (
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={cn(
                        'mb-4 p-3 rounded-xl text-sm',
                        quotaWarning.type === 'error'
                            ? 'bg-danger-500/10 border border-danger-500/30 text-danger-400'
                            : 'bg-warning-500/10 border border-warning-500/30 text-warning-400'
                    )}
                >
                    {quotaWarning.message}
                </motion.div>
            )}

            {/* Mode toggle */}
            <div className="flex items-center gap-2 mb-6">
                <button
                    onClick={() => setMode('camera')}
                    className={cn(
                        'flex-1 flex items-center justify-center gap-2 py-3 rounded-xl font-medium transition-all',
                        mode === 'camera'
                            ? 'bg-success-500/20 text-success-400 border border-success-500/30'
                            : 'bg-neutral-900 text-neutral-400 border border-neutral-800'
                    )}
                >
                    <Camera className="w-4 h-4" />
                    Cámara
                </button>
                <button
                    onClick={() => setMode('manual')}
                    className={cn(
                        'flex-1 flex items-center justify-center gap-2 py-3 rounded-xl font-medium transition-all',
                        mode === 'manual'
                            ? 'bg-success-500/20 text-success-400 border border-success-500/30'
                            : 'bg-neutral-900 text-neutral-400 border border-neutral-800'
                    )}
                >
                    <Keyboard className="w-4 h-4" />
                    DNI Manual
                </button>
            </div>

            {/* Scanner area */}
            <div className="relative aspect-square max-w-md mx-auto mb-6 rounded-2xl overflow-hidden bg-neutral-900 border border-neutral-800">
                {mode === 'camera' ? (
                    <>
                        <video
                            ref={videoRef}
                            autoPlay
                            playsInline
                            muted
                            className="w-full h-full object-cover"
                        />
                        {/* Scan overlay */}
                        <div className="absolute inset-0 flex items-center justify-center">
                            <div className="w-48 h-48 border-2 border-success-400 rounded-2xl relative">
                                <div className="absolute top-0 left-0 w-6 h-6 border-t-4 border-l-4 border-success-400 rounded-tl-lg" />
                                <div className="absolute top-0 right-0 w-6 h-6 border-t-4 border-r-4 border-success-400 rounded-tr-lg" />
                                <div className="absolute bottom-0 left-0 w-6 h-6 border-b-4 border-l-4 border-success-400 rounded-bl-lg" />
                                <div className="absolute bottom-0 right-0 w-6 h-6 border-b-4 border-r-4 border-success-400 rounded-br-lg" />
                                {/* Scan line animation */}
                                <motion.div
                                    className="absolute left-2 right-2 h-0.5 bg-success-400"
                                    animate={{ top: ['10%', '90%', '10%'] }}
                                    transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                                />
                            </div>
                        </div>
                        <div className="absolute bottom-4 left-4 right-4 text-center text-sm text-neutral-400">
                            Apunta la cámara al código QR del socio
                        </div>
                    </>
                ) : (
                    <form onSubmit={handleManualSubmit} className="flex flex-col items-center justify-center h-full p-6">
                        <Keyboard className="w-12 h-12 text-neutral-600 mb-4" />
                        <input
                            ref={inputRef}
                            type="text"
                            inputMode="numeric"
                            value={manualToken}
                            onChange={(e) => setManualToken(e.target.value)}
                            placeholder="Ingresa el DNI..."
                            disabled={scanStatus === 'processing'}
                            className="w-full px-4 py-3 rounded-xl bg-neutral-800 border border-neutral-700 text-white text-center text-lg tracking-widest focus:ring-2 focus:ring-success-500/50 focus:border-success-500 transition-all disabled:opacity-50"
                            autoFocus
                        />
                        <button
                            type="submit"
                            disabled={scanStatus === 'processing' || !manualToken.trim()}
                            className="mt-4 w-full py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-success-500 to-success-600 disabled:opacity-50"
                        >
                            {scanStatus === 'processing' ? 'Verificando...' : 'Registrar Entrada'}
                        </button>
                    </form>
                )}

                {/* Result overlay */}
                <AnimatePresence>
                    {(scanStatus === 'success' || scanStatus === 'error') && lastResult && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className={cn(
                                'absolute inset-0 flex flex-col items-center justify-center',
                                scanStatus === 'success' ? 'bg-success-500/90' : 'bg-danger-500/90'
                            )}
                        >
                            <motion.div
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                transition={{ type: 'spring', damping: 15 }}
                            >
                                {scanStatus === 'success' ? (
                                    <CheckCircle2 className="w-20 h-20 text-white" />
                                ) : (
                                    <XCircle className="w-20 h-20 text-white" />
                                )}
                            </motion.div>
                            <p className="text-white text-xl font-bold mt-4">{lastResult.message}</p>
                            {lastResult.userName && (
                                <p className="text-white/80 mt-2">{lastResult.userName}</p>
                            )}
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* Recent checkins */}
            {recentCheckins.length > 0 && (
                <div className="max-w-md mx-auto">
                    <h2 className="text-sm font-medium text-neutral-400 mb-3 flex items-center gap-2">
                        <Clock className="w-4 h-4" />
                        Últimos Check-ins
                    </h2>
                    <div className="space-y-2">
                        {recentCheckins.slice(0, 5).map((c, i) => (
                            <div
                                key={i}
                                className="flex items-center justify-between p-3 rounded-xl bg-neutral-900/50 border border-neutral-800"
                            >
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-full bg-success-500/20 flex items-center justify-center">
                                        <User className="w-4 h-4 text-success-400" />
                                    </div>
                                    <span className="text-white text-sm">{c.name}</span>
                                </div>
                                <span className="text-xs text-neutral-500">{c.time}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
