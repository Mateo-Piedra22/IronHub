'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
    ScanLine,
    Calendar,
    Clock,
    Users,
    RefreshCw,
    QrCode,
    Copy,
    ExternalLink,
    Check,
    Monitor,
} from 'lucide-react';
import {
    Button,
    DataTable,
    useToast,
    Input,
    type Column,
} from '@/components/ui';
import { api, type Asistencia } from '@/lib/api';
import { formatDate, formatTime, cn } from '@/lib/utils';

export default function AsistenciasPage() {
    const { success, error } = useToast();

    // State
    const [asistencias, setAsistencias] = useState<Asistencia[]>([]);
    const [loading, setLoading] = useState(true);
    const [filterDesde, setFilterDesde] = useState('');
    const [filterHasta, setFilterHasta] = useState('');

    // Station state
    const [stationKey, setStationKey] = useState<string | null>(null);
    const [stationUrl, setStationUrl] = useState<string | null>(null);
    const [loadingStation, setLoadingStation] = useState(true);
    const [copied, setCopied] = useState(false);

    // Stats
    const [todayCount, setTodayCount] = useState(0);

    // Load station key on mount
    useEffect(() => {
        const loadStationKey = async () => {
            setLoadingStation(true);
            try {
                const res = await api.getStationKey();
                if (res.ok && res.data) {
                    setStationKey(res.data.station_key);
                    setStationUrl(res.data.station_url);
                }
            } catch {
                // Station key not available
            } finally {
                setLoadingStation(false);
            }
        };
        loadStationKey();
    }, []);

    // Load
    const loadAsistencias = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.getAsistencias({
                desde: filterDesde || undefined,
                hasta: filterHasta || undefined,
                limit: 100,
            });
            if (res.ok && res.data) {
                setAsistencias(res.data.asistencias);

                // Count today
                const today = new Date().toISOString().split('T')[0];
                const todayItems = res.data.asistencias.filter((a) => a.fecha === today);
                setTodayCount(todayItems.length);
            }
        } catch {
            error('Error al cargar asistencias');
        } finally {
            setLoading(false);
        }
    }, [filterDesde, filterHasta, error]);

    useEffect(() => {
        loadAsistencias();
    }, [loadAsistencias]);

    // Copy URL handler
    const handleCopyUrl = async () => {
        if (!stationUrl) return;
        try {
            await navigator.clipboard.writeText(stationUrl);
            setCopied(true);
            success('URL copiada al portapapeles');
            setTimeout(() => setCopied(false), 2000);
        } catch {
            error('No se pudo copiar');
        }
    };

    // Open station handler
    const handleOpenStation = () => {
        if (stationKey) {
            window.open(`/station/${stationKey}`, '_blank');
        }
    };

    // Table columns
    const columns: Column<Asistencia>[] = [
        {
            key: 'fecha',
            header: 'Fecha',
            sortable: true,
            render: (row) => (
                <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-slate-500" />
                    <span className="font-medium text-white">{formatDate(row.fecha)}</span>
                </div>
            ),
        },
        {
            key: 'hora',
            header: 'Hora',
            render: (row) => (
                <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-slate-500" />
                    <span>{row.hora ? formatTime(row.hora) : '-'}</span>
                </div>
            ),
        },
        {
            key: 'usuario_nombre',
            header: 'Usuario',
            sortable: true,
            render: (row) => (
                <span className="font-medium">{row.usuario_nombre || `ID: ${row.usuario_id}`}</span>
            ),
        },
    ];

    // Group by date for summary
    const byDate: Record<string, number> = {};
    asistencias.forEach((a) => {
        byDate[a.fecha] = (byDate[a.fecha] || 0) + 1;
    });

    return (
        <div className="space-y-6">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
            >
                <div>
                    <h1 className="text-2xl font-display font-bold text-white">Asistencias</h1>
                    <p className="text-slate-400 mt-1">
                        Registro de check-ins de los socios
                    </p>
                </div>
                <Button
                    leftIcon={<ScanLine className="w-4 h-4" />}
                    onClick={() => window.open('/checkin', '_blank')}
                >
                    Abrir Check-in
                </Button>
            </motion.div>

            {/* Station QR Card */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05 }}
                className="card p-6 border border-primary-500/30 bg-gradient-to-br from-primary-500/10 to-transparent"
            >
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                    <div className="flex items-start gap-4">
                        <div className="w-14 h-14 rounded-xl bg-primary-500/20 flex items-center justify-center flex-shrink-0">
                            <Monitor className="w-7 h-7 text-primary-400" />
                        </div>
                        <div>
                            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                                <QrCode className="w-5 h-5" />
                                Pantalla de Estación QR
                            </h2>
                            <p className="text-slate-400 text-sm mt-1">
                                Abrí esta URL en una pantalla del gimnasio. Los socios escanean el QR con su celular para registrar asistencia.
                            </p>
                            {stationUrl && !loadingStation && (
                                <div className="mt-3 flex items-center gap-2 flex-wrap">
                                    <code className="px-3 py-1.5 rounded-lg bg-slate-900/70 text-primary-300 text-sm font-mono border border-slate-700">
                                        {stationUrl}
                                    </code>
                                    <button
                                        onClick={handleCopyUrl}
                                        className="p-2 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
                                        title="Copiar URL"
                                    >
                                        {copied ? <Check className="w-4 h-4 text-success-400" /> : <Copy className="w-4 h-4" />}
                                    </button>
                                </div>
                            )}
                            {loadingStation && (
                                <div className="mt-3 text-sm text-slate-500">Cargando URL...</div>
                            )}
                        </div>
                    </div>
                    <div className="flex gap-2 lg:flex-shrink-0">
                        <Button
                            variant="primary"
                            leftIcon={<ExternalLink className="w-4 h-4" />}
                            onClick={handleOpenStation}
                            disabled={!stationKey || loadingStation}
                        >
                            Abrir Pantalla
                        </Button>
                    </div>
                </div>
            </motion.div>

            {/* Stats */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="grid grid-cols-2 md:grid-cols-4 gap-4"
            >
                <div className="card p-4">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-success-500/20 flex items-center justify-center">
                            <Users className="w-5 h-5 text-success-400" />
                        </div>
                        <div>
                            <div className="text-2xl font-display font-bold text-white">
                                {todayCount}
                            </div>
                            <div className="text-xs text-slate-500">Hoy</div>
                        </div>
                    </div>
                </div>
                <div className="card p-4">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-primary-500/20 flex items-center justify-center">
                            <Calendar className="w-5 h-5 text-primary-400" />
                        </div>
                        <div>
                            <div className="text-2xl font-display font-bold text-white">
                                {asistencias.length}
                            </div>
                            <div className="text-xs text-slate-500">Total mostrado</div>
                        </div>
                    </div>
                </div>
            </motion.div>

            {/* Filters */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
                className="card p-4"
            >
                <div className="flex flex-col sm:flex-row gap-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 flex-1">
                        <Input
                            label="Desde"
                            type="date"
                            value={filterDesde}
                            onChange={(e) => setFilterDesde(e.target.value)}
                        />
                        <Input
                            label="Hasta"
                            type="date"
                            value={filterHasta}
                            onChange={(e) => setFilterHasta(e.target.value)}
                        />
                    </div>
                    <div className="flex items-end gap-2">
                        <Button variant="ghost" onClick={loadAsistencias}>
                            <RefreshCw className="w-4 h-4" />
                        </Button>
                    </div>
                </div>
            </motion.div>

            {/* Table */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
            >
                <DataTable
                    data={asistencias}
                    columns={columns}
                    loading={loading}
                    emptyMessage="No se encontraron asistencias"
                />
            </motion.div>
        </div>
    );
}

