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
    Trash2,
} from 'lucide-react';
import {
    Button,
    DataTable,
    useToast,
    Input,
    ConfirmModal,
    type Column,
} from '@/components/ui';
import { api, type Asistencia } from '@/lib/api';
import { formatDate, formatTime } from '@/lib/utils';

export default function AsistenciasPage() {
    const { success, error } = useToast();

    // State
    const [asistencias, setAsistencias] = useState<Asistencia[]>([]);
    const [loading, setLoading] = useState(true);
    const [filterDesde, setFilterDesde] = useState('');
    const [filterHasta, setFilterHasta] = useState('');
    const [filterQ, setFilterQ] = useState('');
    const [page, setPage] = useState(1);
    const pageSize = 50;
    const [total, setTotal] = useState(0);
    const [deleteState, setDeleteState] = useState<{ open: boolean; asistencia_id?: number }>({ open: false });
    const [deleting, setDeleting] = useState(false);
    const [allowMultipleAsistenciasDia, setAllowMultipleAsistenciasDia] = useState(false);

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

    useEffect(() => {
        (async () => {
            try {
                const res = await api.getGymData();
                if (res.ok && res.data) {
                    setAllowMultipleAsistenciasDia(Boolean(res.data.attendance_allow_multiple_per_day));
                }
            } catch {
            }
        })();
    }, []);

    // Load
    const loadAsistencias = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.getAsistencias({
                desde: filterDesde || undefined,
                hasta: filterHasta || undefined,
                q: filterQ || undefined,
                page,
                limit: pageSize,
            });
            if (res.ok && res.data) {
                setAsistencias(res.data.asistencias);
                setTotal(Number(res.data.total || 0));

                const today = new Date().toISOString().split('T')[0];
                const todayRes = await api.getAsistencias({ desde: today, hasta: today, limit: 1 });
                if (todayRes.ok && todayRes.data) {
                    setTodayCount(Number(todayRes.data.total || todayRes.data.asistencias?.length || 0));
                }
            }
        } catch {
            error('Error al cargar asistencias');
        } finally {
            setLoading(false);
        }
    }, [filterDesde, filterHasta, filterQ, page, error]);

    useEffect(() => {
        loadAsistencias();
    }, [loadAsistencias]);

    useEffect(() => {
        const handler = () => {
            setPage(1);
            loadAsistencias();
        };
        window.addEventListener('ironhub:sucursal-changed', handler);
        return () => window.removeEventListener('ironhub:sucursal-changed', handler);
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
        {
            key: 'usuario_dni',
            header: 'DNI',
            render: (row) => <span className="text-slate-400">{row.usuario_dni || '-'}</span>,
        },
        {
            key: 'acciones',
            header: '',
            render: (row) => (
                <button
                    onClick={() => setDeleteState({ open: true, asistencia_id: row.id })}
                    className="p-2 rounded-lg bg-slate-800 text-slate-300 hover:text-white"
                    title="Eliminar"
                >
                    <Trash2 className="w-4 h-4" />
                </button>
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
                <div className="text-sm text-slate-400">
                    Modo:{' '}
                    <span className="text-slate-200 font-medium">
                        {allowMultipleAsistenciasDia ? 'Múltiples por día' : '1 por día'}
                    </span>
                </div>
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
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 flex-1">
                        <Input
                            label="Desde"
                            type="date"
                            value={filterDesde}
                            onChange={(e) => {
                                setPage(1);
                                setFilterDesde(e.target.value);
                            }}
                        />
                        <Input
                            label="Hasta"
                            type="date"
                            value={filterHasta}
                            onChange={(e) => {
                                setPage(1);
                                setFilterHasta(e.target.value);
                            }}
                        />
                        <Input
                            label="Buscar"
                            value={filterQ}
                            onChange={(e) => {
                                setPage(1);
                                setFilterQ(e.target.value);
                            }}
                            placeholder="Nombre o DNI"
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
                <div className="flex items-center justify-between mb-3">
                    <div className="text-sm text-slate-400">
                        Total: <span className="text-slate-200 font-medium">{total}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button variant="ghost" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
                            Anterior
                        </Button>
                        <div className="text-xs text-slate-500">Página {page}</div>
                        <Button
                            variant="ghost"
                            onClick={() => setPage((p) => p + 1)}
                            disabled={page * pageSize >= total}
                        >
                            Siguiente
                        </Button>
                    </div>
                </div>
                <DataTable
                    data={asistencias}
                    columns={columns}
                    loading={loading}
                    emptyMessage="No se encontraron asistencias"
                />
            </motion.div>

            <ConfirmModal
                isOpen={deleteState.open}
                onClose={() => setDeleteState({ open: false })}
                title="Eliminar asistencia"
                message="Esta acción no se puede deshacer."
                confirmText="Eliminar"
                cancelText="Cancelar"
                variant="danger"
                isLoading={deleting}
                onConfirm={async () => {
                    if (!deleteState.asistencia_id) return;
                    setDeleting(true);
                    try {
                        const res = await api.deleteAsistenciaById(deleteState.asistencia_id);
                        if (res.ok) {
                            success('Asistencia eliminada');
                            setDeleteState({ open: false });
                            loadAsistencias();
                        } else {
                            error(res.error || 'Error al eliminar asistencia');
                        }
                    } finally {
                        setDeleting(false);
                    }
                }}
            />
        </div>
    );
}

