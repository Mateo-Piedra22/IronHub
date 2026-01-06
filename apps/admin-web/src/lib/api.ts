/**
 * Admin API Client
 * Handles all communication with admin-api
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

// Types
export interface Gym {
    id: number;
    nombre: string;
    subdominio: string;
    db_name: string;
    status: 'active' | 'suspended' | 'maintenance';
    created_at?: string;
    owner_phone?: string;
    wa_configured?: boolean;
    b2_bucket_name?: string;
}

export interface GymCreateInput {
    nombre: string;
    subdominio?: string;
    owner_phone?: string;
}

export interface Metrics {
    total_gyms: number;
    active_gyms: number;
    suspended_gyms: number;
    total_members?: number;
    total_revenue?: number;
}

export interface Payment {
    id: number;
    gym_id: number;
    amount: number;
    currency: string;
    status: string;
    created_at: string;
    valid_until?: string;
    notes?: string;
}

export interface ApiResponse<T> {
    ok: boolean;
    data?: T;
    error?: string;
}

// Helper for API requests
async function request<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<ApiResponse<T>> {
    try {
        const res = await fetch(`${API_URL}${endpoint}`, {
            ...options,
            credentials: 'include',
            headers: {
                ...options.headers,
            },
        });

        const data = await res.json();

        if (!res.ok) {
            return { ok: false, error: data.error || data.detail || 'Request failed' };
        }

        return { ok: true, data };
    } catch (error) {
        return { ok: false, error: 'Network error' };
    }
}

// Auth
export const api = {
    // Auth
    login: (password: string) =>
        request<{ ok: boolean }>('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ password }),
        }),

    logout: () => request('/logout', { method: 'POST' }),

    checkSession: () => request<{ ok: boolean }>('/session'),

    // Gyms
    getGyms: (params?: { page?: number; page_size?: number; q?: string; status?: string }) => {
        const searchParams = new URLSearchParams();
        if (params?.page) searchParams.set('page', String(params.page));
        if (params?.page_size) searchParams.set('page_size', String(params.page_size));
        if (params?.q) searchParams.set('q', params.q);
        if (params?.status) searchParams.set('status', params.status);
        return request<{ gyms: Gym[]; total: number; page: number; page_size: number }>(
            `/gyms?${searchParams.toString()}`
        );
    },

    getGym: (id: number) => request<Gym>(`/gyms/${id}`),

    createGym: (data: GymCreateInput) =>
        request<Gym>('/gyms', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams(data as unknown as Record<string, string>),
        }),

    updateGym: (id: number, data: Partial<GymCreateInput>) =>
        request<Gym>(`/gyms/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams(data as unknown as Record<string, string>),
        }),

    deleteGym: (id: number) =>
        request<{ ok: boolean }>(`/gyms/${id}`, { method: 'DELETE' }),

    setGymStatus: (id: number, status: string, reason?: string) =>
        request<Gym>(`/gyms/${id}/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ status, ...(reason && { reason }) }),
        }),

    // Metrics
    getMetrics: () => request<Metrics>('/metrics'),

    getWarnings: () => request<{ warnings: any[] }>('/warnings'),

    getExpirations: (days = 30) =>
        request<{ expirations: any[] }>(`/expirations?days=${days}`),

    // Payments
    getGymPayments: (gymId: number) =>
        request<{ payments: Payment[] }>(`/gyms/${gymId}/payments`),

    registerPayment: (gymId: number, data: { amount: number; plan?: string; valid_until?: string }) =>
        request<Payment>(`/gyms/${gymId}/payments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams(data as unknown as Record<string, string>),
        }),

    getRecentPayments: (limit = 10) =>
        request<{ payments: Payment[] }>(`/payments/recent?limit=${limit}`),

    // Subdomain
    checkSubdomain: (subdomain: string) =>
        request<{ available: boolean }>(`/subdomain/check?subdomain=${subdomain}`),

    suggestSubdomain: (name: string) =>
        request<{ suggestion: string }>(`/subdomain/suggest?name=${name}`),

    // Audit
    getAuditSummary: (days = 7) =>
        request<{ summary: any }>(`/audit/summary?days=${days}`),

    getGymAudit: (gymId: number, limit = 50) =>
        request<{ logs: any[] }>(`/gyms/${gymId}/audit?limit=${limit}`),
};

export default api;
