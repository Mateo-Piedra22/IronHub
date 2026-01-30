/**
 * API Client for webapp-web
 * Handles all communication with webapp-api
 * Supports multi-tenant with dynamic API URL based on subdomain
 */

import { getCurrentTenant, getCsrfTokenFromCookie } from '@/lib/tenant';
const TENANT_DOMAIN = process.env.NEXT_PUBLIC_TENANT_DOMAIN || 'ironhub.motiona.xyz';

/**
 * Build the API base URL for the current tenant
 * 
 * ARCHITECTURE: Single API deployment at api.ironhub.motiona.xyz
 * Tenant context is passed via:
 * - X-Tenant header (set automatically by ApiClient)
 * - Origin header extraction (middleware on backend)
 * - Session cookie (after login)
 */
function getApiBaseUrl(): string {
    // 1. Check for explicit override (dev/testing)
    const staticUrl = process.env.NEXT_PUBLIC_API_URL;
    if (staticUrl) return staticUrl;

    // 2. Default production API URL
    // The API is deployed at a single domain and handles multi-tenancy
    // via headers/cookies, not per-tenant subdomains
    return `https://api.${TENANT_DOMAIN}`;
}

// Get API base URL (dynamically or from env)
const API_BASE_URL = typeof window !== 'undefined' ? getApiBaseUrl() : '';

// Types for API responses
export interface ApiResponse<T> {
    ok: boolean;
    data?: T;
    error?: string;
}

type CacheEntry<T> = {
    ts: number;
    data: ApiResponse<T>;
    etag?: string;
};

const _inMemoryCache: Record<string, CacheEntry<any> | undefined> = {};
const _inFlight: Record<string, Promise<any> | undefined> = {};
const _MAX_CACHE_ENTRIES = 250;

function _setCache<T>(key: string, entry: CacheEntry<T>) {
    _inMemoryCache[key] = entry;
    try {
        const keys = Object.keys(_inMemoryCache);
        if (keys.length > _MAX_CACHE_ENTRIES) {
            keys
                .sort((a, b) => (Number(_inMemoryCache[a]?.ts || 0) - Number(_inMemoryCache[b]?.ts || 0)))
                .slice(0, Math.max(1, keys.length - _MAX_CACHE_ENTRIES))
                .forEach((k) => {
                    delete _inMemoryCache[k];
                });
        }
    } catch {
    }
}

function _clearCacheByPrefix(prefix: string) {
    try {
        const p = String(prefix || '');
        if (!p) return;
        Object.keys(_inMemoryCache).forEach((k) => {
            if (k.startsWith(p)) delete _inMemoryCache[k];
        });
    } catch {
    }
}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
}

// === User Types ===
export interface Usuario {
    id: number;
    nombre: string;
    dni?: string;
    telefono?: string;
    email?: string;
    activo: boolean;
    rol: 'user' | 'admin' | 'profesor' | 'owner';
    tipo_cuota_id?: number;
    tipo_cuota_nombre?: string;
    tipo_cuota_duracion_dias?: number;
    fecha_registro?: string;
    fecha_proximo_vencimiento?: string;
    dias_restantes?: number;
    cuotas_vencidas?: number;
    exento?: boolean;
    notas?: string;
    sucursal_registro_id?: number | null;
    sucursal_registro_nombre?: string | null;
}

export interface UsuarioEntitlements {
    ok?: boolean;
    enabled: boolean;
    sucursal_actual_id?: number | null;
    branch_access?: {
        all_sucursales: boolean;
        allowed_sucursal_ids: number[];
        denied_sucursal_ids: number[];
    } | null;
    allowed_sucursales: Sucursal[];
    class_allowlist_enabled: boolean;
    allowed_tipo_clases: { id: number; nombre: string; activo: boolean }[];
    allowed_clases: { id: number; nombre: string; sucursal_id?: number | null; activa: boolean }[];
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
    class_rules: { sucursal_id?: number | null; target_type: 'tipo_clase' | 'clase'; target_id: number; allow: boolean }[];
}

export interface UsuarioEntitlementsGestion {
    ok: boolean;
    branch_overrides: { id: number; sucursal_id: number; allow: boolean; motivo?: string; starts_at?: string | null; ends_at?: string | null }[];
    class_overrides: { id: number; sucursal_id?: number | null; target_type: string; target_id: number; allow: boolean; motivo?: string; starts_at?: string | null; ends_at?: string | null }[];
}

export interface UsuarioEntitlementsGestionUpdate {
    branch_overrides: { sucursal_id: number; allow: boolean; motivo?: string; starts_at?: string | null; ends_at?: string | null }[];
    class_overrides: { sucursal_id?: number | null; target_type: 'tipo_clase' | 'clase'; target_id: number; allow: boolean; motivo?: string; starts_at?: string | null; ends_at?: string | null }[];
}

export interface UsuarioCreateInput {
    nombre: string;
    dni?: string;
    telefono?: string;
    email?: string;
    tipo_cuota_id?: number;
    activo?: boolean;
    rol?: string;
    notas?: string;
}

// === Payment Types ===
export interface Pago {
    id: number;
    usuario_id: number;
    usuario_nombre?: string;
    monto: number;
    fecha: string;
    fecha_pago?: string;
    mes?: number;
    anio?: number;
    sucursal_id?: number | null;
    sucursal_nombre?: string | null;
    metodo_pago_id?: number;
    metodo_pago_nombre?: string;
    metodo_pago?: string;
    concepto_id?: number;
    concepto_nombre?: string;
    tipo_cuota_id?: number;
    tipo_cuota_nombre?: string;
    notas?: string;
    recibo_numero?: string | number;
    estado?: string;
}

// Multi-concept payment line item
export interface PagoConceptoItem {
    concepto_id?: number;      // Optional - use registered concept
    descripcion?: string;      // Required when no concepto_id
    cantidad: number;          // Quantity (default: 1)
    precio_unitario: number;   // Unit price
}

// Preset templates for common payment combinations
export interface PagoPresetTemplate {
    id: string;
    nombre: string;
    conceptos: Omit<PagoConceptoItem, 'concepto_id'>[];
}

export const PAGO_PRESET_TEMPLATES: PagoPresetTemplate[] = [
    {
        id: 'cuota_mensual',
        nombre: 'Cuota Mensual',
        conceptos: [{ descripcion: 'Cuota Mensual', cantidad: 1, precio_unitario: 0 }]
    },
    {
        id: 'cuota_personal',
        nombre: 'Cuota + Personal Training',
        conceptos: [
            { descripcion: 'Cuota Mensual', cantidad: 1, precio_unitario: 0 },
            { descripcion: 'Personal Training', cantidad: 1, precio_unitario: 0 }
        ]
    },
    {
        id: 'inscripcion',
        nombre: 'Inscripción + Cuota',
        conceptos: [
            { descripcion: 'Inscripción', cantidad: 1, precio_unitario: 0 },
            { descripcion: 'Cuota Mensual', cantidad: 1, precio_unitario: 0 }
        ]
    }
];

export interface PagoCreateInput {
    usuario_id: number;
    monto?: number;            // Calculated from conceptos
    fecha_pago?: string;       // ISO date string for payment date
    mes?: number;
    anio?: number;
    metodo_pago_id?: number;
    notas?: string;
    // Multi-concept support (required)
    conceptos: PagoConceptoItem[];
}

// === Profesor Types ===
export interface Profesor {
    id: number;
    nombre: string;
    email?: string;
    telefono?: string;
    activo: boolean;
    horarios?: Horario[];
    usuario_id?: number;
    tipo?: string | null;
    scopes?: string[];
}

export interface Horario {
    id: number;
    profesor_id: number;
    dia_semana: number; // 0-6 (Sunday-Saturday)
    hora_inicio: string; // HH:MM
    hora_fin: string;
}

export interface Sesion {
    id: number;
    profesor_id: number;
    fecha: string;
    hora_inicio: string;
    hora_fin: string;
    minutos: number;
    tipo: 'normal' | 'extra';
    inicio?: string | null;
    fin?: string | null;
    notas?: string | null;
}

// === Rutina Types ===
export interface Rutina {
    id: number;
    nombre: string;
    descripcion?: string;
    categoria?: string;
    activa: boolean;
    es_plantilla: boolean;
    usuario_id?: number;
    usuario_nombre?: string;
    uuid_rutina?: string;
    dias: DiasRutina[];
    fecha_creacion?: string;
    sucursal_id?: number | null;
    sucursal_nombre?: string | null;
    creada_por_usuario_id?: number | null;
    creada_por_nombre?: string | null;
}

export interface DiasRutina {
    id?: number;
    numero: number;
    nombre?: string;
    ejercicios: EjercicioRutina[];
}

export interface EjercicioRutina {
    id?: number;
    ejercicio_id: number;
    ejercicio_nombre?: string;
    series?: number | string;
    repeticiones?: string;
    descanso?: number;
    notas?: string;
    orden: number;
    dia?: number;
    video_url?: string;
    ejercicio_video_url?: string;
    descripcion?: string;
    equipamiento?: string;
}

// === Ejercicio Types ===
export interface Ejercicio {
    id: number;
    nombre: string;
    descripcion?: string;
    video_url?: string;
    grupo_muscular?: string;
    equipamiento?: string;
    variantes?: string;
    objetivo?: string;
}

// === Clase Types ===
export interface Clase {
    id: number;
    nombre: string;
    descripcion?: string;
    hora_inicio?: string;
    hora_fin?: string;
    dia_semana?: number;
    profesor_id?: number | null;
    profesor_nombre?: string | null;
    capacidad?: number | null;
    color?: string | null;
    activo?: boolean;
    activa?: boolean;
}

export interface ClaseBloque {
    id: number;
    clase_id: number;
    nombre: string;
}

export interface ClaseBloqueItem {
    id?: number;
    bloque_id?: number;
    ejercicio_id: number;
    nombre_ejercicio?: string;
    orden: number;
    series?: number;
    repeticiones?: string;
    descanso_segundos?: number;
    notas?: string;
}

// === Asistencia Types ===
export interface Asistencia {
    id: number;
    usuario_id: number;
    usuario_nombre?: string;
    usuario_dni?: string;
    fecha: string;
    hora?: string;
    hora_entrada?: string;
    hora_salida?: string;
    duracion_minutos?: number;
    tipo?: string;
    sucursal_id?: number | null;
    sucursal_nombre?: string | null;
}

// === Config Types ===
export interface TipoCuota {
    id: number;
    nombre: string;
    precio?: number;
    duracion_dias?: number;
    activo: boolean;
}

export interface MetodoPago {
    id: number;
    nombre: string;
    activo: boolean;
}

export interface ConceptoPago {
    id: number;
    nombre: string;
    activo: boolean;
}

// === Gym / Session ===
export interface GymData {
    id?: number;
    nombre: string;
    logo_url?: string;
    theme?: Record<string, string>;
    subdominio?: string;
}

export interface PublicGymData {
    gym_name?: string;
    logo_url?: string;
}

export interface MaintenanceStatus {
    active: boolean;
    active_now?: boolean;
    until?: string;
    message?: string;
}

export interface SuspensionStatus {
    suspended: boolean;
    reason?: string;
    until?: string;
    hard?: boolean;
}

export interface BootstrapPayload {
    tenant?: string | null;
    gym: PublicGymData;
    session: { authenticated: boolean; user?: SessionUser | null };
    sucursales?: Sucursal[];
    sucursal_actual_id?: number | null;
    branch_required?: boolean;
    flags?: Record<string, any>;
}

export interface FeatureFlags {
    modules?: Record<string, boolean>;
}

export interface SessionUser {
    id: number;
    nombre: string;
    rol: 'owner' | 'admin' | 'profesor' | 'empleado' | 'recepcionista' | 'staff' | 'user';
    dni?: string;
    gestion_profesor_id?: number | null;
    sucursal_id?: number | null;
    scopes?: string[];
}

export interface Sucursal {
    id: number;
    nombre: string;
    codigo: string;
    activa: boolean;
    direccion?: string | null;
    timezone?: string | null;
}

export interface StaffItem {
    id: number;
    nombre: string;
    dni: string;
    email: string;
    rol: string;
    activo: boolean;
    staff?: { tipo?: string | null; estado?: string | null } | null;
    sucursales: number[];
    scopes: string[];
}

export interface Membership {
    id: number;
    usuario_id: number;
    plan_name?: string | null;
    status: string;
    start_date: string;
    end_date?: string | null;
    all_sucursales: boolean;
}

// === User Tags & States ===
export interface Etiqueta {
    id: number;
    usuario_id: number;
    nombre: string;
    created_at?: string;
}

export interface Estado {
    id: number;
    usuario_id: number;
    nombre: string;
    descripcion?: string;
    fecha_vencimiento?: string;
    activo: boolean;
    created_at?: string;
}

export interface EstadoTemplate {
    id: number;
    nombre: string;
    color?: string;
}

// === Clase Types Extended ===
export interface ClaseTipo {
    id: number;
    nombre: string;
    color?: string;
    activo: boolean;
}

export interface ClaseHorario {
    id: number;
    clase_id: number;
    dia: string;
    hora_inicio: string;
    hora_fin: string;
    profesor_id?: number;
    profesor_nombre?: string;
    cupo?: number;
    inscriptos_count?: number;
}

export interface ClaseAgendaItem {
    horario_id: number;
    clase_id: number;
    clase_nombre: string;
    clase_descripcion?: string | null;
    dia: string;
    hora_inicio: string;
    hora_fin: string;
    profesor_id?: number | null;
    profesor_nombre?: string | null;
    cupo?: number | null;
    inscriptos_count?: number;
}

export interface Inscripcion {
    id: number;
    horario_id: number;
    usuario_id: number;
    usuario_nombre?: string;
    usuario_telefono?: string;
    fecha_inscripcion?: string;
}

export interface ListaEspera {
    id: number;
    horario_id: number;
    usuario_id: number;
    usuario_nombre?: string;
    posicion: number;
    fecha_registro?: string;
}

export interface ClaseEjercicio {
    id: number;
    clase_id: number;
    ejercicio_id: number;
    ejercicio_nombre?: string;
    orden: number;
    ejercicio?: Ejercicio;
}

// === Profesor Types Extended ===
export interface ProfesorHorario {
    id: number;
    profesor_id: number;
    dia: string;
    hora_inicio: string;
    hora_fin: string;
    disponible: boolean;
}

export interface ProfesorConfig {
    id: number;
    profesor_id: number;
    usuario_vinculado_id?: number;
    usuario_vinculado_nombre?: string;
    monto?: number;
    monto_tipo: 'mensual' | 'hora';
    especialidad?: string;
    experiencia_anios?: number;
    certificaciones?: string;
    notas?: string;
}

export interface ProfesorResumen {
    horas_trabajadas: number;
    horas_proyectadas: number;
    horas_extra: number;
    horas_totales: number;
}

// === WhatsApp Types ===
export interface WhatsAppConfig {
    id?: number;
    phone_number_id?: string;
    whatsapp_business_account_id?: string;
    access_token?: string;
    access_token_present?: boolean;
    webhook_verify_token?: string;
    enabled: boolean;
    webhook_enabled: boolean;
}

export interface WhatsAppMensaje {
    id: number;
    usuario_id: number;
    usuario_nombre?: string;
    telefono?: string;
    tipo: string;
    estado: string;
    contenido?: string;
    error_detail?: string;
    fecha_envio?: string;
    created_at?: string;
}

export interface WhatsAppMensajesTotals {
    by_estado: Record<string, number>;
    by_tipo: Record<string, number>;
}

export interface WhatsAppMensajesResponse {
    mensajes: WhatsAppMensaje[];
    totals?: WhatsAppMensajesTotals;
}

export interface WhatsAppStatus {
    available: boolean;
    enabled: boolean;
    server_ok: boolean;
    config_valid: boolean;
}

export interface WhatsAppEmbeddedSignupConfig {
    app_id: string;
    config_id: string;
    api_version: string;
}

export interface WhatsAppEmbeddedSignupReadiness {
    ok: boolean;
    app_id_present: boolean;
    app_secret_present: boolean;
    config_id_present: boolean;
    api_version: string;
    redirect_uri?: string;
    waba_encryption_key_present: boolean;
    missing: string[];
    recommended_urls?: {
        privacy_policy?: string;
        terms?: string;
        data_deletion_instructions?: string;
        data_deletion_callback?: string;
    };
}

export interface WhatsAppTemplate {
    template_name: string;
    body_text: string;
    active: boolean;
    created_at?: string;
}

export interface WhatsAppTrigger {
    trigger_key: string;
    enabled: boolean;
    template_name?: string | null;
    cooldown_minutes: number;
    last_run_at?: string | null;
}

export interface WhatsAppOnboardingStatus {
    connected: boolean;
    health: any;
    actions: { enabled_keys: number; template_keys: number };
}

// === Recibo Types ===
export interface ReciboConfig {
    prefijo: string;
    separador: string;
    numero_inicial: number;
    longitud_numero: number;
    reiniciar_anual: boolean;
    incluir_anio: boolean;
    incluir_mes: boolean;
}

export interface ReciboItem {
    descripcion: string;
    cantidad: number;
    precio: number;
}

export interface ReciboPreview {
    numero?: string;
    titulo: string;
    fecha: string;
    gym_nombre: string;
    gym_direccion?: string;
    logo_url?: string;
    usuario_nombre: string;
    usuario_dni?: string;
    metodo_pago?: string;
    items: ReciboItem[];
    subtotal: number;
    total: number;
    observaciones?: string;
    emitido_por?: string;
    mostrar_logo: boolean;
    mostrar_metodo: boolean;
    mostrar_dni: boolean;
}

// === API Client Class ===
class ApiClient {
    private baseUrl: string;

    constructor(baseUrl: string) {
        this.baseUrl = baseUrl;
    }

    private async request<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<ApiResponse<T>> {
        try {
            const url = `${this.baseUrl}${endpoint}`;
            const method = (options.method || 'GET').toUpperCase();
            const isGet = method === 'GET';
            const cacheKey = `${method}:${url}`;
            const now = Date.now();

            const cached = isGet ? _inMemoryCache[cacheKey] : undefined;
            if (isGet && cached && now - cached.ts < 1500) {
                return cached.data as ApiResponse<T>;
            }

            if (isGet && _inFlight[cacheKey]) {
                return (await _inFlight[cacheKey]) as ApiResponse<T>;
            }

            const doFetch = async (): Promise<ApiResponse<T>> => {
                const headers: Record<string, string> = {
                    'X-Tenant': typeof window !== 'undefined' ? getCurrentTenant() : '',
                };
                try {
                    const m = method.toUpperCase();
                    const isWrite = m !== 'GET';
                    const isAuthRoute = endpoint.startsWith('/api/auth/');
                    if (isWrite && !isAuthRoute && typeof document !== 'undefined') {
                        const csrf = getCsrfTokenFromCookie();
                        if (csrf) headers['X-CSRF-Token'] = csrf;
                    }
                } catch {}
                if (!((options.body instanceof FormData) || (options.body instanceof URLSearchParams))) {
                    headers['Content-Type'] = 'application/json';
                }
                for (const [k, v] of Object.entries((options.headers as any) || {})) {
                    headers[k] = String(v);
                }
                if (isGet && cached?.etag && !headers['If-None-Match']) {
                    headers['If-None-Match'] = cached.etag;
                }

                const response = await fetch(url, {
                    ...options,
                    method,
                    credentials: 'include',
                    headers,
                });

                if (isGet && response.status === 304 && cached) {
                    const hit = cached.data as ApiResponse<T>;
                    _setCache(cacheKey, { ts: now, data: hit, etag: cached.etag });
                    return hit;
                }

                const data = await response.json().catch(() => ({}));

                if (!response.ok) {
                    return {
                        ok: false,
                        error: (data as any).detail || (data as any).message || (data as any).error || 'Error de servidor',
                    };
                }

                const okRes: ApiResponse<T> = { ok: true, data: data as T };
                if (isGet) {
                    const etag = response.headers.get('etag') || undefined;
                    _setCache(cacheKey, { ts: now, data: okRes, etag: etag || cached?.etag });
                }
                return okRes;
            };

            const p = doFetch();
            if (isGet) _inFlight[cacheKey] = p;
            try {
                return await p;
            } finally {
                if (isGet) delete _inFlight[cacheKey];
            }
        } catch (error) {
            console.error('API Error:', error);
            return {
                ok: false,
                error: 'Error de conexión. Verifica tu conexión a internet.',
            };
        }
    }

    async uploadGymLogo(file: File): Promise<ApiResponse<{ ok: boolean; logo_url?: string; error?: string }>> {
        const formData = new FormData();
        formData.append('file', file);
        try {
            const url = `${this.baseUrl}/api/gym/logo`;
            const headers: Record<string, string> = { 'X-Tenant': typeof window !== 'undefined' ? getCurrentTenant() : '' };
            try {
                if (typeof document !== 'undefined') {
                    const csrf = getCsrfTokenFromCookie();
                    if (csrf) headers['X-CSRF-Token'] = csrf;
                }
            } catch {}
            const response = await fetch(url, {
                method: 'POST',
                body: formData,
                credentials: 'include',
                headers,
            });

            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                return {
                    ok: false,
                    error: data?.error || data?.detail || `Error ${response.status}`,
                };
            }

            return { ok: true, data };
        } catch {
            return {
                ok: false,
                error: 'Error de conexión. Verifica tu conexión a internet.',
            };
        }
    }

    // === Auth ===
    async login(credentials: { dni: string; password: string }) {
        return this.request<{ ok: boolean; user: SessionUser }>('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify(credentials),
        });
    }

    // Usuario login with DNI + PIN (for /usuario-login)
    async usuarioLogin(credentials: { dni: string; pin: string }) {
        return this.request<{
            success: boolean;
            user_id?: number;
            activo?: boolean;
            message?: string;
            cuotas_vencidas?: number;
            dias_restantes?: number;
            fecha_proximo_vencimiento?: string;
            exento?: boolean;
            tipo_cuota_nombre?: string | null;
            tipo_cuota_duracion_dias?: number;
        }>('/api/usuario/login', {
            method: 'POST',
            body: JSON.stringify(credentials),
        });
    }

    // Gestion login with professor selector or owner (for /gestion-login)
    async gestionLogin(credentials: {
        usuario_id?: string; // '__OWNER__' for owner (legacy) or numeric user ID
        profesor_id?: string; // professor profile id
        pin?: string;
        owner_password?: string;
    }) {
        return this.request<{ ok: boolean; message?: string }>('/gestion/auth', {
            method: 'POST',
            body: JSON.stringify(credentials),
        });
    }

    // Owner-only login (for /login - dashboard)
    async ownerLogin(password: string) {
        return this.request<{ ok: boolean; message?: string }>('/login', {
            method: 'POST',
            body: JSON.stringify({ password }),
        });
    }

    // Check-in auth with DNI (phone optional)
    async checkinAuth(credentials: { dni: string; telefono?: string }) {
        return this.request<{
            success: boolean;
            message?: string;
            usuario_id?: number;
            token?: string;
            cuotas_vencidas?: number;
            dias_restantes?: number;
            fecha_proximo_vencimiento?: string;
            exento?: boolean;
            activo?: boolean;
            tipo_cuota_nombre?: string | null;
            tipo_cuota_duracion_dias?: number;
        }>('/api/checkin/auth', {
            method: 'POST',
            body: JSON.stringify(credentials),
        });
    }

    // Scan station QR
    async scanStationQR(token: string, idempotencyKey?: string) {
        return this.request<{
            ok: boolean;
            mensaje: string;
            usuario?: {
                nombre: string;
                dni: string;
            };
        }>('/api/checkin/qr', {
            method: 'POST',
            body: JSON.stringify({ token, ...(idempotencyKey ? { idempotency_key: idempotencyKey } : {}) }),
        });
    }

    // Get basic professor list for gestion login dropdown
    async getProfesoresBasico() {
        return this.request<Array<{
            nombre: string;
            profesor_id: number;
        }>>('/api/profesores_basico');
    }

    async getGestionLoginProfiles() {
        return this.request<{ ok: boolean; items: Array<{ kind: 'owner' | 'user'; id: string | number; nombre: string; rol: string }> }>(
            '/api/gestion/login-profiles'
        );
    }

    // Change user PIN (for usuario-login)
    async changePin(credentials: { dni: string; old_pin: string; new_pin: string }) {
        return this.request<{ ok: boolean; error?: string }>('/api/usuario/change_pin', {
            method: 'POST',
            body: JSON.stringify(credentials),
        });
    }

    async logout() {
        return this.request<{ ok: boolean }>('/api/auth/logout_user', {
            method: 'POST',
        });
    }

    async logoutGestion() {
        return this.request<{ ok: boolean }>('/api/auth/logout_gestion', {
            method: 'POST',
        });
    }

    async resetUsuarioPin(usuarioId: number, pin?: string) {
        return this.request<{ ok: boolean; usuario_id: number; pin: string; error?: string }>(`/api/usuarios/${usuarioId}/pin/reset`, {
            method: 'POST',
            body: JSON.stringify(pin ? { pin } : {}),
        });
    }

    async getSession(context?: 'auto' | 'gestion' | 'usuario') {
        const cacheKey = `GET:/api/auth/session:${context || 'auto'}`;
        const now = Date.now();
        const cached = _inMemoryCache[cacheKey];
        if (cached && now - cached.ts < 10_000) {
            return cached.data as ApiResponse<{ authenticated: boolean; user?: SessionUser }>;
        }
        const p = new URLSearchParams();
        if (context) p.set('context', context);
        const qs = p.toString();
        const res = await this.request<{ authenticated: boolean; user?: SessionUser }>(
            `/api/auth/session${qs ? `?${qs}` : ''}`
        );
        _setCache(cacheKey, { ts: now, data: res });
        return res;
    }

    async getBootstrap(context?: 'auto' | 'gestion' | 'usuario') {
        const ctx = context || 'auto';
        const cacheKey = `GET:/api/bootstrap:${ctx}`;
        const now = Date.now();
        const cached = _inMemoryCache[cacheKey];
        if (cached && now - cached.ts < 5_000) {
            return cached.data as ApiResponse<BootstrapPayload>;
        }
        const p = new URLSearchParams();
        if (ctx) p.set('context', ctx);
        const qs = p.toString();
        const res = await this.request<BootstrapPayload>(`/api/bootstrap${qs ? `?${qs}` : ''}`);
        _setCache(cacheKey, { ts: now, data: res });

        try {
            if (res.ok && res.data?.gym) {
                _setCache(`GET:/gym/data:${getCurrentTenant() || ''}`, { ts: now, data: { ok: true, data: res.data.gym } });
            }
            if (res.ok && res.data?.session) {
                _setCache(`GET:/api/auth/session:${ctx}`, {
                    ts: now,
                    data: { ok: true, data: { authenticated: !!res.data.session.authenticated, user: (res.data.session.user as any) || undefined } }
                });
            }
        } catch {
        }
        return res;
    }

    async getSucursales() {
        return this.request<{ ok: boolean; items: Sucursal[]; sucursal_actual_id?: number | null }>('/api/sucursales');
    }

    async seleccionarSucursal(sucursal_id: number) {
        const res = await this.request<{ ok: boolean; sucursal_actual_id?: number | null; error?: string }>(
            '/api/sucursales/seleccionar',
            {
                method: 'POST',
                body: JSON.stringify({ sucursal_id }),
            }
        );
        try {
            _clearCacheByPrefix('GET:/api/bootstrap');
            _clearCacheByPrefix('GET:/api/auth/session');
        } catch {
        }
        return res;
    }

    async updateSucursal(sucursalId: number, payload: Partial<{ nombre: string; codigo: string; direccion: string | null; timezone: string | null; activa: boolean }>) {
        return this.request<{ ok: boolean; error?: string }>(`/api/sucursales/${sucursalId}`, {
            method: 'PUT',
            body: JSON.stringify(payload),
        });
    }

    async getStaff(search: string = '', opts?: { all?: boolean }) {
        const qp = new URLSearchParams();
        if (search) qp.set('search', search);
        if (opts?.all) qp.set('all', '1');
        const q = qp.toString() ? `?${qp.toString()}` : '';
        return this.request<{ items: StaffItem[] }>(`/api/staff${q}`);
    }

    async updateStaff(usuario_id: number, payload: Partial<StaffItem> & { tipo?: string; estado?: string }) {
        return this.request<{ ok: boolean }>(`/api/staff/${usuario_id}`, {
            method: 'PUT',
            body: JSON.stringify(payload),
        });
    }

    // === Gym Data ===
    async getGymData() {
        const cacheKey = 'GET:/api/gym/data';
        const now = Date.now();
        const cached = _inMemoryCache[cacheKey];
        if (cached && now - cached.ts < 5 * 60 * 1000) {
            return cached.data as ApiResponse<GymData>;
        }
        const res = await this.request<GymData>('/api/gym/data');
        try {
            if (res.ok && res.data?.logo_url && res.data.logo_url.startsWith('/')) {
                res.data.logo_url = `${this.baseUrl}${res.data.logo_url}`;
            }
        } catch {
        }
        _setCache(cacheKey, { ts: now, data: res });
        return res;
    }

    async getFeatureFlags() {
        return this.request<{ ok: boolean; flags: FeatureFlags }>('/api/gym/feature-flags');
    }

    async setFeatureFlags(flags: FeatureFlags) {
        const res = await this.request<{ ok: boolean; flags: FeatureFlags }>(
            '/api/gym/feature-flags',
            {
                method: 'POST',
                body: JSON.stringify({ flags }),
            }
        );
        try {
            _clearCacheByPrefix('GET:/api/bootstrap');
        } catch {
        }
        return res;
    }

    async getPublicGymData() {
        const cacheKey = `GET:/gym/data:${getCurrentTenant() || ''}`;
        const now = Date.now();
        const cached = _inMemoryCache[cacheKey];
        if (cached && now - cached.ts < 5 * 60 * 1000) {
            return cached.data as ApiResponse<PublicGymData>;
        }
        const res = await this.request<PublicGymData>('/gym/data');
        try {
            if (res.ok && res.data?.logo_url && res.data.logo_url.startsWith('/')) {
                res.data.logo_url = `${this.baseUrl}${res.data.logo_url}`;
            }
        } catch {
        }
        _setCache(cacheKey, { ts: now, data: res });
        return res;
    }

    async getMaintenanceStatus() {
        return this.request<MaintenanceStatus>('/maintenance_status');
    }

    async getSuspensionStatus() {
        return this.request<SuspensionStatus>('/suspension_status');
    }

    // === Usuarios ===
    async getUsuarios(params?: { search?: string; activo?: boolean; page?: number; limit?: number }) {
        const searchParams = new URLSearchParams();
        if (params?.search) searchParams.set('search', params.search);
        if (params?.activo !== undefined) searchParams.set('activo', String(params.activo));
        if (params?.page) searchParams.set('page', String(params.page));
        if (params?.limit) searchParams.set('limit', String(params.limit));

        const query = searchParams.toString();
        return this.request<{ usuarios: Usuario[]; total: number }>(
            `/api/usuarios${query ? `?${query}` : ''}`
        );
    }

    async getUsuario(id: number) {
        return this.request<Usuario>(`/api/usuarios/${id}`);
    }

    async getUsuarioEntitlements() {
        return this.request<UsuarioEntitlements>(`/api/usuario/entitlements`);
    }

    async checkDniAvailable(dni: string, excludeId?: number) {
        const params = new URLSearchParams({ dni });
        if (excludeId !== undefined) params.set('exclude_id', String(excludeId));
        return this.request<{ available: boolean; user_id?: number; user_name?: string }>(
            `/api/usuarios/check-dni?${params.toString()}`
        );
    }

    async createUsuario(data: UsuarioCreateInput) {
        return this.request<Usuario>('/api/usuarios', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async updateUsuario(id: number, data: Partial<UsuarioCreateInput>) {
        return this.request<Usuario>(`/api/usuarios/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async deleteUsuario(id: number) {
        return this.request<{ ok: boolean }>(`/api/usuarios/${id}`, {
            method: 'DELETE',
        });
    }

    async toggleUsuarioActivo(id: number) {
        return this.request<Usuario>(`/api/usuarios/${id}/toggle-activo`, {
            method: 'POST',
        });
    }

    // === Files ===
    async uploadExerciseVideo(file: File, name?: string): Promise<ApiResponse<{ url: string; mime: string }>> {
        const formData = new FormData();
        formData.append('file', file);
        try {
            const p = new URLSearchParams();
            if (name) p.set('name', String(name));
            const url = `${this.baseUrl}/api/exercises/video${p.toString() ? `?${p.toString()}` : ''}`;
            const headers: Record<string, string> = {
                'X-Tenant': typeof window !== 'undefined' ? getCurrentTenant() : '',
            };
            try {
                if (typeof document !== 'undefined') {
                    const csrf = getCsrfTokenFromCookie();
                    if (csrf) headers['X-CSRF-Token'] = csrf;
                }
            } catch {}
            const response = await fetch(url, {
                method: 'POST',
                body: formData,
                credentials: 'include', // Ensure cookies are sent
                headers,
                // Do NOT set 'Content-Type' header for FormData, browser handles it
            });

            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                return {
                    ok: false,
                    error: data.detail || data.message || data.error || 'Error de servidor',
                };
            }

            return { ok: true, data: data as { url: string; mime: string } };
        } catch (error) {
            console.error('API Error:', error);
            return {
                ok: false,
                error: 'Error de conexión. Verifica tu conexión a internet.',
            };
        }
    }

    // === Pagos ===
    async getPagos(params?: {
        usuario_id?: number;
        desde?: string;
        hasta?: string;
        metodo_id?: number;
        page?: number;
        limit?: number;
    }) {
        const searchParams = new URLSearchParams();
        if (params?.usuario_id) searchParams.set('usuario_id', String(params.usuario_id));
        if (params?.desde) searchParams.set('desde', params.desde);
        if (params?.hasta) searchParams.set('hasta', params.hasta);
        if (params?.metodo_id) searchParams.set('metodo_id', String(params.metodo_id));
        if (params?.page) searchParams.set('page', String(params.page));
        if (params?.limit) searchParams.set('limit', String(params.limit));

        const query = searchParams.toString();
        return this.request<{ pagos: Pago[]; total: number }>(
            `/api/pagos${query ? `?${query}` : ''}`
        );
    }

    async createPago(data: PagoCreateInput) {
        return this.request<Pago>('/api/pagos', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async deletePago(id: number) {
        return this.request<{ ok: boolean }>(`/api/pagos/${id}`, {
            method: 'DELETE',
        });
    }

    async previewReceipt(data: any): Promise<ApiResponse<{ blob: Blob }>> {
        const url = `${this.baseUrl}/api/pagos/preview`;
        try {
            const headers: Record<string, string> = {
                'Content-Type': 'application/json',
                'X-Tenant': typeof window !== 'undefined' ? getCurrentTenant() : '',
            };
            try {
                if (typeof document !== 'undefined') {
                    const csrf = getCsrfTokenFromCookie();
                    if (csrf) headers['X-CSRF-Token'] = csrf;
                }
            } catch {}
            const response = await fetch(url, {
                method: 'POST',
                body: JSON.stringify(data),
                headers,
                credentials: 'include'
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                return {
                    ok: false,
                    error: errData.detail || errData.error || 'Error generando vista previa'
                };
            }

            const blob = await response.blob();
            return { ok: true, data: { blob } };
        } catch (e) {
            console.error('API Error:', e);
            return { ok: false, error: 'Error de conexión' };
        }
    }

    async downloadReceipt(id: number): Promise<ApiResponse<{ blob: Blob }>> {
        const url = `${this.baseUrl}/api/pagos/${id}/recibo.pdf`;
        try {
            const response = await fetch(url, {
                method: 'GET',
                credentials: 'include'
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                return {
                    ok: false,
                    error: errData.detail || errData.error || 'Error descargando recibo'
                };
            }

            const blob = await response.blob();
            return { ok: true, data: { blob } };
        } catch (e) {
            console.error('API Error:', e);
            return { ok: false, error: 'Error de conexión' };
        }
    }

    // === Profesores ===
    async getProfesores() {
        return this.request<{ profesores: Profesor[] }>('/api/profesores');
    }

    async updateProfesorPassword(profesorId: number, password: string) {
        return this.request<{ ok: boolean; message?: string }>(`/api/profesores/${profesorId}/password`, {
            method: 'PUT',
            body: JSON.stringify({ password }),
        });
    }

    async getProfesor(id: number) {
        return this.request<Profesor>(`/api/profesores/${id}`);
    }

    async getSesiones(profesorId: number, params?: { desde?: string; hasta?: string }) {
        const searchParams = new URLSearchParams();
        if (params?.desde) searchParams.set('desde', params.desde);
        if (params?.hasta) searchParams.set('hasta', params.hasta);

        const query = searchParams.toString();
        return this.request<{ sesiones: Sesion[] }>(
            `/api/profesores/${profesorId}/sesiones${query ? `?${query}` : ''}`
        );
    }

    async getSesionActiva(profesorId: number) {
        return this.request<{ sesion: Sesion | null }>(`/api/profesores/${profesorId}/sesiones/activa`);
    }

    // === Rutinas ===
    async getRutinas(params?: { plantillas?: boolean; usuario_id?: number; search?: string }) {
        const searchParams = new URLSearchParams();
        if (params?.plantillas !== undefined) searchParams.set('plantillas', String(params.plantillas));
        if (params?.usuario_id) searchParams.set('usuario_id', String(params.usuario_id));
        if (params?.search) searchParams.set('search', params.search);

        const query = searchParams.toString();
        return this.request<{ rutinas: Rutina[] }>(
            `/api/rutinas${query ? `?${query}` : ''}`
        );
    }

    async getRutina(id: number) {
        return this.request<Rutina>(`/api/rutinas/${id}`);
    }

    async createRutina(data: Partial<Rutina>) {
        return this.request<Rutina>('/api/rutinas', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async updateRutina(id: number, data: Partial<Rutina>) {
        return this.request<Rutina>(`/api/rutinas/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async deleteRutina(id: number) {
        return this.request<{ ok: boolean }>(`/api/rutinas/${id}`, {
            method: 'DELETE',
        });
    }

    async duplicateRutina(id: number): Promise<ApiResponse<any>> {
        try {
            const res = await this.getRutina(id);
            if (!res.ok || !res.data) return { ok: false, error: 'Rutina no encontrada' };
            const original = res.data;

            // Create copy
            const copyRes = await this.createRutina({
                ...original,
                id: undefined,
                nombre: `${original.nombre} (Copia)`,
                activa: true,
                fecha_creacion: undefined,
                uuid_rutina: undefined,
            });

            if (!copyRes.ok || !copyRes.data) return copyRes;

            // If createRutina doesn't save exercises (it seems it relies on update), we might need to handle it.
            // But UnifiedRutinaEditor logic handles exercises via update.
            // If we duplicate, we want exercises too.
            // Assuming backend/gym_service create_rutina DOES NOT copy exercises automatically.
            // We need to fetch exercises of original?
            // getRutina (singular) returns full structure with exercises?
            // If so, we need to save them.
            // But API createRutina likely doesn't accept exercises list unless updated.
            // Just return success for now, user can edit. 
            // OR ideally, use unified editor "save" logic.
            // For now, simple duplicate is enough, or let's omit this method and rely on "Assign/Clone" flow which opens editor.
            return copyRes;
        } catch (e) {
            return { ok: false, error: String(e) };
        }
    }

    getRutinaPdfUrl(id: number, weeks: number = 1): string {
        const p = new URLSearchParams();
        p.set('weeks', String(weeks));
        const t = typeof window !== 'undefined' ? getCurrentTenant() : '';
        if (t) p.set('tenant', t);
        return `${this.baseUrl}/api/rutinas/${id}/export/pdf?${p.toString()}`;
    }

    getRutinaExcelUrl(id: number, params?: {
        weeks?: number;
        qr_mode?: 'inline' | 'sheet' | 'none';
        sheet_name?: string;
        user_override?: string;
        filename?: string;
    }): string {
        const p = new URLSearchParams();
        if (params?.weeks) p.set('weeks', String(params.weeks));
        if (params?.qr_mode) p.set('qr_mode', params.qr_mode);
        if (params?.sheet_name) p.set('sheet', params.sheet_name);
        if (params?.user_override) p.set('user_override', params.user_override);
        if (params?.filename) p.set('filename', params.filename);

        const t = typeof window !== 'undefined' ? getCurrentTenant() : '';
        if (t) p.set('tenant', t);

        const query = p.toString();
        return `${this.baseUrl}/api/rutinas/${id}/export/excel${query ? `?${query}` : ''}`;
    }

    /**
     * Get a signed URL for Excel preview in Office Online Viewer.
     * This URL can be embedded in an iframe to display the Excel file inline.
     */
    async getRutinaExcelViewUrl(id: number, params?: {
        weeks?: number;
        qr_mode?: 'inline' | 'sheet' | 'none';
        sheet_name?: string;
    }): Promise<ApiResponse<{ url: string }>> {
        const p = new URLSearchParams();
        if (params?.weeks) p.set('weeks', String(params.weeks));
        if (params?.qr_mode) p.set('qr_mode', params.qr_mode);
        if (params?.sheet_name) p.set('sheet', params.sheet_name);

        const t = typeof window !== 'undefined' ? getCurrentTenant() : '';
        if (t) p.set('tenant', t);

        const query = p.toString();
        return this.request<{ url: string }>(`/api/rutinas/${id}/export/excel_view_url${query ? `?${query}` : ''}`);
    }

    /**
     * Get a signed URL for a robust in-app preview (PDF rendered server-side).
     * This is intended to be embedded in an iframe and does not rely on Office Online.
     */
    async getRutinaPdfViewUrl(id: number, params?: {
        weeks?: number;
        qr_mode?: 'inline' | 'sheet' | 'none';
        sheet_name?: string;
    }): Promise<ApiResponse<{ url: string }>> {
        const p = new URLSearchParams();
        if (params?.weeks) p.set('weeks', String(params.weeks));
        if (params?.qr_mode) p.set('qr_mode', params.qr_mode);
        if (params?.sheet_name) p.set('sheet', params.sheet_name);

        const t = typeof window !== 'undefined' ? getCurrentTenant() : '';
        if (t) p.set('tenant', t);

        const query = p.toString();
        return this.request<{ url: string }>(`/api/rutinas/${id}/export/pdf_view_url${query ? `?${query}` : ''}`);
    }

    async getRutinaDraftExcelViewUrl(data: any) {
        return this.request<{ url: string }>('/api/rutinas/export/draft_url', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async getRutinaDraftPdfViewUrl(data: any) {
        return this.request<{ url: string }>('/api/rutinas/export/draft_pdf_url', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async verifyRoutineQR(uuid: string): Promise<ApiResponse<{
        rutina: Rutina;
        access_granted: boolean;
        expires_in_seconds: number;
    }>> {
        return this.request<{
            rutina: Rutina;
            access_granted: boolean;
            expires_in_seconds: number;
        }>('/api/rutinas/verify_qr', {
            method: 'POST',
            body: JSON.stringify({ uuid })
        });
    }

    async assignRutina(rutinaId: number, usuarioId: number) {
        return this.request<Rutina>(`/api/rutinas/${rutinaId}/assign`, {
            method: 'POST',
            body: JSON.stringify({ usuario_id: usuarioId }),
        });
    }

    async toggleRutinaActiva(rutinaId: number) {
        return this.request<{ ok: boolean; activa: boolean }>(`/api/rutinas/${rutinaId}/toggle-activa`, {
            method: 'PUT',
        });
    }

    // === Ejercicios ===
    async getEjercicios(params?: { search?: string; grupo?: string; objetivo?: string }) {
        const searchParams = new URLSearchParams();
        if (params?.search) searchParams.set('search', params.search);
        if (params?.grupo) searchParams.set('grupo', params.grupo);
        if (params?.objetivo) searchParams.set('objetivo', params.objetivo);

        const query = searchParams.toString();
        return this.request<{ ejercicios: Ejercicio[] }>(
            `/api/ejercicios${query ? `?${query}` : ''}`
        );
    }

    async createEjercicio(data: Partial<Ejercicio>) {
        return this.request<Ejercicio>('/api/ejercicios', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async updateEjercicio(id: number, data: Partial<Ejercicio>) {
        return this.request<Ejercicio>(`/api/ejercicios/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async deleteEjercicio(id: number) {
        return this.request<{ ok: boolean }>(`/api/ejercicios/${id}`, {
            method: 'DELETE',
        });
    }

    // === Clases ===
    async getClases() {
        return this.request<{ clases: Clase[] }>('/api/clases');
    }

    async getClasesAgenda() {
        return this.request<{ agenda: ClaseAgendaItem[] }>('/api/clases/agenda');
    }

    // === Asistencias ===
    async getAsistencias(params?: { usuario_id?: number; desde?: string; hasta?: string; q?: string; limit?: number; offset?: number; page?: number }) {
        const searchParams = new URLSearchParams();
        if (params?.usuario_id) searchParams.set('usuario_id', String(params.usuario_id));
        if (params?.desde) searchParams.set('desde', params.desde);
        if (params?.hasta) searchParams.set('hasta', params.hasta);
        if (params?.q) searchParams.set('q', params.q);
        if (params?.limit) searchParams.set('limit', String(params.limit));
        if (params?.offset !== undefined) searchParams.set('offset', String(params.offset));
        if (params?.page !== undefined) searchParams.set('page', String(params.page));

        const query = searchParams.toString();
        return this.request<{ asistencias: Asistencia[]; total?: number }>(
            `/api/asistencias${query ? `?${query}` : ''}`
        );
    }

    // === Configuration ===
    async getTiposCuota() {
        return this.request<{ tipos: TipoCuota[] }>('/api/config/tipos-cuota');
    }

    async getTipoCuotaEntitlements(tipoCuotaId: number) {
        return this.request<TipoCuotaEntitlements>(`/api/gestion/tipos-cuota/${tipoCuotaId}/entitlements`);
    }

    async updateTipoCuotaEntitlements(tipoCuotaId: number, data: TipoCuotaEntitlementsUpdate) {
        return this.request<{ ok: boolean }>(`/api/gestion/tipos-cuota/${tipoCuotaId}/entitlements`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async getUsuarioEntitlementsGestion(usuarioId: number) {
        return this.request<UsuarioEntitlementsGestion>(`/api/gestion/usuarios/${usuarioId}/entitlements`);
    }

    async updateUsuarioEntitlementsGestion(usuarioId: number, data: UsuarioEntitlementsGestionUpdate) {
        return this.request<{ ok: boolean }>(`/api/gestion/usuarios/${usuarioId}/entitlements`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async getMetodosPago() {
        return this.request<{ metodos: MetodoPago[] }>('/api/config/metodos-pago');
    }

    async getConceptosPago() {
        return this.request<{ conceptos: ConceptoPago[] }>('/api/config/conceptos');
    }

    // === KPIs / Statistics ===
    async getOwnerDashboardOverview() {
        return this.request<any>('/api/owner_dashboard/overview');
    }

    async getOwnerAttendanceAudit(params?: { dias?: number; desde?: string; hasta?: string; umbral_multiples?: number; umbral_repeticion_minutos?: number }) {
        const searchParams = new URLSearchParams();
        if (params?.dias !== undefined) searchParams.set('dias', String(params.dias));
        if (params?.desde) searchParams.set('desde', params.desde);
        if (params?.hasta) searchParams.set('hasta', params.hasta);
        if (params?.umbral_multiples !== undefined) searchParams.set('umbral_multiples', String(params.umbral_multiples));
        if (params?.umbral_repeticion_minutos !== undefined) searchParams.set('umbral_repeticion_minutos', String(params.umbral_repeticion_minutos));
        const q = searchParams.toString();
        return this.request<any>(`/api/owner_dashboard/attendance_audit${q ? `?${q}` : ''}`);
    }

    async getOwnerGymSettings() {
        return this.request<{ ok: boolean; settings: Record<string, any> }>('/api/owner/gym/settings');
    }

    async updateOwnerGymSettings(updates: Record<string, any>) {
        return this.request<{ ok: boolean; settings?: Record<string, any>; error?: string }>('/api/owner/gym/settings', {
            method: 'POST',
            body: JSON.stringify(updates),
        });
    }

    async getOwnerGymBilling() {
        return this.request<any>('/api/owner/gym/billing');
    }

    async getKPIs() {
        return this.request<{
            total_activos: number;
            total_inactivos: number;
            ingresos_mes: number;
            asistencias_hoy: number;
            nuevos_30_dias: number;
        }>('/api/kpis');
    }

    async getKPIsAvanzados() {
        return this.request<{
            churn_rate?: number;
            avg_pago?: number;
            churned_30d?: number;
        }>('/api/kpis_avanzados');
    }

    async getActivosInactivos() {
        return this.request<{ activos: number; inactivos: number }>('/api/activos_inactivos');
    }

    async getARPU12m() {
        return this.request<{ data: Array<{ mes: string; arpu: number }> }>('/api/arpu12m');
    }

    async getCohortRetencionHeatmap() {
        return this.request<{ cohorts: any[] }>('/api/cohort_retencion_heatmap');
    }

    async getARPAByTipoCuota() {
        return this.request<{ data: Array<{ tipo: string; arpa: number }> }>('/api/arpa_por_tipo_cuota');
    }

    async getPaymentStatusDist() {
        return this.request<any>('/api/payment_status_dist');
    }

    async getWaitlistEvents() {
        return this.request<{ events: any[] }>('/api/waitlist_events');
    }

    async getGymSubscription() {
        return this.request<any>('/api/gym/subscription');
    }

    async getWhatsAppStats() {
        return this.request<any>('/api/whatsapp/stats');
    }

    async getWhatsAppPendientes(params?: { dias?: number; limit?: number }) {
        const searchParams = new URLSearchParams();
        if (params?.dias) searchParams.set('dias', String(params.dias));
        if (params?.limit) searchParams.set('limit', String(params.limit));
        const query = searchParams.toString();
        return this.request<{ mensajes: any[] }>(`/api/whatsapp/pendientes${query ? `?${query}` : ''}`);
    }

    // === Profesores CRUD ===
    async createProfesor(data: { nombre: string; email?: string; telefono?: string }) {
        return this.request<Profesor>('/api/profesores', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async updateProfesor(id: number, data: Partial<{ nombre: string; email?: string; telefono?: string }>) {
        return this.request<Profesor>(`/api/profesores/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async deleteProfesor(id: number) {
        return this.request<{ ok: boolean }>(`/api/profesores/${id}`, {
            method: 'DELETE',
        });
    }

    async startSesion(profesorId: number) {
        return this.request<Sesion>(`/api/profesores/${profesorId}/sesiones/start`, {
            method: 'POST',
        });
    }

    async endSesion(profesorId: number, sesionId: number) {
        return this.request<Sesion>(`/api/profesores/${profesorId}/sesiones/${sesionId}/end`, {
            method: 'POST',
        });
    }

    // === Clases CRUD ===
    async createClase(data: Partial<Clase>) {
        return this.request<Clase>('/api/clases', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async updateClase(id: number, data: Partial<Clase>) {
        return this.request<Clase>(`/api/clases/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async deleteClase(id: number) {
        return this.request<{ ok: boolean }>(`/api/clases/${id}`, {
            method: 'DELETE',
        });
    }

    // === Configuration CRUD ===
    async createTipoCuota(data: { nombre: string; precio?: number; duracion_dias?: number }) {
        return this.request<TipoCuota>('/api/config/tipos-cuota', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async updateTipoCuota(id: number, data: Partial<{ nombre: string; precio?: number; duracion_dias?: number; activo?: boolean }>) {
        return this.request<TipoCuota>(`/api/config/tipos-cuota/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async deleteTipoCuota(id: number) {
        return this.request<{ ok: boolean }>(`/api/config/tipos-cuota/${id}`, {
            method: 'DELETE',
        });
    }

    async toggleTipoCuota(id: number) {
        return this.request<TipoCuota>(`/api/config/tipos-cuota/${id}/toggle`, {
            method: 'POST',
        });
    }

    async createMetodoPago(data: { nombre: string }) {
        return this.request<MetodoPago>('/api/config/metodos-pago', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async updateMetodoPago(id: number, data: Partial<{ nombre: string; activo?: boolean }>) {
        return this.request<MetodoPago>(`/api/config/metodos-pago/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async deleteMetodoPago(id: number) {
        return this.request<{ ok: boolean }>(`/api/config/metodos-pago/${id}`, {
            method: 'DELETE',
        });
    }

    async toggleMetodoPago(id: number) {
        return this.request<MetodoPago>(`/api/config/metodos-pago/${id}/toggle`, {
            method: 'POST',
        });
    }

    async createConcepto(data: { nombre: string }) {
        return this.request<ConceptoPago>('/api/config/conceptos', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async updateConcepto(id: number, data: Partial<{ nombre: string; activo?: boolean }>) {
        return this.request<ConceptoPago>(`/api/config/conceptos/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async deleteConcepto(id: number) {
        return this.request<{ ok: boolean }>(`/api/config/conceptos/${id}`, {
            method: 'DELETE',
        });
    }

    async toggleConcepto(id: number) {
        return this.request<ConceptoPago>(`/api/config/conceptos/${id}/toggle`, {
            method: 'POST',
        });
    }

    // === Check-in ===
    async checkIn(token: string, idempotencyKey?: string) {
        return this.request<{ ok: boolean; usuario_nombre?: string; mensaje?: string }>('/api/checkin', {
            method: 'POST',
            body: JSON.stringify({ token, ...(idempotencyKey ? { idempotency_key: idempotencyKey } : {}) }),
        });
    }

    async checkInByDni(dni: string, pin?: string, idempotencyKey?: string) {
        return this.request<{ ok: boolean; usuario_nombre?: string; mensaje?: string; require_pin?: boolean }>('/api/checkin/dni', {
            method: 'POST',
            body: JSON.stringify({ dni, ...(pin ? { pin } : {}), ...(idempotencyKey ? { idempotency_key: idempotencyKey } : {}) }),
        });
    }

    async getCheckinConfig() {
        return this.request<{ require_pin: boolean }>('/api/checkin/config');
    }

    async createAsistencia(usuarioId: number, fecha?: string) {
        return this.request<{ success: boolean; asistencia_id?: number; message?: string }>('/api/asistencias/registrar', {
            method: 'POST',
            body: JSON.stringify({ usuario_id: usuarioId, fecha }),
        });
    }

    async deleteAsistencia(usuarioId: number, fecha?: string) {
        return this.request<{ success: boolean }>('/api/asistencias/eliminar', {
            method: 'DELETE',
            body: JSON.stringify({
                usuario_id: usuarioId,
                fecha: fecha || new Date().toISOString().split('T')[0]
            }),
        });
    }

    async deleteAsistenciaById(asistenciaId: number) {
        return this.request<{ success: boolean }>('/api/asistencias/eliminar', {
            method: 'DELETE',
            body: JSON.stringify({
                asistencia_id: asistenciaId,
            }),
        });
    }

    async getAsistenciasHoyIds() {
        return this.request<number[]>('/api/asistencias_hoy_ids');
    }

    async getUserAsistencias(usuarioId: number, limit?: number) {
        const params = new URLSearchParams();
        params.set('usuario_id', String(usuarioId));
        if (limit) params.set('limit', String(limit));
        return this.request<{ asistencias: Asistencia[] }>(`/api/usuario_asistencias?${params.toString()}`);
    }

    async createCheckinToken(usuarioId: number, expiresMinutes?: number) {
        return this.request<{ success: boolean; token: string; expires_minutes: number }>('/api/checkin/create_token', {
            method: 'POST',
            body: JSON.stringify({ usuario_id: usuarioId, expires_minutes: expiresMinutes || 5 }),
        });
    }

    async getCheckinTokenStatus(token: string) {
        return this.request<{ exists: boolean; used: boolean; expired: boolean }>(`/api/checkin/token_status?token=${encodeURIComponent(token)}`);
    }



    async getStationKey() {
        return this.request<{ station_key: string; station_url: string }>('/api/gestion/station-key');
    }

    async regenerateStationKey() {
        return this.request<{ station_key: string; station_url: string }>('/api/gestion/station-key/regenerate', {
            method: 'POST',
        });
    }

    async getUsuarioMembership(usuarioId: number) {
        return this.request<{ ok: boolean; membership: Membership | null; sucursales?: number[] }>(`/api/gestion/usuarios/${usuarioId}/membership`);
    }

    async setUsuarioMembership(
        usuarioId: number,
        data: { plan_name?: string | null; start_date?: string | null; end_date?: string | null; all_sucursales: boolean; sucursal_ids: number[] }
    ) {
        return this.request<{ ok: boolean; membership?: Membership; sucursales?: number[]; error?: string }>(`/api/gestion/usuarios/${usuarioId}/membership`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    // === User Tags (Etiquetas) ===
    async getEtiquetas(usuarioId: number) {
        return this.request<{ etiquetas: Etiqueta[] }>(`/api/usuarios/${usuarioId}/etiquetas`);
    }

    async addEtiqueta(usuarioId: number, nombre: string) {
        return this.request<Etiqueta>(`/api/usuarios/${usuarioId}/etiquetas`, {
            method: 'POST',
            body: JSON.stringify({ nombre }),
        });
    }

    async deleteEtiqueta(usuarioId: number, etiquetaId: number) {
        return this.request<{ ok: boolean }>(`/api/usuarios/${usuarioId}/etiquetas/${etiquetaId}`, {
            method: 'DELETE',
        });
    }

    async getEtiquetasSuggestions() {
        return this.request<{ etiquetas: string[] }>('/api/etiquetas/suggestions');
    }

    // === User States (Estados) ===
    async getEstados(usuarioId: number) {
        return this.request<{ estados: Estado[] }>(`/api/usuarios/${usuarioId}/estados`);
    }

    async addEstado(usuarioId: number, data: { nombre: string; descripcion?: string; fecha_vencimiento?: string }) {
        return this.request<Estado>(`/api/usuarios/${usuarioId}/estados`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async deleteEstado(usuarioId: number, estadoId: number) {
        return this.request<{ ok: boolean }>(`/api/usuarios/${usuarioId}/estados/${estadoId}`, {
            method: 'DELETE',
        });
    }

    async getEstadoTemplates() {
        return this.request<{ templates: EstadoTemplate[] }>('/api/estados/templates');
    }

    // === User Notes ===
    async updateUsuarioNotas(usuarioId: number, notas: string) {
        return this.request<{ ok: boolean }>(`/api/usuarios/${usuarioId}/notas`, {
            method: 'PUT',
            body: JSON.stringify({ notas }),
        });
    }

    // === User QR ===
    async generateUserQR(usuarioId: number) {
        return this.request<{ qr_url: string; token: string }>(`/api/usuarios/${usuarioId}/qr`);
    }

    // === Clase Types ===
    async getClaseTipos() {
        return this.request<{ tipos: ClaseTipo[] }>('/api/clases/tipos');
    }

    async createClaseTipo(data: { nombre: string; color?: string }) {
        return this.request<ClaseTipo>('/api/clases/tipos', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async deleteClaseTipo(id: number) {
        return this.request<{ ok: boolean }>(`/api/clases/tipos/${id}`, {
            method: 'DELETE',
        });
    }

    // === Clase Horarios ===
    async getClaseHorarios(claseId: number) {
        return this.request<{ horarios: ClaseHorario[] }>(`/api/clases/${claseId}/horarios`);
    }

    async createClaseHorario(claseId: number, data: { dia: string; hora_inicio: string; hora_fin: string; profesor_id?: number; cupo?: number }) {
        return this.request<ClaseHorario>(`/api/clases/${claseId}/horarios`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async updateClaseHorario(claseId: number, horarioId: number, data: Partial<ClaseHorario>) {
        return this.request<ClaseHorario>(`/api/clases/${claseId}/horarios/${horarioId}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async deleteClaseHorario(claseId: number, horarioId: number) {
        return this.request<{ ok: boolean }>(`/api/clases/${claseId}/horarios/${horarioId}`, {
            method: 'DELETE',
        });
    }

    // === Inscripciones ===
    async getInscripciones(horarioId: number) {
        return this.request<{ inscripciones: Inscripcion[] }>(`/api/horarios/${horarioId}/inscripciones`);
    }

    async inscribirUsuario(horarioId: number, usuarioId: number) {
        return this.request<Inscripcion>(`/api/horarios/${horarioId}/inscripciones`, {
            method: 'POST',
            body: JSON.stringify({ usuario_id: usuarioId }),
        });
    }

    async desinscribirUsuario(horarioId: number, usuarioId: number) {
        return this.request<{ ok: boolean }>(`/api/horarios/${horarioId}/inscripciones/${usuarioId}`, {
            method: 'DELETE',
        });
    }

    // === Lista de Espera ===
    async getListaEspera(horarioId: number) {
        return this.request<{ lista: ListaEspera[] }>(`/api/horarios/${horarioId}/lista-espera`);
    }

    async addToListaEspera(horarioId: number, usuarioId: number) {
        return this.request<ListaEspera>(`/api/horarios/${horarioId}/lista-espera`, {
            method: 'POST',
            body: JSON.stringify({ usuario_id: usuarioId }),
        });
    }

    async removeFromListaEspera(horarioId: number, usuarioId: number) {
        return this.request<{ ok: boolean }>(`/api/horarios/${horarioId}/lista-espera/${usuarioId}`, {
            method: 'DELETE',
        });
    }

    async notifyListaEspera(horarioId: number) {
        return this.request<{ ok: boolean; notified_user?: string }>(`/api/horarios/${horarioId}/lista-espera/notify`, {
            method: 'POST',
        });
    }

    // === Clase Ejercicios ===
    async getClaseEjercicios(claseId: number) {
        return this.request<{ ejercicios: ClaseEjercicio[] }>(`/api/clases/${claseId}/ejercicios`);
    }

    async updateClaseEjercicios(claseId: number, ejercicioIds: number[]) {
        return this.request<{ ok: boolean }>(`/api/clases/${claseId}/ejercicios`, {
            method: 'PUT',
            body: JSON.stringify({ ejercicio_ids: ejercicioIds }),
        });
    }

    // === Clase Bloques ===
    async getClaseBloques(claseId: number) {
        return this.request<ClaseBloque[]>(`/api/clases/${claseId}/bloques`);
    }

    async getClaseBloqueItems(claseId: number, bloqueId: number) {
        return this.request<ClaseBloqueItem[]>(`/api/clases/${claseId}/bloques/${bloqueId}`);
    }

    async createClaseBloque(claseId: number, data: { nombre: string; items?: ClaseBloqueItem[] }) {
        return this.request<{ ok: boolean; id: number }>(`/api/clases/${claseId}/bloques`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async updateClaseBloque(claseId: number, bloqueId: number, data: { nombre: string; items?: ClaseBloqueItem[] }) {
        return this.request<{ ok: boolean }>(`/api/clases/${claseId}/bloques/${bloqueId}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async deleteClaseBloque(claseId: number, bloqueId: number) {
        return this.request<{ ok: boolean }>(`/api/clases/${claseId}/bloques/${bloqueId}`, {
            method: 'DELETE',
        });
    }

    // === Profesor Horarios ===
    async getProfesorHorarios(profesorId: number) {
        return this.request<{ horarios: ProfesorHorario[] }>(`/api/profesores/${profesorId}/horarios`);
    }

    async createProfesorHorario(profesorId: number, data: { dia: string; hora_inicio: string; hora_fin: string; disponible?: boolean }) {
        return this.request<ProfesorHorario>(`/api/profesores/${profesorId}/horarios`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async updateProfesorHorario(profesorId: number, horarioId: number, data: Partial<ProfesorHorario>) {
        return this.request<ProfesorHorario>(`/api/profesores/${profesorId}/horarios/${horarioId}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async deleteProfesorHorario(profesorId: number, horarioId: number) {
        return this.request<{ ok: boolean }>(`/api/profesores/${profesorId}/horarios/${horarioId}`, {
            method: 'DELETE',
        });
    }

    // === Profesor Config ===
    async getProfesorConfig(profesorId: number) {
        return this.request<ProfesorConfig>(`/api/profesores/${profesorId}/config`);
    }

    async updateProfesorConfig(profesorId: number, data: Partial<ProfesorConfig>) {
        return this.request<ProfesorConfig>(`/api/profesores/${profesorId}/config`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    // === Profesor Resumen ===
    async getProfesorResumenMensual(profesorId: number, mes?: number, anio?: number) {
        const params = new URLSearchParams();
        if (mes) params.set('mes', String(mes));
        if (anio) params.set('anio', String(anio));
        const query = params.toString();
        return this.request<ProfesorResumen>(`/api/profesores/${profesorId}/resumen/mensual${query ? `?${query}` : ''}`);
    }

    async getProfesorResumenSemanal(profesorId: number, fecha?: string) {
        const params = new URLSearchParams();
        if (fecha) params.set('fecha', fecha);
        const query = params.toString();
        return this.request<ProfesorResumen>(`/api/profesores/${profesorId}/resumen/semanal${query ? `?${query}` : ''}`);
    }

    // === Sesiones ===
    async deleteSesion(sesionId: number) {
        return this.request<{ ok: boolean }>(`/api/sesiones/${sesionId}`, {
            method: 'DELETE',
        });
    }

    // === WhatsApp ===
    async getWhatsAppConfig() {
        return this.request<WhatsAppConfig>('/api/whatsapp/config');
    }

    async updateWhatsAppConfig(data: Partial<WhatsAppConfig>) {
        return this.request<WhatsAppConfig>('/api/whatsapp/config', {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async getWhatsAppStatus() {
        return this.request<WhatsAppStatus>('/api/whatsapp/status');
    }

    async getWhatsAppMensajesPendientes() {
        return this.request<WhatsAppMensajesResponse>('/api/whatsapp/pendientes');
    }

    async getWhatsAppMensajes(params: {
        dias?: number;
        status?: string;
        page?: number;
        limit?: number;
        scope?: 'gym' | 'branch';
    } = {}) {
        const q = new URLSearchParams();
        if (params.dias != null) q.set('dias', String(params.dias));
        if (params.status) q.set('status', String(params.status));
        if (params.page != null) q.set('page', String(params.page));
        if (params.limit != null) q.set('limit', String(params.limit));
        if (params.scope) q.set('scope', String(params.scope));
        const qs = q.toString();
        return this.request<any>(`/api/whatsapp/mensajes${qs ? `?${qs}` : ''}`);
    }

    async getWhatsAppEmbeddedSignupConfig() {
        return this.request<WhatsAppEmbeddedSignupConfig>('/api/whatsapp/embedded-signup/config');
    }

    async getWhatsAppEmbeddedSignupReadiness() {
        return this.request<WhatsAppEmbeddedSignupReadiness>('/api/whatsapp/embedded-signup/readiness');
    }

    async completeWhatsAppEmbeddedSignup(data: { code: string; waba_id: string; phone_number_id: string }) {
        return this.request<{ ok: boolean; provision?: any }>(`/api/whatsapp/embedded-signup/complete`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async getWhatsAppTemplates() {
        return this.request<{ templates: WhatsAppTemplate[] }>('/api/whatsapp/templates');
    }

    async upsertWhatsAppTemplate(templateName: string, data: { body_text: string; active?: boolean }) {
        return this.request<{ ok: boolean }>(`/api/whatsapp/templates/${encodeURIComponent(templateName)}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async deleteWhatsAppTemplate(templateName: string) {
        return this.request<{ ok: boolean; deleted: number }>(`/api/whatsapp/templates/${encodeURIComponent(templateName)}`, {
            method: 'DELETE',
        });
    }

    async getWhatsAppTriggers() {
        return this.request<{ triggers: WhatsAppTrigger[] }>('/api/whatsapp/triggers');
    }

    async getWhatsAppOnboardingStatus() {
        return this.request<WhatsAppOnboardingStatus>('/api/whatsapp/onboarding/status');
    }

    async reconcileWhatsAppOnboarding() {
        return this.request<{ ok: boolean }>(`/api/whatsapp/onboarding/reconcile`, { method: 'POST' });
    }

    async updateWhatsAppTrigger(triggerKey: string, data: { enabled: boolean; template_name?: string | null; cooldown_minutes?: number }) {
        return this.request<{ ok: boolean }>(`/api/whatsapp/triggers/${encodeURIComponent(triggerKey)}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async getMyWorkSession() {
        return this.request<any>('/api/my/work-session');
    }
    async startMyWorkSession() {
        return this.request<any>('/api/my/work-session/start', { method: 'POST', body: JSON.stringify({}) });
    }
    async pauseMyWorkSession() {
        return this.request<any>('/api/my/work-session/pause', { method: 'POST', body: JSON.stringify({}) });
    }
    async resumeMyWorkSession() {
        return this.request<any>('/api/my/work-session/resume', { method: 'POST', body: JSON.stringify({}) });
    }
    async endMyWorkSession() {
        return this.request<any>('/api/my/work-session/end', { method: 'POST', body: JSON.stringify({}) });
    }

    async runWhatsAppAutomation(data: { trigger_keys?: string[]; dry_run?: boolean }) {
        return this.request<{ ok: boolean; scanned: number; sent: number; dry_run: boolean }>('/api/whatsapp/automation/run', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async getWhatsAppHistorial(usuarioId: number) {
        return this.request<{ mensajes: WhatsAppMensaje[] }>(`/api/usuarios/${usuarioId}/whatsapp/historial`);
    }

    async retryWhatsAppMessage(mensajeId: number) {
        return this.request<{ ok: boolean }>(`/api/whatsapp/mensajes/${mensajeId}/retry`, {
            method: 'POST',
        });
    }

    async retryAllWhatsAppFailed() {
        return this.request<{ ok: boolean; retried: number }>('/api/whatsapp/retry-all', {
            method: 'POST',
        });
    }

    async clearWhatsAppFailed() {
        return this.request<{ ok: boolean; cleared: number }>('/api/whatsapp/clear-failed', {
            method: 'POST',
        });
    }

    async forceWhatsAppSend(usuarioId: number, tipo: string) {
        return this.request<{ ok: boolean }>(`/api/usuarios/${usuarioId}/whatsapp/force`, {
            method: 'POST',
            body: JSON.stringify({ tipo }),
        });
    }

    // === Recibos ===
    async getReciboConfig() {
        return this.request<ReciboConfig>('/api/config/recibos');
    }

    async updateReciboConfig(data: Partial<ReciboConfig>) {
        return this.request<ReciboConfig>('/api/config/recibos', {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async getReciboPreview(pagoId: number) {
        return this.request<ReciboPreview>(`/api/pagos/${pagoId}/recibo/preview`);
    }

    async downloadReciboPDF(pagoId: number) {
        // Returns URL to PDF
        return this.request<{ pdf_url: string }>(`/api/pagos/${pagoId}/recibo/pdf`);
    }

    async getNextReciboNumber() {
        return this.request<{ numero: string }>('/api/config/recibos/next-number');
    }

    // === Reports / Dashboard ===
    // Update payment with differential calculation
    async updatePago(pagoId: number, data: { items: Array<{ descripcion: string; cantidad: number; precio_unitario: number; concepto_id?: number }> }) {
        return this.request<{
            ok: boolean;
            pago_id: number;
            dias_originales: number;
            dias_nuevos: number;
            delta: number;
            nuevo_monto: number;
            nueva_fecha_vencimiento: string | null;
        }>(`/api/pagos/${pagoId}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    // === Dashboard KPIs ===
    async getKpis() {
        return this.request<{
            total_activos: number;
            total_inactivos: number;
            ingresos_mes: number;
            asistencias_hoy: number;
            nuevos_30_dias: number;
        }>('/api/kpis');
    }

    async getIngresos12m() {
        return this.request<{ data: Array<{ mes: string; total: number }> }>('/api/ingresos12m');
    }

    async getNuevos12m() {
        return this.request<{ data: Array<{ mes: string; total: number }> }>('/api/nuevos12m');
    }

    async getCohortRetencion6m() {
        return this.request<{ cohorts: Array<{ cohort: string; total: number; retained: number; retention_rate: number }> }>('/api/cohort_retencion_6m');
    }

    async getDelinquencyAlertsRecent() {
        return this.request<{ alerts: Array<{ usuario_id: number; usuario_nombre: string; ultimo_pago: string | null }> }>('/api/delinquency_alerts_recent');
    }

    async exportToCsv(type: 'usuarios' | 'pagos' | 'asistencias' | 'asistencias_audit', params?: { desde?: string; hasta?: string }) {
        const searchParams = new URLSearchParams();
        if (params?.desde) searchParams.set('desde', params.desde);
        if (params?.hasta) searchParams.set('hasta', params.hasta);
        const query = searchParams.toString();
        const url = `${this.baseUrl}/api/export/${type}/csv${query ? `?${query}` : ''}`;

        try {
            const response = await fetch(url, {
                credentials: 'include',
                headers: {
                    'X-Tenant': typeof window !== 'undefined' ? getCurrentTenant() : '',
                },
            });
            if (!response.ok) {
                return { ok: false, error: 'Error al exportar' };
            }
            return { ok: true, data: await response.blob() };
        } catch (error) {
            return { ok: false, error: 'Error de conexión' };
        }
    }

}

// Singleton instance
export const api = new ApiClient(API_BASE_URL);

// Re-export for convenience
export default api;


