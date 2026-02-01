'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { QrCode, Check, User, Clock, Wifi, WifiOff, Users, RefreshCw } from 'lucide-react';
import { useParams } from 'next/navigation';
import QRCode from 'qrcode';

interface CheckinEntry {
    nombre: string;
    dni: string;
    hora: string;
}

interface StationInfo {
    valid: boolean;
    gym_id?: number;
    gym_name?: string;
    branch_id?: number;
    branch_name?: string;
    branch_code?: string | null;
    logo_url?: string;
}

interface TokenData {
    token: string;
    expires_at: string;
    expires_in: number;
}

export default function StationPage() {
    const params = useParams();
    const stationKey = params.key as string;

    // State
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [stationInfo, setStationInfo] = useState<StationInfo | null>(null);
    const [tokenData, setTokenData] = useState<TokenData | null>(null);
    const [qrDataUrl, setQrDataUrl] = useState<string>('');
    const [recentCheckins, setRecentCheckins] = useState<CheckinEntry[]>([]);
    const [totalHoy, setTotalHoy] = useState(0);
    const [connected, setConnected] = useState(true);
    const [lastCheckin, setLastCheckin] = useState<CheckinEntry | null>(null);
    const [showCelebration, setShowCelebration] = useState(false);
    const [timeLeft, setTimeLeft] = useState(0);

    const audioRef = useRef<HTMLAudioElement | null>(null);
    const pollRef = useRef<NodeJS.Timeout | null>(null);
    const countdownRef = useRef<NodeJS.Timeout | null>(null);

    const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

    // Play success sound
    const playSuccessSound = useCallback(() => {
        try {
            // Create a simple beep using Web Audio API
            const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
            const oscillator = ctx.createOscillator();
            const gainNode = ctx.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(ctx.destination);

            oscillator.frequency.value = 880; // A5 note
            oscillator.type = 'sine';
            gainNode.gain.setValueAtTime(0.3, ctx.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);

            oscillator.start(ctx.currentTime);
            oscillator.stop(ctx.currentTime + 0.3);
        } catch (e) {
            console.log('Audio not available');
        }
    }, []);

    // Generate QR code image
    const generateQRImage = useCallback(async (token: string) => {
        try {
            // QR content should be the token that user will send to /api/checkin/station/scan
            const dataUrl = await QRCode.toDataURL(token, {
                width: 400,
                margin: 2,
                color: {
                    dark: '#000000',
                    light: '#ffffff'
                },
                errorCorrectionLevel: 'M'
            });
            setQrDataUrl(dataUrl);
        } catch (e) {
            console.error('Error generating QR:', e);
        }
    }, []);

    // Validate station and load info
    const loadStationInfo = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/checkin/station/info/${stationKey}`);
            const data = await res.json();

            if (!res.ok || !data.valid) {
                setError('Estación no válida');
                setLoading(false);
                return false;
            }

            setStationInfo(data);
            return true;
        } catch (e) {
            setError('Error de conexión');
            setConnected(false);
            setLoading(false);
            return false;
        }
    }, [stationKey, API_BASE]);

    // Load token
    const loadToken = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/checkin/station/token/${stationKey}`);
            if (res.ok) {
                const data = await res.json();
                setTokenData(data);
                setTimeLeft(data.expires_in);
                await generateQRImage(data.token);
                setConnected(true);
            } else {
                setConnected(false);
            }
        } catch (e) {
            setConnected(false);
        }
    }, [stationKey, generateQRImage, API_BASE]);

    // Load recent check-ins
    const loadRecent = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/checkin/station/recent/${stationKey}`);
            if (res.ok) {
                const data = await res.json();
                const newCheckins = data.checkins || [];

                // Check for new check-in
                if (recentCheckins.length > 0 && newCheckins.length > 0) {
                    const newest = newCheckins[0];
                    const wasNewest = recentCheckins[0];
                    if (newest.hora !== wasNewest.hora || newest.dni !== wasNewest.dni) {
                        // New check-in detected!
                        setLastCheckin(newest);
                        setShowCelebration(true);
                        playSuccessSound();

                        await loadToken();

                        // Hide celebration after 3 seconds
                        setTimeout(() => {
                            setShowCelebration(false);
                            setLastCheckin(null);
                        }, 3000);
                    }
                }

                setRecentCheckins(newCheckins);
                setTotalHoy(data.stats?.total_hoy || 0);
                setConnected(true);
            }
        } catch (e) {
            // Ignore polling errors
        }
    }, [stationKey, recentCheckins, playSuccessSound, loadToken, API_BASE]);

    // Countdown timer
    useEffect(() => {
        if (!tokenData) return;

        countdownRef.current = setInterval(() => {
            setTimeLeft((prev) => {
                if (prev <= 1) {
                    // Token expired, regenerate
                    loadToken();
                    return 0;
                }
                return prev - 1;
            });
        }, 1000);

        return () => {
            if (countdownRef.current) clearInterval(countdownRef.current);
        };
    }, [tokenData, loadToken]);

    // Initial load
    useEffect(() => {
        const init = async () => {
            const valid = await loadStationInfo();
            if (valid) {
                await loadToken();
                await loadRecent();
                setLoading(false);
            }
        };
        init();
    }, [loadStationInfo, loadToken, loadRecent]);

    // Polling for updates (every 3 seconds)
    useEffect(() => {
        if (loading || error) return;

        pollRef.current = setInterval(() => {
            loadRecent();
        }, 3000);

        return () => {
            if (pollRef.current) clearInterval(pollRef.current);
        };
    }, [loading, error, loadRecent]);

    // Format time
    const formatTime = (seconds: number) => {
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return `${m}:${s.toString().padStart(2, '0')}`;
    };

    // Error state
    if (error) {
        return (
            <div className="min-h-screen bg-slate-950 flex items-center justify-center p-8">
                <div className="text-center">
                    <QrCode className="w-24 h-24 text-red-500 mx-auto mb-6" />
                    <h1 className="text-3xl font-bold text-white mb-4">Estación no válida</h1>
                    <p className="text-slate-400 text-lg">{error}</p>
                </div>
            </div>
        );
    }

    // Loading state
    if (loading) {
        return (
            <div className="min-h-screen bg-slate-950 flex items-center justify-center">
                <div className="text-center">
                    <RefreshCw className="w-16 h-16 text-primary-500 animate-spin mx-auto mb-4" />
                    <p className="text-slate-400 text-xl">Cargando estación...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex flex-col">
            {/* Header */}
            <header className="flex items-center justify-between p-6 border-b border-slate-800">
                <div className="flex items-center gap-4">
                    {stationInfo?.logo_url ? (
                        <img
                            src={stationInfo.logo_url}
                            alt={stationInfo.gym_name}
                            className="h-12 w-auto object-contain"
                        />
                    ) : (
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center">
                            <QrCode className="w-6 h-6 text-white" />
                        </div>
                    )}
                    <div>
                        <h1 className="text-2xl font-bold text-white">{stationInfo?.gym_name || 'Check-in'}</h1>
                        <p className="text-slate-400 text-sm">
                            {stationInfo?.branch_code ? `Sucursal ${stationInfo.branch_code} • ` : ''}
                            Escanea el código con tu celular
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    {/* Connection indicator */}
                    <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${connected ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                        {connected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
                        <span className="text-sm font-medium">{connected ? 'Conectado' : 'Sin conexión'}</span>
                    </div>

                    {/* Today stats */}
                    <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800/50">
                        <Users className="w-5 h-5 text-primary-400" />
                        <span className="text-xl font-bold text-white">{totalHoy}</span>
                        <span className="text-slate-400 text-sm">hoy</span>
                    </div>
                </div>
            </header>

            {/* Main content */}
            <main className="flex-1 flex items-center justify-center p-8">
                <div className="flex gap-16 items-start max-w-6xl w-full">
                    {/* QR Code Section */}
                    <div className="flex-shrink-0">
                        <div className="relative">
                            {/* QR Container */}
                            <div className="bg-white p-6 rounded-3xl shadow-2xl shadow-primary-500/20">
                                {qrDataUrl ? (
                                    <img
                                        src={qrDataUrl}
                                        alt="QR Code"
                                        className="w-80 h-80"
                                    />
                                ) : (
                                    <div className="w-80 h-80 flex items-center justify-center bg-slate-100 rounded-2xl">
                                        <RefreshCw className="w-12 h-12 text-slate-400 animate-spin" />
                                    </div>
                                )}
                            </div>

                            {/* Celebration overlay */}
                            <AnimatePresence>
                                {showCelebration && lastCheckin && (
                                    <motion.div
                                        initial={{ opacity: 0, scale: 0.8 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        exit={{ opacity: 0, scale: 0.8 }}
                                        className="absolute inset-0 flex items-center justify-center bg-emerald-500 rounded-3xl"
                                    >
                                        <div className="text-center text-white">
                                            <motion.div
                                                initial={{ scale: 0 }}
                                                animate={{ scale: 1 }}
                                                transition={{ type: 'spring', damping: 10 }}
                                            >
                                                <Check className="w-24 h-24 mx-auto mb-4" />
                                            </motion.div>
                                            <p className="text-2xl font-bold mb-2">¡Check-in exitoso!</p>
                                            <p className="text-xl opacity-90">{lastCheckin.nombre}</p>
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>

                        {/* Token timer */}
                        <div className="mt-6 text-center">
                            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-slate-800/50">
                                <Clock className="w-4 h-4 text-slate-400" />
                                <span className="text-slate-300 text-sm">
                                    Nuevo código en: <span className="font-mono font-bold text-white">{formatTime(timeLeft)}</span>
                                </span>
                            </div>
                        </div>

                        {/* Token (masked) */}
                        <div className="mt-2 text-center">
                            <span className="font-mono text-xs text-slate-600">
                                {tokenData?.token?.slice(0, 4)}****{tokenData?.token?.slice(-4)}
                            </span>
                        </div>
                    </div>

                    {/* Recent Check-ins Section */}
                    <div className="flex-1">
                        <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-3">
                            <Clock className="w-5 h-5 text-primary-400" />
                            Últimos Check-ins
                        </h2>

                        <div className="space-y-3">
                            <AnimatePresence mode="popLayout">
                                {recentCheckins.length === 0 ? (
                                    <motion.div
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        className="text-center py-12 text-slate-500"
                                    >
                                        <User className="w-12 h-12 mx-auto mb-4 opacity-50" />
                                        <p>Aún no hay check-ins hoy</p>
                                    </motion.div>
                                ) : (
                                    recentCheckins.map((checkin, index) => (
                                        <motion.div
                                            key={`${checkin.dni}-${checkin.hora}`}
                                            initial={{ opacity: 0, x: -20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            exit={{ opacity: 0, x: 20 }}
                                            transition={{ delay: index * 0.05 }}
                                            className={`flex items-center gap-4 p-4 rounded-xl border ${index === 0 && showCelebration
                                                ? 'bg-emerald-500/10 border-emerald-500/30'
                                                : 'bg-slate-800/30 border-slate-700/50'
                                                }`}
                                        >
                                            <div className={`w-12 h-12 rounded-full flex items-center justify-center ${index === 0 && showCelebration
                                                ? 'bg-emerald-500/20'
                                                : 'bg-primary-500/20'
                                                }`}>
                                                {index === 0 && showCelebration ? (
                                                    <Check className="w-6 h-6 text-emerald-400" />
                                                ) : (
                                                    <User className="w-6 h-6 text-primary-400" />
                                                )}
                                            </div>
                                            <div className="flex-1">
                                                <p className="text-lg font-semibold text-white">{checkin.nombre}</p>
                                                <p className="text-sm text-slate-400">DNI: {checkin.dni}</p>
                                            </div>
                                            <div className="text-right">
                                                <p className="text-lg font-mono text-white">{checkin.hora}</p>
                                            </div>
                                        </motion.div>
                                    ))
                                )}
                            </AnimatePresence>
                        </div>
                    </div>
                </div>
            </main>

            {/* Footer */}
            <footer className="p-4 border-t border-slate-800 text-center">
                <p className="text-slate-500 text-sm">
                    Abre <span className="text-primary-400 font-semibold">/checkin</span> en tu celular y escanea el código QR
                </p>
            </footer>
        </div>
    );
}
