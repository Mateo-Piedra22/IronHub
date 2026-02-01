'use client';

type RGB = { r: number; g: number; b: number };

const clamp255 = (n: number) => Math.max(0, Math.min(255, Math.round(n)));

const parseHex = (hex: string): RGB | null => {
    const s = String(hex || '').trim().replace('#', '');
    if (!/^[0-9a-fA-F]{6}$/.test(s)) return null;
    const r = parseInt(s.slice(0, 2), 16);
    const g = parseInt(s.slice(2, 4), 16);
    const b = parseInt(s.slice(4, 6), 16);
    return { r, g, b };
};

const mix = (a: RGB, b: RGB, t: number): RGB => {
    const k = Math.max(0, Math.min(1, Number(t)));
    return {
        r: clamp255(a.r * (1 - k) + b.r * k),
        g: clamp255(a.g * (1 - k) + b.g * k),
        b: clamp255(a.b * (1 - k) + b.b * k),
    };
};

const toVar = (rgb: RGB) => `${rgb.r} ${rgb.g} ${rgb.b}`;

export type GymTheme = {
    primary?: string | null;
    secondary?: string | null;
    background?: string | null;
    text?: string | null;
};

export function applyGymTheme(theme: GymTheme | null | undefined) {
    if (typeof document === 'undefined') return;
    const primary = parseHex(String(theme?.primary || ''));
    if (!primary) return;

    const white: RGB = { r: 255, g: 255, b: 255 };
    const black: RGB = { r: 0, g: 0, b: 0 };

    const shades: Record<string, RGB> = {
        '50': mix(primary, white, 0.92),
        '100': mix(primary, white, 0.85),
        '200': mix(primary, white, 0.72),
        '300': mix(primary, white, 0.56),
        '400': mix(primary, white, 0.32),
        '500': primary,
        '600': mix(primary, black, 0.15),
        '700': mix(primary, black, 0.28),
        '800': mix(primary, black, 0.42),
        '900': mix(primary, black, 0.58),
        '950': mix(primary, black, 0.72),
    };

    for (const [k, v] of Object.entries(shades)) {
        document.documentElement.style.setProperty(`--primary-${k}`, toVar(v));
    }
}
