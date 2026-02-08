'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
    MessageSquare,
    Settings,
    RefreshCw,
    Trash2,
    CheckCircle2,
    XCircle,
    Clock,
    Wifi,
    WifiOff,
    RotateCw,
    User,
    Bell,
} from 'lucide-react';
import {
    Button,
    DataTable,
    Modal,
    ConfirmModal,
    useToast,
    Input,
    type Column,
} from '@/components/ui';
import { api, type WhatsAppConfig, type WhatsAppMensaje, type WhatsAppStatus, type WhatsAppTemplate, type WhatsAppTrigger } from '@/lib/api';
import { formatDate, formatTime, cn } from '@/lib/utils';

// Message type labels
const tipoLabels: Record<string, string> = {
    welcome: 'Bienvenida',
    payment: 'Pago',
    deactivation: 'Desactivación',
    overdue: 'Morosidad',
    class_reminder: 'Recordatorio Clase',
    membership_due_today: 'Vence Hoy',
    membership_due_soon: 'Vence Pronto',
    membership_reactivated: 'Reactivación',
};

// Status badges
const statusBadge = {
    pending: { icon: Clock, className: 'bg-warning-500/20 text-warning-400', label: 'Pendiente' },
    sent: { icon: CheckCircle2, className: 'bg-success-500/20 text-success-400', label: 'Enviado' },
    failed: { icon: XCircle, className: 'bg-danger-500/20 text-danger-400', label: 'Fallido' },
};

function normalizeEstado(raw: string): 'pending' | 'sent' | 'failed' {
    const s = String(raw || '').toLowerCase().trim();
    if (s === 'failed') return 'failed';
    if (s === 'sent' || s === 'delivered' || s === 'read' || s === 'received') return 'sent';
    return 'pending';
}

type FacebookSDK = {
    init: (opts: { appId: string; cookie: boolean; xfbml: boolean; version: string }) => void;
    login: (cb: (response: unknown) => void, opts: Record<string, unknown>) => void;
};

type WindowWithFacebookSDK = typeof window & {
    FB?: FacebookSDK;
    fbAsyncInit?: () => void;
};

export default function WhatsAppPage() {
    const { success, error } = useToast();

    // Status
    const [status, setStatus] = useState<WhatsAppStatus | null>(null);
    const [statusLoading, setStatusLoading] = useState(true);

    // Config
    const [config, setConfig] = useState<Partial<WhatsAppConfig>>({
        phone_number_id: '',
        whatsapp_business_account_id: '',
        access_token: '',
        access_token_present: false,
        webhook_verify_token: '',
        enabled: false,
        webhook_enabled: false,
    });
    const [configModalOpen, setConfigModalOpen] = useState(false);
    const [configSaving, setConfigSaving] = useState(false);

    const [connectLoading, setConnectLoading] = useState(false);

    // Messages
    const [mensajes, setMensajes] = useState<WhatsAppMensaje[]>([]);
    const [mensajesLoading, setMensajesLoading] = useState(false);
    const [mensajesTotals, setMensajesTotals] = useState<{ by_estado: Record<string, number>; by_tipo: Record<string, number> } | null>(null);
    const [filter, setFilter] = useState<'all' | 'pending' | 'failed' | 'sent'>('all');
    const [page, setPage] = useState(1);
    const pageSize = 25;
    const [total, setTotal] = useState(0);

    // Templates
    const [templates, setTemplates] = useState<WhatsAppTemplate[]>([]);
    const [templatesLoading, setTemplatesLoading] = useState(false);
    const [templateModalOpen, setTemplateModalOpen] = useState(false);
    const [templateSaving, setTemplateSaving] = useState(false);
    const [editingTemplateName, setEditingTemplateName] = useState<string>('');
    const [editingTemplateBody, setEditingTemplateBody] = useState<string>('');
    const [editingTemplateActive, setEditingTemplateActive] = useState<boolean>(true);

    // Triggers
    const [triggers, setTriggers] = useState<WhatsAppTrigger[]>([]);
    const [triggersLoading, setTriggersLoading] = useState(false);
    const [automationLoading, setAutomationLoading] = useState(false);
    const [automationLastResult, setAutomationLastResult] = useState<{ scanned: number; sent: number; dry_run: boolean; skipped?: Record<string, string> } | null>(null);

    // Bulk actions
    const [bulkLoading, setBulkLoading] = useState(false);
    const [confirmClearOpen, setConfirmClearOpen] = useState(false);
    const [advancedUnlocked, setAdvancedUnlocked] = useState(false);
    const [confirmUnlockOpen, setConfirmUnlockOpen] = useState(false);
    const [confirmDeleteTemplateOpen, setConfirmDeleteTemplateOpen] = useState(false);
    const [templateToDelete, setTemplateToDelete] = useState<string>('');
    const [confirmAutomationOpen, setConfirmAutomationOpen] = useState(false);
    const [confirmInitTriggersOpen, setConfirmInitTriggersOpen] = useState(false);

    // Load
    const loadStatus = useCallback(async () => {
        setStatusLoading(true);
        const res = await api.getWhatsAppStatus();
        if (res.ok && res.data) {
            setStatus(res.data);
        }
        setStatusLoading(false);
    }, []);

    const loadConfig = useCallback(async () => {
        const res = await api.getWhatsAppConfig();
        if (res.ok && res.data) {
            setConfig({
                phone_number_id: res.data.phone_number_id || '',
                whatsapp_business_account_id: res.data.whatsapp_business_account_id || '',
                access_token: '',
                access_token_present: !!res.data.access_token_present,
                webhook_verify_token: res.data.webhook_verify_token || '',
                enabled: res.data.enabled ?? false,
                webhook_enabled: res.data.webhook_enabled ?? false,
            });
        }
    }, []);

    const loadMensajes = useCallback(async () => {
        setMensajesLoading(true);
        const res = await api.getWhatsAppMensajes({
            dias: 30,
            status: filter === 'all' ? '' : filter,
            page,
            limit: pageSize,
            scope: 'branch',
        });
        if (res.ok && res.data) {
            setMensajes(res.data.mensajes || []);
            setMensajesTotals(res.data.totals || null);
            setTotal(Number(res.data.total || 0));
        }
        setMensajesLoading(false);
    }, [filter, page]);

    const loadTemplates = useCallback(async () => {
        setTemplatesLoading(true);
        const res = await api.getWhatsAppTemplates();
        if (res.ok && res.data?.templates) {
            setTemplates(res.data.templates);
        }
        setTemplatesLoading(false);
    }, []);

    const loadTriggers = useCallback(async () => {
        setTriggersLoading(true);
        const res = await api.getWhatsAppTriggers();
        if (res.ok && res.data?.triggers) {
            setTriggers(res.data.triggers);
        }
        setTriggersLoading(false);
    }, []);

    useEffect(() => {
        setPage(1);
    }, [filter]);

    useEffect(() => {
        loadStatus();
        loadConfig();
        loadMensajes();
        loadTemplates();
        loadTriggers();
    }, [loadStatus, loadConfig, loadMensajes, loadTemplates, loadTriggers]);

    // Save config
    const handleSaveConfig = async () => {
        setConfigSaving(true);
        const res = await api.updateWhatsAppConfig(config);
        setConfigSaving(false);
        if (res.ok) {
            success('Configuración guardada');
            setConfigModalOpen(false);
            loadStatus();
            loadConfig();
        } else {
            error(res.error || 'Error al guardar');
        }
    };

    const ensureFacebookSdk = async (appId: string, apiVersion: string) => {
        const w = window as WindowWithFacebookSDK;
        if (w.FB) {
            try {
                w.FB.init({ appId, cookie: true, xfbml: false, version: apiVersion });
            } catch {}
            return;
        }
        await new Promise<void>((resolve, reject) => {
            w.fbAsyncInit = function () {
                try {
                    w.FB?.init({ appId, cookie: true, xfbml: false, version: apiVersion });
                    resolve();
                } catch {
                    reject(new Error('No se pudo inicializar el SDK de Meta'));
                }
            };
            const id = 'facebook-jssdk';
            if (document.getElementById(id)) return;
            const js = document.createElement('script');
            js.id = id;
            js.src = 'https://connect.facebook.net/en_US/sdk.js';
            js.async = true;
            js.defer = true;
            js.onerror = () => reject(new Error('No se pudo cargar el SDK de Meta'));
            document.body.appendChild(js);
        });
    };

    const handleEmbeddedSignupConnect = async () => {
        setConnectLoading(true);
        setAutomationLastResult(null);
        const connectBaseRaw = (process.env.NEXT_PUBLIC_WHATSAPP_CONNECT_BASE_URL || '').trim();
        const connectBases = connectBaseRaw
            ? connectBaseRaw.split(',').map((s) => s.trim()).filter(Boolean)
            : [];
        const connectOrigins = connectBases
            .map((b) => {
                try {
                    return new URL(b).origin;
                } catch {
                    return '';
                }
            })
            .filter(Boolean);

        let listener: ((event: MessageEvent) => void) | null = null;
        try {
            if (connectBases.length > 0 && connectOrigins.length > 0) {
                const connectBase = connectBases[0].replace(/\/+$/, '');
                const connectUrl = `${connectBase}/connect/whatsapp?return_origin=${encodeURIComponent(window.location.origin)}`;
                const popup = window.open(connectUrl, 'ih-wa-connect', 'popup=yes,width=520,height=720');
                if (!popup) {
                    throw new Error('No se pudo abrir la ventana emergente. Habilitá popups.');
                }

                let done = false;
                let finishResolve: (() => void) | null = null;
                const finishPromise = new Promise<void>((resolve) => (finishResolve = resolve));

                const maybeDone = async (payload: unknown) => {
                    if (done) return;
                    done = true;
                    try {
                        const p = payload && typeof payload === 'object' ? (payload as Record<string, unknown>) : null;
                        if (p?.ok) {
                            const res = await api.completeWhatsAppEmbeddedSignup({
                                code: String(p.code || ''),
                                waba_id: String(p.waba_id || ''),
                                phone_number_id: String(p.phone_number_id || ''),
                            });
                            if (res.ok) {
                                success('WhatsApp conectado. Plantillas en proceso de creación.');
                                await loadConfig();
                                await loadStatus();
                            } else {
                                error(res.error || 'Error al completar el registro');
                            }
                        } else {
                            error(String(p?.error || 'No se pudo completar el registro'));
                        }
                    } finally {
                        finishResolve?.();
                        try {
                            popup.close();
                        } catch {}
                    }
                };

                listener = (event: MessageEvent) => {
                    try {
                        if (!connectOrigins.includes(event.origin)) return;
                        const raw = typeof event.data === 'string' ? (JSON.parse(event.data) as unknown) : (event.data as unknown);
                        if (!raw || typeof raw !== 'object') return;
                        const data = raw as Record<string, unknown>;
                        if (data.type !== 'IH_WA_CONNECT_RESULT') return;
                        void maybeDone(data.payload);
                    } catch {}
                };
                window.addEventListener('message', listener);

                await Promise.race([
                    finishPromise,
                    new Promise<void>((_resolve, reject) => setTimeout(() => reject(new Error('Tiempo de espera agotado')), 180000)),
                    new Promise<void>((_resolve, reject) => {
                        const t = setInterval(() => {
                            try {
                                if (popup.closed && !done) {
                                    clearInterval(t);
                                    reject(new Error('Ventana cerrada'));
                                }
                            } catch {}
                        }, 500);
                    }),
                ]);
                return;
            }

            const cfgRes = await api.getWhatsAppEmbeddedSignupConfig();
            if (!cfgRes.ok || !cfgRes.data?.app_id || !cfgRes.data?.config_id) {
                error(cfgRes.error || 'Falta configuración de Embedded Signup');
                setConnectLoading(false);
                return;
            }
            const embedded = cfgRes.data;

            await ensureFacebookSdk(embedded.app_id, embedded.api_version || 'v19.0');

            const w = window as WindowWithFacebookSDK;
            let code: string | null = null;
            let wabaId: string | null = null;
            let phoneNumberId: string | null = null;
            let done = false;
            let finishResolve: (() => void) | null = null;
            const finishPromise = new Promise<void>((resolve) => {
                finishResolve = resolve;
            });

            const maybeComplete = async () => {
                if (done) return;
                if (!code || !wabaId || !phoneNumberId) return;
                done = true;
                const res = await api.completeWhatsAppEmbeddedSignup({
                    code,
                    waba_id: wabaId,
                    phone_number_id: phoneNumberId,
                });
                if (res.ok) {
                    success('WhatsApp conectado. Plantillas en proceso de creación.');
                    await loadConfig();
                    await loadStatus();
                } else {
                    error(res.error || 'Error al completar el registro');
                }
                finishResolve?.();
            };

            listener = (event: MessageEvent) => {
                try {
                    if (event.origin !== 'https://www.facebook.com' && event.origin !== 'https://web.facebook.com') return;
                    const raw = typeof event.data === 'string' ? (JSON.parse(event.data) as unknown) : (event.data as unknown);
                    if (!raw || typeof raw !== 'object') return;
                    const data = raw as Record<string, unknown>;
                    if (data.type !== 'WA_EMBEDDED_SIGNUP') return;
                    if (data.event === 'FINISH') {
                        const d = data.data && typeof data.data === 'object' ? (data.data as Record<string, unknown>) : {};
                        wabaId = String(d.waba_id || '');
                        phoneNumberId = String(d.phone_number_id || '');
                        void maybeComplete();
                    }
                } catch {}
            };

            window.addEventListener('message', listener);

            await new Promise<void>((resolve) => {
                w.FB?.login(
                    (response: unknown) => {
                        try {
                            if (response && typeof response === 'object') {
                                const r = response as Record<string, unknown>;
                                const auth = r.authResponse && typeof r.authResponse === 'object'
                                    ? (r.authResponse as Record<string, unknown>)
                                    : null;
                                code = auth?.code ? String(auth.code) : null;
                            } else {
                                code = null;
                            }
                        } catch {
                            code = null;
                        }
                        void maybeComplete();
                        resolve();
                    },
                    {
                        config_id: embedded.config_id,
                        response_type: 'code',
                        override_default_response_type: true,
                        extras: { sessionInfoVersion: 2 },
                    }
                );
            });
            await Promise.race([
                finishPromise,
                new Promise<void>((_resolve, reject) => setTimeout(() => reject(new Error('Tiempo de espera agotado')), 120000)),
            ]);
        } catch (e) {
            const message = e instanceof Error ? e.message : '';
            error(message || 'Error al iniciar el registro');
        } finally {
            try {
                if (listener) window.removeEventListener('message', listener);
            } catch {}
            setConnectLoading(false);
        }
    };

    // Retry single
    const handleRetry = async (mensajeId: number) => {
        const res = await api.retryWhatsAppMessage(mensajeId);
        if (res.ok) {
            success('Reintentando envío...');
            loadMensajes();
        } else {
            error(res.error || 'Error al reintentar');
        }
    };

    // Retry all
    const handleRetryAll = async () => {
        setBulkLoading(true);
        const res = await api.retryAllWhatsAppFailed();
        setBulkLoading(false);
        if (res.ok) {
            success(`Reintentando ${res.data?.retried || 0} mensajes...`);
            loadMensajes();
        } else {
            error(res.error || 'Error al reintentar');
        }
    };

    // Clear failed
    const handleClearFailed = async () => {
        setBulkLoading(true);
        const res = await api.clearWhatsAppFailed();
        setBulkLoading(false);
        setConfirmClearOpen(false);
        if (res.ok) {
            success(`${res.data?.cleared || 0} mensajes eliminados`);
            loadMensajes();
        } else {
            error(res.error || 'Error al limpiar');
        }
    };

    const openNewTemplate = () => {
        setEditingTemplateName('');
        setEditingTemplateBody('');
        setEditingTemplateActive(true);
        setTemplateModalOpen(true);
    };

    const openEditTemplate = (t: WhatsAppTemplate) => {
        setEditingTemplateName(t.template_name);
        setEditingTemplateBody(t.body_text || '');
        setEditingTemplateActive(!!t.active);
        setTemplateModalOpen(true);
    };

    const handleSaveTemplate = async () => {
        const name = editingTemplateName.trim();
        if (!name) {
            error('Nombre de plantilla requerido');
            return;
        }
        setTemplateSaving(true);
        const res = await api.upsertWhatsAppTemplate(name, { body_text: editingTemplateBody, active: editingTemplateActive });
        setTemplateSaving(false);
        if (res.ok) {
            success('Plantilla guardada');
            setTemplateModalOpen(false);
            loadTemplates();
        } else {
            error(res.error || 'Error al guardar plantilla');
        }
    };

    const handleDeleteTemplate = async (name: string) => {
        setTemplateToDelete(String(name || '').trim());
        setConfirmDeleteTemplateOpen(true);
    };

    const handleUpdateTrigger = async (t: WhatsAppTrigger) => {
        const res = await api.updateWhatsAppTrigger(t.trigger_key, {
            enabled: !!t.enabled,
            template_name: t.template_name ?? null,
            cooldown_minutes: t.cooldown_minutes,
        });
        if (res.ok) {
            success('Trigger actualizado');
            loadTriggers();
        } else {
            error(res.error || 'Error al actualizar trigger');
        }
    };

    const handleInitDefaultTriggers = async () => {
        setConfirmInitTriggersOpen(true);
    };

    const handleRunAutomation = async (dryRun: boolean) => {
        if (!dryRun) {
            setConfirmAutomationOpen(true);
            return;
        }
        const enabledKeys = triggers.filter((t) => t.enabled).map((t) => t.trigger_key);
        const trigger_keys = enabledKeys.length ? enabledKeys : ['overdue_daily', 'due_today_daily', 'due_soon_daily'];
        setAutomationLoading(true);
        const res = await api.runWhatsAppAutomation({ dry_run: dryRun, trigger_keys });
        setAutomationLoading(false);
        if (res.ok && res.data) {
            setAutomationLastResult({ scanned: res.data.scanned, sent: res.data.sent, dry_run: res.data.dry_run, skipped: res.data.skipped });
            success(dryRun ? 'Dry-run ejecutado' : 'Automatización ejecutada');
        } else {
            error(res.error || 'Error al ejecutar automatización');
        }
    };

    // Filter messages
    const filteredMensajes = mensajes.filter(m => {
        const st = normalizeEstado(m.estado);
        if (filter === 'pending') return st === 'pending';
        if (filter === 'failed') return st === 'failed';
        if (filter === 'sent') return st === 'sent';
        return true;
    });

    // Stats
    const pendingCount = mensajesTotals?.by_estado?.pending ?? mensajes.filter((m) => normalizeEstado(m.estado) === 'pending').length;
    const failedCount = mensajesTotals?.by_estado?.failed ?? mensajes.filter((m) => normalizeEstado(m.estado) === 'failed').length;
    const sentCount = mensajesTotals?.by_estado?.sent ?? mensajes.filter((m) => normalizeEstado(m.estado) === 'sent').length;

    // Columns
    const columns: Column<WhatsAppMensaje>[] = [
        {
            key: 'usuario_nombre',
            header: 'Usuario',
            render: (row) => (
                <div className="flex items-center gap-2">
                    <User className="w-4 h-4 text-slate-500" />
                    <div>
                        <div className="font-medium text-white">{row.usuario_nombre}</div>
                        {row.telefono && <div className="text-xs text-slate-500">{row.telefono}</div>}
                    </div>
                </div>
            ),
        },
        {
            key: 'tipo',
            header: 'Tipo',
            render: (row) => (
                <span className="text-sm">{tipoLabels[row.tipo] || row.tipo}</span>
            ),
        },
        {
            key: 'estado',
            header: 'Estado',
            render: (row) => {
                const badge = statusBadge[normalizeEstado(row.estado)] || statusBadge.pending;
                const Icon = badge.icon;
                return (
                    <span className={cn('inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs', badge.className)}>
                        <Icon className="w-3 h-3" />
                        {badge.label}
                    </span>
                );
            },
        },
        {
            key: 'created_at',
            header: 'Fecha',
            render: (row) => (
                <div className="text-sm text-slate-400">
                    {row.created_at && formatDate(row.created_at)}
                </div>
            ),
        },
        {
            key: 'error_detail',
            header: 'Error',
            render: (row) => (
                <div className="text-xs text-danger-400 max-w-[200px] truncate" title={row.error_detail}>
                    {row.error_detail || '—'}
                </div>
            ),
        },
        {
            key: 'actions',
            header: '',
            width: '80px',
            align: 'right',
            render: (row) => (
                row.estado === 'failed' && (
                    <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleRetry(row.id)}
                        title="Reintentar"
                    >
                        <RotateCw className="w-4 h-4" />
                    </Button>
                )
            ),
        },
    ];

    return (
        <div className="space-y-6">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
            >
                <div>
                    <h1 className="text-2xl font-display font-bold text-white">WhatsApp</h1>
                    <p className="text-slate-400 mt-1">
                        Gestión de mensajes y configuración de la API
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        variant="ghost"
                        onClick={() => {
                            loadStatus();
                            loadMensajes();
                        }}
                        title="Refrescar"
                    >
                        <RefreshCw className="w-4 h-4" />
                    </Button>
                    <Button
                        variant="secondary"
                        leftIcon={<MessageSquare className="w-4 h-4" />}
                        onClick={handleEmbeddedSignupConnect}
                        isLoading={connectLoading}
                    >
                        Conectar con Meta
                    </Button>
                    <Button
                        variant="secondary"
                        leftIcon={<Settings className="w-4 h-4" />}
                        onClick={() => setConfigModalOpen(true)}
                    >
                        Configurar
                    </Button>
                </div>
            </motion.div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.09 }}
                className="card p-4"
            >
                <div className="flex items-start justify-between gap-4">
                    <div>
                        <div className="text-sm text-slate-400">Seguridad</div>
                        <div className="text-white font-semibold mt-1">Modo avanzado</div>
                        <div className="text-slate-400 text-sm mt-1">
                            Plantillas internas, automatizaciones y configuración manual pueden afectar envíos reales.
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        {advancedUnlocked ? (
                            <Button variant="secondary" onClick={() => setAdvancedUnlocked(false)}>
                                Desactivar
                            </Button>
                        ) : (
                            <Button variant="secondary" onClick={() => setConfirmUnlockOpen(true)}>
                                Activar
                            </Button>
                        )}
                    </div>
                </div>
                {!advancedUnlocked ? (
                    <div className="mt-3 rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-xs text-slate-400">
                        Recomendación: dejalo desactivado para evitar cambios accidentales.
                    </div>
                ) : null}
            </motion.div>

            {/* Status Cards */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="grid grid-cols-2 md:grid-cols-4 gap-4"
            >
                {/* Connection status */}
                <div className="card p-4">
                    <div className="flex items-center justify-between">
                        <div className="text-sm text-slate-400">Estado</div>
                        {statusLoading ? (
                            <div className="w-4 h-4 rounded-full bg-slate-700 animate-pulse" />
                        ) : (
                            status?.available ? (
                                <Wifi className="w-5 h-5 text-success-400" />
                            ) : (
                                <WifiOff className="w-5 h-5 text-danger-400" />
                            )
                        )}
                    </div>
                    <div className={cn(
                        'text-xl font-bold mt-2',
                        status?.available ? 'text-success-400' : 'text-danger-400'
                    )}>
                        {status?.available ? 'Conectado' : 'Desconectado'}
                    </div>
                </div>

                {/* Pending */}
                <div className="card p-4">
                    <div className="flex items-center justify-between">
                        <div className="text-sm text-slate-400">Pendientes</div>
                        <Clock className="w-5 h-5 text-warning-400" />
                    </div>
                    <div className="text-xl font-bold text-warning-400 mt-2">
                        {pendingCount}
                    </div>
                </div>

                {/* Failed */}
                <div className="card p-4">
                    <div className="flex items-center justify-between">
                        <div className="text-sm text-slate-400">Fallidos</div>
                        <XCircle className="w-5 h-5 text-danger-400" />
                    </div>
                    <div className="text-xl font-bold text-danger-400 mt-2">
                        {failedCount}
                    </div>
                </div>

                {/* Sent */}
                <div className="card p-4">
                    <div className="flex items-center justify-between">
                        <div className="text-sm text-slate-400">Enviados</div>
                        <CheckCircle2 className="w-5 h-5 text-success-400" />
                    </div>
                    <div className="text-xl font-bold text-success-400 mt-2">
                        {sentCount}
                    </div>
                </div>
            </motion.div>

            {/* Bulk Actions & Filters */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="card p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
            >
                <div className="flex items-center gap-2">
                    <span className="text-sm text-slate-400">Filtrar:</span>
                    {[
                        { value: 'all', label: 'Todos' },
                        { value: 'pending', label: 'Pendientes' },
                        { value: 'failed', label: 'Fallidos' },
                        { value: 'sent', label: 'Enviados' },
                    ].map((opt) => (
                        <button
                            key={opt.value}
                            onClick={() => setFilter(opt.value as typeof filter)}
                            className={cn(
                                'px-3 py-1 rounded-full text-sm transition-colors',
                                filter === opt.value
                                    ? 'bg-primary-500/20 text-primary-400'
                                    : 'text-slate-400 hover:text-white'
                            )}
                        >
                            {opt.label}
                        </button>
                    ))}
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        variant="secondary"
                        size="sm"
                        leftIcon={<RotateCw className="w-4 h-4" />}
                        onClick={handleRetryAll}
                        isLoading={bulkLoading}
                        disabled={failedCount === 0}
                    >
                        Reintentar Fallidos
                    </Button>
                    <Button
                        variant="danger"
                        size="sm"
                        leftIcon={<Trash2 className="w-4 h-4" />}
                        onClick={() => setConfirmClearOpen(true)}
                        disabled={failedCount === 0}
                    >
                        Limpiar Fallidos
                    </Button>
                </div>
            </motion.div>

            {/* Messages Table */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
            >
                <DataTable
                    data={filteredMensajes}
                    columns={columns}
                    loading={mensajesLoading}
                    emptyMessage="No hay mensajes en la cola"
                    pagination={{ page, pageSize, total, onPageChange: setPage }}
                />
            </motion.div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
                className="grid grid-cols-1 lg:grid-cols-2 gap-4"
            >
                <div className="card p-4">
                    <div className="flex items-center justify-between gap-3">
                        <div>
                            <div className="text-white font-semibold">Plantillas (Internas)</div>
                            <div className="text-xs text-slate-500">
                                Biblioteca interna para fallback a texto. No son plantillas de Meta.
                            </div>
                        </div>
                        <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => (advancedUnlocked ? openNewTemplate() : setConfirmUnlockOpen(true))}
                            leftIcon={<Bell className="w-4 h-4" />}
                        >
                            Nueva
                        </Button>
                    </div>
                    {!advancedUnlocked ? (
                        <div className="mt-3 rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-xs text-slate-400">
                            En modo normal es solo lectura. Editar esto puede cambiar el texto que sale si Meta rechaza/falla el envío por plantilla.
                        </div>
                    ) : null}
                    <div className="mt-4 space-y-2">
                        {templatesLoading ? (
                            <div className="text-sm text-slate-400">Cargando...</div>
                        ) : templates.length === 0 ? (
                            <div className="text-sm text-slate-400">No hay plantillas cargadas.</div>
                        ) : (
                            templates.map((t) => (
                                <div key={t.template_name} className="flex items-start justify-between gap-3 rounded-lg bg-slate-900/40 border border-slate-800 p-3">
                                    <div className="min-w-0">
                                        <div className="flex items-center gap-2">
                                            <div className="font-medium text-white truncate">{t.template_name}</div>
                                            <span className={cn('text-xs px-2 py-0.5 rounded-full', t.active ? 'bg-success-500/20 text-success-400' : 'bg-slate-700 text-slate-300')}>
                                                {t.active ? 'Activa' : 'Inactiva'}
                                            </span>
                                        </div>
                                        <div className="text-xs text-slate-500 mt-1 truncate">{t.body_text}</div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Button
                                            size="sm"
                                            variant="ghost"
                                            onClick={() => (advancedUnlocked ? openEditTemplate(t) : setConfirmUnlockOpen(true))}
                                        >
                                            Editar
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="danger"
                                            onClick={() => (advancedUnlocked ? handleDeleteTemplate(t.template_name) : setConfirmUnlockOpen(true))}
                                        >
                                            Borrar
                                        </Button>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                <div className="card p-4">
                    <div className="flex items-center justify-between gap-3">
                        <div>
                            <div className="text-white font-semibold">Automatizaciones</div>
                            <div className="text-xs text-slate-500">
                                Triggers del gimnasio. “Ejecutar” puede enviar mensajes reales.
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => (advancedUnlocked ? handleInitDefaultTriggers() : setConfirmUnlockOpen(true))}
                                disabled={triggersLoading}
                            >
                                Inicializar
                            </Button>
                            <Button size="sm" variant="secondary" onClick={() => loadTriggers()} disabled={triggersLoading}>
                                Refrescar
                            </Button>
                        </div>
                    </div>

                    <div className="mt-4 space-y-2">
                        {triggersLoading ? (
                            <div className="text-sm text-slate-400">Cargando...</div>
                        ) : triggers.length === 0 ? (
                            <div className="text-sm text-slate-400">No hay triggers configurados.</div>
                        ) : (
                            triggers.map((t) => (
                                <div key={t.trigger_key} className="rounded-lg bg-slate-900/40 border border-slate-800 p-3">
                                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                                        <div className="min-w-0">
                                            <div className="font-medium text-white">{t.trigger_key}</div>
                                            <div className="text-xs text-slate-500 mt-1">
                                                Última ejecución: {t.last_run_at ? formatDate(t.last_run_at) + ' ' + formatTime(t.last_run_at) : 'nunca'}
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <label className="flex items-center gap-2 text-sm text-slate-300">
                                                <input
                                                    type="checkbox"
                                                    checked={!!t.enabled}
                                                    onChange={(e) =>
                                                        advancedUnlocked
                                                            ? setTriggers((prev) =>
                                                                  prev.map((x) => (x.trigger_key === t.trigger_key ? { ...x, enabled: e.target.checked } : x))
                                                              )
                                                            : setConfirmUnlockOpen(true)
                                                    }
                                                />
                                                Habilitado
                                            </label>
                                            <div className="flex items-center gap-2">
                                                <span className="text-xs text-slate-500">Cooldown (min)</span>
                                                <input
                                                    className="w-20 bg-slate-950 border border-slate-800 rounded px-2 py-1 text-sm text-white"
                                                    type="number"
                                                    value={t.cooldown_minutes ?? 0}
                                                    onChange={(e) => {
                                                        const v = Number(e.target.value);
                                                        if (!advancedUnlocked) {
                                                            setConfirmUnlockOpen(true);
                                                            return;
                                                        }
                                                        setTriggers((prev) =>
                                                            prev.map((x) => (x.trigger_key === t.trigger_key ? { ...x, cooldown_minutes: Number.isFinite(v) ? v : 0 } : x))
                                                        );
                                                    }}
                                                />
                                            </div>
                                            <Button
                                                size="sm"
                                                variant="secondary"
                                                onClick={() => (advancedUnlocked ? handleUpdateTrigger(t) : setConfirmUnlockOpen(true))}
                                            >
                                                Guardar
                                            </Button>
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>

                    <div className="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-t border-slate-800 pt-4">
                        <div className="text-xs text-slate-500">
                            {automationLastResult ? `Último run: scanned=${automationLastResult.scanned}, sent=${automationLastResult.sent}, dry_run=${automationLastResult.dry_run}` : 'Sin ejecuciones recientes'}
                        </div>
                        <div className="flex items-center gap-2">
                            <Button size="sm" variant="secondary" onClick={() => handleRunAutomation(true)} isLoading={automationLoading}>
                                Dry-run
                            </Button>
                            <Button
                                size="sm"
                                onClick={() => (advancedUnlocked ? handleRunAutomation(false) : setConfirmUnlockOpen(true))}
                                isLoading={automationLoading}
                            >
                                Ejecutar
                            </Button>
                        </div>
                    </div>
                </div>
            </motion.div>

            {/* Config Modal */}
            <Modal
                isOpen={configModalOpen}
                onClose={() => setConfigModalOpen(false)}
                title="Configuración WhatsApp API"
                size="lg"
                footer={
                    <>
                        <Button variant="secondary" onClick={() => setConfigModalOpen(false)}>
                            Cancelar
                        </Button>
                        <Button onClick={handleSaveConfig} isLoading={configSaving}>
                            Guardar
                        </Button>
                    </>
                }
            >
                <div className="space-y-4">
                    <div>
                        <Input
                            label="Phone Number ID"
                            value={config.phone_number_id || ''}
                            onChange={(e) => setConfig({ ...config, phone_number_id: e.target.value })}
                            placeholder="123456789012345"
                        />
                        <p className="text-xs text-slate-500 mt-1">ID del número de WhatsApp Business</p>
                    </div>
                    <div>
                        <Input
                            label="WhatsApp Business Account ID"
                            value={config.whatsapp_business_account_id || ''}
                            onChange={(e) => setConfig({ ...config, whatsapp_business_account_id: e.target.value })}
                            placeholder="123456789012345"
                        />
                        <p className="text-xs text-slate-500 mt-1">ID de la cuenta WABA</p>
                    </div>
                    <div>
                        <Input
                            label="Access Token"
                            value={config.access_token || ''}
                            onChange={(e) => setConfig({ ...config, access_token: e.target.value })}
                            type="password"
                            placeholder="EAAxxxxxx..."
                        />
                        <p className="text-xs text-slate-500 mt-1">
                            {config.access_token_present ? 'Token ya configurado (dejar vacío para mantenerlo).' : 'Token de acceso de la API de Meta.'}
                        </p>
                    </div>
                    <div>
                        <Input
                            label="Webhook Verify Token"
                            value={config.webhook_verify_token || ''}
                            onChange={(e) => setConfig({ ...config, webhook_verify_token: e.target.value })}
                            placeholder="mi_token_secreto"
                            disabled={!advancedUnlocked}
                        />
                        <p className="text-xs text-slate-500 mt-1">
                            Solo para casos especiales. Normalmente lo maneja el sistema.
                        </p>
                    </div>
                    <div className="grid grid-cols-2 gap-4 pt-4">
                        <label className="flex items-center gap-3 p-3 rounded-lg border border-slate-700 cursor-pointer hover:bg-slate-800">
                            <input
                                type="checkbox"
                                checked={config.enabled}
                                onChange={(e) => setConfig({ ...config, enabled: e.target.checked })}
                                className="w-4 h-4"
                            />
                            <div>
                                <div className="font-medium text-white">Habilitar WhatsApp</div>
                                <div className="text-xs text-slate-500">Enviar mensajes automáticos</div>
                            </div>
                        </label>
                        <label className="flex items-center gap-3 p-3 rounded-lg border border-slate-700 cursor-pointer hover:bg-slate-800">
                            <input
                                type="checkbox"
                                checked={config.webhook_enabled}
                                onChange={(e) => setConfig({ ...config, webhook_enabled: e.target.checked })}
                                className="w-4 h-4"
                            />
                            <div>
                                <div className="font-medium text-white">Webhooks</div>
                                <div className="text-xs text-slate-500">Recibir notificaciones</div>
                            </div>
                        </label>
                    </div>
                </div>
            </Modal>

            <Modal
                isOpen={templateModalOpen}
                onClose={() => setTemplateModalOpen(false)}
                title={editingTemplateName ? `Editar plantilla: ${editingTemplateName}` : 'Nueva plantilla'}
                size="lg"
                footer={
                    <>
                        <Button variant="secondary" onClick={() => setTemplateModalOpen(false)}>
                            Cancelar
                        </Button>
                        <Button onClick={handleSaveTemplate} isLoading={templateSaving}>
                            Guardar
                        </Button>
                    </>
                }
            >
                <div className="space-y-4">
                    <Input
                        label="Nombre"
                        value={editingTemplateName}
                        onChange={(e) => setEditingTemplateName(e.target.value)}
                        placeholder="welcome"
                        disabled={templates.some((t) => t.template_name === editingTemplateName)}
                    />
                    <div>
                        <div className="text-sm text-slate-300 mb-1">Body</div>
                        <textarea
                            className="w-full min-h-[160px] bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white text-sm"
                            value={editingTemplateBody}
                            onChange={(e) => setEditingTemplateBody(e.target.value)}
                            placeholder="Texto..."
                        />
                    </div>
                    <label className="flex items-center gap-2 text-sm text-slate-300">
                        <input type="checkbox" checked={editingTemplateActive} onChange={(e) => setEditingTemplateActive(e.target.checked)} />
                        Activa
                    </label>
                </div>
            </Modal>

            {/* Confirm Clear Modal */}
            <ConfirmModal
                isOpen={confirmClearOpen}
                onClose={() => setConfirmClearOpen(false)}
                onConfirm={handleClearFailed}
                title="Limpiar Mensajes Fallidos"
                message={`¿Estás seguro de eliminar ${failedCount} mensajes fallidos? Esta acción no se puede deshacer.`}
                confirmText="Eliminar"
                variant="danger"
            />
            <ConfirmModal
                isOpen={confirmUnlockOpen}
                onClose={() => setConfirmUnlockOpen(false)}
                onConfirm={() => {
                    setAdvancedUnlocked(true);
                    setConfirmUnlockOpen(false);
                }}
                title="Habilitar modo avanzado"
                message="Esto habilita configuración manual, automatizaciones y edición/borrado. Si no estás seguro, no lo actives."
                confirmText="Habilitar"
                variant="warning"
            />
            <ConfirmModal
                isOpen={confirmDeleteTemplateOpen}
                onClose={() => setConfirmDeleteTemplateOpen(false)}
                onConfirm={async () => {
                    const name = String(templateToDelete || '').trim();
                    setConfirmDeleteTemplateOpen(false);
                    if (!name) return;
                    const res = await api.deleteWhatsAppTemplate(name);
                    if (res.ok) {
                        success('Plantilla eliminada');
                        loadTemplates();
                    } else {
                        error(res.error || 'Error al eliminar plantilla');
                    }
                }}
                title="Eliminar plantilla interna"
                message={`¿Eliminar la plantilla "${templateToDelete}"? Esto puede afectar los mensajes de fallback a texto.`}
                confirmText="Eliminar"
                variant="danger"
            />
            <ConfirmModal
                isOpen={confirmAutomationOpen}
                onClose={() => setConfirmAutomationOpen(false)}
                onConfirm={async () => {
                    setConfirmAutomationOpen(false);
                    setAutomationLoading(true);
                    const enabledKeys = triggers.filter((t) => t.enabled).map((t) => t.trigger_key);
                    const trigger_keys = enabledKeys.length ? enabledKeys : ['overdue_daily', 'due_today_daily', 'due_soon_daily'];
                    const res = await api.runWhatsAppAutomation({ dry_run: false, trigger_keys });
                    setAutomationLoading(false);
                    if (res.ok && res.data) {
                        setAutomationLastResult({ scanned: res.data.scanned, sent: res.data.sent, dry_run: res.data.dry_run, skipped: res.data.skipped });
                        success('Automatización ejecutada');
                    } else {
                        error(res.error || 'Error al ejecutar automatización');
                    }
                }}
                title="Ejecutar automatización (real)"
                message="Esto puede enviar mensajes reales a usuarios. Recomendación: ejecutá primero Dry-run y verificá el conteo."
                confirmText="Ejecutar"
                variant="warning"
                isLoading={automationLoading}
            />
            <ConfirmModal
                isOpen={confirmInitTriggersOpen}
                onClose={() => setConfirmInitTriggersOpen(false)}
                onConfirm={async () => {
                    setConfirmInitTriggersOpen(false);
                    const resAll = await Promise.all([
                        api.updateWhatsAppTrigger('overdue_daily', { enabled: false, cooldown_minutes: 1440 }),
                        api.updateWhatsAppTrigger('due_today_daily', { enabled: false, cooldown_minutes: 1440 }),
                        api.updateWhatsAppTrigger('due_soon_daily', { enabled: false, cooldown_minutes: 1440 }),
                    ]);
                    if (resAll.every((r) => r.ok)) {
                        success('Triggers inicializados');
                        loadTriggers();
                    } else {
                        error('Error al inicializar triggers');
                    }
                }}
                title="Inicializar automatizaciones"
                message="Esto ajusta los triggers del gimnasio. Si ya los configuraste, podría sobrescribir valores."
                confirmText="Inicializar"
                variant="warning"
            />
        </div>
    );
}

