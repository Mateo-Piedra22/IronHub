'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
    MessageSquare,
    Settings,
    RefreshCw,
    Trash2,
    Send,
    CheckCircle2,
    XCircle,
    Clock,
    AlertTriangle,
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
import { api, type WhatsAppConfig, type WhatsAppMensaje, type WhatsAppStatus } from '@/lib/api';
import { formatDate, formatTime, cn } from '@/lib/utils';

// Message type labels
const tipoLabels: Record<string, string> = {
    welcome: 'Bienvenida',
    payment: 'Pago',
    deactivation: 'Desactivación',
    overdue: 'Morosidad',
    class_reminder: 'Recordatorio Clase',
};

// Status badges
const statusBadge = {
    pending: { icon: Clock, className: 'bg-warning-500/20 text-warning-400', label: 'Pendiente' },
    sent: { icon: CheckCircle2, className: 'bg-success-500/20 text-success-400', label: 'Enviado' },
    failed: { icon: XCircle, className: 'bg-danger-500/20 text-danger-400', label: 'Fallido' },
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
        webhook_verify_token: '',
        enabled: false,
        webhook_enabled: false,
    });
    const [configModalOpen, setConfigModalOpen] = useState(false);
    const [configSaving, setConfigSaving] = useState(false);

    // Messages
    const [mensajes, setMensajes] = useState<WhatsAppMensaje[]>([]);
    const [mensajesLoading, setMensajesLoading] = useState(false);
    const [filter, setFilter] = useState<'all' | 'pending' | 'failed'>('all');

    // Bulk actions
    const [bulkLoading, setBulkLoading] = useState(false);
    const [confirmClearOpen, setConfirmClearOpen] = useState(false);

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
                access_token: res.data.access_token || '',
                webhook_verify_token: res.data.webhook_verify_token || '',
                enabled: res.data.enabled ?? false,
                webhook_enabled: res.data.webhook_enabled ?? false,
            });
        }
    }, []);

    const loadMensajes = useCallback(async () => {
        setMensajesLoading(true);
        const res = await api.getWhatsAppMensajesPendientes();
        if (res.ok && res.data) {
            setMensajes(res.data.mensajes);
        }
        setMensajesLoading(false);
    }, []);

    useEffect(() => {
        loadStatus();
        loadConfig();
        loadMensajes();
    }, [loadStatus, loadConfig, loadMensajes]);

    // Save config
    const handleSaveConfig = async () => {
        setConfigSaving(true);
        const res = await api.updateWhatsAppConfig(config);
        setConfigSaving(false);
        if (res.ok) {
            success('Configuración guardada');
            setConfigModalOpen(false);
            loadStatus();
        } else {
            error(res.error || 'Error al guardar');
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

    // Filter messages
    const filteredMensajes = mensajes.filter(m => {
        if (filter === 'pending') return m.estado === 'pending';
        if (filter === 'failed') return m.estado === 'failed';
        return true;
    });

    // Stats
    const pendingCount = mensajes.filter(m => m.estado === 'pending').length;
    const failedCount = mensajes.filter(m => m.estado === 'failed').length;
    const sentCount = mensajes.filter(m => m.estado === 'sent').length;

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
                const badge = statusBadge[row.estado];
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
                        leftIcon={<Settings className="w-4 h-4" />}
                        onClick={() => setConfigModalOpen(true)}
                    >
                        Configurar
                    </Button>
                </div>
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
                />
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
                        <p className="text-xs text-slate-500 mt-1">Token de acceso de la API de Meta</p>
                    </div>
                    <div>
                        <Input
                            label="Webhook Verify Token"
                            value={config.webhook_verify_token || ''}
                            onChange={(e) => setConfig({ ...config, webhook_verify_token: e.target.value })}
                            placeholder="mi_token_secreto"
                        />
                        <p className="text-xs text-slate-500 mt-1">Token para verificar webhooks entrantes</p>
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
        </div>
    );
}

