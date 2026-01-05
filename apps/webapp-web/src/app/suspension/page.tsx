'use client';

import { motion } from 'framer-motion';
import { UserX, Phone, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function SuspensionPage() {
    return (
        <div className="min-h-screen bg-gradient-to-br from-neutral-950 via-neutral-900 to-neutral-950 flex items-center justify-center p-4">
            {/* Background effects */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute -top-1/2 -left-1/2 w-full h-full bg-gradient-radial from-danger-500/10 to-transparent" />
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="relative z-10 max-w-md w-full"
            >
                <div className="glass-card p-8 text-center">
                    {/* Icon */}
                    <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
                        className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-danger-500/20 flex items-center justify-center"
                    >
                        <UserX className="w-10 h-10 text-danger-400" />
                    </motion.div>

                    {/* Title */}
                    <motion.h1
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.3 }}
                        className="text-2xl font-display font-bold text-white mb-3"
                    >
                        Cuenta Suspendida
                    </motion.h1>

                    {/* Description */}
                    <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.4 }}
                        className="text-neutral-400 mb-6"
                    >
                        Tu cuenta ha sido suspendida temporalmente debido a cuotas vencidas.
                    </motion.p>

                    {/* Reason box */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.5 }}
                        className="p-4 rounded-xl bg-danger-500/10 border border-danger-500/30 mb-6"
                    >
                        <p className="text-sm text-danger-300">
                            Para reactivar tu cuenta, por favor regulariza tus pagos pendientes.
                        </p>
                    </motion.div>

                    {/* Contact section */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.6 }}
                        className="p-4 rounded-xl bg-neutral-800/50 border border-neutral-700"
                    >
                        <div className="flex items-center justify-center gap-2 text-neutral-400 mb-2">
                            <Phone className="w-4 h-4" />
                            <span className="text-sm font-medium">Contactá al gimnasio</span>
                        </div>
                        <p className="text-sm text-neutral-500">
                            Acercate a recepción o comunicate con el administrador para resolver tu situación.
                        </p>
                    </motion.div>

                    {/* Back button */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.7 }}
                        className="mt-6"
                    >
                        <Link
                            href="/"
                            className="inline-flex items-center gap-2 text-neutral-400 hover:text-neutral-300 transition-colors"
                        >
                            <ArrowLeft className="w-4 h-4" />
                            <span>Volver al inicio</span>
                        </Link>
                    </motion.div>
                </div>
            </motion.div>
        </div>
    );
}
