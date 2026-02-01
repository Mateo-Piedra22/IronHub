'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { AlertTriangle, UploadCloud, Download, RefreshCw, XCircle, Play, CheckCircle2 } from 'lucide-react';
import { Button, DataTable, Input, Select, useToast, type Column } from '@/components/ui';
import { api, type BulkJob, type BulkPreviewRow, type TipoCuota } from '@/lib/api';
import { cn } from '@/lib/utils';

type RowView = {
    id: string;
    row_index: number;
    data: Record<string, any>;
    errors: string[];
    warnings: string[];
    is_valid?: boolean;
    applied?: boolean;
    result?: any;
};

const KIND = 'usuarios_import';

function downloadBlob(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function DashboardAccionesMasivasPage() {
    const { toast } = useToast();
    const fileRef = useRef<HTMLInputElement | null>(null);
    const [tipos, setTipos] = useState<TipoCuota[]>([]);
    const [allowed, setAllowed] = useState<{ bulkModule: boolean; usuariosImport: boolean } | null>(null);
    const [job, setJob] = useState<BulkJob | null>(null);
    const [rows, setRows] = useState<RowView[]>([]);
    const [loading, setLoading] = useState(false);
    const [running, setRunning] = useState(false);
    const [confirming, setConfirming] = useState(false);
    const [polling, setPolling] = useState(false);
    const [dirtyRows, setDirtyRows] = useState<Record<number, boolean>>({});

    useEffect(() => {
        (async () => {
            try {
                try {
                    const b = await api.getBootstrap('auto');
                    const modules = (b.ok ? (b.data?.flags as any)?.modules : null) as Record<string, boolean> | null;
                    const features = (b.ok ? (b.data?.flags as any)?.features : null) as any;
                    const bulkModule = !!modules && modules['bulk_actions'] !== false;
                    const usuariosImport = bulkModule && !!features?.bulk_actions && features.bulk_actions['usuarios_import'] !== false;
                    setAllowed({ bulkModule, usuariosImport });
                } catch {
                    setAllowed({ bulkModule: false, usuariosImport: false });
                }
                const res = await api.getTiposCuota();
                if (res.ok && res.data?.tipos) setTipos(res.data.tipos || []);
            } catch {
                setTipos([]);
            }
        })();
    }, []);

    const tipoOptions = useMemo(() => {
        const items = (tipos || []).map((t) => ({ value: String(t.id), label: String(t.nombre) }));
        items.unshift({ value: '', label: 'Sin tipo de cuota' });
        return items;
    }, [tipos]);

    const canConfirm = useMemo(() => {
        if (!job) return false;
        return job.rows_invalid === 0 && (job.status === 'draft' || job.status === 'validated');
    }, [job]);

    const canRun = useMemo(() => {
        if (!job) return false;
        return job.status === 'confirmed';
    }, [job]);

    const dangerDisabled = useMemo(() => {
        if (!allowed) return true;
        return !(allowed.bulkModule && allowed.usuariosImport);
    }, [allowed]);

    const loadJob = async (jobId: number) => {
        const r = await api.bulkGetJob(jobId);
        if (!r.ok || !r.data?.ok) throw new Error(r.error || 'No se pudo cargar job');
        setJob(r.data.job);
        const mapped: RowView[] = (r.data.rows || []).map((it) => ({
            id: String(it.row_index),
            row_index: it.row_index,
            data: it.data || {},
            errors: (it.errors || []) as string[],
            warnings: (it.warnings || []) as string[],
            is_valid: it.is_valid,
            applied: it.applied,
            result: it.result,
        }));
        setRows(mapped);
    };

    const resetAll = () => {
        setJob(null);
        setRows([]);
        setDirtyRows({});
        setRunning(false);
        setConfirming(false);
        setPolling(false);
        if (fileRef.current) fileRef.current.value = '';
    };

    const downloadTemplate = async (format: 'csv' | 'xlsx') => {
        const res = await api.downloadBulkTemplate(KIND, format);
        if (!res.ok || !res.data) {
            toast({ title: 'No se pudo descargar', description: res.error || 'Error', variant: 'error' });
            return;
        }
        downloadBlob(res.data, `${KIND}.${format}`);
    };

    const onPickFile = async (f: File | null) => {
        if (!f) return;
        resetAll();
        setLoading(true);
        try {
            const res = await api.bulkPreview(KIND, f);
            if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo previsualizar');
            setJob(res.data.job);
            const mapped: RowView[] = (res.data.preview.rows || []).map((it) => ({
                id: String(it.row_index),
                row_index: it.row_index,
                data: it.data || {},
                errors: (it.errors || []) as string[],
                warnings: (it.warnings || []) as string[],
            }));
            setRows(mapped);
            toast({ title: 'Archivo cargado', description: `Filas detectadas: ${res.data.job.rows_total}`, variant: 'success' });
        } catch (e) {
            toast({
                title: 'No se pudo cargar',
                description: e instanceof Error ? e.message : 'Error inesperado',
                variant: 'error',
            });
        } finally {
            setLoading(false);
        }
    };

    const updateLocal = (rowIndex: number, patch: Record<string, any>) => {
        setRows((prev) =>
            prev.map((r) => (r.row_index === rowIndex ? { ...r, data: { ...(r.data || {}), ...patch } } : r))
        );
        setDirtyRows((p) => ({ ...p, [rowIndex]: true }));
    };

    const persistRow = async (rowIndex: number) => {
        if (!job) return;
        if (!dirtyRows[rowIndex]) return;
        const row = rows.find((r) => r.row_index === rowIndex);
        if (!row) return;
        try {
            const res = await api.bulkUpdateRow(job.id, rowIndex, row.data || {});
            if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo guardar fila');
            setJob(res.data.job);
            setRows((prev) =>
                prev.map((r) =>
                    r.row_index === rowIndex
                        ? {
                            ...r,
                            data: res.data?.data ?? r.data,
                            errors: res.data?.errors || [],
                            warnings: res.data?.warnings || [],
                        }
                        : r
                )
            );
            setDirtyRows((p) => {
                const copy = { ...p };
                delete copy[rowIndex];
                return copy;
            });
        } catch (e) {
            toast({ title: 'Error al guardar fila', description: e instanceof Error ? e.message : 'Error', variant: 'error' });
        }
    };

    const confirmJob = async () => {
        if (!job) return;
        setConfirming(true);
        try {
            const res = await api.bulkConfirm(job.id);
            if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo confirmar');
            setJob(res.data.job);
            toast({ title: 'Confirmado', description: 'Listo para ejecutar', variant: 'success' });
        } catch (e) {
            toast({ title: 'No se pudo confirmar', description: e instanceof Error ? e.message : 'Error', variant: 'error' });
        } finally {
            setConfirming(false);
        }
    };

    const runJob = async () => {
        if (!job) return;
        setRunning(true);
        try {
            const res = await api.bulkRun(job.id, job.rows_total);
            if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo ejecutar');
            setJob(res.data.job);
            toast({ title: 'Ejecutando', description: 'Procesando en background', variant: 'success' });
        } catch (e) {
            toast({ title: 'No se pudo ejecutar', description: e instanceof Error ? e.message : 'Error', variant: 'error' });
        } finally {
            setRunning(false);
        }
    };

    const cancelJob = async () => {
        if (!job) return;
        try {
            const res = await api.bulkCancel(job.id);
            if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo cancelar');
            setJob(res.data.job);
            toast({ title: 'Cancelado', description: 'Job cancelado', variant: 'success' });
        } catch (e) {
            toast({ title: 'No se pudo cancelar', description: e instanceof Error ? e.message : 'Error', variant: 'error' });
        }
    };

    useEffect(() => {
        if (!job) return;
        if (!['running', 'confirmed'].includes(job.status)) return;
        if (polling) return;
        setPolling(true);
        const t = setInterval(() => {
            loadJob(job.id).catch(() => {});
        }, 1500);
        return () => {
            clearInterval(t);
            setPolling(false);
        };
    }, [job?.id, job?.status]);

    const columns = useMemo<Column<RowView>[]>(() => {
        return [
            { key: 'row_index', header: '#', width: '72px', render: (r) => <span className="font-mono text-xs text-slate-400">{r.row_index + 1}</span> },
            {
                key: 'nombre',
                header: 'Nombre',
                render: (r) => (
                    <Input
                        value={String(r.data?.nombre || '')}
                        onChange={(e) => updateLocal(r.row_index, { nombre: e.target.value })}
                        onBlur={() => persistRow(r.row_index)}
                        className="px-3 py-2 rounded-lg text-sm"
                    />
                ),
            },
            {
                key: 'dni',
                header: 'DNI',
                width: '140px',
                render: (r) => (
                    <Input
                        value={String(r.data?.dni || '')}
                        onChange={(e) => updateLocal(r.row_index, { dni: e.target.value })}
                        onBlur={() => persistRow(r.row_index)}
                        className="px-3 py-2 rounded-lg text-sm"
                    />
                ),
            },
            {
                key: 'telefono',
                header: 'Teléfono',
                width: '160px',
                render: (r) => (
                    <Input
                        value={String(r.data?.telefono || '')}
                        onChange={(e) => updateLocal(r.row_index, { telefono: e.target.value })}
                        onBlur={() => persistRow(r.row_index)}
                        className="px-3 py-2 rounded-lg text-sm"
                    />
                ),
            },
            {
                key: 'tipo_cuota_id',
                header: 'Tipo de cuota',
                width: '220px',
                render: (r) => (
                    <Select
                        value={String(r.data?.tipo_cuota_id ?? '')}
                        options={tipoOptions}
                        onChange={(e) => {
                            const val = String(e.target.value || '');
                            updateLocal(r.row_index, { tipo_cuota_id: val ? Number(val) : null, tipo_cuota: null });
                        }}
                        onBlur={() => persistRow(r.row_index)}
                        className="px-3 py-2 rounded-lg text-sm"
                    />
                ),
            },
            {
                key: 'activo',
                header: 'Activo',
                width: '96px',
                align: 'center',
                render: (r) => (
                    <div className="flex justify-center">
                        <input
                            type="checkbox"
                            checked={!!r.data?.activo}
                            onChange={(e) => updateLocal(r.row_index, { activo: (e.target as HTMLInputElement).checked })}
                            onBlur={() => persistRow(r.row_index)}
                            className="w-5 h-5 rounded border-slate-700 bg-slate-900 text-primary-500 focus:ring-primary-500/50"
                        />
                    </div>
                ),
            },
            {
                key: 'notas',
                header: 'Notas',
                render: (r) => (
                    <Input
                        value={String(r.data?.notas || '')}
                        onChange={(e) => updateLocal(r.row_index, { notas: e.target.value })}
                        onBlur={() => persistRow(r.row_index)}
                        className="px-3 py-2 rounded-lg text-sm"
                    />
                ),
            },
            {
                key: 'estado',
                header: 'Estado',
                width: '220px',
                render: (r) => {
                    const errs = r.errors || [];
                    const warns = r.warnings || [];
                    const dirty = !!dirtyRows[r.row_index];
                    return (
                        <div className="space-y-1">
                            <div className="flex items-center gap-2">
                                {errs.length === 0 ? (
                                    <span className="inline-flex items-center gap-1 text-xs text-emerald-300">
                                        <CheckCircle2 className="w-3.5 h-3.5" />
                                        OK
                                    </span>
                                ) : (
                                    <span className="inline-flex items-center gap-1 text-xs text-amber-300">
                                        <AlertTriangle className="w-3.5 h-3.5" />
                                        {errs.length} error(es)
                                    </span>
                                )}
                                {dirty && <span className="text-[10px] text-slate-500">sin guardar</span>}
                            </div>
                            {errs.slice(0, 2).map((e, i) => (
                                <div key={i} className="text-[11px] text-amber-200/90">
                                    {e}
                                </div>
                            ))}
                            {warns.slice(0, 1).map((w, i) => (
                                <div key={i} className="text-[11px] text-slate-300/70">
                                    {w}
                                </div>
                            ))}
                        </div>
                    );
                },
            },
        ];
    }, [dirtyRows, rows, tipoOptions, tipos]);

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-primary-500/20 text-primary-300 flex items-center justify-center">
                    <UploadCloud className="w-5 h-5" />
                </div>
                <div className="flex-1">
                    <h1 className="text-xl font-semibold text-white">Acciones masivas</h1>
                    <p className="text-sm text-slate-400">Zona de alto riesgo. Validación + preview + confirmación manual obligatoria.</p>
                </div>
                <Button
                    variant="secondary"
                    leftIcon={<RefreshCw className="w-4 h-4" />}
                    onClick={() => job?.id && loadJob(job.id)}
                    disabled={!job?.id || loading}
                >
                    Refrescar
                </Button>
            </div>

            <div className="flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
                <AlertTriangle className="w-5 h-5 text-amber-300 mt-0.5" />
                <div className="text-sm text-amber-100/90 space-y-1">
                    <div>Recomendación: probá primero en un tenant de staging o con 1–5 filas.</div>
                    <div>Si hay errores, corregí en la tabla (edición in-situ) y asegurate que quede 0 inválidas.</div>
                </div>
            </div>
            {allowed && (!allowed.bulkModule || !allowed.usuariosImport) ? (
                <div className="rounded-2xl border border-slate-800/60 bg-slate-900/40 p-6">
                    <div className="text-sm text-slate-200 font-semibold">Acciones masivas deshabilitadas</div>
                    <div className="mt-1 text-sm text-slate-400">
                        Activá el módulo bulk_actions y la sub-feature usuarios_import desde Configuración.
                    </div>
                </div>
            ) : null}

            <div className="rounded-2xl border border-slate-800/60 bg-slate-900/40 p-4">
                <div className="flex flex-wrap items-center gap-2">
                    <input
                        ref={fileRef}
                        type="file"
                        accept=".csv,.xlsx"
                        className="hidden"
                        onChange={(e) => onPickFile(e.target.files?.[0] || null)}
                    />
                    <Button onClick={() => fileRef.current?.click()} leftIcon={<UploadCloud className="w-4 h-4" />} isLoading={loading} disabled={dangerDisabled}>
                        Cargar archivo (.csv o .xlsx)
                    </Button>
                    <Button variant="secondary" onClick={() => downloadTemplate('csv')} leftIcon={<Download className="w-4 h-4" />} disabled={dangerDisabled}>
                        Descargar template CSV
                    </Button>
                    <Button variant="secondary" onClick={() => downloadTemplate('xlsx')} leftIcon={<Download className="w-4 h-4" />} disabled={dangerDisabled}>
                        Descargar template XLSX
                    </Button>
                    <div className="flex-1" />
                    <Button variant="secondary" onClick={resetAll} leftIcon={<XCircle className="w-4 h-4" />} disabled={loading || running || confirming}>
                        Reset
                    </Button>
                </div>
                {job && (
                    <div className="mt-3 text-xs text-slate-400 flex flex-wrap gap-3">
                        <span>Job #{job.id}</span>
                        <span className="text-slate-500">•</span>
                        <span>Status: <span className="text-slate-200">{job.status}</span></span>
                        <span className="text-slate-500">•</span>
                        <span>Total: <span className="text-slate-200">{job.rows_total}</span></span>
                        <span>Válidas: <span className={cn('text-slate-200', job.rows_invalid === 0 ? 'text-emerald-300' : 'text-amber-300')}>{job.rows_valid}</span></span>
                        <span>Inválidas: <span className={cn('text-slate-200', job.rows_invalid === 0 ? 'text-emerald-300' : 'text-amber-300')}>{job.rows_invalid}</span></span>
                        <span>Aplicadas: <span className="text-slate-200">{job.applied_count}</span></span>
                        <span>Errores: <span className={cn('text-slate-200', job.error_count ? 'text-amber-300' : 'text-emerald-300')}>{job.error_count}</span></span>
                        {job.failure_reason && <span className="text-amber-200/90">• {job.failure_reason}</span>}
                    </div>
                )}
            </div>

            {rows.length > 0 && (
                <div className="space-y-3">
                    <DataTable<RowView>
                        data={rows}
                        columns={columns}
                        keyField="id"
                        compact
                        emptyMessage="Sin filas"
                    />

                    <div className="rounded-2xl border border-slate-800/60 bg-slate-900/40 p-4">
                        <div className="flex items-center gap-2">
                            <Button
                                variant="secondary"
                                disabled={!job?.id}
                                onClick={() => job?.id && loadJob(job.id)}
                                leftIcon={<RefreshCw className="w-4 h-4" />}
                            >
                                Recargar validación
                            </Button>
                            <div className="flex-1" />
                            <Button
                                disabled={dangerDisabled || !canConfirm || confirming}
                                isLoading={confirming}
                                onClick={confirmJob}
                                leftIcon={<CheckCircle2 className="w-4 h-4" />}
                            >
                                Confirmar (CONFIRMAR)
                            </Button>
                            <Button
                                disabled={dangerDisabled || !canRun || running}
                                isLoading={running}
                                onClick={runJob}
                                leftIcon={<Play className="w-4 h-4" />}
                            >
                                Ejecutar (EJECUTAR)
                            </Button>
                            <Button
                                variant="danger"
                                disabled={dangerDisabled || !job || ['completed', 'failed'].includes(job.status)}
                                onClick={cancelJob}
                                leftIcon={<XCircle className="w-4 h-4" />}
                            >
                                Cancelar
                            </Button>
                        </div>
                        <div className="mt-3 text-xs text-slate-500">
                            La ejecución corre en background y usa un lock global para evitar dos acciones masivas simultáneas.
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
