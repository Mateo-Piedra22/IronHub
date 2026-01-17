'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { Dumbbell, LogIn, Eye, EyeOff, User, KeyRound, ChevronDown, ChevronUp, AlertCircle, CheckCircle } from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

export default function UsuarioLoginPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [showPin, setShowPin] = useState(false);
    const [gymLogoUrl, setGymLogoUrl] = useState<string>('');
    const [formData, setFormData] = useState({
        dni: '',
        pin: '',
    });

    // PIN Change state
    const [showPinChange, setShowPinChange] = useState(false);
    const [pinChangeLoading, setPinChangeLoading] = useState(false);
    const [pinChangeError, setPinChangeError] = useState('');
    const [pinChangeSuccess, setPinChangeSuccess] = useState('');
    const [pinChangeData, setPinChangeData] = useState({
        dni: '',
        oldPin: '',
        newPin: '',
    });

    useEffect(() => {
        const loadBranding = async () => {
            try {
                const res = await api.getBootstrap('usuario');
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

        if (!formData.dni.trim()) {
            setError('Ingresá tu DNI');
            return;
        }
        if (!formData.dni.trim()) {
            setError('Ingresá tu DNI');
            return;
        }

        setLoading(true);
        try {
            const res = await api.usuarioLogin({
                dni: formData.dni.trim(),
                pin: "", // PIN is now optional/ignored by default for members
            });

            if (res.ok && res.data?.success) {
                // Check if user is active
                if (res.data.activo === false) {
                    setError('Tu cuenta está inactiva. Consultá en recepción.');
                    return;
                }
                router.push('/usuario');
            } else {
                setError(res.error || res.data?.message || 'Credenciales incorrectas');
            }
        } catch {
            setError('Error de conexión');
        } finally {
            setLoading(false);
        }
    };

    const handlePinChange = async () => {
        setPinChangeError('');
        setPinChangeSuccess('');

        if (!pinChangeData.dni.trim()) {
            setPinChangeError('Ingresá tu DNI');
            return;
        }
        if (!pinChangeData.oldPin.trim()) {
            setPinChangeError('Ingresá tu PIN actual');
            return;
        }
        if (!pinChangeData.newPin.trim() || pinChangeData.newPin.length < 4) {
            setPinChangeError('El nuevo PIN debe tener al menos 4 caracteres');
            return;
        }

        setPinChangeLoading(true);
        try {
            const res = await api.changePin({
                dni: pinChangeData.dni.trim(),
                old_pin: pinChangeData.oldPin.trim(),
                new_pin: pinChangeData.newPin.trim(),
            });

            if (res.ok && res.data?.ok) {
                setPinChangeSuccess('PIN actualizado correctamente');
                // Sync the new PIN to the login form
                setFormData(prev => ({ ...prev, pin: pinChangeData.newPin }));
                // Reset change form
                setPinChangeData({ dni: '', oldPin: '', newPin: '' });
                // Hide after success
                setTimeout(() => {
                    setShowPinChange(false);
                    setPinChangeSuccess('');
                }, 2000);
            } else {
                setPinChangeError(res.error || res.data?.error || 'No se pudo actualizar el PIN');
            }
        } catch {
            setPinChangeError('Error de conexión');
        } finally {
            setPinChangeLoading(false);
        }
    };

    // Pre-fill PIN change DNI when expanding
    const togglePinChange = () => {
        if (!showPinChange && formData.dni) {
            setPinChangeData(prev => ({ ...prev, dni: formData.dni }));
        }
        setShowPinChange(!showPinChange);
        setPinChangeError('');
        setPinChangeSuccess('');
    };

    return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-slate-950">
            {/* Background effects */}
            <div className="fixed inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-primary-500/10 rounded-full blur-3xl" />
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
                        className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 shadow-md mb-4"
                    >
                        {gymLogoUrl ? (
                            <img
                                src={gymLogoUrl}
                                alt="Logo"
                                className="w-10 h-10 object-contain bg-white/90 rounded-xl p-2"
                                onError={() => setGymLogoUrl('')}
                            />
                        ) : (
                            <Dumbbell className="w-8 h-8 text-white" />
                        )}
                    </motion.div>
                    <h1 className="text-2xl font-display font-bold text-white">Acceso Usuario</h1>
                    <p className="text-slate-400 mt-1">Ingresá con tu DNI</p>
                </div>

                {/* Form Card */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="card p-8"
                >
                    <form onSubmit={handleSubmit} className="space-y-6">
                        {/* DNI */}
                        <div className="space-y-2">
                            <label htmlFor="dni" className="block text-sm font-medium text-slate-300">
                                DNI
                            </label>
                            <div className="relative">
                                <input
                                    id="dni"
                                    type="text"
                                    inputMode="numeric"
                                    value={formData.dni}
                                    onChange={(e) => setFormData({ ...formData, dni: e.target.value })}
                                    placeholder="Ingresá tu DNI"
                                    className="w-full px-4 py-3 pl-11 rounded-xl bg-slate-900 border border-slate-800 text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all"
                                    autoComplete="username"
                                    autoFocus
                                />
                                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                            </div>
                            <p className="text-xs text-slate-500">Ingresá los números de tu documento sin puntos.</p>
                        </div>

                        {/* Error */}
                        {error && (
                            <motion.div
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="flex items-center gap-2 p-3 rounded-xl bg-danger-500/10 border border-danger-500/30 text-danger-400 text-sm"
                            >
                                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                                {error}
                            </motion.div>
                        )}

                        {/* Actions */}
                        <div className="flex gap-3">
                            <button
                                type="submit"
                                disabled={loading}
                                className={cn(
                                    'flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-semibold text-white',
                                    'bg-gradient-to-r from-primary-600 to-primary-500',
                                    'hover:shadow-md transition-all duration-300',
                                    'disabled:opacity-50 disabled:cursor-not-allowed'
                                )}
                            >
                                {loading ? (
                                    <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                ) : (
                                    <>
                                        <LogIn className="w-5 h-5" />
                                        Entrar
                                    </>
                                )}
                            </button>
                        </div>
                    </form>

                    {/* PIN Change Section */}
                    <AnimatePresence>
                        {showPinChange && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                className="overflow-hidden"
                            >
                                <div className="mt-6 pt-6 border-t border-slate-800 space-y-4">
                                    <h3 className="text-sm font-medium text-slate-300">Cambiar PIN</h3>

                                    <div className="space-y-3">
                                        <input
                                            type="text"
                                            inputMode="numeric"
                                            value={pinChangeData.dni}
                                            onChange={(e) => setPinChangeData({ ...pinChangeData, dni: e.target.value })}
                                            placeholder="DNI"
                                            className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-white placeholder-neutral-500 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
                                        />
                                        <div className="grid grid-cols-2 gap-3">
                                            <input
                                                type="password"
                                                value={pinChangeData.oldPin}
                                                onChange={(e) => setPinChangeData({ ...pinChangeData, oldPin: e.target.value })}
                                                placeholder="PIN actual"
                                                className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-white placeholder-neutral-500 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
                                            />
                                            <input
                                                type="password"
                                                value={pinChangeData.newPin}
                                                onChange={(e) => setPinChangeData({ ...pinChangeData, newPin: e.target.value })}
                                                placeholder="PIN nuevo"
                                                className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-white placeholder-neutral-500 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
                                            />
                                        </div>
                                    </div>

                                    {/* PIN Change Feedback */}
                                    {pinChangeError && (
                                        <div className="flex items-center gap-2 p-2.5 rounded-lg bg-danger-500/10 border border-danger-500/30 text-danger-400 text-xs">
                                            <AlertCircle className="w-3.5 h-3.5" />
                                            {pinChangeError}
                                        </div>
                                    )}
                                    {pinChangeSuccess && (
                                        <div className="flex items-center gap-2 p-2.5 rounded-lg bg-success-500/10 border border-success-500/30 text-success-400 text-xs">
                                            <CheckCircle className="w-3.5 h-3.5" />
                                            {pinChangeSuccess}
                                        </div>
                                    )}

                                    <button
                                        type="button"
                                        onClick={handlePinChange}
                                        disabled={pinChangeLoading}
                                        className="w-full py-2.5 rounded-xl font-medium text-sm bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700 hover:text-white transition-all disabled:opacity-50"
                                    >
                                        {pinChangeLoading ? 'Actualizando...' : 'Actualizar PIN'}
                                    </button>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* Help text */}
                    <div className="mt-6 pt-6 border-t border-slate-800 text-center">
                        <p className="text-xs text-slate-500">
                            ¿Problemas para ingresar? Comunícate con tu gimnasio
                        </p>
                        {/* Back button */}
                        <Link href="/" className="block w-full py-3 mt-4 rounded-xl font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 text-center transition-all text-sm">
                            ← Volver al inicio
                        </Link>
                    </div>
                </motion.div>
            </motion.div>
        </div>
    );
}

