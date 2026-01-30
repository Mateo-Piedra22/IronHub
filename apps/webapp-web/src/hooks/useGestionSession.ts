'use client';

import { useEffect, useState } from 'react';
import { api, type SessionUser } from '@/lib/api';

export function useGestionSession() {
    const [claims, setClaims] = useState<SessionUser | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;
        const run = async () => {
            setLoading(true);
            try {
                const res = await api.getSession('gestion');
                const nextClaims = res.ok ? res.data?.user ?? null : null;
                if (!cancelled) setClaims(nextClaims);
            } catch {
                if (!cancelled) setClaims(null);
            } finally {
                if (!cancelled) setLoading(false);
            }
        };
        void run();
        return () => {
            cancelled = true;
        };
    }, []);

    return { claims, loading };
}

