'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
    Settings, Shield, Database, Bell, Palette,
    Loader2, Check, AlertTriangle, Lock, Key, Save
} from 'lucide-react';
import { api } from '@/lib/api';

const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null;

interface SettingRow {
    key: string;
    value: unknown;
}

interface JobRun {
    id?: number;
    run_id?: string;
    job_name?: string;
    status?: string;
    started_at?: string;
    finished_at?: string;
    ended_at?: string;
    error?: string;
    output?: unknown;
}

export default function SettingsPage() {
    const [activeTab, setActiveTab] = useState('security');

    // Security state
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [passwordLoading, setPasswordLoading] = useState(false);
    const [passwordMessage, setPasswordMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

    const [settingsLoading, setSettingsLoading] = useState(true);
    const [settingsSaving, setSettingsSaving] = useState(false);
    const [subscriptionSettings, setSubscriptionSettings] = useState({
        reminder_days_before: 7,
        grace_days: 0,
        auto_suspend_enabled: true,
        reminders_enabled: true,
    });
    const [maintenanceSettings, setMaintenanceSettings] = useState({
        default_message: 'Gimnasio en mantenimiento. Volvemos pronto.',
    });
    const [jobRunsLoading, setJobRunsLoading] = useState(true);
    const [jobRuns, setJobRuns] = useState<JobRun[]>([]);
    const [maintenanceRunning, setMaintenanceRunning] = useState(false);

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

    useEffect(() => {
        const run = async () => {
            setSettingsLoading(true);
            try {
                const res = await api.getSettings();
                if (res.ok && res.data?.ok && Array.isArray(res.data.settings)) {
                    const rows = res.data.settings as SettingRow[];
                    const subs = rows.find((r) => r.key === 'subscriptions')?.value;
                    if (isRecord(subs)) {
                        setSubscriptionSettings({
                            reminder_days_before: Number(subs.reminder_days_before ?? 7),
                            grace_days: Number(subs.grace_days ?? 0),
                            auto_suspend_enabled: Boolean(subs.auto_suspend_enabled ?? true),
                            reminders_enabled: Boolean(subs.reminders_enabled ?? true),
                        });
                    }
                    const maint = rows.find((r) => r.key === 'maintenance')?.value;
                    if (isRecord(maint)) {
                        setMaintenanceSettings({
                            default_message: String(maint.default_message || 'Gimnasio en mantenimiento. Volvemos pronto.'),
                        });
                    }
                }
                const jr = await api.listJobRuns('subscriptions_maintenance', 20);
                if (jr.ok && jr.data?.ok && Array.isArray(jr.data.items)) {
                    setJobRuns(jr.data.items as JobRun[]);
                }
            } finally {
                setSettingsLoading(false);
                setJobRunsLoading(false);
            }
        };
        run();
    }, []);

    const saveSettings = async () => {
        setSettingsSaving(true);
        try {
            await api.updateSettings({
                subscriptions: subscriptionSettings,
                maintenance: maintenanceSettings,
            });
        } finally {
            setSettingsSaving(false);
        }
    };

    const refreshJobRuns = async () => {
        setJobRunsLoading(true);
        try {
            const jr = await api.listJobRuns('subscriptions_maintenance', 20);
            if (jr.ok && jr.data?.ok && Array.isArray(jr.data.items)) {
                setJobRuns(jr.data.items as JobRun[]);
            }
        } finally {
            setJobRunsLoading(false);
        }
    };

    const runMaintenanceNow = async () => {
        setMaintenanceRunning(true);
        try {
            await api.runSubscriptionsMaintenance({
                days: subscriptionSettings.reminder_days_before,
                grace_days: subscriptionSettings.grace_days,
            });
            await refreshJobRuns();
        } finally {
            setMaintenanceRunning(false);
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
                        <div className="flex items-center justify-between">
                            <h2 className="text-lg font-semibold text-white">Configuración General</h2>
                            <button
                                onClick={saveSettings}
                                disabled={settingsSaving || settingsLoading}
                                className="btn-primary flex items-center gap-2"
                            >
                                {settingsSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                                Guardar
                            </button>
                        </div>
                        {settingsLoading ? (
                            <div className="flex items-center justify-center py-10">
                                <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
                            </div>
                        ) : (
                            <div className="grid gap-4 max-w-lg">
                                <div>
                                    <label className="label">Mensaje por defecto de mantenimiento</label>
                                    <input
                                        type="text"
                                        className="input"
                                        value={maintenanceSettings.default_message}
                                        onChange={(e) => setMaintenanceSettings({ ...maintenanceSettings, default_message: e.target.value })}
                                    />
                                </div>
                            </div>
                        )}
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
                        <div className="flex items-center justify-between">
                            <h2 className="text-lg font-semibold text-white">Notificaciones</h2>
                            <button
                                onClick={saveSettings}
                                disabled={settingsSaving || settingsLoading}
                                className="btn-primary flex items-center gap-2"
                            >
                                {settingsSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                                Guardar
                            </button>
                        </div>
                        {settingsLoading ? (
                            <div className="flex items-center justify-center py-10">
                                <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
                            </div>
                        ) : (
                            <div className="space-y-6 max-w-3xl">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <label className="label">Días antes para recordar</label>
                                        <input
                                            type="number"
                                            className="input"
                                            value={subscriptionSettings.reminder_days_before}
                                            min={1}
                                            max={90}
                                            onChange={(e) =>
                                                setSubscriptionSettings({ ...subscriptionSettings, reminder_days_before: Number(e.target.value) })
                                            }
                                        />
                                    </div>
                                    <div>
                                        <label className="label">Grace period (días)</label>
                                        <input
                                            type="number"
                                            className="input"
                                            value={subscriptionSettings.grace_days}
                                            min={0}
                                            max={60}
                                            onChange={(e) => setSubscriptionSettings({ ...subscriptionSettings, grace_days: Number(e.target.value) })}
                                        />
                                    </div>
                                    <label className="flex items-center gap-3">
                                        <input
                                            type="checkbox"
                                            checked={subscriptionSettings.reminders_enabled}
                                            onChange={(e) =>
                                                setSubscriptionSettings({ ...subscriptionSettings, reminders_enabled: e.target.checked })
                                            }
                                            className="w-4 h-4"
                                        />
                                        <span className="text-slate-300">Habilitar recordatorios de vencimiento</span>
                                    </label>
                                    <label className="flex items-center gap-3">
                                        <input
                                            type="checkbox"
                                            checked={subscriptionSettings.auto_suspend_enabled}
                                            onChange={(e) =>
                                                setSubscriptionSettings({ ...subscriptionSettings, auto_suspend_enabled: e.target.checked })
                                            }
                                            className="w-4 h-4"
                                        />
                                        <span className="text-slate-300">Auto-suspender vencidos</span>
                                    </label>
                                </div>

                                <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700 space-y-3">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <div className="text-white font-medium">Mantenimiento de suscripciones</div>
                                            <div className="text-slate-500 text-sm">Marca overdue → envía recordatorios → auto-suspende</div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={refreshJobRuns}
                                                disabled={jobRunsLoading}
                                                className="btn-secondary px-3 py-2"
                                            >
                                                {jobRunsLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Refrescar'}
                                            </button>
                                            <button
                                                onClick={runMaintenanceNow}
                                                disabled={maintenanceRunning}
                                                className="btn-primary px-3 py-2 flex items-center gap-2"
                                            >
                                                {maintenanceRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Bell className="w-4 h-4" />}
                                                Ejecutar ahora
                                            </button>
                                        </div>
                                    </div>

                                    {jobRunsLoading ? (
                                        <div className="flex items-center justify-center py-6">
                                            <Loader2 className="w-6 h-6 animate-spin text-primary-400" />
                                        </div>
                                    ) : jobRuns.length === 0 ? (
                                        <div className="text-slate-500 text-sm">Sin ejecuciones registradas.</div>
                                    ) : (
                                        <div className="overflow-x-auto">
                                            <table className="data-table">
                                                <thead>
                                                    <tr>
                                                        <th>Run</th>
                                                        <th>Estado</th>
                                                        <th>Inicio</th>
                                                        <th>Fin</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {jobRuns.map((r) => (
                                                        <tr key={String(r.run_id)}>
                                                            <td className="font-mono text-slate-300">{String(r.run_id).slice(0, 32)}</td>
                                                            <td>
                                                                <span
                                                                    className={`badge ${String(r.status).toLowerCase() === 'success'
                                                                            ? 'badge-success'
                                                                            : String(r.status).toLowerCase() === 'failed'
                                                                                ? 'badge-danger'
                                                                                : 'badge-warning'
                                                                        }`}
                                                                >
                                                                    {String(r.status)}
                                                                </span>
                                                            </td>
                                                            <td className="text-slate-400">{String(r.started_at || '').slice(0, 19).replace('T', ' ')}</td>
                                                            <td className="text-slate-400">{String(r.finished_at || '').slice(0, 19).replace('T', ' ') || '—'}</td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
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
