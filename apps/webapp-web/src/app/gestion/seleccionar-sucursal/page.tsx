'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Building2 } from 'lucide-react';
import { Button, useToast } from '@/components/ui';
import { api, type Sucursal } from '@/lib/api';

export default function GestionSeleccionarSucursalPage() {
    const router = useRouter();
    const { toast } = useToast();
    const [loading, setLoading] = useState(true);
    const [items, setItems] = useState<Sucursal[]>([]);
    const [currentId, setCurrentId] = useState<number | null>(null);
    const [selectingId, setSelectingId] = useState<number | null>(null);

    useEffect(() => {
        const load = async () => {
            setLoading(true);
            try {
                const res = await api.getSucursales();
                if (!res.ok) throw new Error(res.error || 'Error cargando sucursales');
                const list = (res.data?.items || []).filter((s) => !!s.activa);
                setItems(list);
                const sid = res.data?.sucursal_actual_id ?? null;
                setCurrentId(typeof sid === 'number' ? sid : null);
                if (typeof sid === 'number' && sid > 0) {
                    window.location.assign('/gestion/usuarios');
                }
            } catch (e) {
                toast({
                    title: 'No se pudo cargar sucursales',
                    description: e instanceof Error ? e.message : 'Error inesperado',
                    variant: 'error',
                });
                setItems([]);
                setCurrentId(null);
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [router, toast]);

    const handleSelect = async (sid: number) => {
        setSelectingId(sid);
        try {
            const res = await api.seleccionarSucursal(sid);
            if (!res.ok) throw new Error(res.error || 'No se pudo seleccionar la sucursal');
            setCurrentId(sid);
            window.location.assign('/gestion/usuarios');
        } catch (e) {
            toast({
                title: 'No se pudo seleccionar sucursal',
                description: e instanceof Error ? e.message : 'Error inesperado',
                variant: 'error',
            });
        } finally {
            setSelectingId(null);
        }
    };

    return (
        <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center p-6">
            <div className="w-full max-w-lg rounded-2xl border border-slate-800/60 bg-slate-900/40 backdrop-blur-lg p-6">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-xl bg-primary-500/20 text-primary-300 flex items-center justify-center">
                        <Building2 className="w-5 h-5" />
                    </div>
                    <div>
                        <h1 className="text-lg font-semibold text-white">Elegí una sucursal</h1>
                        <p className="text-sm text-slate-400">Necesitás seleccionar una sucursal para continuar.</p>
                    </div>
                </div>

                {loading ? (
                    <div className="text-sm text-slate-400">Cargando…</div>
                ) : items.length === 0 ? (
                    <div className="text-sm text-slate-400">No tenés sucursales disponibles.</div>
                ) : (
                    <div className="space-y-2">
                        {items.map((s) => (
                            <Button
                                key={s.id}
                                variant={currentId === s.id ? 'primary' : 'secondary'}
                                className="w-full justify-between"
                                disabled={selectingId !== null}
                                onClick={() => handleSelect(s.id)}
                            >
                                <span>{s.nombre}</span>
                                {selectingId === s.id ? <span className="text-xs opacity-80">Seleccionando…</span> : null}
                            </Button>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
