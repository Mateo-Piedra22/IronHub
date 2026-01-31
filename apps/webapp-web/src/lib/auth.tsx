'use client';

import { createContext, useContext, useEffect, useRef, useState, useCallback, type ReactNode } from 'react';
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
    '/gestion': ['owner', 'admin', 'profesor', 'empleado', 'recepcionista', 'staff'],
    '/dashboard': ['owner', 'admin'],
    '/usuario': ['user', 'owner', 'admin', 'profesor', 'empleado', 'recepcionista', 'staff'],
};

export function AuthProvider({ children }: { children: ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();
    const [user, setUser] = useState<SessionUser | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const pathnameRef = useRef<string>('');
    useEffect(() => {
        pathnameRef.current = pathname || '';
    }, [pathname]);

    const checkSession = useCallback(async () => {
        setIsLoading(true);
        try {
            const p = pathnameRef.current || '';
            const context = p.startsWith('/gestion')
                ? 'gestion'
                : p.startsWith('/usuario')
                    ? 'usuario'
                    : 'auto';
            const res = await api.getBootstrap(context);
            if (res.ok && res.data?.session?.authenticated && res.data.session.user) {
                const u = { ...(res.data.session.user as any) } as SessionUser;
                if (!u.sucursal_id) {
                    const sid = (res.data as any)?.sucursal_actual_id;
                    if (typeof sid === 'number' && sid > 0) {
                        (u as any).sucursal_id = sid;
                    }
                }
                setUser(u);
            } else {
                setUser(null);
            }
        } catch {
            setUser(null);
        } finally {
            setIsLoading(false);
        }
    }, []);

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

    // Check session on mount + lightweight background refresh (avoid checking on every navigation)
    useEffect(() => {
        checkSession();
        const id = window.setInterval(() => {
            checkSession();
        }, 60_000);
        return () => window.clearInterval(id);
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
                } else if (matchedRoute === '/dashboard') {
                    router.replace('/login');
                } else {
                    router.replace('/usuario-login');
                }
            } else if (
                !user.sucursal_id &&
                !pathname?.includes('/seleccionar-sucursal')
            ) {
                if (matchedRoute === '/dashboard') {
                    return;
                } else if (matchedRoute === '/usuario') {
                    return;
                } else {
                    router.replace('/gestion/seleccionar-sucursal');
                }
            } else if (!allowedRoles.includes(user.rol)) {
                // Wrong role - redirect to home
                router.replace('/');
            }
        }
    }, [pathname, user, isLoading, router, checkSession]);

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

