'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { User, Mail, Phone, Calendar, Shield, Loader2 } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { api, type Usuario } from '@/lib/api';

export default function ProfilePage() {
    const { user } = useAuth();
    const [profile, setProfile] = useState<Usuario | null>(null);
    const [loading, setLoading] = useState(true);

    const loadProfile = useCallback(async () => {
        if (!user?.id) return;
        setLoading(true);
        try {
            const res = await api.getUsuario(user.id);
            if (res.ok && res.data) {
                setProfile(res.data);
            }
        } catch (error) {
            console.error('Error loading profile:', error);
        } finally {
            setLoading(false);
        }
    }, [user?.id]);

    useEffect(() => {
        loadProfile();
    }, [loadProfile]);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
            </div>
        );
    }

    if (!profile) {
        return (
            <div className="flex items-center justify-center h-64">
                <p className="text-slate-500">No se pudo cargar el perfil</p>
            </div>
        );
    }

    const getInitials = (name: string) => {
        return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
    };

    return (
        <div className="space-y-6 py-6">
            <div>
                <h1 className="text-2xl font-display font-bold text-white">Mi Perfil</h1>
                <p className="text-slate-400 mt-1">Información de tu cuenta</p>
            </div>

            {/* Profile Card */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="card p-6"
            >
                <div className="flex items-center gap-4">
                    <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-3xl font-display font-bold text-white shadow-md">
                        {getInitials(profile.nombre)}
                    </div>
                    <div>
                        <h2 className="text-xl font-semibold text-white">{profile.nombre}</h2>
                        <p className="text-slate-400">DNI: {profile.dni || '-'}</p>
                        <div className="flex items-center gap-2 mt-2">
                            <span className={`badge ${profile.activo ? 'badge-success' : 'badge-danger'}`}>
                                <Shield className="w-3 h-3 mr-1" />
                                {profile.activo ? 'Activo' : 'Inactivo'}
                            </span>
                            {profile.fecha_registro && (
                                <span className="text-xs text-slate-500">
                                    Socio desde {new Date(profile.fecha_registro).toLocaleDateString('es-AR', { month: 'long', year: 'numeric' })}
                                </span>
                            )}
                        </div>
                    </div>
                </div>
            </motion.div>

            {/* Info Cards */}
            <div className="grid gap-4">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="card p-4"
                >
                    <h3 className="text-sm font-medium text-slate-400 mb-4">Información de Contacto</h3>
                    <div className="space-y-4">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center">
                                <Mail className="w-5 h-5 text-slate-400" />
                            </div>
                            <div>
                                <div className="text-xs text-slate-500">Email</div>
                                <div className="text-white">{profile.email || 'No registrado'}</div>
                            </div>
                        </div>
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center">
                                <Phone className="w-5 h-5 text-slate-400" />
                            </div>
                            <div>
                                <div className="text-xs text-slate-500">Teléfono</div>
                                <div className="text-white">{profile.telefono || 'No registrado'}</div>
                            </div>
                        </div>
                    </div>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="card p-4"
                >
                    <h3 className="text-sm font-medium text-slate-400 mb-4">Plan y Membresía</h3>
                    <div className="space-y-4">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center">
                                <User className="w-5 h-5 text-slate-400" />
                            </div>
                            <div>
                                <div className="text-xs text-slate-500">Plan Actual</div>
                                <div className="text-white">{profile.tipo_cuota_nombre || 'Sin plan'}</div>
                            </div>
                        </div>
                        {profile.fecha_proximo_vencimiento && (
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center">
                                    <Calendar className="w-5 h-5 text-slate-400" />
                                </div>
                                <div>
                                    <div className="text-xs text-slate-500">Próximo Vencimiento</div>
                                    <div className="text-white">
                                        {new Date(profile.fecha_proximo_vencimiento).toLocaleDateString('es-AR')}
                                        {profile.dias_restantes !== undefined && (
                                            <span className={`ml-2 text-sm ${profile.dias_restantes <= 7 ? 'text-warning-400' : 'text-success-400'}`}>
                                                ({profile.dias_restantes} días)
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </motion.div>
            </div>

            {/* Help Text */}
            <p className="text-center text-slate-500 text-xs">
                Para modificar tus datos, contactá a recepción.
            </p>
        </div>
    );
}

