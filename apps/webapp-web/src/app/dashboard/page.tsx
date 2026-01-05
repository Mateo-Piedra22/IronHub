'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
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
} from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { api, type Usuario, type Pago, type Rutina } from '@/lib/api';
import { formatDate, formatDateRelative, formatCurrency, cn } from '@/lib/utils';

export default function UserDashboardPage() {
    const { user, logout, isLoading: authLoading } = useAuth();
    const [userData, setUserData] = useState<Usuario | null>(null);
    const [pagos, setPagos] = useState<Pago[]>([]);
    const [rutina, setRutina] = useState<Rutina | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (user?.id) {
            loadData();
        }
    }, [user?.id]);

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

    if (authLoading || loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-neutral-950">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-12 h-12 border-4 border-iron-500/30 border-t-iron-500 rounded-full animate-spin" />
                    <p className="text-neutral-400">Cargando...</p>
                </div>
            </div>
        );
    }

    if (!user || !userData) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-neutral-950">
                <p className="text-neutral-400">Error al cargar datos</p>
            </div>
        );
    }

    // Calculate subscription status
    const daysRemaining = userData.dias_restantes ?? 0;
    const isExpired = daysRemaining <= 0;
    const isExpiringSoon = daysRemaining > 0 && daysRemaining <= 7;

    return (
        <div className="min-h-screen bg-neutral-950 pb-20">
            {/* Header */}
            <div className="glass border-b border-neutral-800/50 p-4">
                <div className="max-w-md mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-iron-500 to-iron-700 flex items-center justify-center text-white font-bold text-lg">
                            {userData.nombre.charAt(0)}
                        </div>
                        <div>
                            <h1 className="font-semibold text-white">{userData.nombre}</h1>
                            <p className="text-xs text-neutral-500">{userData.tipo_cuota_nombre || 'Sin cuota'}</p>
                        </div>
                    </div>
                    <button
                        onClick={() => logout()}
                        className="p-2 rounded-lg text-neutral-400 hover:text-danger-400 hover:bg-danger-500/10 transition-colors"
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
                        'glass-card p-6 border-l-4',
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
                            <p className="text-sm text-neutral-400 mt-1">
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
                            <p className="text-xs text-neutral-500">restantes</p>
                        </div>
                    </div>
                </motion.div>

                {/* Quick Actions */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="grid grid-cols-2 gap-4"
                >
                    <button className="glass-card p-4 text-left hover:border-iron-500/50 transition-colors group">
                        <div className="w-10 h-10 rounded-xl bg-iron-500/20 flex items-center justify-center mb-3 group-hover:bg-iron-500/30 transition-colors">
                            <QrCode className="w-5 h-5 text-iron-400" />
                        </div>
                        <div className="font-medium text-white">Mi QR</div>
                        <p className="text-xs text-neutral-500">Para check-in</p>
                    </button>
                    <button
                        className="glass-card p-4 text-left hover:border-iron-500/50 transition-colors group"
                        onClick={() => {/* Navigate to rutina */ }}
                    >
                        <div className="w-10 h-10 rounded-xl bg-iron-500/20 flex items-center justify-center mb-3 group-hover:bg-iron-500/30 transition-colors">
                            <Dumbbell className="w-5 h-5 text-iron-400" />
                        </div>
                        <div className="font-medium text-white">Mi Rutina</div>
                        <p className="text-xs text-neutral-500">{rutina?.nombre || 'Sin asignar'}</p>
                    </button>
                </motion.div>

                {/* Recent Payments */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="glass-card overflow-hidden"
                >
                    <div className="p-4 border-b border-neutral-800 flex items-center justify-between">
                        <h2 className="font-semibold text-white flex items-center gap-2">
                            <CreditCard className="w-4 h-4 text-iron-400" />
                            Últimos pagos
                        </h2>
                    </div>
                    <div className="divide-y divide-neutral-800">
                        {pagos.length === 0 ? (
                            <div className="p-6 text-center text-neutral-500">
                                No hay pagos registrados
                            </div>
                        ) : (
                            pagos.map((pago) => (
                                <div key={pago.id} className="p-4 flex items-center justify-between">
                                    <div>
                                        <div className="text-sm text-white">{formatDate(pago.fecha)}</div>
                                        <div className="text-xs text-neutral-500">{pago.tipo_cuota_nombre || 'Pago'}</div>
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
                        className="glass-card overflow-hidden"
                    >
                        <div className="p-4 border-b border-neutral-800">
                            <h2 className="font-semibold text-white flex items-center gap-2">
                                <Dumbbell className="w-4 h-4 text-iron-400" />
                                {rutina.nombre}
                            </h2>
                            {rutina.descripcion && (
                                <p className="text-sm text-neutral-400 mt-1">{rutina.descripcion}</p>
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
                                                    ? 'bg-iron-500/30 text-iron-300'
                                                    : 'bg-neutral-800/50 text-neutral-600'
                                            )}
                                        >
                                            {day}
                                        </div>
                                    );
                                })}
                            </div>
                            <button className="mt-4 w-full py-2.5 rounded-xl border border-neutral-800 text-sm text-neutral-400 hover:text-white hover:border-neutral-700 transition-colors flex items-center justify-center gap-2">
                                Ver rutina completa
                                <ChevronRight className="w-4 h-4" />
                            </button>
                        </div>
                    </motion.div>
                )}
            </div>
        </div>
    );
}
