'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { AlertTriangle, ArrowRight, BarChart3, CalendarDays, CreditCard, Download, Loader2, MessageSquare, Plus, ScanLine, Settings, Users } from 'lucide-react';
import { formatCurrency, formatDate, formatDateRelative, formatNumber } from '@/lib/utils';
import { BarChart, ChartCard, DonutChart, HeatmapTable, LineChart } from '@/components/owner-dashboard/charts';
import { ConfirmModal } from '@/components/ui';

export default function DashboardPage() {
    return <OwnerDashboard />;
}

function OwnerDashboard() {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [kpis, setKpis] = useState<{ total_activos: number; total_inactivos: number; ingresos_mes: number; asistencias_hoy: number; nuevos_30_dias: number } | null>(
        null
    );
    const [kpisAdv, setKpisAdv] = useState<{ churn_rate?: number; avg_pago?: number; churned_30d?: number } | null>(null);
    const [activos, setActivos] = useState<{ activos: number; inactivos: number } | null>(null);
    const [ingresos12m, setIngresos12m] = useState<Array<{ mes: string; total: number }>>([]);
    const [nuevos12m, setNuevos12m] = useState<Array<{ mes: string; total: number }>>([]);
    const [arpu12m, setArpu12m] = useState<Array<{ mes: string; arpu: number }>>([]);
    const [arpaTipos, setArpaTipos] = useState<Array<{ tipo: string; arpa: number }>>([]);
    const [paymentDist, setPaymentDist] = useState<{ al_dia: number; vencido: number; sin_pagos: number } | null>(null);
    const [cohorts, setCohorts] = useState<Array<{ cohort: string; retention_rate: number; total: number; retained: number }>>([]);
    const [waitlistEvents, setWaitlistEvents] = useState<Array<{ id?: number; usuario_nombre?: string; posicion?: number; fecha?: string | null }>>([]);
    const [delinquencyAlerts, setDelinquencyAlerts] = useState<Array<{ usuario_id?: number; usuario_nombre?: string; ultimo_pago?: string | null }>>([]);
    const [waStats, setWaStats] = useState<{ total?: number; ultimo_mes?: number; por_tipo?: Record<string, number>; por_estado?: Record<string, number> } | null>(null);
    const [waPendientes, setWaPendientes] = useState<any[]>([]);
    const [ownerGymSettings, setOwnerGymSettings] = useState<{ attendance_allow_multiple_per_day: boolean } | null>(null);
    const [ownerGymBilling, setOwnerGymBilling] = useState<any>(null);
    const [savingGymSettings, setSavingGymSettings] = useState(false);
    const [toggleConfirm, setToggleConfirm] = useState<{ open: boolean; next: boolean } | null>(null);
    const [usuariosSearch, setUsuariosSearch] = useState('');
    const [usuariosSearchDebounced, setUsuariosSearchDebounced] = useState('');
    const [usuariosActivo, setUsuariosActivo] = useState<'all' | 'true' | 'false'>('all');
    const [usuarios, setUsuarios] = useState<any[]>([]);
    const [usuariosTotal, setUsuariosTotal] = useState(0);
    const [pagosDesde, setPagosDesde] = useState('');
    const [pagosHasta, setPagosHasta] = useState('');
    const [pagos, setPagos] = useState<any[]>([]);
    const [metodosPago, setMetodosPago] = useState<any[]>([]);
    const [metodoId, setMetodoId] = useState<number | null>(null);
    const [asistencias, setAsistencias] = useState<any[]>([]);
    const [refreshing, setRefreshing] = useState(false);
    const [audit, setAudit] = useState<any>(null);
    const [auditLoading, setAuditLoading] = useState(false);
    const [auditDesde, setAuditDesde] = useState(() => new Date(Date.now() - 34 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10));
    const [auditHasta, setAuditHasta] = useState(() => new Date().toISOString().slice(0, 10));
    const [auditUmbralMultiples, setAuditUmbralMultiples] = useState(3);
    const [auditUmbralRepeticion, setAuditUmbralRepeticion] = useState(5);

    useEffect(() => {
        const run = async () => {
            setLoading(true);
            setError('');
            try {
                const [rOverview, rMetodos, rSettings, rBilling, rAudit] = await Promise.all([
                    api.getOwnerDashboardOverview(),
                    api.getMetodosPago(),
                    api.getOwnerGymSettings(),
                    api.getOwnerGymBilling(),
                    api.getOwnerAttendanceAudit({ desde: auditDesde, hasta: auditHasta, umbral_multiples: auditUmbralMultiples, umbral_repeticion_minutos: auditUmbralRepeticion }),
                ]);

                if (rOverview.ok && rOverview.data?.ok) {
                    const d = rOverview.data as any;
                    if (d.kpis) setKpis(d.kpis);
                    if (d.kpis_avanzados) setKpisAdv(d.kpis_avanzados);
                    if (d.activos_inactivos) setActivos(d.activos_inactivos);
                    setIngresos12m((d.ingresos12m?.data || []) as any[]);
                    setNuevos12m((d.nuevos12m?.data || []) as any[]);
                    setArpu12m((d.arpu12m?.data || []) as any[]);
                    setArpaTipos((d.arpa_por_tipo_cuota?.data || []) as any[]);
                    if (d.payment_status_dist) setPaymentDist(d.payment_status_dist);
                    const items = (d.cohort_retencion_6m?.cohorts || []) as Array<any>;
                    setCohorts(
                        items.map((it) => ({
                            cohort: String((it as any)?.cohort || ''),
                            retention_rate: Number((it as any)?.retention_rate || 0),
                            total: Number((it as any)?.total || 0),
                            retained: Number((it as any)?.retained || 0),
                        }))
                    );
                    setWaitlistEvents((d.waitlist_events?.events || []) as any[]);
                    setDelinquencyAlerts((d.delinquency_alerts_recent?.alerts || []) as any[]);
                    setWaStats((d.whatsapp_stats || null) as any);
                    setWaPendientes((d.whatsapp_pendientes?.mensajes || []) as any[]);
                }
                if (rMetodos.ok && rMetodos.data) setMetodosPago((rMetodos.data.metodos || []) as any[]);
                if (rSettings.ok && rSettings.data?.ok) {
                    const v = Boolean((rSettings.data.settings || {})['attendance_allow_multiple_per_day']);
                    setOwnerGymSettings({ attendance_allow_multiple_per_day: v });
                }
                if (rBilling.ok && rBilling.data?.ok) setOwnerGymBilling(rBilling.data);
                if (rAudit.ok && rAudit.data?.ok) setAudit(rAudit.data);
            } catch (e) {
                setError(String(e) || 'No se pudieron cargar los datos');
            } finally {
                setLoading(false);
            }
        };
        run();
    }, []);

    const refreshAudit = useCallback(async () => {
        setAuditLoading(true);
        try {
            const r = await api.getOwnerAttendanceAudit({
                desde: auditDesde,
                hasta: auditHasta,
                umbral_multiples: auditUmbralMultiples,
                umbral_repeticion_minutos: auditUmbralRepeticion,
            });
            if (r.ok && r.data?.ok) setAudit(r.data);
        } finally {
            setAuditLoading(false);
        }
    }, [auditDesde, auditHasta, auditUmbralMultiples, auditUmbralRepeticion]);

    const downloadBlob = useCallback(async (name: string, blob: Blob) => {
        const url = URL.createObjectURL(blob);
        try {
            const a = document.createElement('a');
            a.href = url;
            a.download = name;
            document.body.appendChild(a);
            a.click();
            a.remove();
        } finally {
            URL.revokeObjectURL(url);
        }
    }, []);

    const refreshTables = useCallback(async () => {
        setRefreshing(true);
        try {
            const [rUsuarios, rPagos, rAsist] = await Promise.all([
                api.getUsuarios({
                    search: usuariosSearchDebounced || undefined,
                    activo: usuariosActivo === 'all' ? undefined : usuariosActivo === 'true',
                    page: 1,
                    limit: 20,
                }),
                api.getPagos({
                    desde: pagosDesde || undefined,
                    hasta: pagosHasta || undefined,
                    metodo_id: metodoId || undefined,
                    page: 1,
                    limit: 20,
                }),
                api.getAsistencias({
                    desde: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
                    hasta: new Date().toISOString().slice(0, 10),
                    limit: 20,
                }),
            ]);
            if (rUsuarios.ok && rUsuarios.data) {
                setUsuarios(rUsuarios.data.usuarios || []);
                setUsuariosTotal(rUsuarios.data.total || 0);
            }
            if (rPagos.ok && rPagos.data) {
                setPagos(rPagos.data.pagos || []);
            }
            if (rAsist.ok && rAsist.data) {
                setAsistencias(rAsist.data.asistencias || []);
            }
        } finally {
            setRefreshing(false);
        }
    }, [usuariosSearchDebounced, usuariosActivo, pagosDesde, pagosHasta, metodoId]);

    useEffect(() => {
        if (!loading) refreshTables();
    }, [loading, refreshTables]);

    useEffect(() => {
        if (!loading) refreshTables();
    }, [usuariosSearchDebounced, usuariosActivo, loading, refreshTables]);

    useEffect(() => {
        if (!loading) refreshTables();
    }, [pagosDesde, pagosHasta, metodoId, loading, refreshTables]);

    useEffect(() => {
        const t = setTimeout(() => setUsuariosSearchDebounced(usuariosSearch), 300);
        return () => clearTimeout(t);
    }, [usuariosSearch]);

    const ingresosSeries = useMemo(() => ingresos12m.map((x) => Number(x.total || 0)), [ingresos12m]);
    const nuevosSeries = useMemo(() => nuevos12m.map((x) => Number(x.total || 0)), [nuevos12m]);
    const arpuSeries = useMemo(() => arpu12m.map((x) => Number(x.arpu || 0)), [arpu12m]);
    const arpaSeries = useMemo(() => arpaTipos.map((x) => Number(x.arpa || 0)), [arpaTipos]);
    const waitlistSeries = useMemo(() => waitlistEvents.map((e) => Number(e.posicion || 0)).slice(0, 12), [waitlistEvents]);
    const auditDailyTotals = useMemo(() => ((audit?.daily || []) as any[]).map((d) => Number(d.total_checkins || 0)), [audit]);
    const auditDailyUnique = useMemo(() => ((audit?.daily || []) as any[]).map((d) => Number(d.unique_users || 0)), [audit]);

    const kpiCards = useMemo(() => {
        const activosN = Number(kpis?.total_activos || 0);
        const inactivosN = Number(kpis?.total_inactivos || 0);
        const ingresosMesN = Number(kpis?.ingresos_mes || 0);
        const asistHoyN = Number(kpis?.asistencias_hoy || 0);
        const nuevos30N = Number(kpis?.nuevos_30_dias || 0);
        const churnRate = Number(kpisAdv?.churn_rate || 0);
        const avgPago = Number(kpisAdv?.avg_pago || 0);
        const churned30 = Number(kpisAdv?.churned_30d || 0);
        const alDia = Number(paymentDist?.al_dia || 0);
        const vencido = Number(paymentDist?.vencido || 0);
        const sinPagos = Number(paymentDist?.sin_pagos || 0);
        const delinquencyTop = delinquencyAlerts.length;
        const waTotal = Number(waStats?.total || 0);
        const waMes = Number(waStats?.ultimo_mes || 0);

        const ticketProm = avgPago || (ingresosMesN && (alDia + vencido) ? ingresosMesN / Math.max(1, alDia + vencido) : 0);
        const ratioMorosidad = activosN ? (vencido / activosN) * 100 : 0;

        return [
            { label: 'Usuarios activos', value: formatNumber(activosN), accent: 'text-primary-300' },
            { label: 'Usuarios inactivos', value: formatNumber(inactivosN), accent: 'text-slate-200' },
            { label: 'Ingresos (mes)', value: formatCurrency(ingresosMesN), accent: 'text-gold-300' },
            { label: 'Asistencias (hoy)', value: formatNumber(asistHoyN), accent: 'text-primary-300' },
            { label: 'Altas (30 días)', value: formatNumber(nuevos30N), accent: 'text-slate-200' },
            { label: 'Ticket promedio (30 días)', value: avgPago ? formatCurrency(avgPago) : formatCurrency(ticketProm), accent: 'text-slate-200' },
            { label: 'Churn aprox (30d)', value: `${formatNumber(churned30)} (${churnRate.toFixed(1)}%)`, accent: 'text-slate-200' },
            { label: 'Al día', value: formatNumber(alDia), accent: 'text-emerald-300' },
            { label: 'Vencidos', value: formatNumber(vencido), accent: 'text-danger-300' },
            { label: 'Sin pagos', value: formatNumber(sinPagos), accent: 'text-yellow-200' },
            { label: 'Morosidad (ratio)', value: `${ratioMorosidad.toFixed(1)}%`, accent: 'text-danger-300' },
            { label: 'Alertas morosidad (top)', value: formatNumber(delinquencyTop), accent: 'text-danger-300' },
            { label: 'WhatsApp total', value: formatNumber(waTotal), accent: 'text-emerald-300' },
            { label: 'WhatsApp (últ. 30d)', value: formatNumber(waMes), accent: 'text-emerald-300' },
            { label: 'Cola WhatsApp (30d)', value: formatNumber(waPendientes.length), accent: 'text-slate-200' },
        ];
    }, [kpis, kpisAdv, paymentDist, delinquencyAlerts.length, waStats, waPendientes.length]);

    const paymentSegments = useMemo(() => {
        const alDia = Number(paymentDist?.al_dia || 0);
        const vencido = Number(paymentDist?.vencido || 0);
        const sinPagos = Number(paymentDist?.sin_pagos || 0);
        return [
            { label: 'Al día', value: alDia, className: 'stroke-emerald-400' },
            { label: 'Vencidos', value: vencido, className: 'stroke-red-400' },
            { label: 'Sin pagos', value: sinPagos, className: 'stroke-yellow-400' },
        ];
    }, [paymentDist]);

    const activeSegments = useMemo(() => {
        const a = Number(activos?.activos || kpis?.total_activos || 0);
        const i = Number(activos?.inactivos || kpis?.total_inactivos || 0);
        return [
            { label: 'Activos', value: a, className: 'stroke-primary-400' },
            { label: 'Inactivos', value: i, className: 'stroke-slate-400' },
        ];
    }, [activos, kpis]);

    const waStatusSegments = useMemo(() => {
        const entries = Object.entries(waStats?.por_estado || {}).map(([k, v]) => ({ k, v: Number(v || 0) }));
        const known = (name: string) => {
            const n = name.toLowerCase();
            if (n.includes('sent') || n.includes('delivered') || n.includes('read')) return 'stroke-emerald-400';
            if (n.includes('fail') || n.includes('error')) return 'stroke-red-400';
            if (n.includes('pending')) return 'stroke-yellow-400';
            return 'stroke-slate-400';
        };
        return entries
            .slice(0, 5)
            .map((e) => ({ label: e.k || 'estado', value: e.v, className: known(e.k) }))
            .filter((s) => s.value > 0);
    }, [waStats]);

    return (
        <div className="p-4 lg:p-6">
            <div className="max-w-7xl mx-auto space-y-6">
                <div className="card p-5">
                    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                        <div>
                            <h1 className="text-xl font-display font-bold text-white flex items-center gap-2">
                                <BarChart3 className="w-5 h-5 text-primary-400" />
                                Dashboard del dueño
                            </h1>
                            <p className="text-sm text-slate-400 mt-1">KPIs reales, reportes, tablas y acciones rápidas.</p>
                            {error ? <div className="text-xs text-danger-400 mt-2">{error}</div> : null}
                            {loading ? <div className="text-xs text-slate-500 mt-2">Cargando datos…</div> : null}
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                            <Link href="/gestion/usuarios" className="btn-secondary flex items-center gap-2">
                                <Users className="w-4 h-4" />
                                Abrir gestión
                                <ArrowRight className="w-4 h-4" />
                            </Link>
                            <Link href="/gestion/usuarios" className="btn-primary flex items-center gap-2">
                                <Plus className="w-4 h-4" />
                                Alta usuario
                            </Link>
                            <Link href="/gestion/pagos" className="btn-primary flex items-center gap-2">
                                <CreditCard className="w-4 h-4" />
                                Registrar pago
                            </Link>
                            <Link href="/gestion/asistencias" className="btn-secondary flex items-center gap-2">
                                <ScanLine className="w-4 h-4" />
                                Check-in
                            </Link>
                            <Link href="/gestion/whatsapp" className="btn-secondary flex items-center gap-2">
                                <MessageSquare className="w-4 h-4" />
                                WhatsApp
                            </Link>
                            <Link href="/gestion/configuracion" className="btn-secondary flex items-center gap-2">
                                <Settings className="w-4 h-4" />
                                Configuración
                            </Link>
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <div className="card p-5 lg:col-span-2">
                        <div className="flex items-center justify-between gap-3 mb-4">
                            <h2 className="text-base font-semibold text-white flex items-center gap-2">
                                <CreditCard className="w-4 h-4 text-primary-400" />
                                Suscripción del gimnasio
                            </h2>
                            {ownerGymBilling?.gym?.status && (
                                <span className={`badge ${String(ownerGymBilling.gym.status) === 'active' ? 'badge-success' : 'badge-warning'}`}>
                                    {String(ownerGymBilling.gym.status)}
                                </span>
                            )}
                        </div>

                        {!ownerGymBilling ? (
                            <div className="text-sm text-slate-500 flex items-center gap-2">
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Cargando…
                            </div>
                        ) : ownerGymBilling.subscription ? (
                            <div className="space-y-4">
                                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                    <div className="rounded-xl bg-slate-900/60 border border-slate-800/60 p-4">
                                        <div className="text-xs text-slate-500">Plan</div>
                                        <div className="mt-1 text-white font-semibold">
                                            {ownerGymBilling.subscription.plan?.name || ownerGymBilling.subscription.plan_name || '—'}
                                        </div>
                                        <div className="text-xs text-slate-500 mt-1">
                                            {ownerGymBilling.subscription.plan?.currency || 'ARS'}{' '}
                                            {formatCurrency(Number(ownerGymBilling.subscription.plan?.amount || 0))}
                                        </div>
                                    </div>
                                    <div className="rounded-xl bg-slate-900/60 border border-slate-800/60 p-4">
                                        <div className="text-xs text-slate-500">Vence</div>
                                        <div className="mt-1 text-white font-semibold">
                                            {ownerGymBilling.subscription.next_due_date ? formatDate(ownerGymBilling.subscription.next_due_date) : '—'}
                                        </div>
                                        <div className="text-xs text-slate-500 mt-1">
                                            estado: {String(ownerGymBilling.subscription.status || '—')}
                                        </div>
                                    </div>
                                    <div className="rounded-xl bg-slate-900/60 border border-slate-800/60 p-4">
                                        <div className="text-xs text-slate-500">Alertas</div>
                                        {ownerGymBilling.gym?.suspended_reason ? (
                                            <div className="mt-2 flex items-start gap-2 text-danger-300 text-sm">
                                                <AlertTriangle className="w-4 h-4 mt-0.5" />
                                                <div>{String(ownerGymBilling.gym.suspended_reason)}</div>
                                            </div>
                                        ) : (
                                            <div className="mt-1 text-slate-300 text-sm">Sin alertas</div>
                                        )}
                                    </div>
                                </div>

                                <div>
                                    <div className="text-xs text-slate-500 mb-2">Pagos recientes</div>
                                    <div className="rounded-xl border border-slate-800 overflow-hidden">
                                        <table className="w-full text-sm">
                                            <thead className="bg-slate-900/60">
                                                <tr className="text-left text-slate-400">
                                                    <th className="px-4 py-3">Fecha</th>
                                                    <th className="px-4 py-3">Monto</th>
                                                    <th className="px-4 py-3">Estado</th>
                                                    <th className="px-4 py-3">Notas</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-slate-800">
                                                {(ownerGymBilling.payments || []).slice(0, 5).map((p: any) => (
                                                    <tr key={p.id} className="text-slate-200">
                                                        <td className="px-4 py-3">{p.paid_at ? formatDate(p.paid_at) : '—'}</td>
                                                        <td className="px-4 py-3">
                                                            {p.currency || 'ARS'} {formatCurrency(Number(p.amount || 0))}
                                                        </td>
                                                        <td className="px-4 py-3">
                                                            <span className={`badge ${String(p.status) === 'paid' ? 'badge-success' : 'badge-warning'}`}>
                                                                {String(p.status || '—')}
                                                            </span>
                                                        </td>
                                                        <td className="px-4 py-3 text-slate-400 max-w-xs truncate">{p.notes || '—'}</td>
                                                    </tr>
                                                ))}
                                                {(ownerGymBilling.payments || []).length === 0 && (
                                                    <tr>
                                                        <td className="px-4 py-6 text-slate-500" colSpan={4}>
                                                            Sin pagos registrados.
                                                        </td>
                                                    </tr>
                                                )}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="text-sm text-slate-500">Sin suscripción configurada.</div>
                        )}
                    </div>

                    <div className="card p-5">
                        <div className="flex items-center justify-between gap-3 mb-4">
                            <h2 className="text-base font-semibold text-white flex items-center gap-2">
                                <ScanLine className="w-4 h-4 text-primary-400" />
                                Asistencias
                            </h2>
                        </div>
                        <div className="space-y-3">
                            <div className="text-sm text-slate-400">
                                Permitir múltiples asistencias por día por usuario
                            </div>
                            <button
                                className={`w-full rounded-xl border px-4 py-3 text-left transition-colors ${ownerGymSettings?.attendance_allow_multiple_per_day
                                        ? 'border-emerald-600/50 bg-emerald-500/10 text-emerald-200'
                                        : 'border-slate-800 bg-slate-900/60 text-slate-200'
                                    }`}
                                disabled={savingGymSettings}
                                onClick={() => {
                                    const current = Boolean(ownerGymSettings?.attendance_allow_multiple_per_day);
                                    setToggleConfirm({ open: true, next: !current });
                                }}
                            >
                                <div className="flex items-center justify-between gap-3">
                                    <div className="font-semibold">
                                        {ownerGymSettings?.attendance_allow_multiple_per_day ? 'Activado' : 'Desactivado'}
                                    </div>
                                    {savingGymSettings ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                                </div>
                                <div className="text-xs text-slate-400 mt-1">
                                    Si está activado, el check-in registra todas las entradas del día. Si está desactivado, solo 1 por día.
                                </div>
                            </button>
                            <div className="text-xs text-slate-500">
                                Aplica a gestión, QR personal y estación QR. Impacta desde el próximo check-in.
                            </div>
                        </div>
                    </div>
                </div>

                <div className="card p-5">
                    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
                        <div>
                            <h2 className="text-base font-semibold text-white flex items-center gap-2">
                                <ScanLine className="w-4 h-4 text-primary-400" />
                                Auditoría de check-ins
                            </h2>
                            <div className="text-xs text-slate-500 mt-1">Totales vs únicos, anomalías y export (modo enterprise).</div>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                            <button className="btn-secondary flex items-center gap-2" onClick={refreshAudit} disabled={auditLoading}>
                                {auditLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                                Refrescar
                            </button>
                            <button
                                className="btn-secondary flex items-center gap-2"
                                onClick={async () => {
                                    const r = await api.exportToCsv('asistencias_audit', { desde: auditDesde, hasta: auditHasta });
                                    if (r.ok && r.data) await downloadBlob(`asistencias_audit_${auditDesde}_${auditHasta}.csv`, r.data);
                                }}
                                disabled={auditLoading}
                            >
                                <Download className="w-4 h-4" />
                                CSV audit
                            </button>
                            <button
                                className="btn-secondary flex items-center gap-2"
                                onClick={async () => {
                                    const r = await api.exportToCsv('asistencias', { desde: auditDesde, hasta: auditHasta });
                                    if (r.ok && r.data) await downloadBlob(`asistencias_${auditDesde}_${auditHasta}.csv`, r.data);
                                }}
                                disabled={auditLoading}
                            >
                                <Download className="w-4 h-4" />
                                CSV registros
                            </button>
                        </div>
                    </div>

                    <div className="mt-4 grid grid-cols-1 lg:grid-cols-5 gap-3">
                        <div className="lg:col-span-2 grid grid-cols-2 gap-2">
                            <div>
                                <div className="text-xs text-slate-500 mb-1">Desde</div>
                                <input className="input w-full" type="date" value={auditDesde} onChange={(e) => setAuditDesde(e.target.value)} />
                            </div>
                            <div>
                                <div className="text-xs text-slate-500 mb-1">Hasta</div>
                                <input className="input w-full" type="date" value={auditHasta} onChange={(e) => setAuditHasta(e.target.value)} />
                            </div>
                        </div>
                        <div>
                            <div className="text-xs text-slate-500 mb-1">Umbral múltiples/día</div>
                            <input
                                className="input w-full"
                                type="number"
                                min={2}
                                max={50}
                                value={auditUmbralMultiples}
                                onChange={(e) => setAuditUmbralMultiples(Number(e.target.value) || 3)}
                            />
                        </div>
                        <div>
                            <div className="text-xs text-slate-500 mb-1">Repetición rápida (min)</div>
                            <input
                                className="input w-full"
                                type="number"
                                min={1}
                                max={60}
                                value={auditUmbralRepeticion}
                                onChange={(e) => setAuditUmbralRepeticion(Number(e.target.value) || 5)}
                            />
                        </div>
                        <div className="rounded-xl bg-slate-900/60 border border-slate-800/60 p-4">
                            <div className="text-xs text-slate-500">Resumen</div>
                            <div className="mt-1 text-sm text-slate-200">
                                check-ins: <span className="font-semibold">{formatNumber(Number(audit?.summary?.total_checkins || 0))}</span>
                            </div>
                            <div className="text-sm text-slate-200">
                                únicos: <span className="font-semibold">{formatNumber(Number(audit?.summary?.unique_users_total || 0))}</span>
                            </div>
                            <div className="text-xs text-slate-500 mt-1">
                                avg: {Number(audit?.summary?.avg_checkins_per_user || 0).toFixed(2)} / usuario
                            </div>
                        </div>
                    </div>

                    <div className="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
                        <ChartCard title="Check-ins diarios" subtitle="Total por día" className="lg:col-span-1">
                            <LineChart data={auditDailyTotals} />
                        </ChartCard>
                        <ChartCard title="Usuarios únicos diarios" subtitle="Distinct por día" className="lg:col-span-1">
                            <LineChart data={auditDailyUnique} strokeClassName="stroke-emerald-300" fillClassName="fill-emerald-500/10" />
                        </ChartCard>
                    </div>

                    <div className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
                        <ChartCard title="Picos detectados" subtitle="Días con spike vs promedio 7d" className="lg:col-span-1">
                            <div className="space-y-2">
                                {(audit?.anomalies?.spikes || []).slice(0, 8).map((s: any) => (
                                    <div key={String(s?.fecha || '')} className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
                                        <div className="flex items-center justify-between gap-2">
                                            <div className="text-sm text-slate-200">{formatDate(String(s?.fecha || ''))}</div>
                                            <div className="text-sm text-danger-200 font-semibold">{formatNumber(Number(s?.total_checkins || 0))}</div>
                                        </div>
                                        <div className="text-xs text-slate-500 mt-1">avg prev 7d: {Number(s?.avg_prev_7d || 0).toFixed(2)}</div>
                                    </div>
                                ))}
                                {!(audit?.anomalies?.spikes || []).length ? <div className="text-sm text-slate-400">Sin picos.</div> : null}
                            </div>
                        </ChartCard>

                        <ChartCard title="Múltiples en un día" subtitle="Usuarios con alta frecuencia" className="lg:col-span-1">
                            <div className="space-y-2">
                                {(audit?.anomalies?.multiples_en_dia || []).slice(0, 8).map((m: any, idx: number) => (
                                    <div key={`${m?.fecha || ''}-${m?.usuario_id || idx}`} className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
                                        <div className="flex items-center justify-between gap-2">
                                            <div className="text-sm text-slate-200">{m?.usuario_nombre || `ID ${m?.usuario_id}`}</div>
                                            <div className="text-sm text-yellow-200 font-semibold">{formatNumber(Number(m?.count || 0))}</div>
                                        </div>
                                        <div className="text-xs text-slate-500 mt-1">
                                            {m?.usuario_dni ? `DNI ${m.usuario_dni} · ` : ''}{m?.fecha ? formatDate(m.fecha) : ''}
                                        </div>
                                    </div>
                                ))}
                                {!(audit?.anomalies?.multiples_en_dia || []).length ? <div className="text-sm text-slate-400">Sin casos.</div> : null}
                            </div>
                        </ChartCard>

                        <ChartCard title="Repeticiones rápidas" subtitle="Check-ins con delta muy bajo" className="lg:col-span-1">
                            <div className="space-y-2">
                                {(audit?.anomalies?.repeticiones_rapidas || []).slice(0, 8).map((r: any, idx: number) => (
                                    <div key={`${r?.hora || ''}-${idx}`} className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
                                        <div className="flex items-center justify-between gap-2">
                                            <div className="text-sm text-slate-200">{r?.usuario_nombre || `ID ${r?.usuario_id}`}</div>
                                            <div className="text-sm text-danger-200 font-semibold">{Math.max(0, Math.round(Number(r?.delta_seconds || 0) / 60))}m</div>
                                        </div>
                                        <div className="text-xs text-slate-500 mt-1">
                                            {r?.fecha ? formatDate(r.fecha) : ''}{r?.usuario_dni ? ` · DNI ${r.usuario_dni}` : ''}
                                        </div>
                                    </div>
                                ))}
                                {!(audit?.anomalies?.repeticiones_rapidas || []).length ? <div className="text-sm text-slate-400">Sin casos.</div> : null}
                            </div>
                        </ChartCard>
                    </div>
                </div>

                <div className="card p-5">
                    <div className="flex items-center justify-between gap-3 mb-4">
                        <h2 className="text-base font-semibold text-white">KPIs ejecutivos</h2>
                        <button className="btn-secondary flex items-center gap-2" onClick={refreshTables} disabled={refreshing || loading}>
                            {refreshing ? <span className="animate-pulse">Actualizando…</span> : 'Actualizar'}
                        </button>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                        {kpiCards.map((k) => (
                            <div key={k.label} className="rounded-xl bg-slate-900/60 border border-slate-800/60 p-4">
                                <div className="text-xs text-slate-500">{k.label}</div>
                                <div className={`mt-1 text-lg font-bold ${k.accent}`}>{k.value}</div>
                            </div>
                        ))}
                    </div>
                </div>

                <section id="reportes" className="space-y-4">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        <ChartCard title="Ingresos (12 meses)" subtitle="Suma mensual de pagos">
                            <LineChart data={ingresosSeries} />
                            <div className="mt-2 text-xs text-slate-500 flex flex-wrap gap-3">
                                <span>max: {formatCurrency(Math.max(0, ...ingresosSeries))}</span>
                                <span>meses: {formatNumber(ingresosSeries.length)}</span>
                            </div>
                        </ChartCard>

                        <ChartCard title="Altas (12 meses)" subtitle="Usuarios registrados por mes">
                            <BarChart values={nuevosSeries} />
                            <div className="mt-2 text-xs text-slate-500">total: {formatNumber(nuevosSeries.reduce((a, b) => a + b, 0))}</div>
                        </ChartCard>

                        <ChartCard title="ARPU (12 meses)" subtitle="Ingreso promedio por usuario (según pagos)">
                            <LineChart data={arpuSeries} strokeClassName="stroke-gold-300" fillClassName="fill-gold-500/10" />
                        </ChartCard>

                        <ChartCard title="ARPA por tipo de cuota" subtitle="Promedio de pago por tipo (últimos 3 meses)">
                            <BarChart values={arpaSeries} barClassName="fill-emerald-500/50" />
                            <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-slate-400">
                                {arpaTipos.slice(0, 6).map((t) => (
                                    <div key={t.tipo} className="flex items-center justify-between gap-2">
                                        <span className="truncate">{t.tipo}</span>
                                        <span className="text-slate-300">{formatCurrency(Number(t.arpa || 0))}</span>
                                    </div>
                                ))}
                            </div>
                        </ChartCard>

                        <ChartCard title="Estado de pagos (usuarios activos)" subtitle="Corte ~últimos 35 días">
                            <DonutChart segments={paymentSegments} />
                        </ChartCard>

                        <ChartCard title="Pagos por estado" subtitle="Usuarios activos por condición">
                            <BarChart
                                values={[
                                    Number(paymentDist?.al_dia || 0),
                                    Number(paymentDist?.vencido || 0),
                                    Number(paymentDist?.sin_pagos || 0),
                                ]}
                                barClassName="fill-primary-500/45"
                            />
                            <div className="mt-2 text-xs text-slate-500 flex flex-wrap gap-3">
                                <span>al día={formatNumber(Number(paymentDist?.al_dia || 0))}</span>
                                <span>vencido={formatNumber(Number(paymentDist?.vencido || 0))}</span>
                                <span>sin pagos={formatNumber(Number(paymentDist?.sin_pagos || 0))}</span>
                            </div>
                        </ChartCard>

                        <ChartCard title="Activos vs inactivos" subtitle="Distribución actual de usuarios">
                            <DonutChart segments={activeSegments} />
                        </ChartCard>

                        <ChartCard title="Lista de espera (eventos recientes)" subtitle="Posición de los últimos eventos">
                            <BarChart values={waitlistSeries} barClassName="fill-primary-500/45" />
                            <div className="mt-2 text-xs text-slate-500">eventos: {formatNumber(waitlistEvents.length)}</div>
                        </ChartCard>

                        <ChartCard title="Retención (cohortes 6 meses)" subtitle="Aproximación por cohorte/mes">
                            <HeatmapTable
                                cohorts={cohorts.map((c) => ({ cohort: c.cohort, values: [Number(c.retention_rate || 0) / 100] }))}
                            />
                        </ChartCard>

                        <ChartCard title="WhatsApp por estado" subtitle="Mensajes enviados por estado (histórico)">
                            {waStatusSegments.length ? <DonutChart segments={waStatusSegments} /> : <div className="text-sm text-slate-400">Sin datos</div>}
                        </ChartCard>

                        <ChartCard title="Morosidad (top 20)" subtitle="Usuarios activos sin pago reciente">
                            <div className="space-y-2">
                                {delinquencyAlerts.length ? (
                                    delinquencyAlerts.map((a) => (
                                        <div key={String(a.usuario_id)} className="flex items-center justify-between gap-3 text-sm">
                                            <span className="text-slate-200 truncate">{a.usuario_nombre || `Usuario ${a.usuario_id}`}</span>
                                            <span className="text-slate-500">{a.ultimo_pago ? formatDateRelative(a.ultimo_pago) : 'sin pagos'}</span>
                                        </div>
                                    ))
                                ) : (
                                    <div className="text-sm text-slate-400">Sin alertas</div>
                                )}
                            </div>
                        </ChartCard>
                    </div>
                </section>

                <section id="usuarios" className="card p-5">
                    <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
                        <div>
                            <h2 className="text-base font-semibold text-white">Usuarios</h2>
                            <div className="text-xs text-slate-500 mt-1">Últimos 20 (total: {formatNumber(usuariosTotal)})</div>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                            <input
                                className="input w-64"
                                placeholder="Buscar por nombre/DNI..."
                                value={usuariosSearch}
                                onChange={(e) => setUsuariosSearch(e.target.value)}
                            />
                            <select className="input" value={usuariosActivo} onChange={(e) => setUsuariosActivo(e.target.value as any)}>
                                <option value="all">Todos</option>
                                <option value="true">Activos</option>
                                <option value="false">Inactivos</option>
                            </select>
                            <Link className="btn-secondary flex items-center gap-2" href="/api/export/usuarios/csv">
                                <Download className="w-4 h-4" />
                                CSV
                            </Link>
                        </div>
                    </div>
                    <div className="mt-4 overflow-x-auto">
                        <table className="min-w-full text-sm">
                            <thead>
                                <tr className="text-slate-500">
                                    <th className="text-left font-medium py-2 pr-4">Nombre</th>
                                    <th className="text-left font-medium py-2 pr-4">DNI</th>
                                    <th className="text-left font-medium py-2 pr-4">Teléfono</th>
                                    <th className="text-left font-medium py-2 pr-4">Estado</th>
                                    <th className="text-left font-medium py-2 pr-4">Alta</th>
                                </tr>
                            </thead>
                            <tbody>
                                {usuarios.map((u) => (
                                    <tr key={String(u.id)} className="border-t border-slate-800/60">
                                        <td className="py-2 pr-4 text-slate-200">{u.nombre}</td>
                                        <td className="py-2 pr-4 text-slate-400">{u.dni}</td>
                                        <td className="py-2 pr-4 text-slate-400">{u.telefono || '-'}</td>
                                        <td className="py-2 pr-4">
                                            {u.activo ? (
                                                <span className="text-emerald-300">Activo</span>
                                            ) : (
                                                <span className="text-slate-400">Inactivo</span>
                                            )}
                                        </td>
                                        <td className="py-2 pr-4 text-slate-400">{formatDate(u.fecha_registro)}</td>
                                    </tr>
                                ))}
                                {!usuarios.length ? (
                                    <tr>
                                        <td className="py-3 text-slate-400" colSpan={5}>
                                            Sin resultados
                                        </td>
                                    </tr>
                                ) : null}
                            </tbody>
                        </table>
                    </div>
                </section>

                <section id="pagos" className="card p-5">
                    <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
                        <div>
                            <h2 className="text-base font-semibold text-white">Pagos</h2>
                            <div className="text-xs text-slate-500 mt-1">Últimos 20</div>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                            <div>
                                <div className="text-xs text-slate-500 mb-1">Desde</div>
                                <input className="input" type="date" value={pagosDesde} onChange={(e) => setPagosDesde(e.target.value)} />
                            </div>
                            <div>
                                <div className="text-xs text-slate-500 mb-1">Hasta</div>
                                <input className="input" type="date" value={pagosHasta} onChange={(e) => setPagosHasta(e.target.value)} />
                            </div>
                            <div>
                                <div className="text-xs text-slate-500 mb-1">Método</div>
                                <select className="input" value={metodoId || ''} onChange={(e) => setMetodoId(Number(e.target.value) || null)}>
                                    <option value="">Todos</option>
                                    {metodosPago.map((m) => (
                                        <option key={String(m.id)} value={String(m.id)}>
                                            {m.nombre}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <Link
                                className="btn-secondary flex items-center gap-2"
                                href={`/api/export/pagos/csv?desde=${encodeURIComponent(pagosDesde || '')}&hasta=${encodeURIComponent(pagosHasta || '')}`}
                            >
                                <Download className="w-4 h-4" />
                                CSV
                            </Link>
                        </div>
                    </div>
                    <div className="mt-4 overflow-x-auto">
                        <table className="min-w-full text-sm">
                            <thead>
                                <tr className="text-slate-500">
                                    <th className="text-left font-medium py-2 pr-4">Fecha</th>
                                    <th className="text-left font-medium py-2 pr-4">Usuario</th>
                                    <th className="text-left font-medium py-2 pr-4">Monto</th>
                                    <th className="text-left font-medium py-2 pr-4">Método</th>
                                </tr>
                            </thead>
                            <tbody>
                                {pagos.map((p) => (
                                    <tr key={String(p.id)} className="border-t border-slate-800/60">
                                        <td className="py-2 pr-4 text-slate-400">{formatDate(p.fecha_pago)}</td>
                                        <td className="py-2 pr-4 text-slate-200">{p.usuario_nombre || `#${p.usuario_id}`}</td>
                                        <td className="py-2 pr-4 text-slate-200">{formatCurrency(Number(p.monto || 0))}</td>
                                        <td className="py-2 pr-4 text-slate-400">{p.metodo_pago || '-'}</td>
                                    </tr>
                                ))}
                                {!pagos.length ? (
                                    <tr>
                                        <td className="py-3 text-slate-400" colSpan={4}>
                                            Sin pagos
                                        </td>
                                    </tr>
                                ) : null}
                            </tbody>
                        </table>
                    </div>
                </section>

                <section id="whatsapp" className="card p-5">
                    <div className="flex items-center justify-between gap-3">
                        <div>
                            <h2 className="text-base font-semibold text-white">WhatsApp</h2>
                            <div className="text-xs text-slate-500 mt-1">Operación y cola del último período</div>
                        </div>
                        <Link href="/gestion/whatsapp" className="btn-secondary flex items-center gap-2">
                            <MessageSquare className="w-4 h-4" />
                            Abrir panel
                        </Link>
                    </div>
                    <div className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
                        <ChartCard title="Volumen" subtitle="Total y últimos 30 días" className="lg:col-span-1">
                            <div className="space-y-2">
                                <div className="flex items-center justify-between text-sm">
                                    <span className="text-slate-400">Total</span>
                                    <span className="text-slate-200 font-semibold">{formatNumber(Number(waStats?.total || 0))}</span>
                                </div>
                                <div className="flex items-center justify-between text-sm">
                                    <span className="text-slate-400">Últimos 30d</span>
                                    <span className="text-slate-200 font-semibold">{formatNumber(Number(waStats?.ultimo_mes || 0))}</span>
                                </div>
                                <div className="flex items-center justify-between text-sm">
                                    <span className="text-slate-400">Pendientes/errores</span>
                                    <span className="text-slate-200 font-semibold">{formatNumber(waPendientes.length)}</span>
                                </div>
                            </div>
                        </ChartCard>
                        <ChartCard title="Por tipo" subtitle="Distribución por acción" className="lg:col-span-1">
                            <div className="space-y-2">
                                {Object.entries(waStats?.por_tipo || {})
                                    .slice(0, 8)
                                    .map(([k, v]) => (
                                        <div key={k} className="flex items-center justify-between text-sm">
                                            <span className="text-slate-400">{k}</span>
                                            <span className="text-slate-200 font-semibold">{formatNumber(Number(v || 0))}</span>
                                        </div>
                                    ))}
                                {!Object.keys(waStats?.por_tipo || {}).length ? <div className="text-sm text-slate-400">Sin datos</div> : null}
                            </div>
                        </ChartCard>
                        <ChartCard title="Cola (top)" subtitle="Mensajes con problemas recientes" className="lg:col-span-1">
                            <div className="space-y-2">
                                {waPendientes.slice(0, 8).map((m, idx) => (
                                    <div key={idx} className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
                                        <div className="flex items-center justify-between gap-2">
                                            <div className="text-sm text-slate-200">{String(m?.tipo || m?.type || 'mensaje')}</div>
                                            <div className="text-xs text-slate-500">{String(m?.estado || m?.status || '')}</div>
                                        </div>
                                        <div className="text-xs text-slate-500 mt-1 truncate">{String(m?.telefono || m?.phone || '')}</div>
                                    </div>
                                ))}
                                {!waPendientes.length ? <div className="text-sm text-slate-400">Sin pendientes</div> : null}
                            </div>
                        </ChartCard>
                    </div>
                </section>

                <section className="card p-5">
                    <div className="flex items-center justify-between gap-3">
                        <div>
                            <h2 className="text-base font-semibold text-white">Asistencias (últimos 7 días)</h2>
                            <div className="text-xs text-slate-500 mt-1">Últimos 20 check-ins</div>
                        </div>
                        <Link className="btn-secondary flex items-center gap-2" href="/api/export/asistencias/csv">
                            <Download className="w-4 h-4" />
                            CSV
                        </Link>
                    </div>
                    <div className="mt-4 overflow-x-auto">
                        <table className="min-w-full text-sm">
                            <thead>
                                <tr className="text-slate-500">
                                    <th className="text-left font-medium py-2 pr-4">Fecha</th>
                                    <th className="text-left font-medium py-2 pr-4">Usuario</th>
                                    <th className="text-left font-medium py-2 pr-4">Tipo</th>
                                </tr>
                            </thead>
                            <tbody>
                                {asistencias.map((a) => (
                                    <tr key={String(a.id)} className="border-t border-slate-800/60">
                                        <td className="py-2 pr-4 text-slate-400">{formatDate(a.fecha)}</td>
                                        <td className="py-2 pr-4 text-slate-200">{a.usuario_nombre || `#${a.usuario_id}`}</td>
                                        <td className="py-2 pr-4 text-slate-400">{a.tipo || '-'}</td>
                                    </tr>
                                ))}
                                {!asistencias.length ? (
                                    <tr>
                                        <td className="py-3 text-slate-400" colSpan={3}>
                                            Sin asistencias recientes
                                        </td>
                                    </tr>
                                ) : null}
                            </tbody>
                        </table>
                    </div>
                </section>

                <section className="card p-5">
                    <div className="flex items-center justify-between gap-3">
                        <div>
                            <h2 className="text-base font-semibold text-white">Accesos extra</h2>
                            <div className="text-xs text-slate-500 mt-1">Incluye Meta Review (no visible en Gestión)</div>
                        </div>
                        <div className="flex items-center gap-2">
                            <Link href="/dashboard/meta-review" className="btn-secondary flex items-center gap-2">
                                <CalendarDays className="w-4 h-4" />
                                Meta Review
                            </Link>
                        </div>
                    </div>
                </section>

                <ConfirmModal
                    isOpen={Boolean(toggleConfirm?.open)}
                    onClose={() => setToggleConfirm(null)}
                    title="Cambiar política de asistencias"
                    message={
                        toggleConfirm?.next
                            ? 'Se habilitarán múltiples asistencias por día por usuario. Esto afecta gestión, QR personal y estación QR.'
                            : 'Se limitará a 1 asistencia por día por usuario. Si hoy ya tiene asistencia, los próximos check-ins del día quedarán “ya registrado”.'
                    }
                    confirmText="Aplicar"
                    cancelText="Cancelar"
                    variant="warning"
                    isLoading={savingGymSettings}
                    onConfirm={async () => {
                        if (!toggleConfirm) return;
                        setSavingGymSettings(true);
                        try {
                            const res = await api.updateOwnerGymSettings({ attendance_allow_multiple_per_day: toggleConfirm.next });
                            if (res.ok && res.data?.ok) {
                                setOwnerGymSettings({ attendance_allow_multiple_per_day: toggleConfirm.next });
                                setToggleConfirm(null);
                            }
                        } finally {
                            setSavingGymSettings(false);
                        }
                    }}
                />
            </div>
        </div>
    );
}
