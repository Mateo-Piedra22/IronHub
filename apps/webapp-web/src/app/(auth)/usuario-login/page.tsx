'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Dumbbell, LogIn, Eye, EyeOff, User } from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

export default function UsuarioLoginPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [formData, setFormData] = useState({
        dni: '',
        password: '',
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (!formData.dni.trim()) {
            setError('Ingresa tu DNI');
            return;
        }

        setLoading(true);
        try {
            const res = await api.login({
                dni: formData.dni,
                password: formData.password || formData.dni, // Default password = DNI
            });

            if (res.ok && res.data?.ok) {
                router.push('/dashboard');
            } else {
                setError(res.error || 'DNI no encontrado o datos incorrectos');
            }
        } catch {
            setError('Error de conexión');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-neutral-950">
            {/* Background effects */}
            <div className="fixed inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-iron-500/10 rounded-full blur-3xl" />
                <div className="absolute bottom-1/3 left-1/4 w-80 h-80 bg-success-500/5 rounded-full blur-3xl" />
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full max-w-md relative"
            >
                {/* Logo */}
                <div className="text-center mb-8">
                    <motion.div
                        initial={{ scale: 0.8 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.1 }}
                        className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-iron-500 to-iron-700 shadow-glow-md mb-4"
                    >
                        <Dumbbell className="w-8 h-8 text-white" />
                    </motion.div>
                    <h1 className="text-2xl font-display font-bold text-white">Mi Gimnasio</h1>
                    <p className="text-neutral-400 mt-1">Accede a tu panel de socio</p>
                </div>

                {/* Form Card */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="glass-card p-8"
                >
                    <form onSubmit={handleSubmit} className="space-y-6">
                        {/* DNI */}
                        <div className="space-y-2">
                            <label htmlFor="dni" className="block text-sm font-medium text-neutral-300">
                                DNI
                            </label>
                            <div className="relative">
                                <input
                                    id="dni"
                                    type="text"
                                    inputMode="numeric"
                                    value={formData.dni}
                                    onChange={(e) => setFormData({ ...formData, dni: e.target.value })}
                                    placeholder="Ingresa tu DNI"
                                    className="w-full px-4 py-3 pl-11 rounded-xl bg-neutral-900 border border-neutral-800 text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-iron-500/50 focus:border-iron-500 transition-all"
                                    autoComplete="username"
                                />
                                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-500" />
                            </div>
                        </div>

                        {/* Password (optional for users) */}
                        <div className="space-y-2">
                            <label htmlFor="password" className="block text-sm font-medium text-neutral-300">
                                Contraseña <span className="text-neutral-500">(opcional)</span>
                            </label>
                            <div className="relative">
                                <input
                                    id="password"
                                    type={showPassword ? 'text' : 'password'}
                                    value={formData.password}
                                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                    placeholder="Deja vacío si usas tu DNI"
                                    className="w-full px-4 py-3 pr-12 rounded-xl bg-neutral-900 border border-neutral-800 text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-iron-500/50 focus:border-iron-500 transition-all"
                                    autoComplete="current-password"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-neutral-500 hover:text-white transition-colors"
                                    tabIndex={-1}
                                >
                                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                </button>
                            </div>
                        </div>

                        {/* Error */}
                        {error && (
                            <motion.div
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="p-3 rounded-xl bg-danger-500/10 border border-danger-500/30 text-danger-400 text-sm"
                            >
                                {error}
                            </motion.div>
                        )}

                        {/* Submit */}
                        <button
                            type="submit"
                            disabled={loading}
                            className={cn(
                                'w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-semibold text-white',
                                'bg-gradient-to-r from-iron-600 to-iron-500',
                                'hover:shadow-glow-md transition-all duration-300',
                                'disabled:opacity-50 disabled:cursor-not-allowed'
                            )}
                        >
                            {loading ? (
                                <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            ) : (
                                <>
                                    <LogIn className="w-5 h-5" />
                                    Ingresar
                                </>
                            )}
                        </button>
                    </form>

                    {/* Help text */}
                    <div className="mt-6 pt-6 border-t border-neutral-800 text-center">
                        <p className="text-xs text-neutral-500">
                            ¿Problemas para ingresar? Comunícate con tu gimnasio
                        </p>
                    </div>
                </motion.div>
            </motion.div>
        </div>
    );
}
