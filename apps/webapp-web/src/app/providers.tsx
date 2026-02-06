'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
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

    useEffect(() => {
        (async () => {
            try {
                const res = await api.getBootstrap('auto');
                if (res.ok && res.data?.gym?.theme) {
                    applyGymTheme(res.data.gym.theme);
                }
            } catch {
            }
        })();
    }, []);

    return (
        <QueryClientProvider client={queryClient}>
            <AuthProvider>
                {children}
                <ToastContainer />
            </AuthProvider>
        </QueryClientProvider>
    );
}

