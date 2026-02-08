'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { BarChart3, Loader2, RefreshCw } from 'lucide-react';
import { Button, useToast } from '@/components/ui';
import { api } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { BarChart, ChartCard, HeatmapTable, LineChart } from '@/components/owner-dashboard/charts';

type Kpis = {
    total_activos: number;
    total_inactivos: number;
    ingresos_mes: number;
    asistencias_hoy: number;
    nuevos_30_dias: number;
};

export default function GestionReportesPage() {
    const { success, error } = useToast();
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);

    const [kpis, setKpis] = useState<Kpis | null>(null);
    const [ingresos12m, setIngresos12m] = useState<Array<{ mes: string; total: number }>>([]);
    const [nuevos12m, setNuevos12m] = useState<Array<{ mes: string; total: number }>>([]);
    const [cohortHeatmap, setCohortHeatmap] = useState<Array<{ cohort: string; values: number[] }>>([]);

    const load = useCallback(async (opts?: { silent?: boolean }) => {
        const silent = Boolean(opts?.silent);
        if (!silent) setLoading(true);
        try {
            const [kpisRes, ingresosRes, nuevosRes, cohortRes] = await Promise.all([
                api.getKpis(),
                api.getIngresos12m(),
                api.getNuevos12m(),
                api.getCohortRetencionHeatmap(),
            ]);

            if (kpisRes.ok && kpisRes.data) {
                setKpis({
                    total_activos: Number(kpisRes.data.total_activos || 0),
                    total_inactivos: Number(kpisRes.data.total_inactivos || 0),
                    ingresos_mes: Number(kpisRes.data.ingresos_mes || 0),
                    asistencias_hoy: Number(kpisRes.data.asistencias_hoy || 0),
                    nuevos_30_dias: Number(kpisRes.data.nuevos_30_dias || 0),
                });
            } else {
                setKpis(null);
            }

            if (ingresosRes.ok && ingresosRes.data?.data) {
                setIngresos12m((ingresosRes.data.data || []).map((x) => ({ mes: String(x.mes || ''), total: Number(x.total || 0) })));
            } else {
                setIngresos12m([]);
            }

            if (nuevosRes.ok && nuevosRes.data?.data) {
                setNuevos12m((nuevosRes.data.data || []).map((x) => ({ mes: String(x.mes || ''), total: Number(x.total || 0) })));
            } else {
                setNuevos12m([]);
            }

            const cohortsRaw = cohortRes.ok ? cohortRes.data?.cohorts : null;
            if (Array.isArray(cohortsRaw)) {
                const safe = cohortsRaw
                    .map((c) => {
                        const rec = c as Record<string, unknown>;
                        const cohort = String(rec.cohort || rec.cohorte || '—');
                        const values = Array.isArray(rec.values) ? rec.values.map((v) => Number(v)) : [];
                        return { cohort, values };
                    })
                    .filter((c) => c.values.length > 0);
                setCohortHeatmap(safe);
            } else {
                setCohortHeatmap([]);
            }
        } catch {
            if (!silent) error('No se pudieron cargar reportes');
            setKpis(null);
            setIngresos12m([]);
            setNuevos12m([]);
            setCohortHeatmap([]);
        } finally {
            if (!silent) setLoading(false);
        }
    }, [error]);

    useEffect(() => {
        void load();
    }, [load]);

    useEffect(() => {
        const handler: EventListener = () => {
            void load({ silent: true });
        };
        window.addEventListener('ironhub:sucursal-changed', handler);
        return () => window.removeEventListener('ironhub:sucursal-changed', handler);
    }, [load]);

    const ingresosSerie = useMemo(() => ingresos12m.map((x) => Number(x.total || 0)), [ingresos12m]);
    const nuevosSerie = useMemo(() => nuevos12m.map((x) => Number(x.total || 0)), [nuevos12m]);
    const meses12m = useMemo(() => ingresos12m.map((x) => x.mes).filter(Boolean), [ingresos12m]);

    const header = (
        <div className="flex items-start justify-between gap-4">
            <div>
                <div className="text-white font-semibold text-lg flex items-center gap-2">
                    <BarChart3 className="w-5 h-5" />
                    Reportes
                </div>
                <div className="text-sm text-slate-400 mt-1">KPIs y métricas de la sucursal seleccionada</div>
            </div>
            <Button
                variant="secondary"
                size="sm"
                isLoading={refreshing}
                onClick={async () => {
                    setRefreshing(true);
                    try {
                        await load({ silent: true });
                        success('Actualizado');
                    } finally {
                        setRefreshing(false);
                    }
                }}
            >
                <RefreshCw className="w-4 h-4" />
                Actualizar
            </Button>
        </div>
    );

    if (loading) {
        return (
            <div className="space-y-4">
                {header}
                <div className="card p-6 flex items-center gap-2 text-slate-300">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Cargando…
                </div>
            </div>
        );
    }

    if (!kpis) {
        return (
            <div className="space-y-4">
                {header}
                <div className="card p-6 text-slate-300">
                    No hay datos disponibles o no tenés permisos para ver reportes.
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {header}

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3">
                <div className="card p-4">
                    <div className="text-xs text-slate-500">Activos</div>
                    <div className="text-2xl font-semibold text-white mt-1">{kpis.total_activos}</div>
                </div>
                <div className="card p-4">
                    <div className="text-xs text-slate-500">Inactivos</div>
                    <div className="text-2xl font-semibold text-white mt-1">{kpis.total_inactivos}</div>
                </div>
                <div className="card p-4">
                    <div className="text-xs text-slate-500">Ingresos (mes)</div>
                    <div className="text-2xl font-semibold text-white mt-1">{formatCurrency(kpis.ingresos_mes)}</div>
                </div>
                <div className="card p-4">
                    <div className="text-xs text-slate-500">Asistencias (hoy)</div>
                    <div className="text-2xl font-semibold text-white mt-1">{kpis.asistencias_hoy}</div>
                </div>
                <div className="card p-4">
                    <div className="text-xs text-slate-500">Nuevos (30 días)</div>
                    <div className="text-2xl font-semibold text-white mt-1">{kpis.nuevos_30_dias}</div>
                </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                <ChartCard
                    title="Ingresos últimos 12 meses"
                    subtitle={meses12m.length ? meses12m.join(' · ') : undefined}
                >
                    {ingresosSerie.length ? <LineChart data={ingresosSerie} /> : <div className="text-sm text-slate-500">Sin datos</div>}
                </ChartCard>
                <ChartCard title="Nuevos últimos 12 meses">
                    {nuevosSerie.length ? <BarChart values={nuevosSerie} /> : <div className="text-sm text-slate-500">Sin datos</div>}
                </ChartCard>
            </div>

            <ChartCard title="Retención (heatmap cohortes)">
                {cohortHeatmap.length ? <HeatmapTable cohorts={cohortHeatmap} /> : <div className="text-sm text-slate-500">Sin datos</div>}
            </ChartCard>
        </div>
    );
}

