'use client';

import { useState, useEffect, use, useRef } from 'react';
import { motion } from 'framer-motion';
import {
    Loader2, ArrowLeft, MessageSquare, Wrench, Palette, CreditCard,
    Key, Activity, FileText, Save, Send, Check, X, AlertCircle, Upload, Trash2
} from 'lucide-react';
import Link from 'next/link';
import { api, type Gym, type GymDetails, type WhatsAppConfig, type Payment, type WhatsAppTemplateCatalogItem } from '@/lib/api';

type Section = 'subscription' | 'payments' | 'whatsapp' | 'maintenance' | 'branding' | 'health' | 'password';

interface BrandingConfig {
    nombre_publico: string;
    direccion: string;
    logo_url: string;
    color_primario: string;
    color_secundario: string;
    color_fondo: string;
    color_texto: string;
}

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

    // Reminder
    const [reminderMessage, setReminderMessage] = useState('');
    const [webappReminderMessage, setWebappReminderMessage] = useState('');

    // WhatsApp test
    const [waTestPhone, setWaTestPhone] = useState('');
    const [waTestMessage, setWaTestMessage] = useState('Mensaje de prueba');
    const [provisioningTemplates, setProvisioningTemplates] = useState(false);
    const [provisionTemplatesMsg, setProvisionTemplatesMsg] = useState('');
    const [waHealthLoading, setWaHealthLoading] = useState(false);
    const [waHealthMsg, setWaHealthMsg] = useState('');
    const [waActionsLoading, setWaActionsLoading] = useState(false);
    const [waActions, setWaActions] = useState<Array<{ action_key: string; enabled: boolean; template_name: string; required_params: number }>>([]);
    const [waCatalog, setWaCatalog] = useState<WhatsAppTemplateCatalogItem[]>([]);
    const [savingWaAction, setSavingWaAction] = useState<string>('');

    // Payment form
    const [paymentAmount, setPaymentAmount] = useState('');
    const [paymentPlan, setPaymentPlan] = useState('');
    const [paymentValidUntil, setPaymentValidUntil] = useState('');

    // Payments
    const [payments, setPayments] = useState<Payment[]>([]);

    // Branding
    const [branding, setBranding] = useState<BrandingConfig>({
        nombre_publico: '',
        direccion: '',
        logo_url: '',
        color_primario: '#6366f1',
        color_secundario: '#22c55e',
        color_fondo: '#0a0a0a',
        color_texto: '#ffffff',
    });
    const [uploading, setUploading] = useState(false);
    const logoInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        async function load() {
            setLoading(true);
            try {
                const res = await api.getGym(gymId);
                if (res.ok && res.data) {
                    setGym(res.data);
                    const g: any = res.data;
                    setWaConfig({
                        phone_id: g.whatsapp_phone_id || '',
                        access_token: g.whatsapp_access_token || '',
                        business_account_id: g.whatsapp_business_account_id || '',
                        verify_token: g.whatsapp_verify_token || '',
                        app_secret: g.whatsapp_app_secret || '',
                        nonblocking: Boolean(g.whatsapp_nonblocking || false),
                        send_timeout_seconds: g.whatsapp_send_timeout_seconds ? Number(g.whatsapp_send_timeout_seconds) : 25,
                    });
                    if (g.status === 'maintenance') {
                        setMaintMessage(String(g.suspended_reason || ''));
                        setMaintUntil(g.suspended_until ? String(g.suspended_until).slice(0, 16) : '');
                    }
                }
                const payRes = await api.getGymPayments(gymId);
                if (payRes.ok && payRes.data) {
                    setPayments(payRes.data.payments || []);
                }
                const reminderRes = await api.getGymReminderMessage(gymId);
                if (reminderRes.ok && reminderRes.data) {
                    setWebappReminderMessage(reminderRes.data.message || '');
                }
                // Load branding
                const brandRes = await api.getGymBranding(gymId);
                if (brandRes.ok && brandRes.data?.branding) {
                    setBranding(prev => ({
                        ...prev,
                        ...brandRes.data!.branding
                    }));
                }
                const tplRes = await api.getWhatsAppTemplateCatalog(false);
                if (tplRes.ok && tplRes.data) {
                    setWaCatalog(tplRes.data.templates || []);
                }
                setWaActionsLoading(true);
                const actRes = await api.getGymWhatsAppActions(gymId);
                if (actRes.ok && actRes.data) {
                    setWaActions(actRes.data.actions || []);
                }
            } catch {
                // Ignore
            } finally {
                setWaActionsLoading(false);
                setLoading(false);
            }
        }
        load();
    }, [gymId]);

    const refresh = async () => {
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
    };

    const handleSaveWebappReminder = async () => {
        setSaving(true);
        try {
            const res = await api.setGymReminderMessage(gymId, webappReminderMessage);
            if (res.ok) {
                showMessage('Recordatorio guardado');
            } else {
                showMessage(res.error || 'Error');
            }
        } catch {
            showMessage('Error');
        } finally {
            setSaving(false);
        }
    };

    const showMessage = (msg: string) => {
        setMessage(msg);
        setTimeout(() => setMessage(''), 3000);
    };

    const countMetaParams = (bodyText: string) => {
        const matches = String(bodyText || '').match(/\{\{(\d+)\}\}/g) || [];
        const nums = matches
            .map((m) => {
                const n = m.replace(/[^\d]/g, '');
                return Number(n);
            })
            .filter((n) => Number.isFinite(n) && n > 0);
        return nums.length ? Math.max(...nums) : 0;
    };

    const actionLabel: Record<string, string> = {
        welcome: 'Bienvenida',
        payment: 'Confirmación de pago',
        membership_due_today: 'Cuota vence hoy',
        membership_due_soon: 'Cuota vence pronto',
        overdue: 'Cuota vencida',
        deactivation: 'Desactivación',
        membership_reactivated: 'Reactivación',
        class_booking_confirmed: 'Reserva confirmada',
        class_booking_cancelled: 'Reserva cancelada',
        class_reminder: 'Recordatorio de clase',
        waitlist: 'Cupo disponible (waitlist)',
        waitlist_confirmed: 'Confirmación waitlist',
        schedule_change: 'Cambio de horario',
        marketing_promo: 'Marketing promo',
        marketing_new_class: 'Marketing nueva clase',
    };

    const saveWaAction = async (actionKey: string) => {
        const item = waActions.find((a) => a.action_key === actionKey);
        if (!item) return;
        setSavingWaAction(actionKey);
        try {
            const res = await api.setGymWhatsAppAction(gymId, actionKey, Boolean(item.enabled), String(item.template_name || ''));
            if (res.ok) {
                showMessage('Acción WhatsApp guardada');
            } else {
                showMessage(res.error || 'Error');
            }
        } finally {
            setSavingWaAction('');
        }
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

    const handleClearWhatsApp = async () => {
        if (!confirm('¿Borrar la configuración de WhatsApp de este gimnasio?')) return;
        setSaving(true);
        try {
            const res = await api.clearGymWhatsApp(gymId);
            if (res.ok) {
                setWaConfig({});
                showMessage('Configuración de WhatsApp borrada');
            } else {
                showMessage(res.error || 'Error al borrar');
            }
        } catch {
            showMessage('Error al borrar');
        } finally {
            setSaving(false);
        }
    };

    const handleSaveBranding = async () => {
        setSaving(true);
        try {
            const res = await api.saveGymBranding(gymId, branding);
            if (res.ok) {
                showMessage('Branding guardado correctamente');
            } else {
                showMessage(res.error || 'Error al guardar branding');
            }
        } catch {
            showMessage('Error al guardar branding');
        } finally {
            setSaving(false);
        }
    };

    const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setUploading(true);
        try {
            const res = await api.uploadGymLogo(gymId, file);
            if (res.ok && res.data?.url) {
                setBranding(prev => ({ ...prev, logo_url: res.data!.url }));
                showMessage('Logo subido correctamente');
            } else {
                showMessage(res.error || 'Error al subir logo');
            }
        } catch {
            showMessage('Error al subir logo');
        } finally {
            setUploading(false);
        }
    };

    const handleChangePassword = async () => {
        if (!newPassword || newPassword.length < 6) {
            showMessage('La contraseña debe tener al menos 6 caracteres');
            return;
        }
        setSaving(true);
        try {
            const res = await api.setGymOwnerPassword(gymId, newPassword);
            if (res.ok) {
                showMessage('Contraseña actualizada');
                setNewPassword('');
            } else {
                showMessage(res.error || 'Error al cambiar contraseña');
            }
        } catch {
            showMessage('Error al cambiar contraseña');
        } finally {
            setSaving(false);
        }
    };

    const handleActivateMaintenance = async () => {
        setSaving(true);
        try {
            if (maintUntil) {
                await api.sendMaintenanceNoticeUntil([gymId], maintMessage, maintUntil);
            } else {
                await api.sendMaintenanceNotice([gymId], maintMessage);
            }
            showMessage('Mantenimiento activado');
            await refresh();
        } catch {
            showMessage('Error');
        } finally {
            setSaving(false);
        }
    };

    const handleDeactivateMaintenance = async () => {
        setSaving(true);
        try {
            await api.clearMaintenance([gymId]);
            showMessage('Mantenimiento desactivado');
            setMaintMessage('');
            setMaintUntil('');
            await refresh();
        } catch {
            showMessage('Error');
        } finally {
            setSaving(false);
        }
    };

    const handleSendReminder = async () => {
        if (!reminderMessage.trim()) return;
        setSaving(true);
        try {
            const res = await api.sendReminder([gymId], reminderMessage.trim());
            if (res.ok) {
                showMessage('Recordatorio enviado');
                setReminderMessage('');
            } else {
                showMessage(res.error || 'Error');
            }
        } catch {
            showMessage('Error');
        } finally {
            setSaving(false);
        }
    };

    const handleRegisterPayment = async () => {
        if (!paymentAmount) return;
        setSaving(true);
        try {
            const res = await api.registerPayment(gymId, {
                amount: Number(paymentAmount),
                plan: paymentPlan || undefined,
                valid_until: paymentValidUntil || undefined,
            });
            if (res.ok) {
                showMessage('Pago registrado');
                setPaymentAmount('');
                setPaymentPlan('');
                setPaymentValidUntil('');
                await refresh();
            } else {
                showMessage(res.error || 'Error');
            }
        } catch {
            showMessage('Error');
        } finally {
            setSaving(false);
        }
    };

    const handleSendWhatsAppTest = async () => {
        if (!waTestPhone.trim()) return;
        setSaving(true);
        try {
            const res = await api.sendWhatsAppTest(gymId, waTestPhone.trim(), waTestMessage);
            if (res.ok && res.data?.ok) {
                showMessage(res.data.message || 'Mensaje enviado');
            } else {
                showMessage(res.data?.error || res.error || 'Error');
            }
        } catch {
            showMessage('Error');
        } finally {
            setSaving(false);
        }
    };

    const handleProvisionTemplates = async () => {
        setProvisioningTemplates(true);
        setProvisionTemplatesMsg('');
        try {
            const res = await api.provisionGymWhatsAppTemplates(gymId);
            if (res.ok && res.data) {
                const failed = (res.data.failed || []).length;
                setProvisionTemplatesMsg(`OK: created=${(res.data.created || []).length}, failed=${failed}, existing=${res.data.existing_count}`);
            } else {
                setProvisionTemplatesMsg(res.error || 'Error provisionando plantillas');
            }
        } finally {
            setProvisioningTemplates(false);
        }
    };

    const handleWhatsAppHealthCheck = async () => {
        setWaHealthLoading(true);
        setWaHealthMsg('');
        try {
            const res = await api.getGymWhatsAppHealth(gymId);
            if (res.ok && res.data) {
                const t = res.data.templates || {};
                const phone = res.data.phone || {};
                const sub = res.data.subscribed_apps || {};
                setWaHealthMsg(
                    `OK: phone=${phone.display_phone_number || '—'} quality=${phone.quality_rating || '—'} templates=${t.count || 0} approved=${t.approved || 0} pending=${t.pending || 0} subscribed=${String(sub.subscribed)}`
                );
            } else {
                setWaHealthMsg(res.error || 'Error en health-check');
            }
        } finally {
            setWaHealthLoading(false);
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
                                <input
                                    type="text"
                                    className="input flex-1"
                                    placeholder="Mensaje de recordatorio"
                                    value={reminderMessage}
                                    onChange={(e) => setReminderMessage(e.target.value)}
                                />
                                <button onClick={handleSendReminder} disabled={saving || !reminderMessage.trim()} className="btn-primary flex items-center gap-2">
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
                                <input type="number" className="input" placeholder="Monto" value={paymentAmount} onChange={(e) => setPaymentAmount(e.target.value)} />
                                <input type="text" className="input" placeholder="Plan" value={paymentPlan} onChange={(e) => setPaymentPlan(e.target.value)} />
                                <input type="date" className="input" value={paymentValidUntil} onChange={(e) => setPaymentValidUntil(e.target.value)} />
                                <button type="button" onClick={handleRegisterPayment} disabled={saving || !paymentAmount} className="btn-primary">Registrar</button>
                            </form>
                        </div>
                    </div>
                )}

                {activeSection === 'whatsapp' && (
                    <div className="space-y-6">
                        <h2 className="text-lg font-semibold text-white">Configuración de WhatsApp</h2>
                        <div className="card p-4 border border-slate-800 bg-slate-950/40 max-w-2xl">
                            <div className="text-sm text-slate-400 mb-2">Estado actual (guardado en el tenant)</div>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                                <div>
                                    <div className="text-slate-500">Phone ID</div>
                                    <div className="text-white break-all">{(gym as any)?.tenant_whatsapp_phone_id || '—'}</div>
                                </div>
                                <div>
                                    <div className="text-slate-500">WABA ID</div>
                                    <div className="text-white break-all">{(gym as any)?.tenant_whatsapp_waba_id || '—'}</div>
                                </div>
                                <div>
                                    <div className="text-slate-500">Token</div>
                                    <div className="text-white">{(gym as any)?.tenant_whatsapp_access_token_present ? 'presente' : '—'}</div>
                                </div>
                            </div>
                        </div>
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
                        <div className="flex flex-wrap gap-3">
                            <button onClick={handleSaveWhatsApp} disabled={saving} className="btn-primary flex items-center gap-2">
                                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                                Guardar
                            </button>
                            <button onClick={handleClearWhatsApp} disabled={saving} className="btn-danger flex items-center gap-2">
                                <Trash2 className="w-4 h-4" />
                                Borrar configuración
                            </button>
                            <button onClick={handleProvisionTemplates} disabled={provisioningTemplates} className="btn-secondary flex items-center gap-2">
                                {provisioningTemplates ? <Loader2 className="w-4 h-4 animate-spin" /> : <MessageSquare className="w-4 h-4" />}
                                Provisionar plantillas estándar
                            </button>
                            <button onClick={handleWhatsAppHealthCheck} disabled={waHealthLoading} className="btn-secondary flex items-center gap-2">
                                {waHealthLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Activity className="w-4 h-4" />}
                                Health check
                            </button>
                        </div>
                        {provisionTemplatesMsg ? (
                            <div className="text-sm text-slate-300">{provisionTemplatesMsg}</div>
                        ) : null}
                        {waHealthMsg ? (
                            <div className="text-sm text-slate-300">{waHealthMsg}</div>
                        ) : null}
                        <div className="pt-4 border-t border-slate-800">
                            <h3 className="font-medium text-white mb-3">Acciones y versiones (por gimnasio)</h3>
                            {waActionsLoading ? (
                                <div className="text-slate-400 flex items-center gap-2">
                                    <Loader2 className="w-4 h-4 animate-spin" /> Cargando...
                                </div>
                            ) : (
                                <div className="space-y-3 max-w-3xl">
                                    {waActions.map((a) => (
                                        <div key={a.action_key} className="flex flex-col md:flex-row md:items-center gap-2 rounded-lg border border-slate-800 bg-slate-950/40 p-3">
                                            <div className="min-w-44 text-slate-200">{actionLabel[a.action_key] || a.action_key}</div>
                                            <label className="flex items-center gap-2 text-slate-300">
                                                <input
                                                    type="checkbox"
                                                    checked={Boolean(a.enabled)}
                                                    onChange={(e) =>
                                                        setWaActions((prev) => prev.map((x) => (x.action_key === a.action_key ? { ...x, enabled: e.target.checked } : x)))
                                                    }
                                                />
                                                Habilitado
                                            </label>
                                            <select
                                                className="input flex-1"
                                                value={a.template_name || ''}
                                                onChange={(e) =>
                                                    setWaActions((prev) =>
                                                        prev.map((x) => (x.action_key === a.action_key ? { ...x, template_name: e.target.value } : x))
                                                    )
                                                }
                                            >
                                                {waCatalog
                                                    .filter((t) => Boolean(t.active))
                                                    .filter((t) => countMetaParams(String(t.body_text || '')) === Number(a.required_params || 0))
                                                    .map((t) => (
                                                        <option key={t.template_name} value={t.template_name}>
                                                            {t.template_name}
                                                        </option>
                                                    ))}
                                            </select>
                                            <button
                                                className="btn-primary"
                                                disabled={savingWaAction === a.action_key}
                                                onClick={() => saveWaAction(a.action_key)}
                                            >
                                                {savingWaAction === a.action_key ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Guardar'}
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                        <div className="pt-4 border-t border-slate-800">
                            <h3 className="font-medium text-white mb-3">Prueba de WhatsApp</h3>
                            <div className="flex gap-3">
                                <input type="text" className="input w-48" placeholder="+5493411234567" value={waTestPhone} onChange={(e) => setWaTestPhone(e.target.value)} />
                                <input type="text" className="input flex-1" value={waTestMessage} onChange={(e) => setWaTestMessage(e.target.value)} />
                                <button onClick={handleSendWhatsAppTest} disabled={saving || !waTestPhone.trim()} className="btn-secondary flex items-center gap-2">
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
                                <button onClick={handleDeactivateMaintenance} disabled={saving} className="btn-secondary">Desactivar</button>
                            </div>
                        </div>
                        <div className="pt-4 border-t border-slate-800">
                            <h3 className="font-medium text-white mb-3">Recordatorio en WebApp</h3>
                            <div className="flex gap-3">
                                <input
                                    type="text"
                                    className="input flex-1"
                                    placeholder="Mensaje de recordatorio"
                                    value={webappReminderMessage}
                                    onChange={(e) => setWebappReminderMessage(e.target.value)}
                                />
                                <button onClick={handleSaveWebappReminder} disabled={saving} className="btn-primary">Guardar recordatorio</button>
                            </div>
                        </div>
                    </div>
                )}

                {activeSection === 'branding' && (
                    <div className="space-y-6">
                        <h2 className="text-lg font-semibold text-white">Branding</h2>

                        {/* Logo Upload */}
                        <div className="flex items-start gap-6">
                            <div className="flex-shrink-0">
                                {branding.logo_url ? (
                                    <img
                                        src={branding.logo_url}
                                        alt="Logo"
                                        className="w-24 h-24 rounded-xl object-cover border border-slate-700"
                                    />
                                ) : (
                                    <div className="w-24 h-24 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-500">
                                        <Palette className="w-8 h-8" />
                                    </div>
                                )}
                            </div>
                            <div className="space-y-2">
                                <label className="label">Logo del gimnasio</label>
                                <input
                                    ref={logoInputRef}
                                    type="file"
                                    accept="image/*"
                                    onChange={handleLogoUpload}
                                    className="hidden"
                                />
                                <button
                                    onClick={() => logoInputRef.current?.click()}
                                    disabled={uploading}
                                    className="btn-secondary flex items-center gap-2"
                                >
                                    {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                                    {uploading ? 'Subiendo...' : 'Subir logo'}
                                </button>
                                <p className="text-xs text-slate-500">PNG, JPG, GIF, WebP. Máx. 5MB</p>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
                            <div>
                                <label className="label">Nombre público</label>
                                <input
                                    type="text"
                                    className="input"
                                    value={branding.nombre_publico || gym.nombre}
                                    onChange={(e) => setBranding(prev => ({ ...prev, nombre_publico: e.target.value }))}
                                />
                            </div>
                            <div>
                                <label className="label">Dirección</label>
                                <input
                                    type="text"
                                    className="input"
                                    placeholder="Calle, número, ciudad"
                                    value={branding.direccion}
                                    onChange={(e) => setBranding(prev => ({ ...prev, direccion: e.target.value }))}
                                />
                            </div>
                            <div className="md:col-span-2">
                                <label className="label">Logo URL (o sube uno arriba)</label>
                                <input
                                    type="text"
                                    className="input"
                                    placeholder="https://..."
                                    value={branding.logo_url}
                                    onChange={(e) => setBranding(prev => ({ ...prev, logo_url: e.target.value }))}
                                />
                            </div>
                            <div className="md:col-span-2">
                                <h3 className="text-sm font-medium text-slate-300 mb-2">Colores</h3>
                                <div className="grid grid-cols-4 gap-3">
                                    <div>
                                        <label className="label text-xs">Primario</label>
                                        <input
                                            type="color"
                                            className="w-full h-10 rounded border-0 cursor-pointer"
                                            value={branding.color_primario}
                                            onChange={(e) => setBranding(prev => ({ ...prev, color_primario: e.target.value }))}
                                        />
                                    </div>
                                    <div>
                                        <label className="label text-xs">Secundario</label>
                                        <input
                                            type="color"
                                            className="w-full h-10 rounded border-0 cursor-pointer"
                                            value={branding.color_secundario}
                                            onChange={(e) => setBranding(prev => ({ ...prev, color_secundario: e.target.value }))}
                                        />
                                    </div>
                                    <div>
                                        <label className="label text-xs">Fondo</label>
                                        <input
                                            type="color"
                                            className="w-full h-10 rounded border-0 cursor-pointer"
                                            value={branding.color_fondo}
                                            onChange={(e) => setBranding(prev => ({ ...prev, color_fondo: e.target.value }))}
                                        />
                                    </div>
                                    <div>
                                        <label className="label text-xs">Texto</label>
                                        <input
                                            type="color"
                                            className="w-full h-10 rounded border-0 cursor-pointer"
                                            value={branding.color_texto}
                                            onChange={(e) => setBranding(prev => ({ ...prev, color_texto: e.target.value }))}
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                        <button onClick={handleSaveBranding} disabled={saving} className="btn-primary flex items-center gap-2">
                            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
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
                        <button onClick={refresh} disabled={loading} className="btn-secondary">Actualizar estado</button>
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
