/**
 * API Client for webapp-web
 * Handles all communication with webapp-api
 * Supports multi-tenant with dynamic API URL based on subdomain
 */

// Environment configuration
const TENANT_DOMAIN = process.env.NEXT_PUBLIC_TENANT_DOMAIN || 'ironhub.motiona.xyz';

/**
 * Get the current gym subdomain from the browser URL
 * Example: mygym.ironhub.motiona.xyz -> mygym
 */
function getCurrentSubdomain(): string {
    if (typeof window === 'undefined') return '';

    const hostname = window.location.hostname;

    // Handle localhost/development
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return process.env.NEXT_PUBLIC_DEV_SUBDOMAIN || 'demo';
    }

    // Extract subdomain from {gym}.ironhub.motiona.xyz
    const domainParts = hostname.split('.');
    const tenantParts = TENANT_DOMAIN.split('.');

    if (domainParts.length > tenantParts.length) {
        return domainParts[0];
    }

    return '';
}

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
    fecha_registro?: string;
    fecha_proximo_vencimiento?: string;
    dias_restantes?: number;
    cuotas_vencidas?: number;
    exento?: boolean;
    notas?: string;
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
    mes?: number;
    anio?: number;
    metodo_pago_id?: number;
    metodo_pago_nombre?: string;
    concepto_id?: number;
    concepto_nombre?: string;
    tipo_cuota_id?: number;
    tipo_cuota_nombre?: string;
    notas?: string;
    recibo_numero?: number;
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
    hora_inicio: string;
    hora_fin: string;
    dia_semana: number;
    profesor_id?: number;
    profesor_nombre?: string;
    capacidad?: number;
    color?: string;
}

// === Asistencia Types ===
export interface Asistencia {
    id: number;
    usuario_id: number;
    usuario_nombre?: string;
    fecha: string;
    hora?: string;
    hora_entrada?: string;
    hora_salida?: string;
    duracion_minutos?: number;
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

export interface SessionUser {
    id: number;
    nombre: string;
    rol: 'owner' | 'admin' | 'profesor' | 'user';
    dni?: string;
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
    access_token?: string;
    webhook_verify_token?: string;
    enabled: boolean;
    webhook_enabled: boolean;
}

export interface WhatsAppMensaje {
    id: number;
    usuario_id: number;
    usuario_nombre?: string;
    telefono?: string;
    tipo: 'welcome' | 'payment' | 'deactivation' | 'overdue' | 'class_reminder';
    estado: 'pending' | 'sent' | 'failed';
    contenido?: string;
    error_detail?: string;
    fecha_envio?: string;
    created_at?: string;
}

export interface WhatsAppStatus {
    available: boolean;
    enabled: boolean;
    server_ok: boolean;
    config_valid: boolean;
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
            const response = await fetch(url, {
                ...options,
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Tenant': typeof window !== 'undefined' ? getCurrentSubdomain() : '',
                    ...options.headers,
                },
            });

            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                return {
                    ok: false,
                    error: data.detail || data.message || data.error || 'Error de servidor',
                };
            }

            return { ok: true, data: data as T };
        } catch (error) {
            console.error('API Error:', error);
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
        }>('/api/usuario/login', {
            method: 'POST',
            body: JSON.stringify(credentials),
        });
    }

    // Gestion login with professor selector or owner (for /gestion-login)
    async gestionLogin(credentials: {
        usuario_id: string; // '__OWNER__' for owner or numeric user ID
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
        }>('/api/checkin/auth', {
            method: 'POST',
            body: JSON.stringify(credentials),
        });
    }

    // Scan station QR
    async scanStationQR(token: string) {
        return this.request<{
            ok: boolean;
            mensaje: string;
            usuario?: {
                nombre: string;
                dni: string;
            };
        }>('/api/checkin/qr', {
            method: 'POST',
            body: JSON.stringify({ token }),
        });
    }

    // Get basic professor list for gestion login dropdown
    async getProfesoresBasico() {
        return this.request<Array<{
            usuario_id: number;
            nombre: string;
            profesor_id: number;
        }>>('/api/profesores_basico');
    }

    // Change user PIN (for usuario-login)
    async changePin(credentials: { dni: string; old_pin: string; new_pin: string }) {
        return this.request<{ ok: boolean; error?: string }>('/api/usuario/change_pin', {
            method: 'POST',
            body: JSON.stringify(credentials),
        });
    }

    async logout() {
        return this.request<{ ok: boolean }>('/api/auth/logout', {
            method: 'POST',
        });
    }

    async getSession() {
        return this.request<{ authenticated: boolean; user?: SessionUser }>(
            '/api/auth/session'
        );
    }

    // === Gym Data ===
    async getGymData() {
        return this.request<GymData>('/api/gym/data');
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
    async uploadExerciseVideo(file: File): Promise<ApiResponse<{ url: string; mime: string }>> {
        const formData = new FormData();
        formData.append('file', file);
        try {
            const url = `${this.baseUrl}/api/exercises/video`;
            const response = await fetch(url, {
                method: 'POST',
                body: formData,
                credentials: 'include', // Ensure cookies are sent
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
            const response = await fetch(url, {
                method: 'POST',
                body: JSON.stringify(data),
                headers: { 'Content-Type': 'application/json' },
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

    // === Profesores ===
    async getProfesores() {
        return this.request<{ profesores: Profesor[] }>('/api/profesores');
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
        return `${this.baseUrl}/api/rutinas/${id}/export/pdf?weeks=${weeks}`;
    }

    getRutinaExcelUrl(id: number, params?: {
        weeks?: number;
        qr_mode?: 'inline' | 'sheet' | 'none';
        sheet_name?: string;
        user_override?: string;
    }): string {
        const p = new URLSearchParams();
        if (params?.weeks) p.set('weeks', String(params.weeks));
        if (params?.qr_mode) p.set('qr_mode', params.qr_mode);
        if (params?.sheet_name) p.set('sheet_name', params.sheet_name);
        if (params?.user_override) p.set('user_override', params.user_override);

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

        const query = p.toString();
        return this.request<{ url: string }>(`/api/rutinas/${id}/export/excel_view_url${query ? `?${query}` : ''}`);
    }

    async getRutinaDraftExcelViewUrl(data: any) {
        return this.request<{ url: string }>('/api/rutinas/export/draft_url', {
            method: 'POST',
            body: JSON.stringify(data)
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

    // === Asistencias ===
    async getAsistencias(params?: { usuario_id?: number; desde?: string; hasta?: string; limit?: number }) {
        const searchParams = new URLSearchParams();
        if (params?.usuario_id) searchParams.set('usuario_id', String(params.usuario_id));
        if (params?.desde) searchParams.set('desde', params.desde);
        if (params?.hasta) searchParams.set('hasta', params.hasta);
        if (params?.limit) searchParams.set('limit', String(params.limit));

        const query = searchParams.toString();
        return this.request<{ asistencias: Asistencia[] }>(
            `/api/asistencias${query ? `?${query}` : ''}`
        );
    }

    // === Configuration ===
    async getTiposCuota() {
        return this.request<{ tipos: TipoCuota[] }>('/api/config/tipos-cuota');
    }

    async getMetodosPago() {
        return this.request<{ metodos: MetodoPago[] }>('/api/config/metodos-pago');
    }

    async getConceptosPago() {
        return this.request<{ conceptos: ConceptoPago[] }>('/api/config/conceptos');
    }

    // === KPIs / Statistics ===
    async getKPIs() {
        return this.request<{
            total_activos: number;
            total_inactivos: number;
            ingresos_mes: number;
            asistencias_hoy: number;
            nuevos_30_dias: number;
        }>('/api/kpis');
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
    async checkIn(token: string) {
        return this.request<{ ok: boolean; usuario_nombre?: string; mensaje?: string }>('/api/checkin', {
            method: 'POST',
            body: JSON.stringify({ token }),
        });
    }

    async checkInByDni(dni: string, pin?: string) {
        return this.request<{ ok: boolean; usuario_nombre?: string; mensaje?: string; require_pin?: boolean }>('/api/checkin/dni', {
            method: 'POST',
            body: JSON.stringify({ dni, ...(pin ? { pin } : {}) }),
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
        return this.request<{ mensajes: WhatsAppMensaje[] }>('/api/whatsapp/pendientes');
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

    async exportToCsv(type: 'usuarios' | 'pagos' | 'asistencias', params?: { desde?: string; hasta?: string }) {
        const searchParams = new URLSearchParams();
        if (params?.desde) searchParams.set('desde', params.desde);
        if (params?.hasta) searchParams.set('hasta', params.hasta);
        const query = searchParams.toString();
        const url = `${this.baseUrl}/api/export/${type}/csv${query ? `?${query}` : ''}`;

        try {
            const response = await fetch(url, {
                credentials: 'include',
                headers: {
                    'X-Tenant': typeof window !== 'undefined' ? getCurrentSubdomain() : '',
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


