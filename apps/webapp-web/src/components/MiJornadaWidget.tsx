'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Pause, Play, Square } from 'lucide-react';
import { Button } from '@/components/ui';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import { useGestionSession } from '@/hooks/useGestionSession';

function pad2(n: number) {
    return String(Math.max(0, Math.floor(n))).padStart(2, '0');
}

function formatHms(totalSeconds: number) {
    const s = Math.max(0, Math.floor(totalSeconds));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const ss = s % 60;
    return `${pad2(h)}:${pad2(m)}:${pad2(ss)}`;
}

export function MiJornadaWidget({ className = '' }: { className?: string }) {
    const { claims } = useGestionSession();
    const role = String((claims as any)?.role || '').toLowerCase().trim();

    const shouldShow = useMemo(() => {
        if (!role) return false;
        if (role === 'owner' || role === 'dueño' || role === 'dueno') return false;
        return true;
    }, [role]);

    const [loading, setLoading] = useState(false);
    const [state, setState] = useState<any>(null);
    const [errorText, setErrorText] = useState('');
    const tickRef = useRef<number | null>(null);

    const refresh = useCallback(async () => {
        setErrorText('');
        const res = await api.getMyWorkSession();
        if (res.ok && res.data) {
            setState(res.data);
        } else {
            setState(null);
            setErrorText(res.error || 'No disponible');
        }
    }, []);

    useEffect(() => {
        if (!shouldShow) return;
        void refresh();
        const id = window.setInterval(() => void refresh(), 15000);
        return () => window.clearInterval(id);
    }, [shouldShow, refresh]);

    useEffect(() => {
        if (!shouldShow) return;
        if (tickRef.current != null) window.clearInterval(tickRef.current);
        tickRef.current = window.setInterval(() => {
            setState((prev: any) => {
                const a = prev?.active;
                if (!a) return prev;
                if (a.paused) return prev;
                const next = { ...prev, active: { ...a } };
                const eff = Number(a.effective_elapsed_seconds || 0);
                next.active.effective_elapsed_seconds = eff + 1;
                return next;
            });
        }, 1000);
        return () => {
            if (tickRef.current != null) window.clearInterval(tickRef.current);
            tickRef.current = null;
        };
    }, [shouldShow]);

    const active = state?.active || null;
    const allowed = !!state?.allowed;
    const paused = !!active?.paused;
    const effectiveSeconds = Number(active?.effective_elapsed_seconds || 0);

    const onStart = async () => {
        setLoading(true);
        try {
            await api.startMyWorkSession();
            await refresh();
        } finally {
            setLoading(false);
        }
    };
    const onPause = async () => {
        setLoading(true);
        try {
            await api.pauseMyWorkSession();
            await refresh();
        } finally {
            setLoading(false);
        }
    };
    const onResume = async () => {
        setLoading(true);
        try {
            await api.resumeMyWorkSession();
            await refresh();
        } finally {
            setLoading(false);
        }
    };
    const onEnd = async () => {
        setLoading(true);
        try {
            await api.endMyWorkSession();
            await refresh();
        } finally {
            setLoading(false);
        }
    };

    if (!shouldShow) return null;
    if (!allowed && !active) return null;

    return (
        <div className={cn('flex items-center gap-2', className)}>
            <div className="hidden md:block text-xs text-slate-400">Mi jornada</div>
            <div className="font-mono text-sm text-white tabular-nums">{formatHms(effectiveSeconds)}</div>
            {!active ? (
                <Button size="sm" variant="secondary" onClick={onStart} isLoading={loading}>
                    <Play className="w-4 h-4 mr-1" />
                    Iniciar
                </Button>
            ) : paused ? (
                <>
                    <Button size="sm" variant="secondary" onClick={onResume} isLoading={loading}>
                        <Play className="w-4 h-4 mr-1" />
                        Reanudar
                    </Button>
                    <Button size="sm" variant="danger" onClick={onEnd} isLoading={loading}>
                        <Square className="w-4 h-4 mr-1" />
                        Terminar
                    </Button>
                </>
            ) : (
                <>
                    <Button size="sm" variant="secondary" onClick={onPause} isLoading={loading}>
                        <Pause className="w-4 h-4 mr-1" />
                        Pausar
                    </Button>
                    <Button size="sm" variant="danger" onClick={onEnd} isLoading={loading}>
                        <Square className="w-4 h-4 mr-1" />
                        Terminar
                    </Button>
                </>
            )}
            {errorText ? <div className="hidden lg:block text-xs text-danger-400">{errorText}</div> : null}
        </div>
    );
}

