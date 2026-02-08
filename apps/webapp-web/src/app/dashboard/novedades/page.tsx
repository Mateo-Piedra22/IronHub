'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Loader2, Megaphone, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui';
import { api, type ChangelogItem } from '@/lib/api';

function renderMarkdownLite(md: string) {
    const lines = String(md || '').split('\n');
    const blocks: Array<{ kind: 'ul' | 'p'; lines: string[] }> = [];
    let cur: { kind: 'ul' | 'p'; lines: string[] } | null = null;
    for (const raw of lines) {
        const line = raw.replace(/\r/g, '');
        const isBullet = line.trim().startsWith('- ');
        const kind: 'ul' | 'p' = isBullet ? 'ul' : 'p';
        const content = isBullet ? line.trim().slice(2) : line;
        if (!cur || cur.kind !== kind) {
            cur = { kind, lines: [] };
            blocks.push(cur);
        }
        cur.lines.push(content);
    }
    return (
        <div className="space-y-3">
            {blocks.map((b, i) => {
                if (b.kind === 'ul') {
                    return (
                        <ul key={i} className="list-disc pl-5 space-y-1 text-sm text-slate-200">
                            {b.lines.filter((x) => x.trim()).map((x, idx) => (
                                <li key={idx}>{x}</li>
                            ))}
                        </ul>
                    );
                }
                const text = b.lines.join('\n').trim();
                if (!text) return null;
                return (
                    <div key={i} className="text-sm text-slate-200 whitespace-pre-wrap">
                        {text}
                    </div>
                );
            })}
        </div>
    );
}

export default function DashboardNovedadesPage() {
    const [loading, setLoading] = useState(true);
    const [items, setItems] = useState<ChangelogItem[]>([]);
    const [page, setPage] = useState(1);
    const pageSize = 20;
    const [total, setTotal] = useState(0);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.listChangelogs({ page, limit: pageSize });
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
    }, [page]);

    useEffect(() => {
        load();
    }, [load]);

    useEffect(() => {
        api.markChangelogsRead().catch(() => {});
    }, []);

    const totalPages = useMemo(() => Math.max(1, Math.ceil(total / pageSize)), [total]);

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-primary-500/20 text-primary-300 flex items-center justify-center">
                    <Megaphone className="w-5 h-5" />
                </div>
                <div className="flex-1">
                    <h1 className="text-xl font-semibold text-white">Novedades</h1>
                    <p className="text-sm text-slate-400">Cambios, mejoras y anuncios importantes.</p>
                </div>
                <Button variant="secondary" onClick={load} leftIcon={<RefreshCw className="w-4 h-4" />} disabled={loading}>
                    Refrescar
                </Button>
            </div>

            <div className="rounded-2xl border border-slate-800/60 bg-slate-900/40 overflow-hidden">
                {loading ? (
                    <div className="p-8 flex items-center justify-center text-slate-400">
                        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Cargando…
                    </div>
                ) : items.length === 0 ? (
                    <div className="p-6 text-sm text-slate-500">No hay novedades publicadas.</div>
                ) : (
                    <div className="divide-y divide-slate-800/60">
                        {items.map((it) => (
                            <div key={it.id} className="p-5">
                                <div className="flex items-start justify-between gap-3">
                                    <div className="min-w-0">
                                        <div className="text-xs text-slate-500">{it.version} • {it.change_type} • {it.published_at || ''}</div>
                                        <div className="text-white font-semibold mt-1">{it.title}</div>
                                    </div>
                                    {it.image_url ? (
                                        <a className="text-xs text-primary-300 underline" href={it.image_url} target="_blank" rel="noreferrer">
                                            Ver imagen
                                        </a>
                                    ) : null}
                                </div>
                                <div className="mt-3">{renderMarkdownLite(it.body_markdown)}</div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <div className="flex items-center justify-between">
                <Button variant="secondary" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
                    Prev
                </Button>
                <div className="text-xs text-slate-500">
                    Página {page} / {totalPages}
                </div>
                <Button variant="secondary" disabled={page >= totalPages} onClick={() => setPage((p) => Math.min(totalPages, p + 1))}>
                    Next
                </Button>
            </div>
        </div>
    );
}
