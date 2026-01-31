'use client';

import { useEffect, useMemo, useState } from 'react';
import { Building2, RefreshCw, AlertTriangle } from 'lucide-react';
import { Button, Input, Modal, ConfirmModal, useToast } from '@/components/ui';
import { api, type Sucursal } from '@/lib/api';
import { cn } from '@/lib/utils';

type EditState = {
    id: number;
    nombre: string;
    codigo: string;
    direccion: string;
    timezone: string;
    activa: boolean;
};

export default function DashboardSucursalesPage() {
    const { toast } = useToast();
    const [loading, setLoading] = useState(true);
    const [items, setItems] = useState<Sucursal[]>([]);
    const [open, setOpen] = useState(false);
    const [saving, setSaving] = useState(false);
    const [confirmOpen, setConfirmOpen] = useState(false);
    const [confirmText, setConfirmText] = useState('');
    const [pendingSave, setPendingSave] = useState<null | (() => Promise<void>)>(null);

    const [original, setOriginal] = useState<EditState | null>(null);
    const [edit, setEdit] = useState<EditState | null>(null);
    const [stationLoading, setStationLoading] = useState(false);
    const [stationKey, setStationKey] = useState('');
    const [stationUrl, setStationUrl] = useState('');

    const active = useMemo(() => items.filter((s) => !!s.activa), [items]);
    const inactive = useMemo(() => items.filter((s) => !s.activa), [items]);

    const load = async () => {
        setLoading(true);
        try {
            const res = await api.getSucursales();
            if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudieron cargar sucursales');
            setItems(res.data.items || []);
        } catch (e) {
            toast({
                title: 'No se pudo cargar sucursales',
                description: e instanceof Error ? e.message : 'Error inesperado',
                variant: 'error',
            });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
    }, []);

    const openEdit = (s: Sucursal) => {
        const st: EditState = {
            id: s.id,
            nombre: s.nombre || '',
            codigo: s.codigo || '',
            direccion: String(s.direccion || ''),
            timezone: String(s.timezone || ''),
            activa: !!s.activa,
        };
        setOriginal(st);
        setEdit(st);
        setOpen(true);
        setStationKey('');
        setStationUrl('');
        setStationLoading(true);
        (async () => {
            try {
                const r = await api.getSucursalStationKey(s.id);
                if (r.ok && r.data?.ok) {
                    setStationKey(String(r.data.station_key || ''));
                    setStationUrl(String(r.data.station_url || ''));
                }
            } finally {
                setStationLoading(false);
            }
        })();
    };

    const saveNow = async () => {
        if (!edit || !original) return;
        const payload: any = {};
        if (edit.nombre.trim() !== original.nombre.trim()) payload.nombre = edit.nombre.trim();
        if (edit.codigo.trim().toLowerCase() !== original.codigo.trim().toLowerCase()) payload.codigo = edit.codigo.trim().toLowerCase();
        if (edit.direccion.trim() !== original.direccion.trim()) payload.direccion = edit.direccion.trim() || null;
        if (edit.timezone.trim() !== original.timezone.trim()) payload.timezone = edit.timezone.trim() || null;
        if (edit.activa !== original.activa) payload.activa = edit.activa;

        setSaving(true);
        try {
            const res = await api.updateSucursal(edit.id, payload);
            if (!res.ok || !res.data?.ok) throw new Error(res.error || res.data?.error || 'No se pudo guardar');
            toast({ title: 'Guardado', description: 'Sucursal actualizada', variant: 'success' });
            setOpen(false);
            setConfirmOpen(false);
            setPendingSave(null);
            await load();
        } catch (e) {
            toast({
                title: 'No se pudo guardar',
                description: e instanceof Error ? e.message : 'Error inesperado',
                variant: 'error',
            });
        } finally {
            setSaving(false);
        }
    };

    const requestSave = async () => {
        if (!edit || !original) return;
        const nameChanged = edit.nombre.trim() !== original.nombre.trim();
        const codeChanged = edit.codigo.trim().toLowerCase() !== original.codigo.trim().toLowerCase();
        if (nameChanged || codeChanged) {
            const parts: string[] = [];
            if (nameChanged) parts.push('nombre');
            if (codeChanged) parts.push('código');
            setConfirmText(`Vas a cambiar ${parts.join(' y ')}. Esto puede desincronizar datos con Admin DB si no se replica correctamente. ¿Confirmás el cambio?`);
            setPendingSave(() => saveNow);
            setConfirmOpen(true);
            return;
        }
        await saveNow();
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-primary-500/20 text-primary-300 flex items-center justify-center">
                    <Building2 className="w-5 h-5" />
                </div>
                <div className="flex-1">
                    <h1 className="text-xl font-semibold text-white">Sucursales</h1>
                    <p className="text-sm text-slate-400">Edición segura de datos y estado por sucursal.</p>
                </div>
                <Button variant="secondary" leftIcon={<RefreshCw className="w-4 h-4" />} onClick={load} disabled={loading}>
                    Refrescar
                </Button>
            </div>

            <div className="rounded-2xl border border-slate-800/60 bg-slate-900/40 overflow-hidden">
                <div className="px-4 py-3 border-b border-slate-800/60 text-xs font-semibold text-slate-400 grid grid-cols-12 gap-3">
                    <div className="col-span-6">Sucursal</div>
                    <div className="col-span-3">Código</div>
                    <div className="col-span-1">Activa</div>
                    <div className="col-span-2 text-right">Acciones</div>
                </div>
                {loading ? (
                    <div className="p-4 text-sm text-slate-400">Cargando…</div>
                ) : items.length === 0 ? (
                    <div className="p-4 text-sm text-slate-400">Sin sucursales.</div>
                ) : (
                    <div className="divide-y divide-slate-800/60">
                        {[...active, ...inactive].map((s) => (
                            <div key={s.id} className="px-4 py-3 grid grid-cols-12 gap-3 items-center">
                                <div className="col-span-6">
                                    <div className="text-sm font-medium text-white">{s.nombre}</div>
                                    <div className="text-xs text-slate-400">ID {s.id}</div>
                                </div>
                                <div className="col-span-3 text-sm text-slate-200 font-mono">{s.codigo}</div>
                                <div className="col-span-1 text-sm text-slate-200">{s.activa ? 'Sí' : 'No'}</div>
                                <div className="col-span-2 text-right">
                                    <Button size="sm" variant="secondary" onClick={() => openEdit(s)}>
                                        Editar
                                    </Button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <Modal
                isOpen={open}
                onClose={() => setOpen(false)}
                title="Editar sucursal"
                description={edit ? `${edit.nombre} (${edit.codigo})` : undefined}
                size="lg"
                footer={
                    <div className="flex justify-end gap-2">
                        <Button variant="secondary" onClick={() => setOpen(false)} disabled={saving}>
                            Cancelar
                        </Button>
                        <Button onClick={requestSave} isLoading={saving} disabled={!edit}>
                            Guardar
                        </Button>
                    </div>
                }
            >
                <div className="p-6 space-y-5">
                    <div className="flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
                        <AlertTriangle className="w-5 h-5 text-amber-300 mt-0.5" />
                        <div className="text-sm text-amber-100/90">
                            Cambiar nombre/código es sensible. Si algún sistema externo o Admin DB no se actualiza, puede haber desincronización.
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <div className="text-sm font-medium text-slate-200">Nombre</div>
                            <Input value={edit?.nombre || ''} onChange={(e) => setEdit((p) => (p ? { ...p, nombre: e.target.value } : p))} />
                        </div>
                        <div className="space-y-2">
                            <div className="text-sm font-medium text-slate-200">Código</div>
                            <Input value={edit?.codigo || ''} onChange={(e) => setEdit((p) => (p ? { ...p, codigo: e.target.value } : p))} />
                        </div>
                        <div className="space-y-2 md:col-span-2">
                            <div className="text-sm font-medium text-slate-200">Dirección</div>
                            <Input value={edit?.direccion || ''} onChange={(e) => setEdit((p) => (p ? { ...p, direccion: e.target.value } : p))} placeholder="Opcional" />
                        </div>
                        <div className="space-y-2">
                            <div className="text-sm font-medium text-slate-200">Timezone</div>
                            <Input value={edit?.timezone || ''} onChange={(e) => setEdit((p) => (p ? { ...p, timezone: e.target.value } : p))} placeholder="Ej: America/Argentina/Buenos_Aires" />
                        </div>
                        <div className="space-y-2">
                            <div className="text-sm font-medium text-slate-200">Estado</div>
                            <div className="flex items-center gap-2">
                                <button
                                    type="button"
                                    onClick={() => setEdit((p) => (p ? { ...p, activa: true } : p))}
                                    className={cn(
                                        'h-10 px-3 rounded-xl border text-sm transition-colors',
                                        edit?.activa
                                            ? 'bg-success-500/20 border-success-500/40 text-success-200'
                                            : 'bg-slate-950/30 border-slate-800/60 text-slate-200 hover:bg-slate-900/40'
                                    )}
                                >
                                    Activa
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setEdit((p) => (p ? { ...p, activa: false } : p))}
                                    className={cn(
                                        'h-10 px-3 rounded-xl border text-sm transition-colors',
                                        edit && !edit.activa
                                            ? 'bg-danger-500/15 border-danger-500/30 text-danger-200'
                                            : 'bg-slate-950/30 border-slate-800/60 text-slate-200 hover:bg-slate-900/40'
                                    )}
                                >
                                    Inactiva
                                </button>
                            </div>
                        </div>
                        <div className="space-y-2 md:col-span-2">
                            <div className="text-sm font-medium text-slate-200">Station URL (QR)</div>
                            <div className="flex flex-col md:flex-row gap-2">
                                <Input value={stationLoading ? 'Cargando…' : stationUrl} readOnly />
                                <Button
                                    variant="secondary"
                                    onClick={async () => {
                                        try {
                                            await navigator.clipboard.writeText(stationUrl || '');
                                            toast({ title: 'Copiado', description: 'URL copiada al portapapeles', variant: 'success' });
                                        } catch {
                                            toast({ title: 'No se pudo copiar', description: 'Copiá manualmente la URL', variant: 'error' });
                                        }
                                    }}
                                    disabled={!stationUrl || stationLoading}
                                >
                                    Copiar
                                </Button>
                                <Button
                                    variant="danger"
                                    onClick={() => {
                                        if (!edit) return;
                                        setConfirmText('Regenerar la Station Key invalida el QR/URL anterior para check-in. ¿Confirmás?');
                                        setPendingSave(() => async () => {
                                            setStationLoading(true);
                                            try {
                                                const r = await api.regenerateSucursalStationKey(edit.id);
                                                if (!r.ok || !r.data?.ok) throw new Error(r.error || r.data?.error || 'No se pudo regenerar');
                                                setStationKey(String(r.data.station_key || ''));
                                                setStationUrl(String(r.data.station_url || ''));
                                                toast({ title: 'Regenerado', description: 'Station Key actualizada', variant: 'success' });
                                            } finally {
                                                setStationLoading(false);
                                                setConfirmOpen(false);
                                                setPendingSave(null);
                                            }
                                        });
                                        setConfirmOpen(true);
                                    }}
                                    disabled={stationLoading || !edit}
                                >
                                    Regenerar
                                </Button>
                            </div>
                            <div className="text-xs text-slate-500">
                                Station Key: <span className="font-mono text-slate-300">{stationKey || (stationLoading ? '…' : '-')}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </Modal>

            <ConfirmModal
                isOpen={confirmOpen}
                title="Confirmar cambio sensible"
                message={confirmText}
                confirmText="Confirmar y guardar"
                cancelText="Cancelar"
                variant="danger"
                onConfirm={() => {
                    const fn = pendingSave;
                    if (!fn) return;
                    void fn();
                }}
                onClose={() => {
                    setConfirmOpen(false);
                    setPendingSave(null);
                }}
            />
        </div>
    );
}
