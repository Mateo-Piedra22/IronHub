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
    whatsapp_phone_id?: string;
    whatsapp_access_token?: string;
    whatsapp_business_account_id?: string;
    whatsapp_verify_token?: string;
    whatsapp_app_secret?: string;
    whatsapp_nonblocking?: boolean;
    whatsapp_send_timeout_seconds?: string;
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
    created_at?: string;
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

// Admin Plans
export interface Plan {
    id: number;
    name: string;
    amount: number;
    currency: string;
    period_days: number;
    active: boolean;
    created_at?: string;
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

export interface WhatsAppTemplateCatalogItem {
    template_name: string;
    category: 'UTILITY' | 'AUTHENTICATION' | 'MARKETING' | string;
    language: string;
    body_text: string;
    example_params?: any;
    active: boolean;
    version: number;
    created_at?: string;
    updated_at?: string;
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

    checkSession: async () => {
        const res = await request<{ logged_in: boolean }>('/session');
        if (!res.ok || !res.data) {
            return { ok: false, error: res.error || 'Request failed' };
        }
        return { ok: true, data: { ok: Boolean(res.data.logged_in) } };
    },

    changeAdminPassword: (currentPassword: string, newPassword: string) =>
        request<{ ok: boolean }>('/admin/password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ current_password: currentPassword, new_password: newPassword }),
        }),

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

    createGym: (data: GymCreateInput) => {
        const params = new URLSearchParams();
        Object.entries(data).forEach(([k, v]) => {
            if (v === undefined || v === null) return;
            if (typeof v === 'boolean') {
                params.set(k, String(v));
                return;
            }
            params.set(k, String(v));
        });
        return request<Gym>('/gyms', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: params,
        });
    },

    updateGym: (id: number, data: Partial<GymCreateInput>) =>
        request<Gym>(`/gyms/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams(data as unknown as Record<string, string>),
        }),

    deleteGym: (id: number) =>
        request<{ ok: boolean }>(`/gyms/${id}`, { method: 'DELETE' }),

    setGymStatus: (id: number, status: string, reason?: string, suspended_until?: string, hard_suspend?: boolean) =>
        request<Gym>(`/gyms/${id}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({
                status,
                ...(reason ? { reason } : {}),
                ...(suspended_until ? { suspended_until } : {}),
                ...(hard_suspend !== undefined ? { hard_suspend: String(hard_suspend) } : {}),
            }),
        }),

    setGymOwnerPassword: (gymId: number, newPassword: string) =>
        request<{ ok: boolean }>(`/gyms/${gymId}/owner-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ new_password: newPassword }),
        }),

    // Metrics
    getMetrics: async () => {
        const res = await request<any>('/metrics');
        if (!res.ok || !res.data) return res as ApiResponse<Metrics>;
        const d = res.data as any;

        // admin-api returns nested metrics; admin-web expects a flat shape
        const gyms = d.gyms || {};
        const payments = d.payments || {};

        const mapped: Metrics = {
            total_gyms: Number(gyms.total ?? d.total_gyms ?? 0),
            active_gyms: Number(gyms.active ?? d.active_gyms ?? 0),
            suspended_gyms: Number(gyms.suspended ?? d.suspended_gyms ?? 0),
            total_members: d.total_members ?? undefined,
            total_revenue: Number(payments.last_30_sum ?? d.total_revenue ?? 0) || undefined,
        };

        return { ok: true, data: mapped };
    },

    getWarnings: () => request<{ warnings: any[] }>('/metrics/warnings'),

    getExpirations: (days = 30) =>
        request<{ expirations: any[] }>(`/metrics/expirations?days=${days}`),

    // Payments
    getGymPayments: async (gymId: number) => {
        const res = await request<{ payments: any[] }>(`/gyms/${gymId}/payments`);
        if (!res.ok || !res.data) return res as ApiResponse<{ payments: Payment[] }>;
        const payments = (res.data.payments || []).map((p: any) => ({
            ...p,
            created_at: p.created_at || p.paid_at,
        }));
        return { ok: true, data: { payments } };
    },

    registerPayment: async (
        gymId: number,
        data: { amount: number; plan?: string; valid_until?: string; notes?: string; currency?: string; status?: string }
    ) => {
        const res = await request<{ ok: boolean; error?: string }>(`/gyms/${gymId}/payments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams(data as unknown as Record<string, string>),
        });
        if (!res.ok) return res;
        if (res.data && (res.data as any).ok === false) {
            return { ok: false, error: (res.data as any).error || 'Payment failed' };
        }
        return res;
    },

    getRecentPayments: async (limit = 10) => {
        const res = await request<{ payments: any[] }>(`/payments/recent?limit=${limit}`);
        if (!res.ok || !res.data) return res as ApiResponse<{ payments: Payment[] }>;
        const payments = (res.data.payments || []).map((p: any) => ({
            ...p,
            created_at: p.created_at || p.paid_at,
        }));
        return { ok: true, data: { payments } };
    },

    // Branding
    getGymBranding: (gymId: number) =>
        request<{ branding: Record<string, string> }>(`/gyms/${gymId}/branding`),

    saveGymBranding: (gymId: number, branding: {
        nombre_publico?: string;
        direccion?: string;
        logo_url?: string;
        color_primario?: string;
        color_secundario?: string;
        color_fondo?: string;
        color_texto?: string;
    }) =>
        request<{ ok: boolean }>(`/gyms/${gymId}/branding`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams(
                Object.fromEntries(Object.entries(branding).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)]))
            ),
        }),

    uploadGymLogo: async (gymId: number, file: File): Promise<ApiResponse<{ ok: boolean; url: string; key: string }>> => {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch(`${API_URL}/gyms/${gymId}/logo`, {
                method: 'POST',
                credentials: 'include',
                body: formData,
            });
            const data = await res.json();
            if (!res.ok) {
                return { ok: false, error: data.error || data.detail || 'Upload failed' };
            }
            return { ok: true, data };
        } catch (error) {
            return { ok: false, error: 'Network error' };
        }
    },

    // Plans
    getPlans: () =>
        request<{ plans: Plan[] }>('/plans'),

    createPlan: (data: { name: string; amount: number; currency: string; period_days: number }) =>
        request<{ ok: boolean; id: number }>('/plans', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({
                name: data.name,
                amount: String(data.amount),
                currency: data.currency,
                period_days: String(data.period_days),
            }),
        }),

    updatePlan: (id: number, data: Partial<{ name: string; amount: number; currency: string; period_days: number }>) =>
        request<{ ok: boolean }>(`/plans/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams(
                Object.fromEntries(Object.entries(data).map(([k, v]) => [k, String(v)]))
            ),
        }),

    togglePlan: (id: number, active: boolean) =>
        request<{ ok: boolean }>(`/plans/${id}/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ active: String(active) }),
        }),

    deletePlan: (id: number) =>
        request<{ ok: boolean }>(`/plans/${id}`, { method: 'DELETE' }),

    // Subdomain
    checkSubdomain: (subdomain: string) =>
        request<{ available: boolean }>(`/subdomain/check?subdomain=${subdomain}`),

    suggestSubdomain: (name: string) =>
        request<{ suggested: string }>(`/subdomain/suggest?name=${name}`),

    // Audit
    getAuditSummary: (days = 7) =>
        request<any>(`/audit?days=${days}`),

    getGymAudit: (gymId: number, limit = 50) =>
        request<{ audit: any[] }>(`/gyms/${gymId}/audit?limit=${limit}`),

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

    sendMaintenanceNoticeUntil: (ids: number[], message: string, until: string) =>
        request<{ ok: boolean }>('/gyms/batch/maintenance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids, message, until }),
        }),

    clearMaintenance: (ids: number[]) =>
        request<{ ok: boolean }>('/gyms/batch/maintenance/clear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids }),
        }),

    // Gym Details
    getGymDetails: (id: number) =>
        request<GymDetails>(`/gyms/${id}/details`),

    getGymReminderMessage: (id: number) =>
        request<{ message: string }>(`/gyms/${id}/reminder`),

    setGymReminderMessage: (id: number, message: string) =>
        request<{ ok: boolean }>(`/gyms/${id}/reminder`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message }),
        }),

    updateGymWhatsApp: (id: number, config: WhatsAppConfig) =>
        request<{ ok: boolean }>(`/gyms/${id}/whatsapp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config),
        }),

    clearGymWhatsApp: (id: number) =>
        request<{ ok: boolean }>(`/gyms/${id}/whatsapp`, {
            method: 'DELETE',
        }),

    sendWhatsAppTest: (gymId: number, phone: string, message: string) =>
        request<{ ok: boolean; message?: string; error?: string }>(`/gyms/${gymId}/whatsapp/test`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ phone, message }),
        }),

    getWhatsAppTemplateCatalog: (activeOnly = false) =>
        request<{ templates: WhatsAppTemplateCatalogItem[] }>(`/whatsapp/templates?active_only=${activeOnly ? '1' : '0'}`),

    upsertWhatsAppTemplateCatalog: (templateName: string, data: Partial<WhatsAppTemplateCatalogItem>) =>
        request<{ ok: boolean }>(`/whatsapp/templates/${encodeURIComponent(templateName)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        }),

    deleteWhatsAppTemplateCatalog: (templateName: string) =>
        request<{ ok: boolean }>(`/whatsapp/templates/${encodeURIComponent(templateName)}`, { method: 'DELETE' }),

    provisionGymWhatsAppTemplates: (gymId: number) =>
        request<{ ok: boolean; existing_count: number; created: string[]; failed: Array<{ name: string; error: string }> }>(
            `/gyms/${gymId}/whatsapp/provision-templates`,
            { method: 'POST' }
        ),

    getGymWhatsAppHealth: (gymId: number) =>
        request<any>(`/gyms/${gymId}/whatsapp/health`),

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

