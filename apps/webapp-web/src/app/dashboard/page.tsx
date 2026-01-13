"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
    Users, UserCheck, UserX, DollarSign, Calendar, TrendingUp,
    AlertTriangle, Download, RefreshCw
} from "lucide-react";
import { Button, Card, CardContent, CardHeader, CardTitle } from "@/components/ui";
import { api } from "@/lib/api";

interface KPIs {
    total_activos: number;
    total_inactivos: number;
    ingresos_mes: number;
    asistencias_hoy: number;
    nuevos_30_dias: number;
}

interface ChartData {
    mes: string;
    total: number;
}

interface CohortData {
    cohort: string;
    total: number;
    retained: number;
    retention_rate: number;
}

interface DelinquencyAlert {
    usuario_id: number;
    usuario_nombre: string;
    ultimo_pago: string | null;
}

export default function DashboardPage() {
    const [kpis, setKpis] = useState<KPIs | null>(null);
    const [ingresos12m, setIngresos12m] = useState<ChartData[]>([]);
    const [nuevos12m, setNuevos12m] = useState<ChartData[]>([]);
    const [cohorts, setCohorts] = useState<CohortData[]>([]);
    const [alerts, setAlerts] = useState<DelinquencyAlert[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [kpisRes, ingresosRes, nuevosRes, cohortRes, alertsRes] = await Promise.all([
                api.getKpis(),
                api.getIngresos12m(),
                api.getNuevos12m(),
                api.getCohortRetencion6m(),
                api.getDelinquencyAlertsRecent(),
            ]);

            if (kpisRes.ok && kpisRes.data) {
                setKpis(kpisRes.data);
            }
            if (ingresosRes.ok && ingresosRes.data) {
                setIngresos12m(ingresosRes.data.data || []);
            }
            if (nuevosRes.ok && nuevosRes.data) {
                setNuevos12m(nuevosRes.data.data || []);
            }
            if (cohortRes.ok && cohortRes.data) {
                setCohorts(cohortRes.data.cohorts || []);
            }
            if (alertsRes.ok && alertsRes.data) {
                setAlerts(alertsRes.data.alerts || []);
            }
        } catch (error) {
            console.error("Error fetching dashboard data:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const formatCurrency = (value: number) => {
        return new Intl.NumberFormat("es-AR", {
            style: "currency",
            currency: "ARS",
            minimumFractionDigits: 0,
        }).format(value);
    };

    const formatMonth = (mes: string) => {
        const [year, month] = mes.split("-");
        const months = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
        return `${months[parseInt(month) - 1]} ${year.slice(2)}`;
    };

    const maxIngreso = Math.max(...ingresos12m.map(d => d.total), 1);
    const maxNuevos = Math.max(...nuevos12m.map(d => d.total), 1);

    const handleExport = async (type: "usuarios" | "pagos" | "asistencias") => {
        try {
            const result = await api.exportToCsv(type);
            if (result.ok && result.data) {
                const url = window.URL.createObjectURL(result.data);
                const a = document.createElement("a");
                a.href = url;
                a.download = `${type}_${new Date().toISOString().split("T")[0]}.csv`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            }
        } catch (error) {
            console.error(`Error exporting ${type}:`, error);
        }
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">Dashboard</h1>
                    <p className="text-muted-foreground">Resumen general del gimnasio</p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" onClick={fetchData} disabled={loading}>
                        <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
                        Actualizar
                    </Button>
                    <Button variant="outline" onClick={() => handleExport("usuarios")}>
                        <Download className="h-4 w-4 mr-2" />
                        Exportar Usuarios
                    </Button>
                </div>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0 }}>
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                                <UserCheck className="h-4 w-4 text-green-500" />
                                Activos
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{kpis?.total_activos ?? "-"}</div>
                        </CardContent>
                    </Card>
                </motion.div>

                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                                <UserX className="h-4 w-4 text-red-500" />
                                Inactivos
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{kpis?.total_inactivos ?? "-"}</div>
                        </CardContent>
                    </Card>
                </motion.div>

                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                                <DollarSign className="h-4 w-4 text-blue-500" />
                                Ingresos Mes
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">
                                {kpis ? formatCurrency(kpis.ingresos_mes) : "-"}
                            </div>
                        </CardContent>
                    </Card>
                </motion.div>

                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                                <Calendar className="h-4 w-4 text-purple-500" />
                                Asistencias Hoy
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{kpis?.asistencias_hoy ?? "-"}</div>
                        </CardContent>
                    </Card>
                </motion.div>

                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                                <TrendingUp className="h-4 w-4 text-emerald-500" />
                                Nuevos (30d)
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{kpis?.nuevos_30_dias ?? "-"}</div>
                        </CardContent>
                    </Card>
                </motion.div>
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Income Chart */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <DollarSign className="h-5 w-5" />
                            Ingresos últimos 12 meses
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="h-[200px] flex items-end gap-2">
                            {ingresos12m.length > 0 ? (
                                ingresos12m.map((d, i) => (
                                    <div key={d.mes} className="flex-1 flex flex-col items-center gap-1">
                                        <motion.div
                                            initial={{ height: 0 }}
                                            animate={{ height: `${(d.total / maxIngreso) * 160}px` }}
                                            transition={{ delay: i * 0.05 }}
                                            className="w-full bg-gradient-to-t from-blue-600 to-blue-400 rounded-t"
                                            title={formatCurrency(d.total)}
                                        />
                                        <span className="text-xs text-muted-foreground">{formatMonth(d.mes)}</span>
                                    </div>
                                ))
                            ) : (
                                <div className="flex-1 flex items-center justify-center text-muted-foreground">
                                    Sin datos
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>

                {/* New Users Chart */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Users className="h-5 w-5" />
                            Nuevos usuarios últimos 12 meses
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="h-[200px] flex items-end gap-2">
                            {nuevos12m.length > 0 ? (
                                nuevos12m.map((d, i) => (
                                    <div key={d.mes} className="flex-1 flex flex-col items-center gap-1">
                                        <motion.div
                                            initial={{ height: 0 }}
                                            animate={{ height: `${(d.total / maxNuevos) * 160}px` }}
                                            transition={{ delay: i * 0.05 }}
                                            className="w-full bg-gradient-to-t from-emerald-600 to-emerald-400 rounded-t"
                                            title={`${d.total} usuarios`}
                                        />
                                        <span className="text-xs text-muted-foreground">{formatMonth(d.mes)}</span>
                                    </div>
                                ))
                            ) : (
                                <div className="flex-1 flex items-center justify-center text-muted-foreground">
                                    Sin datos
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Cohort Retention & Alerts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Cohort Retention */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <TrendingUp className="h-5 w-5" />
                            Retención por Cohorte (6 meses)
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        {cohorts.length > 0 ? (
                            <div className="space-y-3">
                                {cohorts.map((c) => (
                                    <div key={c.cohort} className="flex items-center gap-3">
                                        <span className="w-16 text-sm text-muted-foreground">{formatMonth(c.cohort)}</span>
                                        <div className="flex-1 h-6 bg-muted rounded-full overflow-hidden">
                                            <motion.div
                                                initial={{ width: 0 }}
                                                animate={{ width: `${c.retention_rate}%` }}
                                                className="h-full bg-gradient-to-r from-green-500 to-emerald-400"
                                            />
                                        </div>
                                        <span className="w-16 text-sm font-medium text-right">{c.retention_rate}%</span>
                                        <span className="w-16 text-xs text-muted-foreground">{c.retained}/{c.total}</span>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="text-center text-muted-foreground py-8">Sin datos de cohortes</div>
                        )}
                    </CardContent>
                </Card>

                {/* Delinquency Alerts */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <AlertTriangle className="h-5 w-5 text-amber-500" />
                            Alertas de Morosidad Recientes
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        {alerts.length > 0 ? (
                            <div className="space-y-2 max-h-[250px] overflow-y-auto">
                                {alerts.map((a) => (
                                    <div
                                        key={a.usuario_id}
                                        className="flex items-center justify-between p-2 rounded-lg bg-muted/50"
                                    >
                                        <span className="font-medium">{a.usuario_nombre}</span>
                                        <span className="text-sm text-muted-foreground">
                                            {a.ultimo_pago ? `Último pago: ${new Date(a.ultimo_pago).toLocaleDateString("es-AR")}` : "Sin pagos"}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="text-center text-muted-foreground py-8">
                                Sin alertas de morosidad hoy
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Export Section */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Download className="h-5 w-5" />
                        Exportar Datos
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex flex-wrap gap-4">
                        <Button variant="outline" onClick={() => handleExport("usuarios")}>
                            <Users className="h-4 w-4 mr-2" />
                            Exportar Usuarios (CSV)
                        </Button>
                        <Button variant="outline" onClick={() => handleExport("pagos")}>
                            <DollarSign className="h-4 w-4 mr-2" />
                            Exportar Pagos (CSV)
                        </Button>
                        <Button variant="outline" onClick={() => handleExport("asistencias")}>
                            <Calendar className="h-4 w-4 mr-2" />
                            Exportar Asistencias (CSV)
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}

