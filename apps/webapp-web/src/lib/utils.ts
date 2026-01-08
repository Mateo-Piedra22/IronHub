import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Merge class names with Tailwind CSS classes
 */
export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

/**
 * Format currency (ARS)
 */
export function formatCurrency(value: number): string {
    return new Intl.NumberFormat('es-AR', {
        style: 'currency',
        currency: 'ARS',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(value);
}

/**
 * Format number with dots as thousand separator
 */
export function formatNumber(value: number): string {
    return new Intl.NumberFormat('es-AR').format(value);
}

/**
 * Format date to DD/MM/YYYY
 */
export function formatDate(date: string | Date): string {
    const d = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(d.getTime())) return '-';
    return d.toLocaleDateString('es-AR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
    });
}

/**
 * Format date to human readable: "15 de enero de 2026"
 */
export function formatDateLong(date: string | Date): string {
    const d = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(d.getTime())) return '-';
    return d.toLocaleDateString('es-AR', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
    });
}

/**
 * Format date relative: "hace 2 días", "en 3 días"
 */
export function formatDateRelative(date: string | Date): string {
    const d = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(d.getTime())) return '-';

    const now = new Date();
    const diffMs = d.getTime() - now.getTime();
    const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'hoy';
    if (diffDays === 1) return 'mañana';
    if (diffDays === -1) return 'ayer';
    if (diffDays > 0) return `en ${diffDays} días`;
    return `hace ${Math.abs(diffDays)} días`;
}

/**
 * Format time HH:MM
 */
export function formatTime(time: string): string {
    if (!time) return '-';
    // Handle "HH:MM:SS" format
    if (time.includes(':')) {
        const [h, m] = time.split(':');
        return `${h.padStart(2, '0')}:${m.padStart(2, '0')}`;
    }
    return time;
}

/**
 * Get day name from number (0-6)
 */
export function getDayName(day: number): string {
    const days = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
    return days[day] || '-';
}

/**
 * Get short day name (Lun, Mar, etc.)
 */
export function getDayNameShort(day: number): string {
    const days = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
    return days[day] || '-';
}

/**
 * Get month name from number (1-12)
 */
export function getMonthName(month: number): string {
    const months = [
        'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
    ];
    return months[month - 1] || '-';
}

/**
 * Truncate text with ellipsis
 */
export function truncate(text: string, length: number): string {
    if (!text) return '';
    if (text.length <= length) return text;
    return text.slice(0, length).trim() + '...';
}

/**
 * Generate initials from name
 */
export function getInitials(name: string): string {
    if (!name) return '??';
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/**
 * Slugify string
 */
export function slugify(text: string): string {
    return text
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-|-$/g, '');
}

/**
 * debounce function
 */
export function debounce<T extends (...args: unknown[]) => void>(
    fn: T,
    delay: number
): (...args: Parameters<T>) => void {
    let timeoutId: ReturnType<typeof setTimeout>;
    return (...args: Parameters<T>) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => fn(...args), delay);
    };
}

/**
 * Get status color class
 */
export function getStatusColor(status: string): string {
    switch (status.toLowerCase()) {
        case 'active':
        case 'activo':
        case 'paid':
        case 'pagado':
        case 'success':
            return 'text-success-400';
        case 'inactive':
        case 'inactivo':
        case 'expired':
        case 'vencido':
        case 'danger':
        case 'error':
            return 'text-danger-400';
        case 'pending':
        case 'pendiente':
        case 'warning':
            return 'text-warning-400';
        default:
            return 'text-slate-400';
    }
}

/**
 * Get badge variant class
 */
export function getBadgeVariant(status: string): string {
    switch (status.toLowerCase()) {
        case 'active':
        case 'activo':
        case 'paid':
        case 'pagado':
            return 'badge-success';
        case 'inactive':
        case 'inactivo':
        case 'expired':
        case 'vencido':
            return 'badge-danger';
        case 'pending':
        case 'pendiente':
            return 'badge-warning';
        default:
            return 'badge';
    }
}

/**
 * Parse phone number for WhatsApp link
 */
export function getWhatsAppLink(phone: string, message?: string): string {
    // Remove all non-numeric characters
    const cleanPhone = phone.replace(/\D/g, '');
    // Add Argentina country code if not present
    const fullPhone = cleanPhone.startsWith('54') ? cleanPhone : `54${cleanPhone}`;
    const url = `https://wa.me/${fullPhone}`;
    return message ? `${url}?text=${encodeURIComponent(message)}` : url;
}

/**
 * Copy text to clipboard
 */
export async function copyToClipboard(text: string): Promise<boolean> {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.opacity = '0';
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            document.body.removeChild(textArea);
            return true;
        } catch {
            document.body.removeChild(textArea);
            return false;
        }
    }
}

/**
 * Download file from blob or URL
 */
export function downloadFile(data: Blob | string, filename: string): void {
    const url = typeof data === 'string' ? data : URL.createObjectURL(data);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    if (typeof data !== 'string') {
        URL.revokeObjectURL(url);
    }
}

/**
 * Generate random color for charts/avatars
 */
export function generateColor(seed: string): string {
    let hash = 0;
    for (let i = 0; i < seed.length; i++) {
        hash = seed.charCodeAt(i) + ((hash << 5) - hash);
    }
    const h = hash % 360;
    return `hsl(${h}, 70%, 50%)`;
}

