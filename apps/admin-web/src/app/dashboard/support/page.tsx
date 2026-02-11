'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { LifeBuoy, Loader2, RefreshCw, Search, X, Send, Tag, AlertTriangle, User } from 'lucide-react';
import { api, type SupportTicketAdmin, type SupportTicketMessageAdmin } from '@/lib/api';

const STATUS_OPTIONS = [
    { value: '', label: 'Todos' },
    { value: 'open', label: 'Open' },
    { value: 'in_progress', label: 'In progress' },
    { value: 'waiting_client', label: 'Waiting client' },
    { value: 'resolved', label: 'Resolved' },
    { value: 'closed', label: 'Closed' },
];

const PRIORITY_OPTIONS = [
    { value: '', label: 'Todas' },
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'critical', label: 'Critical' },
];

function badgeClassByStatus(status: string) {
    const s = String(status || '').toLowerCase();
    if (s === 'open') return 'badge-danger';
    if (s === 'in_progress') return 'badge-warning';
    if (s === 'waiting_client') return 'badge-warning';
    if (s === 'resolved') return 'badge-success';
    if (s === 'closed') return 'badge-secondary';
    return 'badge-secondary';
}

function badgeClassByPriority(priority: string) {
    const p = String(priority || '').toLowerCase();
    if (p === 'critical') return 'badge-danger';
    if (p === 'high') return 'badge-warning';
    if (p === 'medium') return 'badge-secondary';
    return 'badge-secondary';
}

export default function SupportTicketsPage() {
    const [loading, setLoading] = useState(true);
    const [items, setItems] = useState<SupportTicketAdmin[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const pageSize = 30;
    const [filters, setFilters] = useState<{ status: string; priority: string; tenant: string; assignee: string; q: string }>({
        status: '',
        priority: '',
        tenant: '',
        assignee: '',
        q: '',
    });

    const [open, setOpen] = useState(false);
    const [selected, setSelected] = useState<SupportTicketAdmin | null>(null);
    const [messages, setMessages] = useState<SupportTicketMessageAdmin[]>([]);
    const [detailLoading, setDetailLoading] = useState(false);
    const [reply, setReply] = useState('');
    const [replyLoading, setReplyLoading] = useState(false);
    const [statusUpdating, setStatusUpdating] = useState(false);
    const [statusDraft, setStatusDraft] = useState('');
    const [priorityDraft, setPriorityDraft] = useState('');
    const [assigneeDraft, setAssigneeDraft] = useState('');
    const [tagsDraft, setTagsDraft] = useState('');
    const [savingMeta, setSavingMeta] = useState(false);
    const [sendingInternal, setSendingInternal] = useState(false);
    const [internalNote, setInternalNote] = useState('');

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.listSupportTickets({
                status: filters.status || undefined,
                priority: filters.priority || undefined,
                tenant: filters.tenant || undefined,
                assignee: filters.assignee || undefined,
                q: filters.q || undefined,
                page,
                page_size: pageSize,
            });
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
    }, [filters.assignee, filters.priority, filters.q, filters.status, filters.tenant, page]);

    useEffect(() => {
        load();
    }, [load]);

    const totalPages = useMemo(() => Math.max(1, Math.ceil(total / pageSize)), [pageSize, total]);

    const openTicket = async (t: SupportTicketAdmin) => {
        setSelected(t);
        setOpen(true);
        setMessages([]);
        setReply('');
        setStatusDraft(String(t.status || ''));
        setPriorityDraft(String(t.priority || ''));
        setAssigneeDraft(String(t.assigned_to || ''));
        try {
            const tagsValue: unknown = t.tags;
            if (Array.isArray(tagsValue)) setTagsDraft(tagsValue.map(String).join(', '));
            else if (typeof tagsValue === 'string') setTagsDraft(tagsValue);
            else setTagsDraft('');
        } catch {
            setTagsDraft('');
        }
        setInternalNote('');
        setDetailLoading(true);
        try {
            const res = await api.getSupportTicket(t.id);
            if (res.ok && res.data?.ok) {
                setSelected(res.data.ticket);
                setMessages(res.data.messages || []);
                setStatusDraft(String(res.data.ticket.status || ''));
                setPriorityDraft(String(res.data.ticket.priority || ''));
                setAssigneeDraft(String(res.data.ticket.assigned_to || ''));
                try {
                    const tagsValue: unknown = res.data.ticket.tags;
                    if (Array.isArray(tagsValue)) setTagsDraft(tagsValue.map(String).join(', '));
                    else if (typeof tagsValue === 'string') setTagsDraft(tagsValue);
                    else setTagsDraft('');
                } catch {
                    setTagsDraft('');
                }
            }
        } finally {
            setDetailLoading(false);
        }
    };

    const sendReply = async () => {
        if (!selected) return;
        const msg = reply.trim();
        if (!msg) return;
        setReplyLoading(true);
        try {
            const res = await api.replySupportTicket(selected.id, msg, []);
            if (res.ok) {
                setReply('');
                await openTicket({ ...selected });
                await load();
            }
        } finally {
            setReplyLoading(false);
        }
    };

    const updateStatus = async () => {
        if (!selected) return;
        const st = String(statusDraft || '').trim();
        if (!st) return;
        setStatusUpdating(true);
        try {
            const res = await api.updateSupportTicketStatus(selected.id, st);
            if (res.ok) {
                await openTicket({ ...selected });
                await load();
            }
        } finally {
            setStatusUpdating(false);
        }
    };

    const saveMeta = async () => {
        if (!selected) return;
        const pr = String(priorityDraft || '').trim();
        const assigned_to = String(assigneeDraft || '').trim();
        const tags = tagsDraft
            .split(',')
            .map((t) => t.trim())
            .filter(Boolean);
        setSavingMeta(true);
        try {
            const res = await api.patchSupportTicket(selected.id, { priority: pr || undefined, assigned_to: assigned_to || null, tags });
            if (res.ok) {
                await openTicket({ ...selected });
                await load();
            }
        } finally {
            setSavingMeta(false);
        }
    };

    const sendInternalNote = async () => {
        if (!selected) return;
        const msg = internalNote.trim();
        if (!msg) return;
        setSendingInternal(true);
        try {
            const res = await api.internalNoteSupportTicket(selected.id, msg);
            if (res.ok) {
                setInternalNote('');
                await openTicket({ ...selected });
                await load();
            }
        } finally {
            setSendingInternal(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-primary-500/20 text-primary-400 flex items-center justify-center">
                    <LifeBuoy className="w-5 h-5" />
                </div>
                <div className="flex-1">
                    <h1 className="page-title">Tickets</h1>
                    <p className="text-slate-400">Soporte centralizado por tenant.</p>
                </div>
                <button onClick={load} className="btn-secondary flex items-center gap-2">
                    <RefreshCw className="w-4 h-4" />
                    Refrescar
                </button>
            </div>

            <div className="card p-4 grid grid-cols-1 md:grid-cols-5 gap-3">
                <div>
                    <label className="text-xs text-slate-500">Status</label>
                    <select
                        className="input mt-1"
                        value={filters.status}
                        onChange={(e) => {
                            setPage(1);
                            setFilters((p) => ({ ...p, status: e.target.value }));
                        }}
                    >
                        {STATUS_OPTIONS.map((o) => (
                            <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                    </select>
                </div>
                <div>
                    <label className="text-xs text-slate-500">Priority</label>
                    <select
                        className="input mt-1"
                        value={filters.priority}
                        onChange={(e) => {
                            setPage(1);
                            setFilters((p) => ({ ...p, priority: e.target.value }));
                        }}
                    >
                        {PRIORITY_OPTIONS.map((o) => (
                            <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                    </select>
                </div>
                <div>
                    <label className="text-xs text-slate-500">Tenant</label>
                    <input
                        className="input mt-1"
                        value={filters.tenant}
                        onChange={(e) => {
                            setPage(1);
                            setFilters((p) => ({ ...p, tenant: e.target.value }));
                        }}
                        placeholder="subdominio"
                    />
                </div>
                <div>
                    <label className="text-xs text-slate-500">Assignee</label>
                    <div className="relative mt-1">
                        <User className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                            className="input pl-9"
                            value={filters.assignee}
                            onChange={(e) => {
                                setPage(1);
                                setFilters((p) => ({ ...p, assignee: e.target.value }));
                            }}
                            placeholder="owner / mail / nombre"
                        />
                    </div>
                </div>
                <div>
                    <label className="text-xs text-slate-500">Buscar</label>
                    <div className="relative mt-1">
                        <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                            className="input pl-9"
                            value={filters.q}
                            onChange={(e) => {
                                setPage(1);
                                setFilters((p) => ({ ...p, q: e.target.value }));
                            }}
                            placeholder="subject/tenant"
                        />
                    </div>
                </div>
            </div>

            <div className="card overflow-hidden">
                <div className="p-4 border-b border-slate-800/50 flex items-center justify-between">
                    <div className="text-sm text-slate-300">
                        Total: <span className="text-white font-semibold">{total}</span>
                    </div>
                    <div className="text-xs text-slate-500">
                        Página {page} / {totalPages}
                    </div>
                </div>
                {loading ? (
                    <div className="p-8 flex items-center justify-center text-slate-400">
                        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Cargando…
                    </div>
                ) : items.length === 0 ? (
                    <div className="p-8 text-center text-slate-500">Sin tickets.</div>
                ) : (
                    <div className="divide-y divide-slate-800/50">
                        {items.map((t) => (
                            <button
                                key={t.id}
                                className="w-full text-left p-4 hover:bg-slate-900/40 transition-colors"
                                onClick={() => openTicket(t)}
                            >
                                <div className="flex items-start gap-3">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2">
                                            <span className={`badge ${badgeClassByStatus(t.status)}`}>{t.status}</span>
                                            <span className={`badge ${badgeClassByPriority(t.priority)}`}>{t.priority}</span>
                                            {t.is_overdue ? (
                                                <span className="badge badge-danger flex items-center gap-1">
                                                    <AlertTriangle className="w-3 h-3" />
                                                    SLA
                                                </span>
                                            ) : null}
                                            {t.unread_by_admin ? (
                                                <span className="badge badge-danger flex items-center gap-1">
                                                    <AlertTriangle className="w-3 h-3" />
                                                    Unread
                                                </span>
                                            ) : null}
                                            <span className="text-slate-500 text-xs">#{t.id}</span>
                                        </div>
                                        <div className="mt-1 text-white font-medium">{t.subject}</div>
                                        <div className="mt-1 text-xs text-slate-500 flex items-center gap-2">
                                            <span className="inline-flex items-center gap-1"><Tag className="w-3 h-3" /> {t.tenant}</span>
                                            {t.gym_nombre ? <span>• {t.gym_nombre}</span> : null}
                                            {t.assigned_to ? <span>• {t.assigned_to}</span> : null}
                                            {t.last_message_at ? <span>• {t.last_message_at}</span> : null}
                                        </div>
                                    </div>
                                    <div className="text-xs text-slate-500">{t.category}</div>
                                </div>
                            </button>
                        ))}
                    </div>
                )}
            </div>

            <div className="flex items-center justify-between">
                <button
                    className="btn-secondary"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                    Prev
                </button>
                <button
                    className="btn-secondary"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                >
                    Next
                </button>
            </div>

            <AnimatePresence>
                {open ? (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4"
                    >
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: 20 }}
                            className="w-full max-w-3xl card p-0 overflow-hidden"
                        >
                            <div className="p-4 border-b border-slate-800/50 flex items-center justify-between">
                                <div className="min-w-0">
                                    <div className="text-sm text-slate-500">Ticket #{selected?.id}</div>
                                    <div className="text-white font-semibold truncate">{selected?.subject}</div>
                                </div>
                                <button onClick={() => setOpen(false)} className="p-2 hover:bg-slate-800/50 rounded-lg">
                                    <X className="w-5 h-5 text-slate-400" />
                                </button>
                            </div>
                            <div className="p-4 space-y-4">
                                {detailLoading ? (
                                    <div className="p-8 flex items-center justify-center text-slate-400">
                                        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Cargando…
                                    </div>
                                ) : (
                                    <>
                                        <div className="flex items-center gap-2">
                                            <select
                                                className="input"
                                                value={statusDraft}
                                                onChange={(e) => setStatusDraft(e.target.value)}
                                            >
                                                {STATUS_OPTIONS.filter((o) => o.value).map((o) => (
                                                    <option key={o.value} value={o.value}>{o.label}</option>
                                                ))}
                                            </select>
                                            <button className="btn-secondary" onClick={updateStatus} disabled={statusUpdating || !statusDraft}>
                                                {statusUpdating ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Actualizar status'}
                                            </button>
                                            <select
                                                className="input"
                                                value={priorityDraft}
                                                onChange={(e) => setPriorityDraft(e.target.value)}
                                            >
                                                {PRIORITY_OPTIONS.filter((o) => o.value).map((o) => (
                                                    <option key={o.value} value={o.value}>{o.label}</option>
                                                ))}
                                            </select>
                                            <input
                                                className="input"
                                                value={assigneeDraft}
                                                onChange={(e) => setAssigneeDraft(e.target.value)}
                                                placeholder="assignee"
                                            />
                                            <input
                                                className="input"
                                                value={tagsDraft}
                                                onChange={(e) => setTagsDraft(e.target.value)}
                                                placeholder="tags (comma)"
                                            />
                                            <button className="btn-secondary" onClick={saveMeta} disabled={savingMeta}>
                                                {savingMeta ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Guardar'}
                                            </button>
                                            <div className="flex-1" />
                                            <span className="text-xs text-slate-500">{selected?.tenant}</span>
                                        </div>

                                        <div className="max-h-[52vh] overflow-y-auto space-y-3 p-2">
                                            {messages.map((m) => (
                                                <div
                                                    key={m.id}
                                                    className={`p-3 rounded-xl border ${
                                                        m.sender_type === 'admin'
                                                            ? 'border-primary-500/30 bg-primary-500/10'
                                                            : m.sender_type === 'internal'
                                                              ? 'border-slate-700/60 bg-slate-800/20'
                                                              : 'border-slate-800/60 bg-slate-900/40'
                                                    }`}
                                                >
                                                    <div className="text-xs text-slate-500 flex items-center justify-between">
                                                        <span>{m.sender_type}</span>
                                                        <span>{m.created_at}</span>
                                                    </div>
                                                    <div className="mt-1 text-sm text-slate-100 whitespace-pre-wrap">{m.content}</div>
                                                </div>
                                            ))}
                                        </div>

                                        <div className="flex gap-2">
                                            <textarea
                                                className="input h-20 resize-none"
                                                placeholder="Nota interna (no visible para el cliente)…"
                                                value={internalNote}
                                                onChange={(e) => setInternalNote(e.target.value)}
                                            />
                                            <button
                                                className="btn-secondary flex items-center gap-2"
                                                onClick={sendInternalNote}
                                                disabled={sendingInternal || !internalNote.trim()}
                                            >
                                                {sendingInternal ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Guardar nota'}
                                            </button>
                                        </div>

                                        <div className="flex gap-2">
                                            <textarea
                                                className="input h-20 resize-none"
                                                placeholder="Responder como Admin…"
                                                value={reply}
                                                onChange={(e) => setReply(e.target.value)}
                                            />
                                            <button
                                                className="btn-primary flex items-center gap-2"
                                                onClick={sendReply}
                                                disabled={replyLoading || !reply.trim()}
                                            >
                                                {replyLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                                                Enviar
                                            </button>
                                        </div>
                                    </>
                                )}
                            </div>
                        </motion.div>
                    </motion.div>
                ) : null}
            </AnimatePresence>
        </div>
    );
}
