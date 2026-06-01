export interface RGB {
    r: number;
    g: number;
    b: number;
}

export function hexToRgb(hex: string): RGB {
    return {
        r: parseInt(hex.slice(1, 3), 16),
        g: parseInt(hex.slice(3, 5), 16),
        b: parseInt(hex.slice(5, 7), 16)
    };
}

export function hexToRgba(hex: string, alpha: number): string {
    const { r, g, b } = hexToRgb(hex);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function rgbaToHex(rgba: string): string | undefined {
    const match = rgba.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    if (!match) return undefined;
    const r = parseInt(match[1]);
    const g = parseInt(match[2]);
    const b = parseInt(match[3]);
    return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
}

/** Formats an `[r, g, b, a]` tuple (alpha in 0-255) as an `rgba(...)` string. */
export function rgbaFromBytes([r, g, b, a]: readonly [number, number, number, number]): string {
    return `rgba(${r}, ${g}, ${b}, ${a / 255})`;
}

/** Returns the input rgba string with its alpha component replaced. Accepts `rgb(...)` too. */
export function withAlpha(color: string, alpha: number): string {
    return color.replace(/rgba?\(([^)]+)\)/, (_, c) => {
        const [r, g, b] = c.split(',').map(Number);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    });
}

/** Drops the alpha channel from an `rgba(...)` string, returning `rgb(r, g, b)`. */
export function stripAlpha(color: string): string {
    return color.replace(/rgba?\((\d+,\s*\d+,\s*\d+)(?:,\s*[\d.]+)?\)/, 'rgb($1)');
}
