'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
    Settings, Shield, Database, Bell, Palette,
    Loader2, Check, AlertTriangle, Lock, Key
} from 'lucide-react';
import { api } from '@/lib/api';

export default function SettingsPage() {
    const [activeTab, setActiveTab] = useState('security');

    // Security state
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [passwordLoading, setPasswordLoading] = useState(false);
    const [passwordMessage, setPasswordMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

    const tabs = [
        { id: 'security', name: 'Seguridad', icon: Shield },
        { id: 'general', name: 'General', icon: Settings },
        { id: 'database', name: 'Base de datos', icon: Database },
        { id: 'notifications', name: 'Notificaciones', icon: Bell },
        { id: 'appearance', name: 'Apariencia', icon: Palette },
    ];

    const handlePasswordChange = async (e: React.FormEvent) => {
        e.preventDefault();
        setPasswordMessage(null);

        if (!currentPassword.trim()) {
            setPasswordMessage({ type: 'error', text: 'Ingresa tu contraseña actual' });
            return;
        }
        if (!newPassword.trim() || newPassword.length < 8) {
            setPasswordMessage({ type: 'error', text: 'La nueva contraseña debe tener al menos 8 caracteres' });
            return;
        }
        if (newPassword !== confirmPassword) {
            setPasswordMessage({ type: 'error', text: 'Las contraseñas no coinciden' });
            return;
        }

        setPasswordLoading(true);
        try {
            const res = await api.changeAdminPassword(currentPassword, newPassword);
            if (res.ok) {
                setPasswordMessage({ type: 'success', text: '¡Contraseña actualizada correctamente!' });
                setCurrentPassword('');
                setNewPassword('');
                setConfirmPassword('');
            } else {
                setPasswordMessage({ type: 'error', text: res.error || 'Error al cambiar la contraseña' });
            }
        } catch {
            setPasswordMessage({ type: 'error', text: 'Error de conexión' });
        } finally {
            setPasswordLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <div>
                <h1 className="page-title">Configuración</h1>
                <p className="text-slate-400 mt-1">Configuración global del sistema</p>
            </div>

            {/* Tabs */}
            <div className="flex gap-2 flex-wrap">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${activeTab === tab.id
                                ? 'bg-primary-500/20 text-primary-400'
                                : 'bg-slate-800/50 text-slate-400 hover:text-white'
                            }`}
                    >
                        <tab.icon className="w-4 h-4" />
                        {tab.name}
                    </button>
                ))}
            </div>

            {/* Content */}
            <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="card p-6"
            >
                {activeTab === 'security' && (
                    <div className="space-y-8">
                        <div>
                            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                                <Lock className="w-5 h-5 text-primary-400" />
                                Cambiar Contraseña Admin
                            </h2>
                            <p className="text-slate-500 text-sm mt-1">
                                Cambia la contraseña de acceso al panel de administración
                            </p>
                        </div>

                        <form onSubmit={handlePasswordChange} className="space-y-4 max-w-md">
                            <div>
                                <label className="label">Contraseña actual</label>
                                <div className="relative">
                                    <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                    <input
                                        type="password"
                                        value={currentPassword}
                                        onChange={(e) => setCurrentPassword(e.target.value)}
                                        className="input pl-10"
                                        placeholder="••••••••"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="label">Nueva contraseña</label>
                                <div className="relative">
                                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                    <input
                                        type="password"
                                        value={newPassword}
                                        onChange={(e) => setNewPassword(e.target.value)}
                                        className="input pl-10"
                                        placeholder="Mínimo 8 caracteres"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="label">Confirmar contraseña</label>
                                <div className="relative">
                                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                    <input
                                        type="password"
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        className="input pl-10"
                                        placeholder="Repite la nueva contraseña"
                                    />
                                </div>
                            </div>

                            {passwordMessage && (
                                <div className={`p-3 rounded-lg flex items-start gap-2 ${passwordMessage.type === 'success'
                                        ? 'bg-success-500/10 border border-success-500/20 text-success-400'
                                        : 'bg-red-500/10 border border-red-500/20 text-red-400'
                                    }`}>
                                    {passwordMessage.type === 'success'
                                        ? <Check className="w-4 h-4 mt-0.5" />
                                        : <AlertTriangle className="w-4 h-4 mt-0.5" />
                                    }
                                    <span className="text-sm">{passwordMessage.text}</span>
                                </div>
                            )}

                            <button
                                type="submit"
                                disabled={passwordLoading}
                                className="btn-primary w-full flex items-center justify-center gap-2"
                            >
                                {passwordLoading ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                    <Shield className="w-4 h-4" />
                                )}
                                Actualizar contraseña
                            </button>
                        </form>

                        <hr className="border-slate-800" />

                        <div>
                            <h3 className="font-medium text-white mb-2">Sesiones activas</h3>
                            <p className="text-slate-500 text-sm">Funcionalidad próximamente</p>
                        </div>
                    </div>
                )}

                {activeTab === 'general' && (
                    <div className="space-y-6">
                        <h2 className="text-lg font-semibold text-white">Configuración General</h2>
                        <div className="grid gap-4 max-w-lg">
                            <div>
                                <label className="label">Nombre del sistema</label>
                                <input type="text" className="input" defaultValue="IronHub" />
                            </div>
                            <div>
                                <label className="label">Dominio de tenants</label>
                                <input
                                    type="text"
                                    className="input"
                                    defaultValue={process.env.NEXT_PUBLIC_TENANT_DOMAIN || 'ironhub.motiona.xyz'}
                                    disabled
                                />
                                <p className="text-xs text-slate-500 mt-1">Configurado via variable de entorno</p>
                            </div>
                            <div>
                                <label className="label">Zona horaria</label>
                                <select className="input" defaultValue="America/Argentina/Buenos_Aires">
                                    <option value="America/Argentina/Buenos_Aires">Argentina (Buenos Aires)</option>
                                    <option value="America/Mexico_City">México (Ciudad de México)</option>
                                    <option value="America/Bogota">Colombia (Bogotá)</option>
                                    <option value="Europe/Madrid">España (Madrid)</option>
                                </select>
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'database' && (
                    <div className="space-y-6">
                        <h2 className="text-lg font-semibold text-white">Base de datos</h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700">
                                <div className="text-sm text-slate-500">Host</div>
                                <div className="text-white font-mono text-sm mt-1">
                                    {process.env.ADMIN_DB_HOST || '***'}
                                </div>
                            </div>
                            <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700">
                                <div className="text-sm text-slate-500">Estado</div>
                                <div className="text-success-400 font-medium mt-1">Conectado</div>
                            </div>
                        </div>
                        <p className="text-slate-500 text-sm">
                            La configuración de base de datos se gestiona via variables de entorno.
                        </p>
                    </div>
                )}

                {activeTab === 'notifications' && (
                    <div className="space-y-6">
                        <h2 className="text-lg font-semibold text-white">Notificaciones</h2>
                        <div className="space-y-4">
                            <label className="flex items-center gap-3">
                                <input type="checkbox" defaultChecked className="w-4 h-4" />
                                <span className="text-slate-300">Notificar vencimientos próximos</span>
                            </label>
                            <label className="flex items-center gap-3">
                                <input type="checkbox" defaultChecked className="w-4 h-4" />
                                <span className="text-slate-300">Notificar nuevos gimnasios</span>
                            </label>
                            <label className="flex items-center gap-3">
                                <input type="checkbox" className="w-4 h-4" />
                                <span className="text-slate-300">Notificar errores críticos por email</span>
                            </label>
                        </div>
                    </div>
                )}

                {activeTab === 'appearance' && (
                    <div className="space-y-6">
                        <h2 className="text-lg font-semibold text-white">Apariencia</h2>
                        <div className="space-y-4 max-w-lg">
                            <div>
                                <label className="label">Tema</label>
                                <select className="input" defaultValue="dark">
                                    <option value="dark">Oscuro</option>
                                    <option value="light" disabled>
                                        Claro (próximamente)
                                    </option>
                                </select>
                            </div>
                            <div>
                                <label className="label">Color primario</label>
                                <input type="color" className="w-12 h-10 rounded border-0" defaultValue="#6366f1" />
                            </div>
                        </div>
                    </div>
                )}
            </motion.div>
        </div>
    );
}
