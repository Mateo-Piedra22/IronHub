/**
 * Admin API Client
 * Handles all communication with admin-api
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null;

// Template Types
export interface Template {
    id: number;
    nombre: string;
    descripcion?: string;
    configuracion: TemplateConfig;
    categoria: string;
    dias_semana?: number;
    activa: boolean;
    publica: boolean;
    creada_por?: number;
    fecha_creacion: string;
    fecha_actualizacion: string;
    version_actual: string;
    tags?: string[];
    preview_url?: string;
    uso_count: number;
    rating_promedio?: number;
    rating_count: number;
}

export interface TemplateConfig {
    metadata: {
        name: string;
        version: string;
        description: string;
        author?: string;
        category?: string;
        difficulty?: string;
        tags?: string[];
        estimated_duration?: number;
    };
    layout: {
        page_size: 'A4' | 'Letter' | 'Legal';
        orientation: 'portrait' | 'landscape';
        margins: {
            top: number;
            right: number;
            bottom: number;
            left: number;
        };
    };
    pages: TemplatePage[];
    variables: { [key: string]: TemplateVariable };
    qr_code?: {
        enabled?: boolean;
        position?: 'header' | 'footer' | 'inline' | 'separate' | 'sheet' | 'none';
        size?: { width: number; height: number } | number;
        data_source?: 'routine_uuid' | 'custom_url' | 'user_data';
        custom_data?: string;
    };
    styling?: {
        fonts?: {
            [key: string]: {
                family?: string;
                size?: number;
                bold?: boolean;
                italic?: boolean;
                color?: string;
            };
        };
        colors?: { [key: string]: string };
    };
}

export interface TemplatePage {
    name: string;
    description?: string;
    sections: TemplatePageSection[];
}

export interface TemplatePageSection {
    type:
        | 'header'
        | 'text'
        | 'table'
        | 'image'
        | 'qr_code'
        | 'exercise_table'
        | 'progress_chart'
        | 'spacing';
    name?: string;
    position?: { x?: number; y?: number; width?: number; height?: number };
    content?: unknown;
    conditional?: { if?: string; show?: boolean };
}

export interface TemplateVariable {
    type: 'string' | 'number' | 'boolean' | 'date' | 'image';
    default?: unknown;
    description?: string;
    required?: boolean;
}

export interface TemplateAnalytics {
    template_id: number;
    usos_totales: number;
    usuarios_unicos: number;
    uso_ultimo_mes: number;
    rating_promedio: number;
    evaluaciones: number;
    tendencias: {
        periodo: string;
        usos: number;
    }[];
    popularidad: {
        posicion: number;
        total_plantillas: number;
    };
}

export interface TemplateStats {
    total_templates: number;
    active_templates: number;
    total_usos: number;
    usuarios_unicos: number;
    rating_promedio: number;
    total_ratings: number;
    categorias_populares: { categoria: string; count: number }[];
    plantillas_top: Template[];
}

export interface TemplatePreviewRequest {
    format: 'pdf' | 'image' | 'thumbnail' | 'html' | 'json';
    quality: 'low' | 'medium' | 'high' | 'ultra';
    qr_mode?: 'header' | 'footer' | 'inline' | 'sheet' | 'none';
    page_number?: number;
    sample_data?: Record<string, unknown> | null;
}

export interface TemplateValidation {
    is_valid: boolean;
    errors: TemplateValidationError[];
    warnings: TemplateValidationWarning[];
    performance_score?: number | null;
    security_score?: number | null;
}

export interface TemplateValidationError {
    message: string;
    path?: string;
    suggestion?: string;
}

export interface TemplateValidationWarning {
    message: string;
    path?: string;
    suggestion?: string;
}

export interface TemplateRating {
    id: number;
    template_id: number;
    usuario_id: number;
    rating: number;
    comment?: string;
    fecha: string;
}

export interface TemplateVersion {
    id: number;
    plantilla_id: number;
    version: string;
    configuracion: Record<string, unknown>;
    descripcion?: string | null;
    creada_por?: number | null;
    fecha_creacion: string;
    es_actual: boolean;
}

export interface Rutina {
    id: number;
    nombre: string;
    dias?: unknown[];
    usuario_nombre?: string;
}

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
    production_ready?: boolean;
    production_ready_at?: string | null;
    // Subscription fields
    subscription_status?: string;
    subscription_plan_name?: string;
    subscription_plan_id?: number | null;
    subscription_plan_amount?: number;
    subscription_next_due_date?: string;
    subscription_start_date?: string;
    suspended_reason?: string | null;
    suspended_until?: string | null;
    whatsapp_phone_id?: string;
    whatsapp_access_token?: string;
    whatsapp_business_account_id?: string;
    whatsapp_verify_token?: string;
    whatsapp_app_secret?: string;
    whatsapp_nonblocking?: boolean;
    whatsapp_send_timeout_seconds?: number | null;
    tenant_whatsapp_phone_id?: string | null;
    tenant_whatsapp_waba_id?: string | null;
    tenant_whatsapp_access_token_present?: boolean;
}

export interface TenantRoutineTemplate {
    id: number;
    nombre: string;
    descripcion?: string | null;
    categoria?: string | null;
    dias_semana?: number | null;
    activa: boolean;
    publica: boolean;
    version_actual?: string | null;
    tags?: string[] | null;
    fecha_creacion?: string | null;
    fecha_actualizacion?: string | null;
}

export interface TenantRoutineTemplateAssignment {
    assignment_id: number;
    gimnasio_id: number;
    plantilla_id: number;
    activa: boolean;
    prioridad: number;
    notas?: string | null;
    fecha_asignacion?: string | null;
    nombre: string;
    descripcion?: string | null;
    categoria?: string | null;
    dias_semana?: number | null;
    publica: boolean;
    version_actual?: string | null;
    tags?: string[] | null;
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

export interface GymCreateV2Input {
    nombre: string;
    subdominio?: string;
    owner_phone?: string;
    owner_password?: string;
    whatsapp_phone_id?: string;
    whatsapp_access_token?: string;
    whatsapp_business_account_id?: string;
    whatsapp_verify_token?: string;
    whatsapp_app_secret?: string;
    whatsapp_nonblocking?: boolean;
    whatsapp_send_timeout_seconds?: number | null;
    branches?: GymBranchCreateInput[];
}

export interface GymCreateV2Response {
    ok: boolean;
    gym: Gym;
    tenant_url?: string | null;
    branches?: GymBranch[];
    owner_password_generated?: boolean;
    owner_password_set?: boolean;
    owner_password?: string;
    bulk_branches?: unknown;
    error?: string;
}

export interface TenantMigrationStatus {
    ok: boolean;
    error?: string;
    gym_id?: number;
    db_name?: string;
    head?: string | null;
    current?: string | null;
    status?: 'up_to_date' | 'outdated' | 'uninitialized' | 'unknown' | 'db_missing';
}

export interface Metrics {
    total_gyms: number;
    active_gyms: number;
    suspended_gyms: number;
    total_members?: number;
    total_revenue?: number;
}

export interface SubscriptionExpiration {
    gym_id: number;
    nombre: string;
    subdominio: string;
    valid_until: string;
    days_remaining: number;
}

export interface Payment {
    id: number;
    gym_id: number;
    nombre?: string;
    subdominio?: string;
    plan?: string;
    plan_id?: number | null;
    amount: number;
    currency: string;
    status: string;
    created_at?: string;
    paid_at?: string;
    valid_until?: string;
    notes?: string;
    provider?: string;
    external_reference?: string;
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
    example_params?: unknown;
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

export interface GymOnboardingStatus {
    ok: boolean;
    gym_id: number;
    subdominio: string;
    gym_status: string;
    tenant_url?: string | null;
    branches_total: number;
    branches_active: number;
    owner_password_set: boolean;
    whatsapp_configured: boolean;
    production_ready?: boolean;
    production_ready_at?: string | null;
}

export interface GymBranch {
    id: number;
    gym_id: number;
    name: string;
    code: string;
    address?: string | null;
    timezone?: string | null;
    status?: string | null;
    station_key?: string | null;
    created_at?: string;
}

export interface GymBranchCreateInput {
    name: string;
    code: string;
    address?: string | null;
    timezone?: string | null;
}

export interface GymBranchUpdateInput {
    name?: string;
    code?: string;
    address?: string | null;
    timezone?: string | null;
    status?: 'active' | 'inactive';
}

export interface FeatureFlags {
    modules: Record<string, boolean>;
    features?: Record<string, unknown>;
}

export interface SupportTicketAdmin {
    id: number;
    tenant: string;
    gym_id?: number | null;
    gym_nombre?: string | null;
    user_id?: number | null;
    user_role?: string | null;
    sucursal_id?: number | null;
    subject: string;
    category: string;
    priority: string;
    status: string;
    origin_url?: string | null;
    user_agent?: string | null;
    last_message_at?: string;
    last_message_sender?: string | null;
    unread_by_admin?: boolean;
    unread_by_client?: boolean;
    assigned_to?: string | null;
    tags?: unknown;
    first_response_due_at?: string | null;
    next_response_due_at?: string | null;
    first_response_at?: string | null;
    is_overdue?: boolean;
    overdue_seconds?: number;
    created_at?: string;
    updated_at?: string;
}

export interface SupportTicketMessageAdmin {
    id: number;
    ticket_id: number;
    sender_type: string;
    sender_id?: number | null;
    content: string;
    attachments?: unknown;
    created_at?: string;
}

export interface ChangelogAdminItem {
    id: number;
    version: string;
    title: string;
    body_markdown: string;
    change_type: string;
    image_url?: string | null;
    is_published: boolean;
    published_at?: string | null;
    pinned?: boolean;
    min_app_version?: string | null;
    audience_roles?: unknown;
    audience_tenants?: unknown;
    audience_modules?: unknown;
    created_at?: string;
    updated_at?: string;
}

export interface GymTipoCuotaItem {
    id: number;
    nombre: string;
    activo: boolean;
    all_sucursales: boolean;
}

export interface GymTipoClaseItem {
    id: number;
    nombre: string;
    activo: boolean;
}

export interface TipoCuotaEntitlements {
    ok: boolean;
    tipo_cuota: { id: number; nombre: string; all_sucursales: boolean };
    sucursal_ids: number[];
    class_rules: { id: number; sucursal_id?: number | null; target_type: string; target_id: number; allow: boolean }[];
}

export interface TipoCuotaEntitlementsUpdate {
    all_sucursales: boolean;
    sucursal_ids: number[];
    class_rules: { sucursal_id?: number | null; target_type: 'tipo_clase'; target_id: number; allow: boolean }[];
}

// Helper for API requests
async function request<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<ApiResponse<T>> {
    const timeoutMs = 15_000;
    const controller = options.signal ? null : new AbortController();
    const signal = options.signal ?? controller?.signal;
    const timer = controller ? setTimeout(() => controller.abort(), timeoutMs) : null;
    try {
        const selectedGymId =
            typeof window !== 'undefined' ? window.localStorage.getItem('ironhub_admin_selected_gym_id') : null;
        const res = await fetch(`${API_URL}${endpoint}`, {
            ...options,
            credentials: 'include',
            signal,
            headers: {
                ...(selectedGymId ? { 'x-gym-id': selectedGymId } : {}),
                ...options.headers,
            },
        });

        let data: unknown = null;
        try {
            data = await res.json();
        } catch {
            data = null;
        }

        if (!res.ok) {
            const msg = (() => {
                if (!data || typeof data !== 'object') return `Request failed (${res.status})`;
                const o = data as Record<string, unknown>;
                const err = o.error;
                const detail = o.detail;
                const message = o.message;
                return (
                    (typeof err === 'string' && err) ||
                    (typeof detail === 'string' && detail) ||
                    (typeof message === 'string' && message) ||
                    `Request failed (${res.status})`
                );
            })();
            return { ok: false, error: String(msg) };
        }

        return { ok: true, data: data as T };
    } catch (e) {
        const msg = String(e || '');
        if (msg.toLowerCase().includes('aborted')) {
            return { ok: false, error: 'Request timeout' };
        }
        return { ok: false, error: 'Network error' };
    } finally {
        if (timer) clearTimeout(timer);
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
    getGyms: (params?: { page?: number; page_size?: number; q?: string; status?: string; production_ready?: boolean }) => {
        const searchParams = new URLSearchParams();
        if (params?.page) searchParams.set('page', String(params.page));
        if (params?.page_size) searchParams.set('page_size', String(params.page_size));
        if (params?.q) searchParams.set('q', params.q);
        if (params?.status) searchParams.set('status', params.status);
        if (params?.production_ready !== undefined) searchParams.set('production_ready', String(params.production_ready));
        return request<{ gyms: Gym[]; total: number; page: number; page_size: number }>(
            `/gyms?${searchParams.toString()}`
        );
    },

    getGym: (id: number) => request<Gym>(`/gyms/${id}`),

    getGymRoutineTemplateCatalog: (gymId: number) =>
        request<{ ok: boolean; gym_id: number; templates: TenantRoutineTemplate[]; error?: string }>(
            `/api/gyms/${gymId}/routine-templates/catalog`
        ),

    getGymRoutineTemplateAssignments: (gymId: number) =>
        request<{ ok: boolean; gym_id: number; assignments: TenantRoutineTemplateAssignment[]; error?: string }>(
            `/api/gyms/${gymId}/routine-templates/assignments`
        ),

    assignGymRoutineTemplate: (
        gymId: number,
        payload: { template_id: number; activa?: boolean; prioridad?: number; notas?: string | null }
    ) =>
        request<{ ok: boolean; gym_id: number; assignment_id?: number; error?: string }>(
            `/api/gyms/${gymId}/routine-templates/assign`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            }
        ),

    updateGymRoutineTemplateAssignment: (
        gymId: number,
        assignmentId: number,
        payload: { activa?: boolean; prioridad?: number; notas?: string | null }
    ) =>
        request<{ ok: boolean; gym_id: number; assignment_id?: number; updated?: boolean; error?: string }>(
            `/api/gyms/${gymId}/routine-templates/assignments/${assignmentId}`,
            {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            }
        ),

    deleteGymRoutineTemplateAssignment: (gymId: number, assignmentId: number) =>
        request<{ ok: boolean; gym_id: number; assignment_id?: number; deleted?: boolean; error?: string }>(
            `/api/gyms/${gymId}/routine-templates/assignments/${assignmentId}`,
            { method: 'DELETE' }
        ),

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

    createGymV2: (payload: GymCreateV2Input) =>
        request<GymCreateV2Response>('/gyms/v2', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        }),

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

    getGymTenantMigrationStatus: (gymId: number) =>
        request<TenantMigrationStatus>(`/gyms/${gymId}/provision/status`),

    provisionGymTenantMigrations: (gymId: number) =>
        request<{ ok: boolean; db_name?: string; status?: TenantMigrationStatus; error?: string }>(`/gyms/${gymId}/provision`, {
            method: 'POST',
        }),

    // Metrics
    getMetrics: async () => {
        const res = await request<unknown>('/metrics');
        if (!res.ok || !res.data) return res as ApiResponse<Metrics>;
        const d: unknown = res.data;

        // admin-api returns nested metrics; admin-web expects a flat shape
        const drec = isRecord(d) ? d : {};
        const gyms = isRecord(drec.gyms) ? drec.gyms : {};
        const payments = isRecord(drec.payments) ? drec.payments : {};

        const mapped: Metrics = {
            total_gyms: Number(gyms.total ?? drec.total_gyms ?? 0),
            active_gyms: Number(gyms.active ?? drec.active_gyms ?? 0),
            suspended_gyms: Number(gyms.suspended ?? drec.suspended_gyms ?? 0),
            total_members: typeof drec.total_members === 'number' ? drec.total_members : undefined,
            total_revenue: Number(payments.last_30_sum ?? drec.total_revenue ?? 0) || undefined,
        };

        return { ok: true, data: mapped };
    },

    getWarnings: () => request<{ warnings: unknown[] }>('/metrics/warnings'),

    getExpirations: (days = 30) =>
        request<{ expirations: SubscriptionExpiration[] }>(`/metrics/expirations?days=${days}`),

    // Payments
    getGymPayments: async (gymId: number) => {
        const res = await request<{ payments: Payment[] }>(`/gyms/${gymId}/payments`);
        if (!res.ok || !res.data) return res as ApiResponse<{ payments: Payment[] }>;
        const payments = (res.data.payments || []).map((p) => ({ ...p, created_at: p.created_at || p.paid_at }));
        return { ok: true, data: { payments } };
    },

    registerPayment: async (
        gymId: number,
        data: {
            amount: number;
            plan?: string;
            plan_id?: number;
            valid_until?: string;
            notes?: string;
            currency?: string;
            status?: string;
            provider?: string;
            external_reference?: string;
            idempotency_key?: string;
            apply_to_subscription?: boolean;
            periods?: number;
        }
    ) => {
        const bodyPairs: Array<[string, string]> = [];
        for (const [k, v] of Object.entries(data)) {
            if (v === undefined || v === null) continue;
            if (k === 'apply_to_subscription') bodyPairs.push([k, String(Boolean(v))]);
            else bodyPairs.push([k, String(v)]);
        }
        const res = await request<{ ok: boolean; error?: string }>(`/gyms/${gymId}/payments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams(bodyPairs),
        });
        if (!res.ok) return res;
        if (res.data && res.data.ok === false) {
            return { ok: false, error: res.data.error || 'Payment failed' };
        }
        return res;
    },

    getRecentPayments: async (limit = 10) => {
        const res = await request<{ payments: Payment[] }>(`/payments/recent?limit=${limit}`);
        if (!res.ok || !res.data) return res as ApiResponse<{ payments: Payment[] }>;
        const payments = (res.data.payments || []).map((p) => ({ ...p, created_at: p.created_at || p.paid_at }));
        return { ok: true, data: { payments } };
    },

    listPayments: async (params: { gym_id?: number; status?: string; q?: string; desde?: string; hasta?: string; page?: number; page_size?: number }) => {
        const qs = new URLSearchParams();
        for (const [k, v] of Object.entries(params || {})) {
            if (v === undefined || v === null || String(v).trim() === '') continue;
            qs.set(k, String(v));
        }
        const res = await request<{ items: Payment[]; total: number; page: number; page_size: number }>(`/payments?${qs.toString()}`);
        if (!res.ok || !res.data) return res as ApiResponse<{ items: Payment[]; total: number; page: number; page_size: number }>;
        const items = (res.data.items || []).map((p) => ({ ...p, created_at: p.created_at || p.paid_at }));
        return { ok: true, data: { ...res.data, items } };
    },

    updateGymPayment: (gymId: number, paymentId: number, updates: Partial<Payment>) =>
        request<{ ok: boolean; updated?: number; error?: string }>(`/gyms/${gymId}/payments/${paymentId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates),
        }),

    deleteGymPayment: (gymId: number, paymentId: number) =>
        request<{ ok: boolean; deleted?: number; error?: string }>(`/gyms/${gymId}/payments/${paymentId}`, {
            method: 'DELETE',
        }),

    // Branding
    getGymBranding: (gymId: number) =>
        request<{ branding: Record<string, unknown> }>(`/gyms/${gymId}/branding`),

    saveGymBranding: (gymId: number, branding: {
        nombre_publico?: string;
        direccion?: string;
        logo_url?: string;
        color_primario?: string;
        color_secundario?: string;
        color_fondo?: string;
        color_texto?: string;
        portal_tagline?: string;
        footer_text?: string;
        show_powered_by?: boolean;
        support_whatsapp_enabled?: boolean;
        support_whatsapp?: string;
        support_email_enabled?: boolean;
        support_email?: string;
        support_url_enabled?: boolean;
        support_url?: string;
        portal_enable_checkin?: boolean;
        portal_enable_member?: boolean;
        portal_enable_staff?: boolean;
        portal_enable_owner?: boolean;
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
        } catch {
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

    // Settings
    getSettings: () => request<{ ok: boolean; settings: Array<{ key: string; value: unknown; updated_at?: string; updated_by?: string }> }>('/settings'),

    updateSettings: (updates: Record<string, unknown>) =>
        request<{ ok: boolean; error?: string }>('/settings', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates),
        }),

    // Subscriptions
    getGymSubscription: (gymId: number) => request<unknown>(`/gyms/${gymId}/subscription`),

    upsertGymSubscription: (gymId: number, payload: { plan_id: number; start_date?: string; next_due_date?: string; status?: string }) =>
        request<unknown>(`/gyms/${gymId}/subscription`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        }),

    renewGymSubscription: (gymId: number, periods = 1) =>
        request<unknown>(`/gyms/${gymId}/subscription/renew`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ periods: String(periods) }),
        }),

    // Manual Subscription Assignment (New)
    assignGymSubscriptionManual: (gymId: number, data: { plan_id: number; start_date?: string; end_date?: string }) => {
        const params = new URLSearchParams();
        params.append('plan_id', String(data.plan_id));
        if (data.start_date) params.append('start_date', data.start_date);
        if (data.end_date) params.append('end_date', data.end_date);
        return request<{ ok: boolean }>(`/gyms/${gymId}/subscription`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: params,
        });
    },

    // Plans List for Admin (New)
    getAdminPlans: () => request<{ plans: Plan[] }>('/admin/plans'),

    listSubscriptions: async (params: { q?: string; status?: string; due_before_days?: number; page?: number; page_size?: number }) => {
        const qs = new URLSearchParams();
        for (const [k, v] of Object.entries(params || {})) {
            if (v === undefined || v === null || String(v).trim() === '') continue;
            qs.set(k, String(v));
        }
        return request<{ items: Array<{ gym_id: number; nombre: string; subdominio: string; plan_id?: number | null; next_due_date?: string | null; subscription_status?: string | null }>; total: number }>(`/subscriptions?${qs.toString()}`);
    },

    runSubscriptionsMaintenance: (params: { days?: number; grace_days?: number } = {}) =>
        request<{ ok: boolean; error?: string }>(
            '/subscriptions/maintenance/run',
            {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams(
                Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)]))
            ),
            }
        ),

    listJobRuns: (job_key: string, limit = 25) =>
        request<{ ok: boolean; items?: unknown[]; error?: string }>(`/jobs/runs?job_key=${encodeURIComponent(job_key)}&limit=${encodeURIComponent(String(limit))}`),

    getJobRun: (run_id: string) => request<{ ok: boolean; run?: unknown; error?: string }>(`/jobs/runs/${encodeURIComponent(run_id)}`),

    // Subdomain
    checkSubdomain: (subdomain: string) =>
        request<{ available: boolean }>(`/subdomain/check?subdomain=${subdomain}`),

    suggestSubdomain: (name: string) =>
        request<{ suggested: string }>(`/subdomain/suggest?name=${name}`),

    // Audit
    getAuditSummary: (days = 7) =>
        request<unknown>(`/audit?days=${days}`),

    getGymAudit: (gymId: number, limit = 50) =>
        request<{ ok: boolean; items?: unknown[]; error?: string }>(`/gyms/${gymId}/audit?limit=${encodeURIComponent(String(limit))}`),

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

    getGymOnboardingStatus: (gymId: number) =>
        request<GymOnboardingStatus>(`/gyms/${gymId}/onboarding`),

    setGymProductionReady: (gymId: number, ready: boolean) =>
        request<{ ok: boolean; production_ready?: boolean; production_ready_at?: string | null; error?: string }>(
            `/gyms/${gymId}/production-ready`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ready }),
            }
        ),

    listGymBranches: (gymId: number) =>
        request<{ ok: boolean; items: GymBranch[] }>(`/gyms/${gymId}/branches`),

    createGymBranch: (gymId: number, payload: GymBranchCreateInput) =>
        request<{ ok: boolean; branch?: GymBranch; error?: string }>(`/gyms/${gymId}/branches`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        }),

    updateGymBranch: (gymId: number, branchId: number, payload: GymBranchUpdateInput) =>
        request<{ ok: boolean; branch?: GymBranch; error?: string }>(`/gyms/${gymId}/branches/${branchId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        }),

    deleteGymBranch: (gymId: number, branchId: number) =>
        request<{ ok: boolean; branch?: GymBranch; error?: string }>(`/gyms/${gymId}/branches/${branchId}`, {
            method: 'DELETE',
        }),

    bulkCreateGymBranches: (gymId: number, items: GymBranchCreateInput[]) =>
        request<{ ok: boolean; created: number; failed: number; results: unknown[]; error?: string }>(`/gyms/${gymId}/branches/bulk`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ items }),
        }),

    syncGymBranches: (gymId: number) =>
        request<{ ok: boolean; items?: GymBranch[]; error?: string }>(`/gyms/${gymId}/branches/sync`, { method: 'POST' }),

    listGymTiposCuota: (gymId: number) =>
        request<{ ok: boolean; items: GymTipoCuotaItem[] }>(`/gyms/${gymId}/tipos-cuota`),

    listGymTiposClases: (gymId: number) =>
        request<{ ok: boolean; items: GymTipoClaseItem[] }>(`/gyms/${gymId}/tipos-clases`),

    getGymTipoCuotaEntitlements: (gymId: number, tipoCuotaId: number) =>
        request<TipoCuotaEntitlements>(`/gyms/${gymId}/tipos-cuota/${tipoCuotaId}/entitlements`),

    setGymTipoCuotaEntitlements: (gymId: number, tipoCuotaId: number, payload: TipoCuotaEntitlementsUpdate) =>
        request<{ ok: boolean }>(`/gyms/${gymId}/tipos-cuota/${tipoCuotaId}/entitlements`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        }),

    getGymFeatureFlags: (gymId: number, params?: { scope?: 'gym' | 'branch'; branch_id?: number }) => {
        const searchParams = new URLSearchParams();
        if (params?.scope) searchParams.set('scope', params.scope);
        if (params?.branch_id) searchParams.set('branch_id', String(params.branch_id));
        const qs = searchParams.toString();
        return request<{ ok: boolean; flags: FeatureFlags }>(`/gyms/${gymId}/feature-flags${qs ? `?${qs}` : ''}`);
    },

    setGymFeatureFlags: (gymId: number, flags: FeatureFlags, params?: { scope?: 'gym' | 'branch'; branch_id?: number }) => {
        const searchParams = new URLSearchParams();
        if (params?.scope) searchParams.set('scope', params.scope);
        if (params?.branch_id) searchParams.set('branch_id', String(params.branch_id));
        const qs = searchParams.toString();
        return request<{ ok: boolean; flags: FeatureFlags }>(`/gyms/${gymId}/feature-flags${qs ? `?${qs}` : ''}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ flags }),
        });
    },

    getGymReminderMessage: (id: number) =>
        request<{ message: string }>(`/gyms/${id}/reminder`),

    setGymReminderMessage: (id: number, message: string) =>
        request<{ ok: boolean }>(`/gyms/${id}/reminder`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message }),
        }),

    getGymAttendancePolicy: (id: number) =>
        request<{ ok: boolean; attendance_allow_multiple_per_day?: boolean; error?: string }>(`/gyms/${id}/attendance-policy`),

    setGymAttendancePolicy: (id: number, attendance_allow_multiple_per_day: boolean) =>
        request<{ ok: boolean; attendance_allow_multiple_per_day?: boolean; error?: string }>(`/gyms/${id}/attendance-policy`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ attendance_allow_multiple_per_day }),
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

    syncWhatsAppTemplateDefaults: (overwrite = true) =>
        request<{ ok: boolean; overwrite: boolean; created: number; updated: number; failed: Array<{ name: string; error: string }> }>(
            `/whatsapp/templates/sync-defaults?overwrite=${overwrite ? '1' : '0'}`,
            { method: 'POST' }
        ),

    bumpWhatsAppTemplateVersion: (templateName: string) =>
        request<{ ok: boolean; new_template_name: string }>(`/whatsapp/templates/bump-version`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ template_name: templateName }),
        }),

    getWhatsAppTemplateBindings: () => request<{ bindings: Record<string, string> }>(`/whatsapp/bindings`),

    upsertWhatsAppTemplateBinding: (bindingKey: string, templateName: string) =>
        request<{ ok: boolean }>(`/whatsapp/bindings/${encodeURIComponent(bindingKey)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ template_name: templateName }),
        }),

    syncWhatsAppTemplateBindings: (overwrite = true) =>
        request<{ ok: boolean; overwrite: boolean; created: number; updated: number; failed: Array<{ name: string; error: string }> }>(
            `/whatsapp/bindings/sync-defaults?overwrite=${overwrite ? '1' : '0'}`,
            { method: 'POST' }
        ),

    getWhatsAppActionSpecs: () =>
        request<{
            ok: boolean;
            items: Array<{
                action_key: string;
                label: string;
                required_params: number;
                default_enabled?: boolean;
                default_template_name?: string;
            }>;
        }>(`/whatsapp/actions/specs`),

    provisionGymWhatsAppTemplates: (gymId: number) =>
        request<{
            ok: boolean;
            existing_count: number;
            created: string[];
            created_bumped?: Array<{ from: string; to: string; reason: string }>;
            failed: Array<{ name: string; error: string }>;
        }>(
            `/gyms/${gymId}/whatsapp/provision-templates`,
            { method: 'POST' }
        ),

    getGymWhatsAppActions: (gymId: number) =>
        request<{
            ok: boolean;
            actions: Array<{
                action_key: string;
                enabled: boolean;
                template_name: string;
                required_params: number;
                default_enabled?: boolean;
                default_template_name?: string;
            }>;
        }>(
            `/gyms/${gymId}/whatsapp/actions`
        ),

    setGymWhatsAppAction: (gymId: number, actionKey: string, enabled: boolean, templateName: string) =>
        request<{ ok: boolean }>(`/gyms/${gymId}/whatsapp/actions/${encodeURIComponent(actionKey)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled, template_name: templateName }),
        }),

    getGymWhatsAppHealth: (gymId: number) =>
        request<unknown>(`/gyms/${gymId}/whatsapp/health`),

    getGymWhatsAppOnboardingEvents: (gymId: number, limit = 30) =>
        request<{ ok: boolean; events: Array<{ event_type: string; severity: string; message: string; details: unknown; created_at: string }> }>(
            `/gyms/${gymId}/whatsapp/onboarding-events?limit=${limit}`
        ),

    // ========== SUPPORT / TICKETS ==========
    listSupportTickets: (params?: { status?: string; priority?: string; tenant?: string; assignee?: string; q?: string; page?: number; page_size?: number }) => {
        const qp = new URLSearchParams();
        if (params?.status) qp.set('status', params.status);
        if (params?.priority) qp.set('priority', params.priority);
        if (params?.tenant) qp.set('tenant', params.tenant);
        if (params?.assignee) qp.set('assignee', params.assignee);
        if (params?.q) qp.set('q', params.q);
        if (params?.page) qp.set('page', String(params.page));
        if (params?.page_size) qp.set('page_size', String(params.page_size));
        const q = qp.toString() ? `?${qp.toString()}` : '';
        return request<{ ok: boolean; items: SupportTicketAdmin[]; total: number; page: number; page_size: number }>(`/support/tickets${q}`);
    },

    getSupportTicket: (ticketId: number) =>
        request<{ ok: boolean; ticket: SupportTicketAdmin; messages: SupportTicketMessageAdmin[] }>(`/support/tickets/${ticketId}`),

    updateSupportTicketStatus: (ticketId: number, status: string) =>
        request<{ ok: boolean }>(`/support/tickets/${ticketId}/status`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status }),
        }),

    patchSupportTicket: (ticketId: number, data: { status?: string; priority?: string; assigned_to?: string | null; tags?: unknown }) =>
        request<{ ok: boolean }>(`/support/tickets/${ticketId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        }),

    replySupportTicket: (ticketId: number, message: string, attachments: unknown[] = []) =>
        request<{ ok: boolean }>(`/support/tickets/${ticketId}/reply`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, attachments }),
        }),

    internalNoteSupportTicket: (ticketId: number, message: string) =>
        request<{ ok: boolean }>(`/support/tickets/${ticketId}/internal-note`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message }),
        }),

    getSupportOpsSummary: () =>
        request<{ ok: boolean; totals: Record<string, unknown>; by_assignee: Array<{ assignee: string | null; total: number; overdue: number }>; by_tenant: Array<{ tenant: string; total: number; overdue: number }> }>(`/support/ops/summary`),

    batchUpdateSupportTickets: (ticketIds: number[], data: Record<string, unknown>) =>
        request<{ ok: boolean; updated: number }>(`/support/tickets/batch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticket_ids: ticketIds, data }),
        }),

    getSupportTenantSettings: (tenant: string) =>
        request<{ ok: boolean; settings: Record<string, unknown> }>(`/support/tenants/${encodeURIComponent(tenant)}/settings`),

    setSupportTenantSettings: (tenant: string, payload: Record<string, unknown>) =>
        request<{ ok: boolean; settings: Record<string, unknown> }>(`/support/tenants/${encodeURIComponent(tenant)}/settings`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        }),

    // ========== CHANGELOGS ==========
    listChangelogs: (params?: { include_drafts?: boolean; page?: number; page_size?: number }) => {
        const qp = new URLSearchParams();
        if (params?.include_drafts !== undefined) qp.set('include_drafts', String(params.include_drafts));
        if (params?.page) qp.set('page', String(params.page));
        if (params?.page_size) qp.set('page_size', String(params.page_size));
        const q = qp.toString() ? `?${qp.toString()}` : '';
        return request<{ ok: boolean; items: ChangelogAdminItem[]; total: number; page: number; page_size: number }>(`/changelogs${q}`);
    },

    createChangelog: (data: Omit<ChangelogAdminItem, 'id'>) =>
        request<{ ok: boolean; id: number }>(`/changelogs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        }),

    updateChangelog: (id: number, data: Omit<ChangelogAdminItem, 'id'>) =>
        request<{ ok: boolean }>(`/changelogs/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        }),

    deleteChangelog: (id: number) =>
        request<{ ok: boolean }>(`/changelogs/${id}`, { method: 'DELETE' }),

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

    // ========== TEMPLATE MANAGEMENT ==========

    // Template CRUD
    getTemplates: (params?: {
        query?: string;
        categoria?: string;
        activa?: boolean;
        sort_by?: string;
        sort_order?: 'asc' | 'desc';
        limit?: number;
        offset?: number;
    }) => {
        const qp = new URLSearchParams();
        if (params?.query) qp.set('query', params.query);
        if (params?.categoria) qp.set('categoria', params.categoria);
        if (params?.activa !== undefined) qp.set('activa', String(params.activa));
        if (params?.sort_by) qp.set('sort_by', params.sort_by);
        if (params?.sort_order) qp.set('sort_order', params.sort_order);
        if (params?.limit) qp.set('limit', String(params.limit));
        if (params?.offset) qp.set('offset', String(params.offset));
        const q = qp.toString() ? `?${qp.toString()}` : '';
        return request<{
            success: boolean;
            templates: Template[];
            total: number;
            has_more: boolean;
            limit?: number;
            offset?: number;
        }>(`/api/v1/templates${q}`);
    },

    getTemplate: (id: number) =>
        request<{ success: boolean; template: Template }>(`/api/v1/templates/${id}`),

    createTemplate: (data: Partial<Template>) =>
        request<{ success: boolean; template: Template }>('/api/v1/templates', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        }),

    updateTemplate: (id: number, data: Partial<Template>) =>
        request<{ success: boolean; template: Template }>(`/api/v1/templates/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        }),

    deleteTemplate: (id: number) =>
        request<{ success: boolean }>(`/api/v1/templates/${id}`, { method: 'DELETE' }),

    duplicateTemplate: async (id: number) => {
        const srcRes = await request<{ success: boolean; template: Template }>(`/api/v1/templates/${id}`);
        if (!srcRes.ok || !srcRes.data?.success) return { ok: false, error: srcRes.error };
        const src = srcRes.data.template;

        const payload: Partial<Template> = {
            nombre: `${src.nombre || 'Plantilla'} (copia)`,
            categoria: src.categoria,
            descripcion: src.descripcion,
            configuracion: src.configuracion,
            publica: src.publica,
            activa: false,
            tags: src.tags,
        };

        return request<{ success: boolean; template: Template }>('/api/v1/templates', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
    },

    // Template Categories
    getTemplateCategories: () =>
        request<{ success: boolean; categories: string[] }>('/api/v1/templates/categories'),

    // Template Analytics
    getTemplateAnalytics: (id: number, days: number = 30) =>
        request<{ success: boolean; analytics: TemplateAnalytics }>(`/api/v1/templates/${id}/analytics?days=${days}`),

    getTemplateStats: async (timeRange?: '7d' | '30d' | '90d' | '1y' | 'all') => {
        const qp = new URLSearchParams();
        const days =
            timeRange === '7d'
                ? 7
                : timeRange === '30d'
                  ? 30
                  : timeRange === '90d'
                    ? 90
                    : timeRange === '1y'
                      ? 365
                      : 30;
        qp.set('days', String(days));
        const q = qp.toString() ? `?${qp.toString()}` : '';
        const res = await request<{ success: boolean; dashboard: Record<string, unknown>; period_days: number }>(
            `/api/v1/templates/analytics/dashboard${q}`
        );
        if (!res.ok || !res.data?.success) return { ok: false, error: res.error || 'Error' };

        const dash = isRecord(res.data.dashboard) ? res.data.dashboard : {};
        const overview = isRecord(dash.overview) ? dash.overview : {};
        const popularTemplates = Array.isArray(dash.popular_templates) ? dash.popular_templates : [];
        const categoryAnalytics = Array.isArray(dash.category_analytics) ? dash.category_analytics : [];

        const emptyConfig: TemplateConfig = {
            metadata: { name: '', version: 'v1', description: '' },
            layout: {
                page_size: 'A4',
                orientation: 'portrait',
                margins: { top: 12, right: 12, bottom: 12, left: 12 },
            },
            pages: [],
            variables: {},
        };

        const stats: TemplateStats = {
            total_templates: Number(overview.total_templates || 0),
            active_templates: Number(overview.total_templates || 0),
            total_usos: Number(overview.total_events || 0),
            usuarios_unicos: Number(overview.unique_users || 0),
            rating_promedio: 0,
            total_ratings: 0,
            categorias_populares: Array.isArray(categoryAnalytics)
                ? categoryAnalytics.map((c) => {
                      const rec = isRecord(c) ? c : {};
                      return {
                          categoria: String(rec.categoria ?? rec.category ?? ''),
                          count: Number(rec.count ?? rec.total ?? 0),
                      };
                  })
                : [],
            plantillas_top: Array.isArray(popularTemplates)
                ? popularTemplates.map((t) => {
                      const rec = isRecord(t) ? t : {};
                      const id = Number(rec.template_id ?? rec.id ?? 0) || 0;
                      const nombre = String(rec.nombre ?? '');
                      const categoria = String(rec.categoria ?? '');
                      return {
                          id,
                          nombre,
                          descripcion: undefined,
                          configuracion: emptyConfig,
                          categoria,
                          dias_semana: undefined,
                          activa: true,
                          publica: true,
                          creada_por: undefined,
                          fecha_creacion: new Date().toISOString(),
                          fecha_actualizacion: new Date().toISOString(),
                          version_actual: 'v1',
                          tags: undefined,
                          preview_url: undefined,
                          uso_count: 0,
                          rating_promedio: undefined,
                          rating_count: 0,
                      };
                  })
                : [],
        };

        return { ok: true, data: { success: true, stats } };
    },

    // Template Preview
    getTemplatePreview: (id: number, previewRequest: TemplatePreviewRequest) =>
        request<{ success: boolean; preview_url?: string; format: string; quality: string; page_number: number }>(
            `/api/v1/templates/${id}/preview?format=${encodeURIComponent(previewRequest.format)}&quality=${encodeURIComponent(previewRequest.quality)}&page_number=${encodeURIComponent(String(previewRequest.page_number || 1))}`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(previewRequest.sample_data ?? null),
            }
        ),
    getTemplatePreviewFromConfig: (configuracion: TemplateConfig, previewRequest: TemplatePreviewRequest) =>
        request<{ success: boolean; preview_url?: string; format: string; quality: string; page_number: number }>(
            `/api/v1/templates/preview?format=${encodeURIComponent(previewRequest.format)}&quality=${encodeURIComponent(previewRequest.quality)}&page_number=${encodeURIComponent(String(previewRequest.page_number || 1))}`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    configuracion,
                    sample_data: previewRequest.sample_data ?? null,
                }),
            }
        ),

    getRutinaPreviewWithTemplate: async (rutinaId: number, templateId: number, previewRequest: TemplatePreviewRequest) => {
        try {
            const qp = new URLSearchParams();
            qp.set('template_id', String(templateId));
            if (previewRequest.qr_mode) qp.set('qr_mode', previewRequest.qr_mode);

            const res = await fetch(`${API_URL}/api/rutinas/${rutinaId}/export/pdf?${qp.toString()}`, {
                method: 'GET',
                credentials: 'include',
            });

            if (!res.ok) {
                let msg = 'Request failed';
                try {
                    const data = await res.json();
                    msg = isRecord(data) ? String(data.error ?? data.detail ?? msg) : msg;
                } catch {
                    try {
                        msg = await res.text();
                    } catch {
                    }
                }
                return { ok: false, error: msg };
            }

            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            return { ok: true, data: { success: true, preview_url: url } };
        } catch {
            return { ok: false, error: 'Network error' };
        }
    },

    // Template Validation
    validateTemplate: (config: TemplateConfig) =>
        request<{ success: boolean; validation: TemplateValidation }>('/api/v1/templates/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config),
        }),

    // Template Versions
    getTemplateVersions: (id: number) =>
        request<{ success: boolean; versions: TemplateVersion[]; total: number }>(`/api/v1/templates/${id}/versions`),

    createTemplateVersion: (id: number, data: { version?: string; descripcion?: string; configuracion: TemplateConfig }) =>
        request<{ success: boolean; version: TemplateVersion; message?: string }>(`/api/v1/templates/${id}/versions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        }),

    restoreTemplateVersion: (id: number, version: string) =>
        request<{ success: boolean; message?: string }>(`/api/v1/templates/${id}/versions/${encodeURIComponent(version)}/restore`, {
            method: 'POST',
        }),

    bulkUpdateTemplates: async (templateIds: number[], data: Partial<Template>) => {
        const ids = Array.from(new Set(templateIds)).filter((id) => Number.isFinite(id));
        let updated = 0;
        for (const id of ids) {
            const res = await request<{ success: boolean; template: Template }>(`/api/v1/templates/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            if (res.ok && res.data?.success) updated += 1;
        }
        return { ok: true, data: { success: true, updated } };
    },

    exportTemplates: async (templateIds: number[]) => {
        const ids = Array.from(new Set(templateIds)).filter((id) => Number.isFinite(id));
        const exports: Array<{ id: number; export_data: unknown }> = [];
        for (const id of ids) {
            const res = await request<{ success: boolean; export_data: unknown; filename?: string }>(
                `/api/v1/templates/${id}/export`
            );
            if (res.ok && res.data?.success) exports.push({ id, export_data: res.data.export_data });
        }
        const blob = new Blob([JSON.stringify({ templates: exports }, null, 2)], {
            type: 'application/json',
        });
        const url = URL.createObjectURL(blob);
        return { ok: true, data: { success: true, download_url: url } };
    },
};

export default api;
