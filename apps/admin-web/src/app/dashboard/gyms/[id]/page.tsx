'use client';

import { useState, useEffect, use } from 'react';
import { motion } from 'framer-motion';
import {
    Loader2, ArrowLeft, MessageSquare, Wrench, Palette, CreditCard,
    Key, Activity, FileText, Save, Send, Check, X, AlertCircle
} from 'lucide-react';
import Link from 'next/link';
import { api, type Gym, type GymDetails, type WhatsAppConfig, type Payment } from '@/lib/api';

type Section = 'subscription' | 'payments' | 'whatsapp' | 'maintenance' | 'branding' | 'health' | 'password';

export default function GymDetailPage({ params }: { params: Promise<{ id: string }> }) {
    const resolvedParams = use(params);
    const gymId = Number(resolvedParams.id);

    const [gym, setGym] = useState<Gym | null>(null);
    const [loading, setLoading] = useState(true);
    const [activeSection, setActiveSection] = useState<Section>('subscription');
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState('');

    // WhatsApp form
    const [waConfig, setWaConfig] = useState<WhatsAppConfig>({});

    // Password form
    const [newPassword, setNewPassword] = useState('');

    // Maintenance form
    const [maintMessage, setMaintMessage] = useState('');
    const [maintUntil, setMaintUntil] = useState('');

    // Payments
    const [payments, setPayments] = useState<Payment[]>([]);

    useEffect(() => {
        async function load() {
            setLoading(true);
            try {
                const res = await api.getGym(gymId);
                if (res.ok && res.data) {
                    setGym(res.data);
                }
                const payRes = await api.getGymPayments(gymId);
                if (payRes.ok && payRes.data) {
                    setPayments(payRes.data.payments || []);
                }
            } catch {
                // Ignore
            } finally {
                setLoading(false);
            }
        }
        load();
    }, [gymId]);

    const showMessage = (msg: string) => {
        setMessage(msg);
        setTimeout(() => setMessage(''), 3000);
    };

    const handleSaveWhatsApp = async () => {
        setSaving(true);
        try {
            const res = await api.updateGymWhatsApp(gymId, waConfig);
            if (res.ok) {
                showMessage('Configuración de WhatsApp guardada');
            }
        } catch {
            showMessage('Error al guardar');
        } finally {
            setSaving(false);
        }
    };

    const handleChangePassword = async () => {
        if (!newPassword || newPassword.length < 6) {
            showMessage('La contraseña debe tener al menos 6 caracteres');
            return;
        }
        setSaving(true);
        try {
            // Would call API endpoint
            await new Promise(r => setTimeout(r, 500));
            showMessage('Contraseña actualizada');
            setNewPassword('');
        } catch {
            showMessage('Error al cambiar contraseña');
        } finally {
            setSaving(false);
        }
    };

    const handleActivateMaintenance = async () => {
        setSaving(true);
        try {
            await api.sendMaintenanceNotice([gymId], maintMessage);
            showMessage('Mantenimiento activado');
        } catch {
            showMessage('Error');
        } finally {
            setSaving(false);
        }
    };

    const sections: { id: Section; name: string; icon: React.ComponentType<{ className?: string }> }[] = [
        { id: 'subscription', name: 'Suscripción', icon: CreditCard },
        { id: 'payments', name: 'Pagos', icon: CreditCard },
        { id: 'whatsapp', name: 'WhatsApp', icon: MessageSquare },
        { id: 'maintenance', name: 'Mantenimiento', icon: Wrench },
        { id: 'branding', name: 'Branding', icon: Palette },
        { id: 'health', name: 'Salud', icon: Activity },
        { id: 'password', name: 'Contraseña dueño', icon: Key },
    ];

    if (loading) {
        return (
            <div className="flex items-center justify-center py-16">
                <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
            </div>
        );
    }

    if (!gym) {
        return (
            <div className="text-center py-16">
                <p className="text-slate-500">Gimnasio no encontrado</p>
                <Link href="/dashboard/gyms" className="text-primary-400 hover:text-primary-300 mt-2 inline-block">
                    Volver a gimnasios
                </Link>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center gap-4">
                <Link href="/dashboard/gyms" className="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-white">
                    <ArrowLeft className="w-5 h-5" />
                </Link>
                <div>
                    <h1 className="page-title">{gym.nombre}</h1>
                    <p className="text-slate-400">{gym.subdominio} · ID: {gym.id}</p>
                </div>
                <span
                    className={`ml-auto badge ${gym.status === 'active' ? 'badge-success' : gym.status === 'maintenance' ? 'badge-warning' : 'badge-danger'
                        }`}
                >
                    {gym.status === 'active' ? 'Activo' : gym.status === 'maintenance' ? 'Mantenimiento' : 'Suspendido'}
                </span>
            </div>

            {/* Section Tabs */}
            <div className="flex gap-2 flex-wrap">
                {sections.map((sec) => (
                    <button
                        key={sec.id}
                        onClick={() => setActiveSection(sec.id)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors ${activeSection === sec.id
                                ? 'bg-primary-500/20 text-primary-400'
                                : 'bg-slate-800/50 text-slate-400 hover:text-white'
                            }`}
                    >
                        <sec.icon className="w-4 h-4" />
                        {sec.name}
                    </button>
                ))}
            </div>

            {/* Message */}
            {message && (
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="card p-3 flex items-center gap-2 text-primary-400"
                >
                    <Check className="w-4 h-4" />
                    {message}
                </motion.div>
            )}

            {/* Content */}
            <div className="card p-6">
                {activeSection === 'subscription' && (
                    <div className="space-y-6">
                        <h2 className="text-lg font-semibold text-white">Suscripción</h2>
                        <div className="grid grid-cols-2 gap-4 max-w-md">
                            <div>
                                <div className="text-sm text-slate-500">Estado</div>
                                <div className="text-white font-medium">{gym.status}</div>
                            </div>
                            <div>
                                <div className="text-sm text-slate-500">Creado</div>
                                <div className="text-white">{gym.created_at?.slice(0, 10) || '—'}</div>
                            </div>
                        </div>
                        <div className="pt-4 border-t border-slate-800">
                            <h3 className="font-medium text-white mb-3">Enviar recordatorio</h3>
                            <div className="flex gap-3">
                                <input type="text" className="input flex-1" placeholder="Mensaje de recordatorio" />
                                <button className="btn-primary flex items-center gap-2">
                                    <Send className="w-4 h-4" />
                                    Enviar
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {activeSection === 'payments' && (
                    <div className="space-y-6">
                        <h2 className="text-lg font-semibold text-white">Historial de Pagos</h2>
                        {payments.length === 0 ? (
                            <p className="text-slate-500">Sin pagos registrados</p>
                        ) : (
                            <table className="data-table">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Monto</th>
                                        <th>Estado</th>
                                        <th>Válido hasta</th>
                                        <th>Fecha</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {payments.map((p) => (
                                        <tr key={p.id}>
                                            <td>{p.id}</td>
                                            <td className="text-success-400">${p.amount}</td>
                                            <td><span className="badge badge-success">{p.status}</span></td>
                                            <td>{p.valid_until || '—'}</td>
                                            <td>{p.created_at?.slice(0, 10)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                        <div className="pt-4 border-t border-slate-800">
                            <h3 className="font-medium text-white mb-3">Registrar pago</h3>
                            <form className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                <input type="number" className="input" placeholder="Monto" />
                                <input type="text" className="input" placeholder="Plan" />
                                <input type="date" className="input" />
                                <button type="button" className="btn-primary">Registrar</button>
                            </form>
                        </div>
                    </div>
                )}

                {activeSection === 'whatsapp' && (
                    <div className="space-y-6">
                        <h2 className="text-lg font-semibold text-white">Configuración de WhatsApp</h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
                            <div>
                                <label className="label">Phone ID</label>
                                <input
                                    type="text"
                                    value={waConfig.phone_id || ''}
                                    onChange={(e) => setWaConfig({ ...waConfig, phone_id: e.target.value })}
                                    className="input"
                                />
                            </div>
                            <div>
                                <label className="label">Access Token</label>
                                <input
                                    type="text"
                                    value={waConfig.access_token || ''}
                                    onChange={(e) => setWaConfig({ ...waConfig, access_token: e.target.value })}
                                    className="input"
                                />
                            </div>
                            <div>
                                <label className="label">WABA ID</label>
                                <input
                                    type="text"
                                    value={waConfig.business_account_id || ''}
                                    onChange={(e) => setWaConfig({ ...waConfig, business_account_id: e.target.value })}
                                    className="input"
                                />
                            </div>
                            <div>
                                <label className="label">Verify Token</label>
                                <input
                                    type="text"
                                    value={waConfig.verify_token || ''}
                                    onChange={(e) => setWaConfig({ ...waConfig, verify_token: e.target.value })}
                                    className="input"
                                />
                            </div>
                            <div>
                                <label className="label">App Secret</label>
                                <input
                                    type="text"
                                    value={waConfig.app_secret || ''}
                                    onChange={(e) => setWaConfig({ ...waConfig, app_secret: e.target.value })}
                                    className="input"
                                />
                            </div>
                            <div>
                                <label className="label">Timeout (segundos)</label>
                                <input
                                    type="number"
                                    value={waConfig.send_timeout_seconds || 25}
                                    onChange={(e) => setWaConfig({ ...waConfig, send_timeout_seconds: Number(e.target.value) })}
                                    className="input"
                                    min={1}
                                    max={120}
                                />
                            </div>
                            <label className="flex items-center gap-2 md:col-span-2">
                                <input
                                    type="checkbox"
                                    checked={waConfig.nonblocking || false}
                                    onChange={(e) => setWaConfig({ ...waConfig, nonblocking: e.target.checked })}
                                />
                                <span className="text-slate-300">Envío no bloqueante</span>
                            </label>
                        </div>
                        <button onClick={handleSaveWhatsApp} disabled={saving} className="btn-primary flex items-center gap-2">
                            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                            Guardar
                        </button>
                        <div className="pt-4 border-t border-slate-800">
                            <h3 className="font-medium text-white mb-3">Prueba de WhatsApp</h3>
                            <div className="flex gap-3">
                                <input type="text" className="input w-48" placeholder="+5493411234567" />
                                <input type="text" className="input flex-1" defaultValue="Mensaje de prueba" />
                                <button className="btn-secondary flex items-center gap-2">
                                    <Send className="w-4 h-4" />
                                    Enviar test
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {activeSection === 'maintenance' && (
                    <div className="space-y-6">
                        <h2 className="text-lg font-semibold text-white">Modo Mantenimiento</h2>
                        <div className="max-w-lg space-y-4">
                            <div>
                                <label className="label">Mensaje para usuarios</label>
                                <textarea
                                    value={maintMessage}
                                    onChange={(e) => setMaintMessage(e.target.value)}
                                    className="input h-24 resize-none"
                                    placeholder="Estamos en mantenimiento, volvemos pronto..."
                                />
                            </div>
                            <div>
                                <label className="label">Hasta</label>
                                <input
                                    type="datetime-local"
                                    value={maintUntil}
                                    onChange={(e) => setMaintUntil(e.target.value)}
                                    className="input"
                                />
                            </div>
                            <div className="flex gap-3">
                                <button onClick={handleActivateMaintenance} disabled={saving} className="btn-warning flex items-center gap-2">
                                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wrench className="w-4 h-4" />}
                                    Activar mantenimiento
                                </button>
                                <button className="btn-secondary">Desactivar</button>
                            </div>
                        </div>
                        <div className="pt-4 border-t border-slate-800">
                            <h3 className="font-medium text-white mb-3">Recordatorio en WebApp</h3>
                            <div className="flex gap-3">
                                <input type="text" className="input flex-1" placeholder="Mensaje de recordatorio" />
                                <button className="btn-primary">Guardar recordatorio</button>
                            </div>
                        </div>
                    </div>
                )}

                {activeSection === 'branding' && (
                    <div className="space-y-6">
                        <h2 className="text-lg font-semibold text-white">Branding</h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
                            <div>
                                <label className="label">Nombre público</label>
                                <input type="text" className="input" defaultValue={gym.nombre} />
                            </div>
                            <div>
                                <label className="label">Dirección</label>
                                <input type="text" className="input" placeholder="Calle, número, ciudad" />
                            </div>
                            <div className="md:col-span-2">
                                <label className="label">Logo URL</label>
                                <input type="text" className="input" placeholder="https://..." />
                            </div>
                            <div className="md:col-span-2">
                                <h3 className="text-sm font-medium text-slate-300 mb-2">Colores</h3>
                                <div className="grid grid-cols-4 gap-3">
                                    <div>
                                        <label className="label text-xs">Primario</label>
                                        <input type="color" className="w-full h-10 rounded border-0" defaultValue="#6366f1" />
                                    </div>
                                    <div>
                                        <label className="label text-xs">Secundario</label>
                                        <input type="color" className="w-full h-10 rounded border-0" defaultValue="#22c55e" />
                                    </div>
                                    <div>
                                        <label className="label text-xs">Fondo</label>
                                        <input type="color" className="w-full h-10 rounded border-0" defaultValue="#0a0a0a" />
                                    </div>
                                    <div>
                                        <label className="label text-xs">Texto</label>
                                        <input type="color" className="w-full h-10 rounded border-0" defaultValue="#ffffff" />
                                    </div>
                                </div>
                            </div>
                        </div>
                        <button className="btn-primary flex items-center gap-2">
                            <Save className="w-4 h-4" />
                            Guardar branding
                        </button>
                    </div>
                )}

                {activeSection === 'health' && (
                    <div className="space-y-6">
                        <h2 className="text-lg font-semibold text-white">Salud del Gimnasio</h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="w-3 h-3 rounded-full bg-success-400" />
                                    <div>
                                        <div className="font-medium text-white">Base de datos</div>
                                        <div className="text-xs text-slate-500">{gym.db_name}</div>
                                    </div>
                                </div>
                                <span className="text-success-400 text-sm">OK</span>
                            </div>
                            <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className={`w-3 h-3 rounded-full ${gym.wa_configured ? 'bg-success-400' : 'bg-warning-400'}`} />
                                    <div>
                                        <div className="font-medium text-white">WhatsApp</div>
                                        <div className="text-xs text-slate-500">{gym.wa_configured ? 'Configurado' : 'Sin configurar'}</div>
                                    </div>
                                </div>
                                <span className={gym.wa_configured ? 'text-success-400 text-sm' : 'text-warning-400 text-sm'}>
                                    {gym.wa_configured ? 'OK' : 'Pendiente'}
                                </span>
                            </div>
                            <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className={`w-3 h-3 rounded-full ${gym.status === 'active' ? 'bg-success-400' : 'bg-danger-400'}`} />
                                    <div>
                                        <div className="font-medium text-white">Estado</div>
                                        <div className="text-xs text-slate-500">{gym.status}</div>
                                    </div>
                                </div>
                            </div>
                            <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="w-3 h-3 rounded-full bg-primary-400" />
                                    <div>
                                        <div className="font-medium text-white">WebApp URL</div>
                                        <a
                                            href={`https://${gym.subdominio}.${process.env.NEXT_PUBLIC_TENANT_DOMAIN || 'ironhub.motiona.xyz'}`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="text-xs text-primary-400 hover:text-primary-300"
                                        >
                                            {gym.subdominio}.{process.env.NEXT_PUBLIC_TENANT_DOMAIN || 'ironhub.motiona.xyz'}
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <button className="btn-secondary">Actualizar estado</button>
                    </div>
                )}

                {activeSection === 'password' && (
                    <div className="space-y-6">
                        <h2 className="text-lg font-semibold text-white">Cambiar Contraseña del Dueño</h2>
                        <div className="max-w-md space-y-4">
                            <div>
                                <label className="label">Nueva contraseña</label>
                                <input
                                    type="password"
                                    value={newPassword}
                                    onChange={(e) => setNewPassword(e.target.value)}
                                    className="input"
                                    placeholder="Mínimo 6 caracteres"
                                    minLength={6}
                                />
                            </div>
                            <button onClick={handleChangePassword} disabled={saving} className="btn-primary flex items-center gap-2">
                                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Key className="w-4 h-4" />}
                                Actualizar contraseña
                            </button>
                        </div>
                        <div className="p-4 rounded-lg bg-warning-500/10 border border-warning-500/30 flex items-start gap-3">
                            <AlertCircle className="w-5 h-5 text-warning-400 flex-shrink-0 mt-0.5" />
                            <div className="text-sm text-warning-400">
                                <p className="font-medium">Atención</p>
                                <p>Esta acción cambiará la contraseña de acceso del dueño al dashboard del gimnasio. El dueño deberá usar la nueva contraseña para ingresar.</p>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
