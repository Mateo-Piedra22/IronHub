'use client';

import { useState } from 'react';
import { Settings, Shield, Database, Bell, Palette } from 'lucide-react';

export default function SettingsPage() {
    const [activeTab, setActiveTab] = useState('general');

    const tabs = [
        { id: 'general', name: 'General', icon: Settings },
        { id: 'security', name: 'Seguridad', icon: Shield },
        { id: 'database', name: 'Base de datos', icon: Database },
        { id: 'notifications', name: 'Notificaciones', icon: Bell },
        { id: 'appearance', name: 'Apariencia', icon: Palette },
    ];

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
            <div className="card p-6">
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

                {activeTab === 'security' && (
                    <div className="space-y-6">
                        <h2 className="text-lg font-semibold text-white">Seguridad</h2>
                        <div className="grid gap-4 max-w-lg">
                            <div>
                                <label className="label">Cambiar contraseña admin</label>
                                <input type="password" className="input" placeholder="Nueva contraseña" />
                            </div>
                            <div>
                                <label className="label">Confirmar contraseña</label>
                                <input type="password" className="input" placeholder="Confirmar" />
                            </div>
                            <button className="btn-primary w-fit">Actualizar contraseña</button>
                        </div>
                        <hr className="border-slate-800" />
                        <div>
                            <h3 className="font-medium text-white mb-2">Sesiones activas</h3>
                            <p className="text-slate-500 text-sm">Funcionalidad próximamente</p>
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
            </div>
        </div>
    );
}

