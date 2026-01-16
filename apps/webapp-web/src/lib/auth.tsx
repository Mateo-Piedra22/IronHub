'use client';

import { createContext, useContext, useEffect, useLayoutEffect, useState, useCallback, type ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { api, type SessionUser } from '@/lib/api';

interface AuthContextType {
    user: SessionUser | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    login: (dni: string, password: string) => Promise<{ ok: boolean; error?: string }>;
    logout: () => Promise<void>;
    checkSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
    login: async () => ({ ok: false }),
    logout: async () => { },
    checkSession: async () => { },
});

export function useAuth() {
    return useContext(AuthContext);
}

// Protected routes config
const protectedRoutes = {
    '/gestion': ['owner', 'admin', 'profesor'],
    '/dashboard': ['owner', 'admin', 'profesor', 'user'],
    '/usuario': ['user'],
};

export function AuthProvider({ children }: { children: ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();
    const [user, setUser] = useState<SessionUser | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    // Avoid redirect races on navigation: mark loading synchronously when route changes.
    useLayoutEffect(() => {
        setIsLoading(true);
    }, [pathname]);

    const checkSession = useCallback(async () => {
        setIsLoading(true);
        try {
            const context = pathname?.startsWith('/gestion')
                ? 'gestion'
                : pathname?.startsWith('/usuario')
                    ? 'usuario'
                    : 'auto';
            const res = await api.getSession(context);
            if (res.ok && res.data?.authenticated && res.data.user) {
                setUser(res.data.user);
            } else {
                setUser(null);
            }
        } catch {
            setUser(null);
        } finally {
            setIsLoading(false);
        }
    }, [pathname]);

    const login = useCallback(async (dni: string, password: string) => {
        const res = await api.login({ dni, password });
        if (res.ok && res.data?.ok && res.data.user) {
            setUser(res.data.user);
            return { ok: true };
        }
        return { ok: false, error: res.error || 'Error de autenticación' };
    }, []);

    const logout = useCallback(async () => {
        await api.logout();
        setUser(null);
        router.push('/');
    }, [router]);

    // Check session on mount
    useEffect(() => {
        checkSession();
    }, [checkSession]);

    // Route protection
    useEffect(() => {
        if (isLoading) return;

        // Check if current path needs protection
        const matchedRoute = Object.keys(protectedRoutes).find((route) => {
            if (!pathname) return false;
            return pathname === route || pathname.startsWith(`${route}/`);
        });

        if (matchedRoute) {
            const allowedRoles = protectedRoutes[matchedRoute as keyof typeof protectedRoutes];

            if (!user) {
                // Not authenticated - redirect to login
                if (matchedRoute === '/gestion') {
                    router.replace('/gestion-login');
                } else {
                    router.replace('/usuario-login');
                }
            } else if (!allowedRoles.includes(user.rol)) {
                // Wrong role - redirect to home
                router.replace('/');
            }
        }
    }, [pathname, user, isLoading, router]);

    return (
        <AuthContext.Provider
            value={{
                user,
                isLoading,
                isAuthenticated: !!user,
                login,
                logout,
                checkSession,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export default AuthProvider;

