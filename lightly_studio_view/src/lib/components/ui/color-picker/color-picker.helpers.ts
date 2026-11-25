import { hsl } from 'd3-color';

interface Hsl {
    h: number;
    s: number;
    l: number;
}

export function hexToHsl(hex: string): Hsl {
    const { h, s, l } = hsl(hex);
    // d3 gives NaN for the hue of gray colors and for the saturation of black and white.
    return {
        h: Math.round(h || 0),
        s: Math.round((s || 0) * 100),
        l: Math.round(l * 100)
    };
}

export function hslToHex({ h, s, l }: Hsl): string {
    return hsl(h, s / 100, l / 100).formatHex();
}

export function isHexColor(value: string): boolean {
    return /^#[0-9a-f]{6}$/i.test(value);
}
