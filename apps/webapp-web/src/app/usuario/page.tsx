'use client';

import { Suspense, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useRouter, useSearchParams } from 'next/navigation';
import { QRScannerModal } from '@/components/QrScannerModal';
import {
    User,
    Calendar,
    CreditCard,
    Dumbbell,
    QrCode,
    LogOut,
    ChevronRight,
    Clock,
    CheckCircle2,
    AlertCircle,
    X,
} from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { api, type Usuario, type Pago, type Rutina, type UsuarioEntitlements } from '@/lib/api';
import { formatDate, formatDateRelative, formatCurrency, cn } from '@/lib/utils';

function UserDashboardContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { user, logout, isLoading: authLoading } = useAuth();
    const [userData, setUserData] = useState<Usuario | null>(null);
    const [pagos, setPagos] = useState<Pago[]>([]);
    const [rutina, setRutina] = useState<Rutina | null>(null);
    const [loading, setLoading] = useState(true);
    const [showScanner, setShowScanner] = useState(false);
    const [entitlementsOpen, setEntitlementsOpen] = useState(false);
    const [entitlementsLoading, setEntitlementsLoading] = useState(false);
    const [entitlements, setEntitlements] = useState<UsuarioEntitlements | null>(null);

    useEffect(() => {
        if (user?.id) {
            loadData();
        }
    }, [user?.id]);

    useEffect(() => {
        // Check for scan action from URL (Deep link / QR Redirect)
        const action = searchParams.get('action');
        const uuid = searchParams.get('uuid');
        if (action === 'scan' && uuid) {
            handleRoutineAccess(uuid);
        }
    }, [searchParams]);

    const loadData = async () => {
        if (!user?.id) return;
        setLoading(true);
        try {
            // Load user data, payments, rutina
            const [userRes, pagosRes, rutinasRes] = await Promise.all([
                api.getUsuario(user.id),
                api.getPagos({ usuario_id: user.id, limit: 5 }),
                api.getRutinas({ usuario_id: user.id }),
            ]);

            if (userRes.ok && userRes.data) setUserData(userRes.data);
            if (pagosRes.ok && pagosRes.data) setPagos(pagosRes.data.pagos);
            if (rutinasRes.ok && rutinasRes.data && rutinasRes.data.rutinas.length > 0) {
                setRutina(rutinasRes.data.rutinas[0]);
            }
        } catch (err) {
            console.error('Error loading data:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleRoutineAccess = async (uuid: string) => {
        try {
            const res = await api.verifyRoutineQR(uuid);
            if (res.ok && res.data) {
                // Success - Navigate to Routine View
                router.push(`/usuario/routines?uuid=${uuid}`);
            } else {
                alert('Código QR inválido o rutina no encontrada');
            }
        } catch (error) {
            console.error('Error verifying QR:', error);
            alert('Error al verificar el código QR');
        }
    };

    const handleScan = (decodedText: string) => {
        console.log("Scanned:", decodedText);

        let uuid = decodedText;
        try {
            if (decodedText.includes('/qr_scan/')) {
                const parts = decodedText.split('/qr_scan/');
                if (parts.length > 1) {
                    uuid = parts[1];
                }
            } else if (decodedText.includes('uuid=')) {
                const urlObj = new URL(decodedText);
                const u = urlObj.searchParams.get('uuid');
                if (u) uuid = u;
            }
        } catch (e) {
            // Fallback to using text as is
        }

        uuid = uuid.split('?')[0].split('&')[0];

        handleRoutineAccess(uuid);
        setShowScanner(false);
    };

    const openEntitlements = async () => {
        setEntitlementsOpen(true);
        if (entitlements) return;
        setEntitlementsLoading(true);
        try {
            const res = await api.getUsuarioEntitlements();
            if (res.ok && res.data) {
                setEntitlements(res.data);
            } else {
                setEntitlements(null);
            }
        } catch {
            setEntitlements(null);
        } finally {
            setEntitlementsLoading(false);
        }
    };

    if (authLoading || loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-950">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-12 h-12 border-4 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
                    <p className="text-slate-400">Cargando...</p>
                </div>

            {entitlementsOpen ? (
                <div className="fixed inset-0 z-50">
                    <div
                        className="absolute inset-0 bg-black/70"
                        onClick={() => setEntitlementsOpen(false)}
                    />
                    <div className="absolute inset-x-0 bottom-0 max-w-md mx-auto p-4">
                        <div className="rounded-2xl border border-slate-800/60 bg-slate-900/95 backdrop-blur-lg p-4">
                            <div className="flex items-start justify-between gap-3">
                                <div>
                                    <div className="text-sm font-semibold text-white">Accesos de tu cuota</div>
                                        <div className="text-xs text-slate-400">{userData?.tipo_cuota_nombre || 'Sin cuota'}</div>
                                </div>
                                <button
                                    type="button"
                                    onClick={() => setEntitlementsOpen(false)}
                                    className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
                                >
                                    <X className="w-4 h-4" />
                                </button>
                            </div>

                            <div className="mt-4 space-y-3">
                                {entitlementsLoading ? (
                                    <div className="text-sm text-slate-400">Cargando…</div>
                                ) : !entitlements ? (
                                    <div className="text-sm text-slate-400">No se pudo cargar la información.</div>
                                ) : (
                                    <>
                                        <div className="rounded-xl border border-slate-800/60 bg-slate-950/40 p-3">
                                            <div className="text-xs font-medium text-slate-300 mb-2">Sucursales habilitadas</div>
                                            {Array.isArray(entitlements.allowed_sucursales) && entitlements.allowed_sucursales.length > 0 ? (
                                                <div className="flex flex-wrap gap-2">
                                                    {entitlements.allowed_sucursales.map((s) => (
                                                        <span
                                                            key={s.id}
                                                            className="px-2 py-1 rounded-lg bg-slate-800/60 text-xs text-slate-200"
                                                        >
                                                            {s.nombre}
                                                        </span>
                                                    ))}
                                                </div>
                                            ) : (
                                                <div className="text-sm text-slate-400">Sin sucursales disponibles.</div>
                                            )}
                                        </div>

                                        <div className="rounded-xl border border-slate-800/60 bg-slate-950/40 p-3">
                                            <div className="text-xs font-medium text-slate-300 mb-2">Clases</div>
                                            {entitlements.class_allowlist_enabled ? (
                                                <>
                                                    {entitlements.allowed_tipo_clases?.length ? (
                                                        <div className="mb-2">
                                                            <div className="text-xs text-slate-400 mb-1">Tipos de clase</div>
                                                            <div className="flex flex-wrap gap-2">
                                                                {entitlements.allowed_tipo_clases.map((t) => (
                                                                    <span
                                                                        key={t.id}
                                                                        className="px-2 py-1 rounded-lg bg-slate-800/60 text-xs text-slate-200"
                                                                    >
                                                                        {t.nombre}
                                                                    </span>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    ) : null}
                                                    {entitlements.allowed_clases?.length ? (
                                                        <div>
                                                            <div className="text-xs text-slate-400 mb-1">Clases específicas</div>
                                                            <div className="flex flex-wrap gap-2">
                                                                {entitlements.allowed_clases.map((c) => (
                                                                    <span
                                                                        key={c.id}
                                                                        className="px-2 py-1 rounded-lg bg-slate-800/60 text-xs text-slate-200"
                                                                    >
                                                                        {c.nombre}
                                                                    </span>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    ) : (
                                                        <div className="text-sm text-slate-400">No hay clases habilitadas explícitamente.</div>
                                                    )}
                                                </>
                                            ) : (
                                                <div className="text-sm text-slate-400">Todas las clases habilitadas.</div>
                                            )}
                                        </div>

                                        {entitlements.enabled ? (
                                            <div className="text-xs text-slate-500">
                                                Accesos calculados por plan y permisos por sucursal.
                                            </div>
                                        ) : (
                                            <div className="text-xs text-slate-500">
                                                Accesos calculados por el sistema actual (sin restricciones por cuota).
                                            </div>
                                        )}
                                    </>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            ) : null}
            </div>
        );
    }

    if (!user || !userData) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-950">
                <p className="text-slate-400">Error al cargar datos</p>
            </div>
        );
    }

    const daysRemaining = userData.dias_restantes ?? 0;
    const isExpired = daysRemaining <= 0;
    const isExpiringSoon = daysRemaining > 0 && daysRemaining <= 7;
    const cycleDays = Math.max(1, Number((userData as any).tipo_cuota_duracion_dias || 30));

    return (
        <div className="min-h-screen bg-slate-950 pb-20">
            {/* Header */}
            <div className="bg-slate-900 border-b border-slate-800/50 p-4">
                <div className="max-w-md mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white font-bold text-lg">
                            {userData.nombre.charAt(0)}
                        </div>
                        <div>
                            <h1 className="font-semibold text-white">{userData.nombre}</h1>
                            <button
                                type="button"
                                onClick={openEntitlements}
                                className="text-xs text-slate-500 hover:text-slate-300 transition-colors inline-flex items-center gap-1"
                            >
                                <span>{userData.tipo_cuota_nombre || 'Sin cuota'}</span>
                                <ChevronRight className="w-3 h-3" />
                            </button>
                        </div>
                    </div>
                    <button
                        onClick={() => logout()}
                        className="p-2 rounded-lg text-slate-400 hover:text-danger-400 hover:bg-danger-500/10 transition-colors"
                    >
                        <LogOut className="w-5 h-5" />
                    </button>
                </div>
            </div>

            <div className="max-w-md mx-auto p-4 space-y-6">
                {/* Subscription Status Card */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={cn(
                        'card p-6 border-l-4',
                        isExpired
                            ? 'border-l-danger-500 bg-danger-500/5'
                            : isExpiringSoon
                                ? 'border-l-warning-500 bg-warning-500/5'
                                : 'border-l-success-500 bg-success-500/5'
                    )}
                >
                    <div className="flex items-start justify-between">
                        <div>
                            <div className="flex items-center gap-2">
                                {isExpired ? (
                                    <AlertCircle className="w-5 h-5 text-danger-400" />
                                ) : (
                                    <CheckCircle2 className="w-5 h-5 text-success-400" />
                                )}
                                <span className="font-medium text-white">
                                    {isExpired ? 'Suscripción vencida' : 'Suscripción activa'}
                                </span>
                            </div>
                            <p className="text-sm text-slate-400 mt-1">
                                {userData.fecha_proximo_vencimiento
                                    ? `Vence: ${formatDate(userData.fecha_proximo_vencimiento)}`
                                    : 'Sin fecha de vencimiento'}
                            </p>
                        </div>
                        <div className="text-right">
                            <div className={cn(
                                'text-2xl font-bold',
                                isExpired ? 'text-danger-400' : isExpiringSoon ? 'text-warning-400' : 'text-success-400'
                            )}>
                                {isExpired ? 'Vencida' : `${daysRemaining} días`}
                            </div>
                            <p className="text-xs text-slate-500">restantes</p>
                        </div>
                    </div>

                    {/* Progress bar */}
                    {!isExpired && daysRemaining > 0 && (
                        <div className="mt-4">
                            <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                                <span>Progreso del ciclo</span>
                                <span>{Math.min(100, Math.round((daysRemaining / cycleDays) * 100))}%</span>
                            </div>
                            <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                                <motion.div
                                    initial={{ width: 0 }}
                                    animate={{ width: `${Math.min(100, Math.round((daysRemaining / cycleDays) * 100))}%` }}
                                    transition={{ duration: 0.8, ease: 'easeOut' }}
                                    className={cn(
                                        'h-full rounded-full',
                                        isExpiringSoon
                                            ? 'bg-gradient-to-r from-warning-600 to-warning-400'
                                            : 'bg-gradient-to-r from-success-600 to-success-400'
                                    )}
                                />
                            </div>
                        </div>
                    )}
                </motion.div>

                {/* Quick Actions */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="grid grid-cols-2 gap-4"
                >
                    <button
                        className="card p-4 text-left hover:border-primary-500/50 transition-colors group"
                        onClick={() => {
                            if (userData.dni) {
                                try { localStorage.setItem('checkin_saved_user', JSON.stringify({ dni: userData.dni })); } catch (e) { }
                            }
                            router.push('/checkin?auto=true');
                        }}
                    >
                        <div className="w-10 h-10 rounded-xl bg-primary-500/20 flex items-center justify-center mb-3 group-hover:bg-primary-500/30 transition-colors">
                            <QrCode className="w-5 h-5 text-primary-400" />
                        </div>
                        <div className="font-medium text-white">Check-in QR</div>
                        <p className="text-xs text-slate-500">Ingresar al gym</p>
                    </button>
                    <button
                        className="card p-4 text-left hover:border-primary-500/50 transition-colors group"
                        onClick={() => router.push('/usuario/routines')}
                    >
                        <div className="w-10 h-10 rounded-xl bg-primary-500/20 flex items-center justify-center mb-3 group-hover:bg-primary-500/30 transition-colors">
                            <Dumbbell className="w-5 h-5 text-primary-400" />
                        </div>
                        <div className="font-medium text-white">Mi Rutina</div>
                        <p className="text-xs text-slate-500">{rutina?.nombre || 'Sin asignar'}</p>
                    </button>
                </motion.div>

                {/* Recent Payments */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="card overflow-hidden"
                >
                    <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                        <h2 className="font-semibold text-white flex items-center gap-2">
                            <CreditCard className="w-4 h-4 text-primary-400" />
                            Últimos pagos
                        </h2>
                    </div>
                    <div className="divide-y divide-neutral-800">
                        {pagos.length === 0 ? (
                            <div className="p-6 text-center text-slate-500">
                                No hay pagos registrados
                            </div>
                        ) : (
                            pagos.map((pago) => (
                                <div key={pago.id} className="p-4 flex items-center justify-between">
                                    <div>
                                        <div className="text-sm text-white">{formatDate(pago.fecha)}</div>
                                        <div className="text-xs text-slate-500">{pago.tipo_cuota_nombre || 'Pago'}</div>
                                    </div>
                                    <div className="text-success-400 font-semibold">
                                        {formatCurrency(pago.monto)}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </motion.div>

                {/* Rutina Preview */}
                {rutina && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.3 }}
                        className="card overflow-hidden"
                    >
                        <div className="p-4 border-b border-slate-800">
                            <h2 className="font-semibold text-white flex items-center gap-2">
                                <Dumbbell className="w-4 h-4 text-primary-400" />
                                {rutina.nombre}
                            </h2>
                            {rutina.descripcion && (
                                <p className="text-sm text-slate-400 mt-1">{rutina.descripcion}</p>
                            )}
                        </div>
                        <div className="p-4">
                            <div className="grid grid-cols-7 gap-1">
                                {['L', 'M', 'Mi', 'J', 'V', 'S', 'D'].map((day, i) => {
                                    const hasTraining = rutina.dias?.some((d) => d.numero === i + 1);
                                    return (
                                        <div
                                            key={day}
                                            className={cn(
                                                'aspect-square rounded-lg flex items-center justify-center text-xs font-medium',
                                                hasTraining
                                                    ? 'bg-primary-500/30 text-primary-300'
                                                    : 'bg-slate-800/50 text-slate-600'
                                            )}
                                        >
                                            {day}
                                        </div>
                                    );
                                })}
                            </div>
                            <button
                                className="mt-4 w-full py-2.5 rounded-xl border border-slate-800 text-sm text-slate-400 hover:text-white hover:border-slate-700 transition-colors flex items-center justify-center gap-2"
                                onClick={() => {
                                    if (rutina?.uuid_rutina) {
                                        router.push(`/usuario/routines?uuid=${rutina.uuid_rutina}`);
                                    }
                                }}
                            >
                                Ver rutina completa
                                <ChevronRight className="w-4 h-4" />
                            </button>
                        </div>
                    </motion.div>
                )}
            </div>

            <QRScannerModal
                isOpen={showScanner}
                onClose={() => setShowScanner(false)}
                onScan={handleScan}
            />
        </div>
    );
}

export default function UserDashboardPage() {
    return (
        <Suspense
            fallback={
                <div className="min-h-screen flex items-center justify-center bg-slate-950">
                    <div className="flex flex-col items-center gap-4">
                        <div className="w-12 h-12 border-4 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
                        <p className="text-slate-400">Cargando...</p>
                    </div>
                </div>
            }
        >
            <UserDashboardContent />
        </Suspense>
    );
}
