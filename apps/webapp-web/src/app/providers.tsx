'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useQuery } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { ToastContainer } from '@/components/ui';
import { AuthProvider } from '@/lib/auth';
import { api } from '@/lib/api';
import { applyGymTheme } from '@/lib/branding';

export function Providers({ children }: { children: React.ReactNode }) {
    const [queryClient] = useState(() => new QueryClient({
        defaultOptions: {
            queries: {
                staleTime: 60 * 1000,
                refetchOnWindowFocus: false,
            },
        },
    }));

    return (
        <QueryClientProvider client={queryClient}>
            <ProvidersContent>{children}</ProvidersContent>
        </QueryClientProvider>
    );
}

function ProvidersContent({ children }: { children: React.ReactNode }) {
    const bootstrapQuery = useQuery({
        queryKey: ['bootstrap', 'auto'],
        queryFn: async () => api.getBootstrap('auto'),
        refetchOnWindowFocus: true,
        refetchInterval: 30_000,
        retry: 1,
    });

    const bootstrap = bootstrapQuery.data?.ok ? bootstrapQuery.data.data : null;
    const flags = (bootstrap?.flags || {}) as Record<string, unknown>;
    const suspended = Boolean(flags.suspended);
    const suspensionReason = (typeof flags.reason === 'string' ? flags.reason : '') || 'Servicio suspendido';
    const suspensionUntil = (typeof flags.until === 'string' ? flags.until : '') || '';
    const maintenance = Boolean(flags.maintenance);
    const maintenanceMessage = (typeof flags.maintenance_message === 'string' ? flags.maintenance_message : '') || 'Mantenimiento en curso';

    useEffect(() => {
        const theme = bootstrap?.gym?.theme;
        if (theme) applyGymTheme(theme);
    }, [bootstrap?.gym?.theme]);

    const reminderQuery = useQuery({
        queryKey: ['systemReminder', bootstrap?.tenant || ''],
        queryFn: async () => api.getSystemReminder(),
        enabled: !!bootstrap?.tenant,
        refetchOnWindowFocus: true,
        refetchInterval: 60_000,
        retry: 1,
    });

    const reminder = reminderQuery.data?.ok ? reminderQuery.data.data : null;
    const reminderActive = Boolean(reminder?.active);
    const reminderMessage = (typeof reminder?.message === 'string' ? reminder.message : '') || '';
    const reminderStorageKey = useMemo(() => {
        const tenant = (bootstrap?.tenant || '').trim();
        const msg = reminderMessage.trim();
        if (!tenant || !msg) return '';
        const hash = Array.from(msg).reduce((acc, ch) => ((acc * 31) ^ ch.charCodeAt(0)) >>> 0, 0).toString(16);
        return `ironhub:reminder:dismissed:${tenant}:${hash}`;
    }, [bootstrap?.tenant, reminderMessage]);
    const [reminderVisible, setReminderVisible] = useState(false);

    useEffect(() => {
        if (!reminderActive || !reminderMessage.trim() || !reminderStorageKey) {
            setReminderVisible(false);
            return;
        }
        try {
            const dismissed = typeof window !== 'undefined' ? window.sessionStorage.getItem(reminderStorageKey) : null;
            setReminderVisible(dismissed !== '1');
        } catch {
            setReminderVisible(true);
        }
    }, [reminderActive, reminderMessage, reminderStorageKey]);

    return (
        <AuthProvider>
            {children}
            {reminderVisible && !suspended && (
                <div className="fixed top-0 inset-x-0 z-[60] p-3">
                    <div className="mx-auto max-w-4xl rounded-xl border border-amber-500/30 bg-black/70 backdrop-blur px-4 py-3 flex items-start gap-3">
                        <div className="min-w-0 flex-1">
                            <div className="text-sm font-semibold text-amber-300">Recordatorio</div>
                            <div className="text-sm text-slate-200 whitespace-pre-wrap break-words">{reminderMessage}</div>
                        </div>
                        <button
                            className="text-sm text-slate-300 hover:text-white"
                            onClick={() => {
                                try {
                                    if (reminderStorageKey) window.sessionStorage.setItem(reminderStorageKey, '1');
                                } catch {
                                }
                                setReminderVisible(false);
                            }}
                        >
                            Cerrar
                        </button>
                    </div>
                </div>
            )}
            {(suspended || maintenance) && (
                <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/80 p-4">
                    <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-950/80 backdrop-blur p-6">
                        {suspended ? (
                            <>
                                <div className="text-lg font-bold text-danger-400">Servicio suspendido</div>
                                <div className="mt-2 text-slate-200">{suspensionReason}</div>
                                {suspensionUntil && (
                                    <div className="mt-2 text-sm text-slate-400">Hasta: {suspensionUntil}</div>
                                )}
                            </>
                        ) : (
                            <>
                                <div className="text-lg font-bold text-white">Mantenimiento</div>
                                <div className="mt-2 text-slate-200 whitespace-pre-wrap break-words">{maintenanceMessage}</div>
                                <button
                                    className="mt-4 w-full btn-secondary"
                                    onClick={() => {
                                        void bootstrapQuery.refetch();
                                        void reminderQuery.refetch();
                                    }}
                                >
                                    Reintentar
                                </button>
                            </>
                        )}
                    </div>
                </div>
            )}
            <ToastContainer />
        </AuthProvider>
    );
}
