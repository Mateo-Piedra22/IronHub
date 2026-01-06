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
}

export interface GymsResponse {
    items: Gym[];
    total: number;
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
