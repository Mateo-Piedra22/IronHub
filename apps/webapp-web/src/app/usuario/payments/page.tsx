'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { CreditCard, Check, AlertCircle, Download, Loader2 } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { api, type Pago } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';

export default function PaymentsPage() {
    const { user } = useAuth();
    const [payments, setPayments] = useState<Pago[]>([]);
    const [loading, setLoading] = useState(true);

    const loadPayments = useCallback(async () => {
        if (!user?.id) return;
        setLoading(true);
        try {
            const res = await api.getPagos({ usuario_id: user.id, limit: 50 });
            if (res.ok && res.data) {
                setPayments(res.data.pagos || []);
            }
        } catch (error) {
            console.error('Error loading payments:', error);
        } finally {
            setLoading(false);
        }
    }, [user?.id]);

    const handleDownloadReceipt = async (paymentId: number) => {
        try {
            const res = await api.downloadReceipt(paymentId);
            if (res.ok && res.data) {
                const url = window.URL.createObjectURL(res.data.blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `recibo-${paymentId}.pdf`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
            } else {
                alert('Error al descargar recibo: ' + (res.error || 'Desconocido'));
            }
        } catch (e) {
            console.error(e);
            alert('Error al descargar recibo');
        }
    };

    useEffect(() => {
        loadPayments();
    }, [loadPayments]);

    const totalPaid = payments.reduce((sum, p) => sum + (p.monto || 0), 0);
    const pendingPayments = payments.filter(p => p.estado === 'pending');

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
            </div>
        );
    }

    return (
        <div className="space-y-6 py-6">
            <div>
                <h1 className="text-2xl font-display font-bold text-white">Mis Pagos</h1>
                <p className="text-slate-400 mt-1">Historial de pagos y cuotas</p>
            </div>

            {/* Pending Payments Alert */}
            {pendingPayments.length > 0 && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="card p-4 border-l-4 border-l-warning-500"
                >
                    <div className="flex items-start gap-3">
                        <AlertCircle className="w-5 h-5 text-warning-400 flex-shrink-0 mt-0.5" />
                        <div className="flex-1">
                            <h3 className="font-medium text-white">Pago Pendiente</h3>
                            <p className="text-sm text-slate-400 mt-1">
                                Tenés {pendingPayments.length} pago(s) pendiente(s)
                            </p>
                        </div>
                    </div>
                </motion.div>
            )}

            {/* Stats */}
            <div className="grid grid-cols-2 gap-4">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="stat-card"
                >
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-success-500/20 flex items-center justify-center">
                            <Check className="w-5 h-5 text-success-400" />
                        </div>
                        <div>
                            <div className="stat-value text-xl">{payments.filter(p => p.estado === 'paid').length}</div>
                            <div className="stat-label text-xs">Pagos realizados</div>
                        </div>
                    </div>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="stat-card"
                >
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-primary-500/20 flex items-center justify-center">
                            <CreditCard className="w-5 h-5 text-primary-400" />
                        </div>
                        <div>
                            <div className="stat-value text-xl">{formatCurrency(totalPaid)}</div>
                            <div className="stat-label text-xs">Total pagado</div>
                        </div>
                    </div>
                </motion.div>
            </div>

            {/* Payments List */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="card overflow-hidden"
            >
                <div className="p-4 border-b border-slate-800/50">
                    <h2 className="font-semibold text-white">Historial de Pagos</h2>
                </div>
                <div className="divide-y divide-neutral-800/50">
                    {payments.length === 0 ? (
                        <div className="p-8 text-center text-slate-500">
                            No hay pagos registrados
                        </div>
                    ) : (
                        payments.map((payment) => (
                            <div key={payment.id} className="p-4 flex items-center justify-between hover:bg-slate-800/30 transition-colors">
                                <div className="flex items-center gap-4">
                                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${payment.estado === 'paid' ? 'bg-success-500/20' : 'bg-warning-500/20'
                                        }`}>
                                        <Check className={`w-5 h-5 ${payment.estado === 'paid' ? 'text-success-400' : 'text-warning-400'
                                            }`} />
                                    </div>
                                    <div>
                                        <div className="text-sm font-medium text-white">
                                            {payment.concepto_nombre || 'Pago'}
                                        </div>
                                        <div className="text-xs text-slate-500">
                                            {payment.fecha ? new Date(payment.fecha).toLocaleDateString('es-AR') : '-'}
                                            {payment.sucursal_nombre && ` • ${payment.sucursal_nombre}`}
                                            {payment.metodo_pago_nombre && ` • ${payment.metodo_pago_nombre}`}
                                        </div>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <div className="text-sm font-medium text-white">
                                        {formatCurrency(payment.monto || 0)}
                                    </div>
                                    <button
                                        onClick={() => handleDownloadReceipt(payment.id)}
                                        className="text-xs text-primary-400 hover:text-primary-300 flex items-center gap-1"
                                    >
                                        <Download className="w-3 h-3" />
                                        Recibo
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </motion.div>
        </div>
    );
}
