'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { LifeBuoy, Loader2, Plus, RefreshCw, Send, X } from 'lucide-react';
import { Button, Input, Select, useToast } from '@/components/ui';
import { api, type SupportMessage, type SupportTicket } from '@/lib/api';

const CATEGORY_OPTIONS = [
    { value: 'general', label: 'General' },
    { value: 'bug', label: 'Bug' },
    { value: 'feature', label: 'Sugerencia' },
    { value: 'billing', label: 'Pagos' },
];

const PRIORITY_OPTIONS = [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'critical', label: 'Critical' },
];

export default function DashboardSoportePage() {
    const { toast } = useToast();
    const [loading, setLoading] = useState(true);
    const [items, setItems] = useState<SupportTicket[]>([]);
    const [total, setTotal] = useState(0);
    const [selected, setSelected] = useState<SupportTicket | null>(null);
    const [messages, setMessages] = useState<SupportMessage[]>([]);
    const [detailLoading, setDetailLoading] = useState(false);
    const [creating, setCreating] = useState(false);
    const [openCreate, setOpenCreate] = useState(false);
    const [reply, setReply] = useState('');
    const [replying, setReplying] = useState(false);
    const [attachments, setAttachments] = useState<any[]>([]);
    const fileRef = useRef<HTMLInputElement | null>(null);

    const [form, setForm] = useState({
        subject: '',
        category: 'general',
        priority: 'medium',
        message: '',
    });

    const load = async () => {
        setLoading(true);
        try {
            const res = await api.listSupportTickets({ page: 1, limit: 50 });
            if (res.ok && res.data?.ok) {
                setItems(res.data.items || []);
                setTotal(Number(res.data.total || 0));
            } else {
                setItems([]);
                setTotal(0);
            }
        } finally {
            setLoading(false);
        }
    };

    const loadTicket = async (ticketId: number) => {
        setDetailLoading(true);
        try {
            const res = await api.getSupportTicket(ticketId);
            if (res.ok && res.data?.ok) {
                setSelected(res.data.ticket);
                setMessages(res.data.messages || []);
            }
        } finally {
            setDetailLoading(false);
        }
    };

    useEffect(() => {
        load();
    }, []);

    const canCreate = useMemo(() => {
        return !!form.subject.trim() && !!form.message.trim();
    }, [form.subject, form.message]);

    const createTicket = async () => {
        if (!canCreate) return;
        setCreating(true);
        try {
            const res = await api.createSupportTicket({
                subject: form.subject.trim(),
                category: form.category,
                priority: form.priority,
                message: form.message.trim(),
                attachments,
                origin_url: typeof window !== 'undefined' ? window.location.href : undefined,
            });
            if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo crear');
            toast({ title: 'Ticket creado', description: `#${res.data.ticket_id}`, variant: 'success' });
            setOpenCreate(false);
            setForm({ subject: '', category: 'general', priority: 'medium', message: '' });
            setAttachments([]);
            await load();
            await loadTicket(res.data.ticket_id);
        } catch (e) {
            toast({ title: 'Error', description: e instanceof Error ? e.message : 'Error', variant: 'error' });
        } finally {
            setCreating(false);
        }
    };

    const sendReply = async () => {
        if (!selected) return;
        const msg = reply.trim();
        if (!msg) return;
        setReplying(true);
        try {
            const res = await api.replySupportTicket(selected.id, { message: msg, attachments: [] });
            if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo enviar');
            setReply('');
            await loadTicket(selected.id);
            await load();
        } catch (e) {
            toast({ title: 'Error', description: e instanceof Error ? e.message : 'Error', variant: 'error' });
        } finally {
            setReplying(false);
        }
    };

    const uploadSelectedFiles = async (files: FileList | null) => {
        if (!files || files.length === 0) return;
        const arr = Array.from(files).slice(0, 5);
        const out: any[] = [];
        for (const f of arr) {
            const res = await api.uploadSupportAttachment(f);
            if (res.ok && res.data?.ok) {
                out.push(res.data.attachment);
            }
        }
        setAttachments((p) => [...p, ...out].slice(0, 10));
        if (fileRef.current) fileRef.current.value = '';
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-primary-500/20 text-primary-300 flex items-center justify-center">
                    <LifeBuoy className="w-5 h-5" />
                </div>
                <div className="flex-1">
                    <h1 className="text-xl font-semibold text-white">Soporte</h1>
                    <p className="text-sm text-slate-400">Canal directo con el equipo para bugs, dudas y mejoras.</p>
                </div>
                <Button variant="secondary" onClick={load} leftIcon={<RefreshCw className="w-4 h-4" />} disabled={loading}>
                    Refrescar
                </Button>
                <Button onClick={() => setOpenCreate(true)} leftIcon={<Plus className="w-4 h-4" />}>
                    Nuevo ticket
                </Button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <div className="rounded-2xl border border-slate-800/60 bg-slate-900/40">
                    <div className="p-4 border-b border-slate-800/60 flex items-center justify-between">
                        <div className="text-sm text-slate-300">
                            Tickets <span className="text-slate-500">({total})</span>
                        </div>
                    </div>
                    {loading ? (
                        <div className="p-8 flex items-center justify-center text-slate-400">
                            <Loader2 className="w-5 h-5 animate-spin mr-2" /> Cargando…
                        </div>
                    ) : items.length === 0 ? (
                        <div className="p-6 text-sm text-slate-500">No hay tickets.</div>
                    ) : (
                        <div className="divide-y divide-slate-800/60">
                            {items.map((t) => (
                                <button
                                    key={t.id}
                                    className={`w-full text-left p-4 hover:bg-slate-900/60 transition-colors ${selected?.id === t.id ? 'bg-slate-900/70' : ''}`}
                                    onClick={() => loadTicket(t.id)}
                                >
                                    <div className="flex items-start justify-between gap-2">
                                        <div className="min-w-0">
                                            <div className="text-xs text-slate-500">#{t.id} • {t.status} • {t.priority}</div>
                                            <div className="text-sm text-white font-medium truncate">{t.subject}</div>
                                            <div className="text-xs text-slate-500 mt-1">{t.last_message_at || ''}</div>
                                        </div>
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                <div className="lg:col-span-2 rounded-2xl border border-slate-800/60 bg-slate-900/40">
                    <div className="p-4 border-b border-slate-800/60 flex items-center justify-between">
                        <div className="text-sm text-slate-300">
                            {selected ? (
                                <>
                                    Ticket <span className="text-white font-semibold">#{selected.id}</span>
                                </>
                            ) : (
                                'Seleccioná un ticket'
                            )}
                        </div>
                    </div>
                    {!selected ? (
                        <div className="p-6 text-sm text-slate-500">Abrí un ticket o seleccioná uno para ver la conversación.</div>
                    ) : detailLoading ? (
                        <div className="p-8 flex items-center justify-center text-slate-400">
                            <Loader2 className="w-5 h-5 animate-spin mr-2" /> Cargando…
                        </div>
                    ) : (
                        <div className="p-4 space-y-4">
                            <div className="text-sm text-white font-semibold">{selected.subject}</div>
                            <div className="max-h-[52vh] overflow-y-auto space-y-3">
                                {messages.map((m) => (
                                    <div
                                        key={m.id}
                                        className={`p-3 rounded-xl border ${m.sender_type === 'admin' ? 'border-primary-500/30 bg-primary-500/10' : 'border-slate-800/60 bg-slate-900/40'}`}
                                    >
                                        <div className="text-xs text-slate-500 flex items-center justify-between">
                                            <span>{m.sender_type === 'admin' ? 'Admin' : 'Vos'}</span>
                                            <span>{m.created_at}</span>
                                        </div>
                                        <div className="mt-1 text-sm text-slate-100 whitespace-pre-wrap">{m.content}</div>
                                        {Array.isArray(m.attachments) && m.attachments.length > 0 ? (
                                            <div className="mt-2 flex flex-wrap gap-2">
                                                {m.attachments.slice(0, 6).map((a: any, idx: number) => (
                                                    <a
                                                        key={idx}
                                                        className="text-xs text-primary-300 underline"
                                                        href={String(a?.url || '#')}
                                                        target="_blank"
                                                        rel="noreferrer"
                                                    >
                                                        {String(a?.filename || 'adjunto')}
                                                    </a>
                                                ))}
                                            </div>
                                        ) : null}
                                    </div>
                                ))}
                            </div>

                            <div className="flex gap-2">
                                <Input
                                    value={reply}
                                    onChange={(e) => setReply(e.target.value)}
                                    placeholder="Escribí tu respuesta…"
                                    className="flex-1"
                                />
                                <Button onClick={sendReply} disabled={!reply.trim() || replying} leftIcon={<Send className="w-4 h-4" />}>
                                    {replying ? 'Enviando…' : 'Enviar'}
                                </Button>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {openCreate ? (
                <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
                    <div className="w-full max-w-2xl rounded-2xl border border-slate-800/60 bg-slate-950 p-4">
                        <div className="flex items-center justify-between">
                            <div className="text-white font-semibold">Nuevo ticket</div>
                            <button className="p-2 rounded-lg hover:bg-slate-800/50" onClick={() => setOpenCreate(false)}>
                                <X className="w-5 h-5 text-slate-400" />
                            </button>
                        </div>
                        <div className="mt-4 space-y-3">
                            <Input
                                value={form.subject}
                                onChange={(e) => setForm((p) => ({ ...p, subject: e.target.value }))}
                                placeholder="Asunto (ej: Error al cobrar)"
                            />
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                <Select
                                    value={form.category}
                                    onChange={(e) => setForm((p) => ({ ...p, category: e.target.value }))}
                                    options={CATEGORY_OPTIONS}
                                />
                                <Select
                                    value={form.priority}
                                    onChange={(e) => setForm((p) => ({ ...p, priority: e.target.value }))}
                                    options={PRIORITY_OPTIONS}
                                />
                            </div>
                            <textarea
                                className="w-full rounded-xl border border-slate-800 bg-slate-900/60 p-3 text-sm text-slate-100 outline-none focus:border-primary-500/60"
                                rows={6}
                                value={form.message}
                                onChange={(e) => setForm((p) => ({ ...p, message: e.target.value }))}
                                placeholder="Contanos qué pasó, pasos para reproducir, etc."
                            />

                            <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-3">
                                <div className="text-xs text-slate-400">Adjuntos (opcional, máx 5 por vez)</div>
                                <div className="mt-2 flex items-center gap-2">
                                    <input ref={fileRef} type="file" accept="image/*" multiple className="hidden" onChange={(e) => uploadSelectedFiles(e.target.files)} />
                                    <Button variant="secondary" onClick={() => fileRef.current?.click()}>
                                        Agregar capturas
                                    </Button>
                                    <div className="flex-1" />
                                    <div className="text-xs text-slate-500">{attachments.length}/10</div>
                                </div>
                                {attachments.length > 0 ? (
                                    <div className="mt-2 flex flex-wrap gap-2">
                                        {attachments.map((a, idx) => (
                                            <div key={idx} className="text-xs text-slate-300 rounded-lg border border-slate-800/60 px-2 py-1">
                                                {String(a?.filename || 'adjunto')}
                                            </div>
                                        ))}
                                    </div>
                                ) : null}
                            </div>

                            <div className="flex items-center justify-end gap-2">
                                <Button variant="secondary" onClick={() => setOpenCreate(false)} disabled={creating}>
                                    Cancelar
                                </Button>
                                <Button onClick={createTicket} disabled={!canCreate || creating} leftIcon={creating ? <Loader2 className="w-4 h-4 animate-spin" /> : undefined}>
                                    Crear
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>
            ) : null}
        </div>
    );
}

