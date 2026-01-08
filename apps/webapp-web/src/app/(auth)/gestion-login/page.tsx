'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Dumbbell, LogIn, Eye, EyeOff, Shield, Users, KeyRound, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface ProfesorBasico {
    usuario_id: number;
    nombre: string;
    profesor_id: number;
}

export default function GestionLoginPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [showPassword, setShowPassword] = useState(false);

    // Professors list
    const [profesores, setProfesores] = useState<ProfesorBasico[]>([]);
    const [loadingProfesores, setLoadingProfesores] = useState(true);

    // Form data
    const [selectedProfile, setSelectedProfile] = useState('__OWNER__');
    const [pin, setPin] = useState('');
    const [ownerPassword, setOwnerPassword] = useState('');

    // Load professors on mount
    useEffect(() => {
        const loadProfesores = async () => {
            try {
                const res = await api.getProfesoresBasico();
                if (res.ok && Array.isArray(res.data)) {
                    setProfesores(res.data);
                }
            } catch (err) {
                console.error('Error loading professors:', err);
            } finally {
                setLoadingProfesores(false);
            }
        };
        loadProfesores();
    }, []);

    const isOwnerSelected = selectedProfile === '__OWNER__';

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        // Validation
        if (!selectedProfile) {
            setError('Seleccioná un perfil');
            return;
        }

        if (isOwnerSelected) {
            if (!ownerPassword.trim()) {
                setError('Ingresá la contraseña del dueño');
                return;
            }
        } else {
            if (!pin.trim()) {
                setError('Ingresá tu PIN');
                return;
            }
        }

        setLoading(true);
        try {
            const credentials = isOwnerSelected
                ? { usuario_id: '__OWNER__', owner_password: ownerPassword }
                : { usuario_id: selectedProfile, pin };

            const res = await api.gestionLogin(credentials);

            if (res.ok && res.data?.ok !== false) {
                router.push('/gestion/usuarios');
            } else {
                setError(res.error || res.data?.message || 'Credenciales incorrectas');
            }
        } catch {
            setError('Error de conexión');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-slate-950">
            {/* Background effects */}
            <div className="fixed inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary-500/10 rounded-full blur-3xl" />
                <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-gold-500/5 rounded-full blur-3xl" />
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
                        <Dumbbell className="w-8 h-8 text-white" />
                    </motion.div>
                    <h1 className="text-2xl font-display font-bold text-white">Panel de Gestión</h1>
                    <p className="text-slate-400 mt-1">Acceso para profesores o dueño</p>
                </div>

                {/* Form Card */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="card p-8"
                >
                    <form onSubmit={handleSubmit} className="space-y-6">
                        {/* Profile Selector */}
                        <div className="space-y-2">
                            <label htmlFor="profile" className="block text-sm font-medium text-slate-300">
                                Seleccionar perfil
                            </label>
                            <div className="relative">
                                <select
                                    id="profile"
                                    value={selectedProfile}
                                    onChange={(e) => {
                                        setSelectedProfile(e.target.value);
                                        setError('');
                                        setPin('');
                                        setOwnerPassword('');
                                    }}
                                    disabled={loadingProfesores}
                                    className="w-full px-4 py-3 pl-11 rounded-xl bg-slate-900 border border-slate-800 text-white appearance-none focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all disabled:opacity-50"
                                >
                                    <option value="__OWNER__">👑 Dueño</option>
                                    {profesores.map((p) => (
                                        <option key={p.usuario_id} value={String(p.usuario_id)}>
                                            {p.nombre || `Profesor ${p.profesor_id}`}
                                        </option>
                                    ))}
                                </select>
                                <Users className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                                {loadingProfesores && (
                                    <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 animate-spin" />
                                )}
                            </div>
                        </div>

                        {/* Conditional: PIN for professors */}
                        {!isOwnerSelected && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                className="space-y-2"
                            >
                                <label htmlFor="pin" className="block text-sm font-medium text-slate-300">
                                    PIN
                                </label>
                                <div className="relative">
                                    <input
                                        id="pin"
                                        type={showPassword ? 'text' : 'password'}
                                        value={pin}
                                        onChange={(e) => setPin(e.target.value)}
                                        placeholder="Ingresá tu PIN"
                                        maxLength={6}
                                        className="w-full px-4 py-3 pl-11 pr-12 rounded-xl bg-slate-900 border border-slate-800 text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all"
                                        autoComplete="current-password"
                                    />
                                    <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-500 hover:text-white transition-colors"
                                        tabIndex={-1}
                                    >
                                        {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                    </button>
                                </div>
                            </motion.div>
                        )}

                        {/* Conditional: Password for owner */}
                        {isOwnerSelected && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                className="space-y-2"
                            >
                                <label htmlFor="owner_password" className="block text-sm font-medium text-slate-300">
                                    Contraseña del dueño
                                </label>
                                <div className="relative">
                                    <input
                                        id="owner_password"
                                        type={showPassword ? 'text' : 'password'}
                                        value={ownerPassword}
                                        onChange={(e) => setOwnerPassword(e.target.value)}
                                        placeholder="Ingresá la contraseña"
                                        className="w-full px-4 py-3 pr-12 rounded-xl bg-slate-900 border border-slate-800 text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all"
                                        autoComplete="current-password"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-500 hover:text-white transition-colors"
                                        tabIndex={-1}
                                    >
                                        {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                    </button>
                                </div>
                            </motion.div>
                        )}

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
                            disabled={loading || loadingProfesores}
                            className={cn(
                                'w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-semibold text-white',
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
                                    Ingresar
                                </>
                            )}
                        </button>
                    </form>

                    {/* Admin notice */}
                    <div className="mt-6 pt-6 border-t border-slate-800">
                        <div className="flex items-center gap-2 text-xs text-slate-500">
                            <Shield className="w-4 h-4" />
                            <span>Acceso restringido a personal autorizado</span>
                        </div>
                    </div>
                </motion.div>
            </motion.div>
        </div>
    );
}

