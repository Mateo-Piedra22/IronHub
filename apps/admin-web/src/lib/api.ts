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

// Payment Management Types (Restored from deprecated)
export interface MetodoPago {
    id: number;
    nombre: string;
    icono?: string;
    color?: string;
    comision?: number;
    activo: boolean;
    descripcion?: string;
    fecha_creacion?: string;
}

export interface TipoCuota {
    id: number;
    nombre: string;
    precio: number;
    duracion_dias: number;
    activo: boolean;
    descripcion?: string;
    icono_path?: string;
}

export interface ConceptoPago {
    id: number;
    nombre: string;
    descripcion?: string;
    precio_base: number;
    tipo?: string;
    activo: boolean;
}

export interface PagoConceptoItem {
    concepto_id?: number;
    descripcion?: string;
    cantidad: number;
    precio_unitario: number;
}

export interface PagoDetalle {
    id: number;
    concepto_id?: number;
    descripcion?: string;
    cantidad: number;
    precio_unitario: number;
    subtotal: number;
    concepto_nombre?: string;
}

export interface PagoCompleto {
    pago: {
        id: number;
        usuario_id: number;
        monto: number;
        mes: number;
        año: number;
        fecha_pago: string;
        metodo_pago_id?: number;
        usuario_nombre?: string;
        dni?: string;
        metodo_nombre?: string;
    };
    detalles: PagoDetalle[];
    total_detalles: number;
}

export interface EstadisticasPagos {
    año: number;
    total_pagos: number;
    total_recaudado: number;
    promedio_pago: number;
    pago_minimo: number;
    pago_maximo: number;
    por_mes: Record<number, { cantidad: number; total: number }>;
    por_metodo: { metodo: string; cantidad: number; total: number }[];
}

export interface ApiResponse<T> {
    ok: boolean;
    data?: T;
    error?: string;
}

export interface WhatsAppConfig {
    phone_id?: string;
    access_token?: string;
    business_account_id?: string;
    verify_token?: string;
    app_secret?: string;
    nonblocking?: boolean;
    send_timeout_seconds?: number;
}

export interface GymDetails extends Gym {
    whatsapp_phone_id?: string;
    whatsapp_access_token?: string;
    whatsapp_business_account_id?: string;
    whatsapp_verify_token?: string;
    whatsapp_app_secret?: string;
    whatsapp_nonblocking?: boolean;
    whatsapp_send_timeout_seconds?: number;
    reminder_message?: string;
    suspension_reason?: string;
    suspension_until?: string;
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

    // Batch Operations
    batchProvision: (ids: number[]) =>
        request<{ ok: boolean }>('/gyms/batch/provision', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids }),
        }),

    batchSuspend: (ids: number[], reason?: string, until?: string, hard?: boolean) =>
        request<{ ok: boolean }>('/gyms/batch/suspend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids, reason, until, hard }),
        }),

    batchReactivate: (ids: number[]) =>
        request<{ ok: boolean }>('/gyms/batch/reactivate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids }),
        }),

    sendReminder: (ids: number[], message: string) =>
        request<{ ok: boolean }>('/gyms/batch/remind', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids, message }),
        }),

    sendMaintenanceNotice: (ids: number[], message: string) =>
        request<{ ok: boolean }>('/gyms/batch/maintenance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids, message }),
        }),

    // Gym Details
    getGymDetails: (id: number) =>
        request<GymDetails>(`/gyms/${id}/details`),

    updateGymWhatsApp: (id: number, config: WhatsAppConfig) =>
        request<{ ok: boolean }>(`/gyms/${id}/whatsapp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config),
        }),

    // ========== PAYMENT MANAGEMENT (Restored from deprecated) ==========

    // Métodos de Pago
    getMetodosPago: (activos = true) =>
        request<MetodoPago[]>(`/api/metodos_pago?activos=${activos}`),

    createMetodoPago: (data: Partial<MetodoPago>) =>
        request<{ ok: boolean; id: number }>('/api/metodos_pago', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        }),

    updateMetodoPago: (id: number, data: Partial<MetodoPago>) =>
        request<{ ok: boolean; id: number }>(`/api/metodos_pago/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        }),

    deleteMetodoPago: (id: number) =>
        request<{ ok: boolean }>(`/api/metodos_pago/${id}`, { method: 'DELETE' }),

    // Tipos de Cuota (Planes)
    getTiposCuota: (activos = false) =>
        request<TipoCuota[]>(`/api/tipos_cuota?activos=${activos}`),

    getTiposCuotaActivos: () =>
        request<TipoCuota[]>('/api/tipos_cuota/activos'),

    createTipoCuota: (data: Partial<TipoCuota>) =>
        request<{ ok: boolean; id: number }>('/api/tipos_cuota', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        }),

    updateTipoCuota: (id: number, data: Partial<TipoCuota>) =>
        request<{ ok: boolean; id: number }>(`/api/tipos_cuota/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        }),

    deleteTipoCuota: (id: number) =>
        request<{ ok: boolean }>(`/api/tipos_cuota/${id}`, { method: 'DELETE' }),

    // Conceptos de Pago
    getConceptosPago: (activos = true) =>
        request<ConceptoPago[]>(`/api/conceptos_pago?activos=${activos}`),

    createConceptoPago: (data: Partial<ConceptoPago>) =>
        request<{ ok: boolean; id: number }>('/api/conceptos_pago', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        }),

    updateConceptoPago: (id: number, data: Partial<ConceptoPago>) =>
        request<{ ok: boolean; id: number }>(`/api/conceptos_pago/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        }),

    deleteConceptoPago: (id: number) =>
        request<{ ok: boolean }>(`/api/conceptos_pago/${id}`, { method: 'DELETE' }),

    // Pagos Avanzados
    getPagoDetalle: (pagoId: number) =>
        request<PagoCompleto>(`/api/pagos/${pagoId}`),

    createPago: (data: {
        usuario_id: number;
        monto?: number;
        mes?: number;
        año?: number;
        metodo_pago_id?: number;
        fecha_pago?: string;
        conceptos?: PagoConceptoItem[];
    }) =>
        request<{ ok: boolean; id: number }>('/api/pagos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        }),

    updatePago: (pagoId: number, data: {
        usuario_id?: number;
        monto?: number;
        mes?: number;
        año?: number;
        metodo_pago_id?: number;
        fecha_pago?: string;
        conceptos?: PagoConceptoItem[];
    }) =>
        request<{ ok: boolean; id: number }>(`/api/pagos/${pagoId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        }),

    deletePago: (pagoId: number) =>
        request<{ ok: boolean }>(`/api/pagos/${pagoId}`, { method: 'DELETE' }),

    // Estadísticas
    getEstadisticasPagos: (año?: number) =>
        request<EstadisticasPagos>(`/api/pagos/estadisticas${año ? `?año=${año}` : ''}`),
};

export default api;

