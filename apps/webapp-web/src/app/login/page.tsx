'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Dumbbell, Eye, EyeOff, Loader2, AlertCircle, Lock } from 'lucide-react';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';

export default function OwnerLoginPage() {
    const router = useRouter();
    const { checkSession } = useAuth();
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [gymLogoUrl, setGymLogoUrl] = useState<string>('');

    useEffect(() => {
        const loadBranding = async () => {
            try {
                const res = await api.getBootstrap('gestion');
                const logo = res.ok ? (res.data?.gym?.logo_url || '') : '';
                if (logo) setGymLogoUrl(logo);
            } catch {
                // ignore
            }
        };
        loadBranding();
    }, []);

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
                await checkSession();
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
                <div className="absolute -top-40 -right-40 h-[500px] w-[500px] rounded-full bg-primary-600/20 blur-[100px]" />
                <div className="absolute bottom-0 -left-40 h-[400px] w-[400px] rounded-full bg-gold-600/10 blur-[100px]" />
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full max-w-md relative z-10"
            >
                <div className="card p-8">
                    {/* Logo */}
                    <div className="flex flex-col items-center mb-8">
                        <div
                            className={`w-16 h-16 rounded-2xl mb-4 shadow-md overflow-hidden flex items-center justify-center ${
                                gymLogoUrl ? 'bg-transparent' : 'bg-gradient-to-br from-primary-500 to-primary-700'
                            }`}
                        >
                            {gymLogoUrl ? (
                                <img
                                    src={gymLogoUrl}
                                    alt="Logo"
                                    className="w-full h-full object-contain"
                                    onError={() => setGymLogoUrl('')}
                                />
                            ) : (
                                <Dumbbell className="w-8 h-8 text-white" />
                            )}
                        </div>
                        <h1 className="text-2xl font-display font-bold text-white">
                            Panel de Control
                        </h1>
                        <p className="text-slate-400 mt-1">Acceso exclusivo del dueño</p>
                    </div>

                    {/* Form */}
                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div>
                            <label htmlFor="password" className="label">
                                Contraseña
                            </label>
                            <div className="relative">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
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
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
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
                    <p className="text-center text-slate-500 text-xs mt-6">
                        Este acceso es exclusivo para el propietario del gimnasio.
                    </p>

                    {/* Back button */}
                    <Link href="/" className="block w-full py-3 mt-4 rounded-xl font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 text-center transition-all text-sm">
                        ← Volver al inicio
                    </Link>
                </div>
            </motion.div>
        </div>
    );
}

