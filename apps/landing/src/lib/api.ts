/**
 * API Service for fetching data from admin-api
 */

const ADMIN_API_URL = typeof window !== 'undefined'
    ? (window as typeof globalThis & { ENV?: { ADMIN_API_URL?: string } }).ENV?.ADMIN_API_URL || 'https://api-admin.ironhub.motiona.xyz'
    : 'https://api-admin.ironhub.motiona.xyz';

export interface Gym {
    id: number;
    nombre: string;
    subdominio: string;
    status: string;
    logo_url?: string | null;
}

export interface GymsResponse {
    items: Gym[];
    total: number;
}

export interface PublicMetrics {
    ok: boolean;
    generated_at?: string;
    totals?: {
        active_gyms: number;
        paying_gyms: number;
        total_users: number;
        total_active_users: number;
    };
    gyms?: Array<{
        id: number;
        subdominio: string;
        users_total: number | null;
        users_active: number | null;
    }>;
}

/**
 * Fetch public gym list from admin-api
 */
export async function fetchPublicGyms(): Promise<Gym[]> {
    try {
        const response = await fetch(`${ADMIN_API_URL}/gyms/public`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
            },
            cache: 'no-store',
        });

        if (!response.ok) {
            console.error('Failed to fetch gyms:', response.status);
            return [];
        }

        const data = await response.json();

        // Handle { items: [...] } response
        if (data.items && Array.isArray(data.items)) {
            return data.items;
        }

        return [];
    } catch (error) {
        console.error('Error fetching gyms:', error);
        return [];
    }
}

export async function fetchPublicMetrics(): Promise<PublicMetrics | null> {
    try {
        const response = await fetch(`${ADMIN_API_URL}/gyms/public/metrics`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
            },
            cache: 'no-store',
        });

        if (!response.ok) {
            return null;
        }

        const data = await response.json();
        if (!data || data.ok === false) return null;
        return data as PublicMetrics;
    } catch {
        return null;
    }
}
