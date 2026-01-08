"use client";

import { useState, useEffect, useCallback } from "react";
import { Send, RefreshCw, Trash2, MessageSquare, Clock, Check, X, AlertCircle } from "lucide-react";
import { Modal, Button, useToast, Select } from "@/components/ui";
import { cn } from "@/lib/utils";

interface WhatsAppMessage {
    id: number;
    message_id?: string;
    message_type: string;
    status: string;
    message_content?: string;
    sent_at?: string;
    created_at?: string;
}

interface WhatsAppUserHistoryProps {
    isOpen: boolean;
    onClose: () => void;
    userId: number;
    userName: string;
}

const MESSAGE_TYPES = [
    { value: "", label: "Todos los tipos" },
    { value: "welcome", label: "Bienvenida" },
    { value: "payment", label: "Confirmación de pago" },
    { value: "deactivation", label: "Desactivación" },
    { value: "overdue", label: "Recordatorio vencimiento" },
    { value: "class_reminder", label: "Recordatorio de clase" },
];

const STATUS_ICONS: Record<string, React.ReactNode> = {
    sent: <Send className="w-3 h-3 text-blue-400" />,
    delivered: <Check className="w-3 h-3 text-green-400" />,
    read: <Check className="w-3 h-3 text-green-500" />,
    failed: <X className="w-3 h-3 text-red-400" />,
};

export function WhatsAppUserHistory({ isOpen, onClose, userId, userName }: WhatsAppUserHistoryProps) {
    const [messages, setMessages] = useState<WhatsAppMessage[]>([]);
    const [loading, setLoading] = useState(false);
    const [filter, setFilter] = useState("");
    const [sendingType, setSendingType] = useState<string | null>(null);
    const { success, error } = useToast();

    const loadHistory = useCallback(async () => {
        if (!userId) return;
        setLoading(true);
        try {
            const res = await fetch(`/api/usuarios/${userId}/whatsapp/historial?limit=50`, {
                credentials: "include",
            });
            if (res.ok) {
                const data = await res.json();
                setMessages(Array.isArray(data.items) ? data.items : Array.isArray(data) ? data : []);
            }
        } catch {
            // Silent fail
        } finally {
            setLoading(false);
        }
    }, [userId]);

    useEffect(() => {
        if (isOpen) {
            loadHistory();
        }
    }, [isOpen, loadHistory]);

    const getStatusLabel = (status: string) => {
        switch (status?.toLowerCase()) {
            case "sent": return "Enviado";
            case "delivered": return "Entregado";
            case "read": return "Leído";
            case "failed": return "Fallido";
            default: return status || "—";
        }
    };

    const getTypeLabel = (type: string) => {
        const found = MESSAGE_TYPES.find(t => t.value === type);
        return found?.label || type;
    };

    const formatDate = (dateStr?: string) => {
        if (!dateStr) return "—";
        try {
            return new Date(dateStr).toLocaleDateString("es-AR", {
                day: "2-digit",
                month: "2-digit",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
            });
        } catch {
            return dateStr;
        }
    };

    const handleForceSend = async (type: string) => {
        setSendingType(type);
        try {
            let url = "";
            let body: Record<string, string> = {};

            switch (type) {
                case "welcome":
                    url = `/api/usuarios/${userId}/whatsapp/bienvenida`;
                    break;
                case "payment":
                    url = `/api/usuarios/${userId}/whatsapp/confirmacion_pago`;
                    break;
                case "deactivation":
                    url = `/api/usuarios/${userId}/whatsapp/desactivacion`;
                    body = { motivo: "cuotas vencidas" };
                    break;
                case "overdue":
                    url = `/api/usuarios/${userId}/whatsapp/recordatorio_vencida`;
                    break;
                default:
                    error("Tipo no soportado");
                    return;
            }

            const res = await fetch(url, {
                method: "POST",
                credentials: "include",
                headers: { "Content-Type": "application/json" },
                body: Object.keys(body).length ? JSON.stringify(body) : undefined,
            });

            if (res.ok) {
                success("Mensaje enviado");
                loadHistory();
            } else {
                const data = await res.json().catch(() => ({}));
                error(data.detail || "Error al enviar");
            }
        } catch {
            error("Error de conexión");
        } finally {
            setSendingType(null);
        }
    };

    const handleRetry = async (msg: WhatsAppMessage) => {
        if (msg.message_type) {
            await handleForceSend(msg.message_type);
        }
    };

    const filteredMessages = messages.filter(m => !filter || m.message_type === filter);

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={`WhatsApp - ${userName}`}
            size="lg"
        >
            <div className="space-y-4">
                {/* Quick actions */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    {["welcome", "payment", "deactivation", "overdue"].map((type) => (
                        <Button
                            key={type}
                            size="sm"
                            variant="secondary"
                            onClick={() => handleForceSend(type)}
                            isLoading={sendingType === type}
                            disabled={!!sendingType}
                            className="text-xs"
                        >
                            <Send className="w-3 h-3 mr-1" />
                            {getTypeLabel(type)}
                        </Button>
                    ))}
                </div>

                {/* Filter */}
                <div className="flex items-center gap-2">
                    <Select
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                        options={MESSAGE_TYPES}
                        className="flex-1"
                    />
                    <Button variant="ghost" size="sm" onClick={loadHistory} disabled={loading}>
                        <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
                    </Button>
                </div>

                {/* History list */}
                <div className="max-h-[400px] overflow-y-auto space-y-2">
                    {filteredMessages.length === 0 ? (
                        <div className="py-8 text-center text-slate-500">
                            <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                            No hay mensajes
                        </div>
                    ) : (
                        filteredMessages.map((msg) => (
                            <div
                                key={msg.id}
                                className={cn(
                                    "p-3 rounded-xl border",
                                    msg.status === "failed"
                                        ? "border-danger-500/30 bg-danger-500/5"
                                        : "border-slate-800 bg-slate-900/50"
                                )}
                            >
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                            {STATUS_ICONS[msg.status?.toLowerCase()] || <AlertCircle className="w-3 h-3" />}
                                            <span className="font-medium text-sm">{getTypeLabel(msg.message_type)}</span>
                                            <span className={cn(
                                                "text-xs px-1.5 py-0.5 rounded",
                                                msg.status === "failed" ? "bg-danger-500/20 text-danger-400" :
                                                    msg.status === "read" ? "bg-success-500/20 text-success-400" :
                                                        "bg-slate-800 text-slate-400"
                                            )}>
                                                {getStatusLabel(msg.status)}
                                            </span>
                                        </div>
                                        <div className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                                            <Clock className="w-3 h-3" />
                                            {formatDate(msg.sent_at || msg.created_at)}
                                        </div>
                                        {msg.message_content && (
                                            <div className="text-xs text-slate-400 mt-2 line-clamp-2">
                                                {msg.message_content}
                                            </div>
                                        )}
                                    </div>

                                    {/* Actions */}
                                    <div className="flex items-center gap-1">
                                        {msg.status === "failed" && (
                                            <Button
                                                size="sm"
                                                variant="ghost"
                                                onClick={() => handleRetry(msg)}
                                                className="text-xs"
                                            >
                                                <RefreshCw className="w-3 h-3" />
                                            </Button>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </Modal>
    );
}

export default WhatsAppUserHistory;

