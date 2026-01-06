'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Dumbbell, Eye, EyeOff, Loader2, AlertCircle, Lock } from 'lucide-react';
import { api } from '@/lib/api';

export default function OwnerLoginPage() {
    const router = useRouter();
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (!password.trim()) {
            setError('Ingresá la contraseña');
            return;
        }

        setLoading(true);

        try {
            const res = await api.ownerLogin(password);

            if (res.ok && res.data?.ok !== false) {
                router.push('/dashboard');
            } else {
                setError(res.error || res.data?.message || 'Contraseña incorrecta');
            }
        } catch {
            setError('Error de conexión');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center p-4">
            {/* Background effects */}
            <div className="fixed inset-0 pointer-events-none">
                <div className="absolute -top-40 -right-40 h-[500px] w-[500px] rounded-full bg-iron-600/20 blur-[100px]" />
                <div className="absolute bottom-0 -left-40 h-[400px] w-[400px] rounded-full bg-gold-600/10 blur-[100px]" />
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full max-w-md relative z-10"
            >
                <div className="glass-card p-8">
                    {/* Logo */}
                    <div className="flex flex-col items-center mb-8">
                        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-iron-500 to-iron-700 flex items-center justify-center mb-4 shadow-glow-md">
                            <Dumbbell className="w-8 h-8 text-white" />
                        </div>
                        <h1 className="text-2xl font-display font-bold text-white">
                            Panel de Control
                        </h1>
                        <p className="text-neutral-400 mt-1">Acceso exclusivo del dueño</p>
                    </div>

                    {/* Form */}
                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div>
                            <label htmlFor="password" className="label">
                                Contraseña
                            </label>
                            <div className="relative">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-500" />
                                <input
                                    id="password"
                                    type={showPassword ? 'text' : 'password'}
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="input pl-12 pr-12"
                                    placeholder="Ingresá tu contraseña"
                                    autoFocus
                                    autoComplete="current-password"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-neutral-300 transition-colors"
                                >
                                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                </button>
                            </div>
                        </div>

                        {error && (
                            <motion.div
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="flex items-center gap-2 text-danger-400 text-sm bg-danger-500/10 border border-danger-500/20 rounded-lg px-4 py-3"
                            >
                                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                                {error}
                            </motion.div>
                        )}

                        <button
                            type="submit"
                            disabled={loading || !password}
                            className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {loading ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Verificando...
                                </>
                            ) : (
                                'Ingresar'
                            )}
                        </button>
                    </form>

                    {/* Help text */}
                    <p className="text-center text-neutral-500 text-xs mt-6">
                        Este acceso es exclusivo para el propietario del gimnasio.
                    </p>
                </div>
            </motion.div>
        </div>
    );
}
