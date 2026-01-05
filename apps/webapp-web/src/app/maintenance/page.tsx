'use client';

import { motion } from 'framer-motion';
import { Wrench, Clock, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function MaintenancePage() {
    return (
        <div className="min-h-screen bg-gradient-to-br from-neutral-950 via-neutral-900 to-neutral-950 flex items-center justify-center p-4">
            {/* Background effects */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute -top-1/2 -left-1/2 w-full h-full bg-gradient-radial from-iron-500/10 to-transparent" />
                <div className="absolute -bottom-1/2 -right-1/2 w-full h-full bg-gradient-radial from-warning-500/10 to-transparent" />
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
                        className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-warning-500/20 flex items-center justify-center"
                    >
                        <Wrench className="w-10 h-10 text-warning-400" />
                    </motion.div>

                    {/* Title */}
                    <motion.h1
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.3 }}
                        className="text-2xl font-display font-bold text-white mb-3"
                    >
                        Sistema en Mantenimiento
                    </motion.h1>

                    {/* Description */}
                    <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.4 }}
                        className="text-neutral-400 mb-6"
                    >
                        Estamos realizando mejoras en el sistema. Por favor, vuelve a intentarlo en unos minutos.
                    </motion.p>

                    {/* Estimated time */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.5 }}
                        className="flex items-center justify-center gap-2 text-sm text-neutral-500 mb-6"
                    >
                        <Clock className="w-4 h-4" />
                        <span>Tiempo estimado: 15-30 minutos</span>
                    </motion.div>

                    {/* Contact info */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.6 }}
                        className="p-4 rounded-xl bg-neutral-800/50 border border-neutral-700"
                    >
                        <p className="text-sm text-neutral-400">
                            Si el problema persiste, contacta al administrador de tu gimnasio.
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
                            className="inline-flex items-center gap-2 text-iron-400 hover:text-iron-300 transition-colors"
                        >
                            <ArrowLeft className="w-4 h-4" />
                            <span>Volver al inicio</span>
                        </Link>
                    </motion.div>
                </div>

                {/* Animated dots */}
                <div className="flex justify-center gap-2 mt-6">
                    {[0, 1, 2].map((i) => (
                        <motion.div
                            key={i}
                            className="w-2 h-2 rounded-full bg-warning-400"
                            animate={{
                                scale: [1, 1.5, 1],
                                opacity: [0.5, 1, 0.5],
                            }}
                            transition={{
                                duration: 1.5,
                                repeat: Infinity,
                                delay: i * 0.2,
                            }}
                        />
                    ))}
                </div>
            </motion.div>
        </div>
    );
}
