'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Dumbbell, LogIn, Eye, EyeOff, Shield, Users, KeyRound, Loader2 } from 'lucide-react';
import { api, type Sucursal } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { cn } from '@/lib/utils';

type LoginProfile = {
    kind: 'owner' | 'user';
    id: string | number;
    nombre: string;
    rol: string;
};

export default function GestionLoginPage() {
    const router = useRouter();
    const { checkSession } = useAuth();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [gymLogoUrl, setGymLogoUrl] = useState<string>('');
    const [step, setStep] = useState<'auth' | 'branch'>('auth');
    const [sucursales, setSucursales] = useState<Sucursal[]>([]);
    const [selectedSucursalId, setSelectedSucursalId] = useState<number>(0);
    const [branchLoading, setBranchLoading] = useState(false);
    const [branchError, setBranchError] = useState('');

    const [profiles, setProfiles] = useState<LoginProfile[]>([]);
    const [profilesLoading, setProfilesLoading] = useState(true);
    const [profileOpen, setProfileOpen] = useState(false);

    // Form data
    const [selectedProfile, setSelectedProfile] = useState('__OWNER__');
    const [pin, setPin] = useState('');
    const [ownerPassword, setOwnerPassword] = useState('');

    const selectedProfileItem = profiles.find((p) => String(p.id) === String(selectedProfile)) || null;
    const selectedRole = String(selectedProfileItem?.rol || (selectedProfile === '__OWNER__' ? 'owner' : '')).toLowerCase();

    const roleLabel = (rol: string) => {
        const r = String(rol || '').trim().toLowerCase();
        if (r === 'owner' || r === 'dueño' || r === 'dueno') return 'Dueño';
        if (r === 'admin' || r === 'administrador') return 'Admin';
        if (r === 'profesor') return 'Profesor';
        if (r === 'recepcionista') return 'Recepción';
        if (r === 'empleado') return 'Empleado';
        if (r === 'staff') return 'Staff';
        return r ? r : '—';
    };

    const roleBadgeClass = (rol: string) => {
        const r = String(rol || '').trim().toLowerCase();
        if (r === 'owner' || r === 'dueño' || r === 'dueno') return 'bg-gold-500/15 text-gold-300 border-gold-500/30';
        if (r === 'admin' || r === 'administrador') return 'bg-primary-500/15 text-primary-200 border-primary-500/30';
        if (r === 'profesor') return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
        if (r === 'recepcionista') return 'bg-sky-500/15 text-sky-300 border-sky-500/30';
        if (r === 'empleado') return 'bg-slate-500/15 text-slate-200 border-slate-500/30';
        if (r === 'staff') return 'bg-violet-500/15 text-violet-300 border-violet-500/30';
        return 'bg-slate-500/10 text-slate-300 border-slate-700/60';
    };

    // Load profiles on mount
    useEffect(() => {
        const loadProfiles = async () => {
            try {
                const res = await api.getGestionLoginProfiles();
                if (res.ok && res.data?.ok) {
                    const items = Array.isArray(res.data.items) ? (res.data.items as LoginProfile[]) : [];
                    setProfiles(items);
                    const first = items[0]?.id;
                    if (first !== undefined && first !== null) {
                        setSelectedProfile(String(first));
                    }
                }
            } catch {
            } finally {
                setProfilesLoading(false);
            }
        };
        loadProfiles();
    }, []);

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

    const isOwnerSelected = selectedProfile === '__OWNER__' || selectedRole === 'owner';

    const loadSucursalesAfterLogin = async () => {
        setBranchLoading(true);
        setBranchError('');
        try {
            const res = await api.getSucursales();
            if (!res.ok || !res.data?.ok) {
                throw new Error(res.error || 'No se pudieron cargar sucursales');
            }
            const items = (res.data.items || []).filter((s) => !!s.activa);
            setSucursales(items);
            const current = Number(res.data.sucursal_actual_id || 0);
            const currentValid = current > 0 && items.some((s) => Number(s.id) === current);
            setSelectedSucursalId(currentValid ? current : 0);
            if (currentValid) {
                await checkSession();
                router.push('/gestion/usuarios');
                return;
            }
            if (items.length === 1 && Number(items[0]?.id)) {
                const selRes = await api.seleccionarSucursal(Number(items[0].id));
                if (selRes.ok && selRes.data?.ok) {
                    await checkSession();
                    router.push('/gestion/usuarios');
                    return;
                }
                throw new Error(selRes.error || selRes.data?.error || 'No se pudo seleccionar sucursal');
            }
            if (items.length === 0) {
                setBranchError('No tenés sucursales asignadas. Pedile al dueño que te habilite una.');
                try { await api.logoutGestion(); } catch { }
                return;
            }
            setStep('branch');
        } catch (e) {
            setBranchError(e instanceof Error ? e.message : 'Error cargando sucursales');
            try { await api.logoutGestion(); } catch { }
        } finally {
            setBranchLoading(false);
        }
    };

    const handleSelectSucursal = async () => {
        setBranchError('');
        const sid = Number(selectedSucursalId || 0);
        if (!sid) {
            setBranchError('Seleccioná una sucursal');
            return;
        }
        setBranchLoading(true);
        try {
            const res = await api.seleccionarSucursal(sid);
            if (res.ok && res.data?.ok) {
                await checkSession();
                router.push('/gestion/usuarios');
            } else {
                setBranchError(res.error || res.data?.error || 'No se pudo seleccionar sucursal');
            }
        } catch {
            setBranchError('Error al seleccionar sucursal');
        } finally {
            setBranchLoading(false);
        }
    };

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
                await checkSession();
                await loadSucursalesAfterLogin();
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
                    <h1 className="text-2xl font-display font-bold text-white">Panel de Gestión</h1>
                    <p className="text-slate-400 mt-1">Acceso para personal autorizado</p>
                </div>

                {/* Form Card */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="card p-8"
                >
                    {step === 'auth' ? (
                        <form onSubmit={handleSubmit} className="space-y-6">
                        {/* Profile Selector */}
                        <div className="space-y-2">
                            <label htmlFor="profile" className="block text-sm font-medium text-slate-300">
                                Seleccionar perfil
                            </label>
                            <div className="relative">
                                <button
                                    id="profile"
                                    type="button"
                                    disabled={profilesLoading}
                                    onClick={() => setProfileOpen((v) => !v)}
                                    className={cn(
                                        'w-full px-4 py-3 pl-11 pr-10 rounded-xl bg-slate-900 border border-slate-800 text-white text-left',
                                        'focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all disabled:opacity-50'
                                    )}
                                >
                                    <div className="flex items-center justify-between gap-3">
                                        <div className="truncate">
                                            {selectedProfileItem?.nombre || (profilesLoading ? 'Cargando…' : 'Seleccioná un perfil')}
                                        </div>
                                        <span className={cn('shrink-0 text-xs px-2 py-0.5 rounded-full border', roleBadgeClass(selectedProfileItem?.rol || (selectedProfile === '__OWNER__' ? 'owner' : '')))}>
                                            {roleLabel(selectedProfileItem?.rol || (selectedProfile === '__OWNER__' ? 'owner' : ''))}
                                        </span>
                                    </div>
                                </button>
                                <Users className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                                {profilesLoading && (
                                    <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 animate-spin" />
                                )}
                                {!profilesLoading && (
                                    <div className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500">
                                        <span className={cn('block w-2 h-2 border-r-2 border-b-2 border-slate-500 rotate-45', profileOpen ? '-translate-y-0.5' : 'translate-y-0')} />
                                    </div>
                                )}
                            </div>
                            {profileOpen && !profilesLoading && (
                                <div className="mt-2 rounded-xl border border-slate-800/60 bg-slate-950/60 backdrop-blur-lg overflow-hidden">
                                    <div className="max-h-72 overflow-auto">
                                        {profiles.map((p) => (
                                            <button
                                                key={`${p.kind}:${String(p.id)}`}
                                                type="button"
                                                onClick={() => {
                                                    setSelectedProfile(String(p.id));
                                                    setProfileOpen(false);
                                                    setError('');
                                                    setPin('');
                                                    setOwnerPassword('');
                                                }}
                                                className={cn(
                                                    'w-full px-4 py-3 flex items-center justify-between gap-3 text-left',
                                                    'hover:bg-slate-900/50 transition-colors',
                                                    String(selectedProfile) === String(p.id) ? 'bg-slate-900/60' : ''
                                                )}
                                            >
                                                <div className="truncate text-sm text-slate-200">{p.nombre}</div>
                                                <span className={cn('shrink-0 text-xs px-2 py-0.5 rounded-full border', roleBadgeClass(p.rol))}>
                                                    {roleLabel(p.rol)}
                                                </span>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
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
                            disabled={loading || profilesLoading}
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
                    ) : (
                        <div className="space-y-6">
                            <div className="space-y-2">
                                <label className="block text-sm font-medium text-slate-300">
                                    Sucursal
                                </label>
                                <div className="relative">
                                    <select
                                        value={String(selectedSucursalId || '')}
                                        onChange={(e) => setSelectedSucursalId(Number(e.target.value) || 0)}
                                        disabled={branchLoading}
                                        className="w-full px-4 py-3 rounded-xl bg-slate-900 border border-slate-800 text-white appearance-none focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all disabled:opacity-50"
                                    >
                                        <option value="">Seleccioná una sucursal</option>
                                        {sucursales.map((s) => (
                                            <option key={s.id} value={String(s.id)}>
                                                {s.nombre}
                                            </option>
                                        ))}
                                    </select>
                                    {branchLoading && (
                                        <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 animate-spin" />
                                    )}
                                </div>
                            </div>

                            {(branchError || error) && (
                                <motion.div
                                    initial={{ opacity: 0, y: -10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="p-3 rounded-xl bg-danger-500/10 border border-danger-500/30 text-danger-400 text-sm"
                                >
                                    {branchError || error}
                                </motion.div>
                            )}

                            <button
                                type="button"
                                onClick={handleSelectSucursal}
                                disabled={branchLoading}
                                className={cn(
                                    'w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-semibold text-white',
                                    'bg-gradient-to-r from-primary-600 to-primary-500',
                                    'hover:shadow-md transition-all duration-300',
                                    'disabled:opacity-50 disabled:cursor-not-allowed'
                                )}
                            >
                                {branchLoading ? (
                                    <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                ) : (
                                    <>
                                        <LogIn className="w-5 h-5" />
                                        Entrar
                                    </>
                                )}
                            </button>

                            <button
                                type="button"
                                onClick={async () => {
                                    try { await api.logoutGestion(); } catch { }
                                    setStep('auth');
                                    setSucursales([]);
                                    setSelectedSucursalId(0);
                                    setBranchError('');
                                }}
                                className="w-full py-3 rounded-xl font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 text-center transition-all text-sm"
                                disabled={branchLoading}
                            >
                                Volver
                            </button>
                        </div>
                    )}

                    {/* Admin notice */}
                    <div className="mt-6 pt-6 border-t border-slate-800">
                        <div className="flex items-center gap-2 text-xs text-slate-500">
                            <Shield className="w-4 h-4" />
                            <span>Acceso restringido a personal autorizado</span>
                        </div>
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

