'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { LifeBuoy, Loader2, RefreshCw, X, Save } from 'lucide-react';
import { api } from '@/lib/api';

function num(v: unknown) {
    try {
        return Number(v || 0) || 0;
    } catch {
        return 0;
    }
}

type SupportOpsTotals = Record<string, unknown>;

interface SupportOpsAssigneeRow {
    assignee: string | null;
    total: number;
    overdue: number;
}

interface SupportOpsTenantRow {
    tenant: string;
    total: number;
    overdue: number;
}

interface SupportOpsSummaryData {
    totals: SupportOpsTotals;
    by_assignee: SupportOpsAssigneeRow[];
    by_tenant: SupportOpsTenantRow[];
}

export default function SupportOpsPage() {
    const [loading, setLoading] = useState(true);
    const [data, setData] = useState<SupportOpsSummaryData | null>(null);
    const [settingsOpen, setSettingsOpen] = useState(false);
    const [settingsTenant, setSettingsTenant] = useState('');
    const [settingsTimezone, setSettingsTimezone] = useState('');
    const [settingsSlaJson, setSettingsSlaJson] = useState('');
    const [settingsLoading, setSettingsLoading] = useState(false);
    const [settingsSaving, setSettingsSaving] = useState(false);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.getSupportOpsSummary();
            if (res.ok && res.data?.ok) {
                setData({
                    totals: (res.data.totals || {}) as SupportOpsTotals,
                    by_assignee: Array.isArray(res.data.by_assignee) ? (res.data.by_assignee as SupportOpsAssigneeRow[]) : [],
                    by_tenant: Array.isArray(res.data.by_tenant) ? (res.data.by_tenant as SupportOpsTenantRow[]) : [],
                });
            } else {
                setData(null);
            }
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        load();
    }, [load]);

    const totals = useMemo(() => data?.totals || {}, [data]);

    const openTenantSettings = async (tenant: string) => {
        const tn = String(tenant || '').trim();
        if (!tn) return;
        setSettingsTenant(tn);
        setSettingsOpen(true);
        setSettingsTimezone('');
        setSettingsSlaJson(
            JSON.stringify(
                {
                    critical: { first: 7200, next: 7200 },
                    high: { first: 21600, next: 21600 },
                    medium: { first: 86400, next: 86400 },
                    low: { first: 259200, next: 259200 },
                },
                null,
                2
            )
        );
        setSettingsLoading(true);
        try {
            const res = await api.getSupportTenantSettings(tn);
            if (res.ok && res.data?.ok) {
                const s = res.data.settings || {};
                setSettingsTimezone(String(s.timezone || ''));
                try {
                    setSettingsSlaJson(JSON.stringify(s.sla_seconds || {}, null, 2));
                } catch {
                    setSettingsSlaJson('{}');
                }
            }
        } finally {
            setSettingsLoading(false);
        }
    };

    const saveTenantSettings = async () => {
        const tn = String(settingsTenant || '').trim();
        if (!tn) return;
        let obj: unknown = {};
        try {
            obj = JSON.parse(settingsSlaJson || '{}');
        } catch {
            obj = {};
        }
        setSettingsSaving(true);
        try {
            const res = await api.setSupportTenantSettings(tn, { timezone: settingsTimezone || null, sla_seconds: obj });
            if (res.ok) {
                setSettingsOpen(false);
            }
        } finally {
            setSettingsSaving(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-primary-500/20 text-primary-400 flex items-center justify-center">
                    <LifeBuoy className="w-5 h-5" />
                </div>
                <div className="flex-1">
                    <h1 className="page-title">Soporte Ops</h1>
                    <p className="text-slate-400">SLA, asignaciones y cola global.</p>
                </div>
                <button onClick={load} className="btn-secondary flex items-center gap-2" disabled={loading}>
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                    Refrescar
                </button>
            </div>

            {loading ? (
                <div className="card p-8 flex items-center justify-center text-slate-400">
                    <Loader2 className="w-5 h-5 animate-spin mr-2" /> Cargando…
                </div>
            ) : !data ? (
                <div className="card p-8 text-center text-slate-500">No se pudo cargar.</div>
            ) : (
                <>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="card p-4">
                            <div className="text-xs text-slate-500">Activos</div>
                            <div className="text-2xl font-semibold text-white">{num(totals.active_total)}</div>
                            <div className="text-xs text-slate-500 mt-1">
                                Open {num(totals.open_total)} • In progress {num(totals.in_progress_total)} • Waiting {num(totals.waiting_client_total)}
                            </div>
                        </div>
                        <div className="card p-4">
                            <div className="text-xs text-slate-500">SLA</div>
                            <div className="text-2xl font-semibold text-white">{num(totals.overdue_total)}</div>
                            <div className="text-xs text-slate-500 mt-1">
                                1h {num(totals.due_1h_total)} • 6h {num(totals.due_6h_total)} • 24h {num(totals.due_24h_total)}
                            </div>
                        </div>
                        <div className="card p-4">
                            <div className="text-xs text-slate-500">Unassigned</div>
                            <div className="text-2xl font-semibold text-white">{num(totals.unassigned_total)}</div>
                            <div className="text-xs text-slate-500 mt-1">Done {num(totals.done_total)}</div>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        <div className="card overflow-hidden">
                            <div className="p-4 border-b border-slate-800/50 text-sm text-slate-300">Por assignee</div>
                            <div className="divide-y divide-slate-800/50">
                                {(data.by_assignee || []).map((r, idx) => (
                                    <div key={idx} className="p-4 flex items-center justify-between gap-2">
                                        <div className="text-sm text-white">{String(r.assignee === '__unassigned__' ? '—' : r.assignee)}</div>
                                        <div className="text-xs text-slate-400">
                                            total <span className="text-white font-semibold">{num(r.total)}</span> • overdue{' '}
                                            <span className="text-white font-semibold">{num(r.overdue)}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="card overflow-hidden">
                            <div className="p-4 border-b border-slate-800/50 text-sm text-slate-300">Por tenant</div>
                            <div className="divide-y divide-slate-800/50">
                                {(data.by_tenant || []).map((r, idx) => (
                                    <button
                                        key={idx}
                                        className="w-full text-left p-4 hover:bg-slate-900/40 transition-colors flex items-center justify-between gap-2"
                                        onClick={() => openTenantSettings(String(r.tenant))}
                                    >
                                        <div className="text-sm text-white">{String(r.tenant)}</div>
                                        <div className="text-xs text-slate-400">
                                            total <span className="text-white font-semibold">{num(r.total)}</span> • overdue{' '}
                                            <span className="text-white font-semibold">{num(r.overdue)}</span>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                </>
            )}

            {settingsOpen ? (
                <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
                    <div className="w-full max-w-2xl card p-0 overflow-hidden">
                        <div className="p-4 border-b border-slate-800/50 flex items-center justify-between">
                            <div className="min-w-0">
                                <div className="text-white font-semibold">Settings soporte</div>
                                <div className="text-xs text-slate-500">{settingsTenant}</div>
                            </div>
                            <button onClick={() => setSettingsOpen(false)} className="p-2 hover:bg-slate-800/50 rounded-lg">
                                <X className="w-5 h-5 text-slate-400" />
                            </button>
                        </div>
                        <div className="p-4 space-y-3">
                            {settingsLoading ? (
                                <div className="p-8 flex items-center justify-center text-slate-400">
                                    <Loader2 className="w-5 h-5 animate-spin mr-2" /> Cargando…
                                </div>
                            ) : (
                                <>
                                    <div>
                                        <label className="text-xs text-slate-500">Timezone</label>
                                        <input
                                            className="input mt-1"
                                            value={settingsTimezone}
                                            onChange={(e) => setSettingsTimezone(e.target.value)}
                                            placeholder="America/Argentina/Buenos_Aires"
                                        />
                                    </div>
                                    <div>
                                        <label className="text-xs text-slate-500">SLA seconds (JSON)</label>
                                        <textarea
                                            className="input mt-1 h-56 resize-none font-mono"
                                            value={settingsSlaJson}
                                            onChange={(e) => setSettingsSlaJson(e.target.value)}
                                        />
                                    </div>
                                    <div className="flex justify-end gap-2">
                                        <button className="btn-secondary" onClick={() => setSettingsOpen(false)} disabled={settingsSaving}>
                                            Cancelar
                                        </button>
                                        <button className="btn-primary flex items-center gap-2" onClick={saveTenantSettings} disabled={settingsSaving}>
                                            {settingsSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                                            Guardar
                                        </button>
                                    </div>
                                </>
                            )}
                        </div>
                    </div>
                </div>
            ) : null}
        </div>
    );
}
