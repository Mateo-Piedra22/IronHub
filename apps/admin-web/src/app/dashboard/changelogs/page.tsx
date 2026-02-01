'use client';

import { useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Megaphone, Loader2, Plus, X, Save, Trash2, RefreshCw } from 'lucide-react';
import { api, type ChangelogAdminItem } from '@/lib/api';

const TYPE_OPTIONS = [
    { value: 'new', label: 'NEW' },
    { value: 'improvement', label: 'IMPROVEMENT' },
    { value: 'fix', label: 'FIX' },
    { value: 'announcement', label: 'ANNOUNCEMENT' },
];

function badgeByType(t: string) {
    const v = String(t || '').toLowerCase();
    if (v === 'new') return 'badge-success';
    if (v === 'fix') return 'badge-danger';
    if (v === 'announcement') return 'badge-warning';
    return 'badge-secondary';
}

export default function AdminChangelogsPage() {
    const [loading, setLoading] = useState(true);
    const [items, setItems] = useState<ChangelogAdminItem[]>([]);
    const [page, setPage] = useState(1);
    const pageSize = 30;
    const [total, setTotal] = useState(0);
    const [includeDrafts, setIncludeDrafts] = useState(true);

    const [open, setOpen] = useState(false);
    const [editing, setEditing] = useState<ChangelogAdminItem | null>(null);
    const [saving, setSaving] = useState(false);
    const [deleting, setDeleting] = useState(false);
    const [pinned, setPinned] = useState(false);
    const [minAppVersion, setMinAppVersion] = useState('');
    const [rolesText, setRolesText] = useState('');
    const [modulesText, setModulesText] = useState('');
    const [tenantsIncludeText, setTenantsIncludeText] = useState('');
    const [tenantsExcludeText, setTenantsExcludeText] = useState('');

    const [form, setForm] = useState<Omit<ChangelogAdminItem, 'id'>>({
        version: 'v',
        title: '',
        body_markdown: '',
        change_type: 'improvement',
        image_url: '',
        is_published: false,
        published_at: null,
        pinned: false,
        min_app_version: null,
        audience_roles: [],
        audience_tenants: {},
        audience_modules: [],
        created_at: undefined,
        updated_at: undefined,
    });

    const load = async () => {
        setLoading(true);
        try {
            const res = await api.listChangelogs({ include_drafts: includeDrafts, page, page_size: pageSize });
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

    useEffect(() => {
        load();
    }, [includeDrafts, page]);

    const totalPages = useMemo(() => Math.max(1, Math.ceil(total / pageSize)), [total]);

    const openCreate = () => {
        setEditing(null);
        setPinned(false);
        setMinAppVersion('');
        setRolesText('');
        setModulesText('');
        setTenantsIncludeText('');
        setTenantsExcludeText('');
        setForm({
            version: 'v',
            title: '',
            body_markdown: '',
            change_type: 'improvement',
            image_url: '',
            is_published: false,
            published_at: null,
            pinned: false,
            min_app_version: null,
            audience_roles: [],
            audience_tenants: {},
            audience_modules: [],
            created_at: undefined,
            updated_at: undefined,
        });
        setOpen(true);
    };

    const openEdit = (it: ChangelogAdminItem) => {
        setEditing(it);
        setPinned(!!it.pinned);
        setMinAppVersion(String(it.min_app_version || ''));
        try {
            const rr = (it.audience_roles as any) || [];
            setRolesText(Array.isArray(rr) ? rr.join(', ') : String(rr || ''));
        } catch {
            setRolesText('');
        }
        try {
            const mm = (it.audience_modules as any) || [];
            setModulesText(Array.isArray(mm) ? mm.join(', ') : String(mm || ''));
        } catch {
            setModulesText('');
        }
        try {
            const tt = (it.audience_tenants as any) || {};
            const inc = Array.isArray(tt?.include) ? tt.include : [];
            const exc = Array.isArray(tt?.exclude) ? tt.exclude : [];
            setTenantsIncludeText(inc.join(', '));
            setTenantsExcludeText(exc.join(', '));
        } catch {
            setTenantsIncludeText('');
            setTenantsExcludeText('');
        }
        setForm({
            version: it.version,
            title: it.title,
            body_markdown: it.body_markdown,
            change_type: it.change_type,
            image_url: it.image_url || '',
            is_published: !!it.is_published,
            published_at: it.published_at || null,
            pinned: !!it.pinned,
            min_app_version: it.min_app_version || null,
            audience_roles: it.audience_roles || [],
            audience_tenants: it.audience_tenants || {},
            audience_modules: it.audience_modules || [],
            created_at: it.created_at,
            updated_at: it.updated_at,
        });
        setOpen(true);
    };

    const save = async () => {
        const payload = {
            version: String(form.version || '').trim(),
            title: String(form.title || '').trim(),
            body_markdown: String(form.body_markdown || '').trim(),
            change_type: String(form.change_type || 'improvement').trim(),
            image_url: String(form.image_url || '').trim() || null,
            is_published: !!form.is_published,
            pinned: !!pinned,
            min_app_version: String(minAppVersion || '').trim() || null,
            audience_roles: rolesText.split(',').map((x) => x.trim()).filter(Boolean),
            audience_modules: modulesText.split(',').map((x) => x.trim()).filter(Boolean),
            audience_tenants: {
                include: tenantsIncludeText.split(',').map((x) => x.trim().toLowerCase()).filter(Boolean),
                exclude: tenantsExcludeText.split(',').map((x) => x.trim().toLowerCase()).filter(Boolean),
            },
            published_at: null,
            created_at: undefined,
            updated_at: undefined,
        } as any;
        if (!payload.version || !payload.title || !payload.body_markdown) return;
        setSaving(true);
        try {
            if (editing) {
                const res = await api.updateChangelog(editing.id, payload);
                if (res.ok) {
                    setOpen(false);
                    await load();
                }
            } else {
                const res = await api.createChangelog(payload);
                if (res.ok) {
                    setOpen(false);
                    await load();
                }
            }
        } finally {
            setSaving(false);
        }
    };

    const del = async () => {
        if (!editing) return;
        setDeleting(true);
        try {
            const res = await api.deleteChangelog(editing.id);
            if (res.ok) {
                setOpen(false);
                await load();
            }
        } finally {
            setDeleting(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-primary-500/20 text-primary-400 flex items-center justify-center">
                    <Megaphone className="w-5 h-5" />
                </div>
                <div className="flex-1">
                    <h1 className="page-title">Changelogs</h1>
                    <p className="text-slate-400">Entradas curadas para mostrar novedades en la WebApp.</p>
                </div>
                <button onClick={load} className="btn-secondary flex items-center gap-2">
                    <RefreshCw className="w-4 h-4" />
                    Refrescar
                </button>
                <button onClick={openCreate} className="btn-primary flex items-center gap-2">
                    <Plus className="w-4 h-4" />
                    Nuevo
                </button>
            </div>

            <div className="card p-4 flex items-center gap-3">
                <label className="flex items-center gap-2 text-sm text-slate-200">
                    <input
                        type="checkbox"
                        checked={includeDrafts}
                        onChange={(e) => {
                            setPage(1);
                            setIncludeDrafts(e.target.checked);
                        }}
                    />
                    Incluir borradores
                </label>
                <div className="flex-1" />
                <div className="text-xs text-slate-500">
                    Total: <span className="text-white font-semibold">{total}</span> • Página {page}/{totalPages}
                </div>
            </div>

            <div className="card overflow-hidden">
                {loading ? (
                    <div className="p-8 flex items-center justify-center text-slate-400">
                        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Cargando…
                    </div>
                ) : items.length === 0 ? (
                    <div className="p-8 text-center text-slate-500">Sin entradas.</div>
                ) : (
                    <div className="divide-y divide-slate-800/50">
                        {items.map((it) => (
                            <button
                                key={it.id}
                                className="w-full text-left p-4 hover:bg-slate-900/40 transition-colors"
                                onClick={() => openEdit(it)}
                            >
                                <div className="flex items-start gap-3">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2">
                                            <span className={`badge ${badgeByType(it.change_type)}`}>{it.change_type}</span>
                                            {it.pinned ? <span className="badge badge-warning">pinned</span> : null}
                                            {it.is_published ? (
                                                <span className="badge badge-success">published</span>
                                            ) : (
                                                <span className="badge badge-secondary">draft</span>
                                            )}
                                            <span className="text-slate-500 text-xs">#{it.id}</span>
                                        </div>
                                        <div className="mt-1 text-white font-medium">{it.title}</div>
                                        <div className="mt-1 text-xs text-slate-500">
                                            {it.version} {it.published_at ? `• ${it.published_at}` : ''}
                                        </div>
                                    </div>
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
                                <div className="text-white font-semibold">{editing ? `Editar #${editing.id}` : 'Nuevo changelog'}</div>
                                <button onClick={() => setOpen(false)} className="p-2 hover:bg-slate-800/50 rounded-lg">
                                    <X className="w-5 h-5 text-slate-400" />
                                </button>
                            </div>
                            <div className="p-4 space-y-3">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    <div>
                                        <label className="text-xs text-slate-500">Versión</label>
                                        <input
                                            className="input mt-1"
                                            value={form.version}
                                            onChange={(e) => setForm((p) => ({ ...p, version: e.target.value }))}
                                            placeholder="v2.1.0"
                                        />
                                    </div>
                                    <div>
                                        <label className="text-xs text-slate-500">Tipo</label>
                                        <select
                                            className="input mt-1"
                                            value={form.change_type}
                                            onChange={(e) => setForm((p) => ({ ...p, change_type: e.target.value }))}
                                        >
                                            {TYPE_OPTIONS.map((o) => (
                                                <option key={o.value} value={o.value}>{o.label}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>
                                <div>
                                    <label className="text-xs text-slate-500">Título</label>
                                    <input
                                        className="input mt-1"
                                        value={form.title}
                                        onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))}
                                        placeholder="Nuevo módulo de Pagos"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs text-slate-500">Imagen (URL opcional)</label>
                                    <input
                                        className="input mt-1"
                                        value={form.image_url || ''}
                                        onChange={(e) => setForm((p) => ({ ...p, image_url: e.target.value }))}
                                        placeholder="https://..."
                                    />
                                </div>
                                <div>
                                    <label className="text-xs text-slate-500">Contenido (Markdown)</label>
                                    <textarea
                                        className="input mt-1 h-56 resize-none"
                                        value={form.body_markdown}
                                        onChange={(e) => setForm((p) => ({ ...p, body_markdown: e.target.value }))}
                                        placeholder="- Nuevo...\n- Fix..."
                                    />
                                </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                <div>
                                    <label className="text-xs text-slate-500">Roles (comma)</label>
                                    <input
                                        className="input mt-1"
                                        value={rolesText}
                                        onChange={(e) => setRolesText(e.target.value)}
                                        placeholder="owner, admin, staff"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs text-slate-500">Módulos requeridos (comma)</label>
                                    <input
                                        className="input mt-1"
                                        value={modulesText}
                                        onChange={(e) => setModulesText(e.target.value)}
                                        placeholder="pagos, whatsapp"
                                    />
                                </div>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                <div>
                                    <label className="text-xs text-slate-500">Tenants include (comma)</label>
                                    <input
                                        className="input mt-1"
                                        value={tenantsIncludeText}
                                        onChange={(e) => setTenantsIncludeText(e.target.value)}
                                        placeholder="gym1, gym2"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs text-slate-500">Tenants exclude (comma)</label>
                                    <input
                                        className="input mt-1"
                                        value={tenantsExcludeText}
                                        onChange={(e) => setTenantsExcludeText(e.target.value)}
                                        placeholder="gymX"
                                    />
                                </div>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                <div>
                                    <label className="text-xs text-slate-500">Min app version (opcional)</label>
                                    <input
                                        className="input mt-1"
                                        value={minAppVersion}
                                        onChange={(e) => setMinAppVersion(e.target.value)}
                                        placeholder="v2.3.0"
                                    />
                                </div>
                                <label className="flex items-center gap-2 text-sm text-slate-200 mt-6">
                                    <input type="checkbox" checked={!!pinned} onChange={(e) => setPinned(e.target.checked)} />
                                    Pinned
                                </label>
                            </div>
                                <label className="flex items-center gap-2 text-sm text-slate-200">
                                    <input
                                        type="checkbox"
                                        checked={!!form.is_published}
                                        onChange={(e) => setForm((p) => ({ ...p, is_published: e.target.checked }))}
                                    />
                                    Publicado
                                </label>
                                <div className="flex items-center gap-2 justify-end">
                                    {editing ? (
                                        <button
                                            className="btn-secondary flex items-center gap-2 text-danger-400 hover:text-danger-300"
                                            onClick={del}
                                            disabled={deleting || saving}
                                        >
                                            {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                                            Eliminar
                                        </button>
                                    ) : null}
                                    <button className="btn-primary flex items-center gap-2" onClick={save} disabled={saving}>
                                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                                        Guardar
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    </motion.div>
                ) : null}
            </AnimatePresence>
        </div>
    );
}
