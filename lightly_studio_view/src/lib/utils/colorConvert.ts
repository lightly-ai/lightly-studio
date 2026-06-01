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

/** Linear-light sRGB channel → gamma-encoded sRGB channel (IEC 61966-2-1). */
function linearToGamma(c: number): number {
    return c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055;
}

/**
 * Converts an OKLCH color to 8-bit sRGB.
 *
 * @param l Lightness, 0-1.
 * @param c Chroma, typically 0-0.4.
 * @param h Hue in degrees, 0-360.
 *
 * Channels that fall outside the sRGB gamut are clamped to [0, 255], which can
 * shift the perceived hue/chroma for highly saturated inputs. Uses Björn
 * Ottosson's OKLab matrices (https://bottosson.github.io/posts/oklab/).
 */
export function oklchToRgb(l: number, c: number, h: number): RGB {
    const hRad = (h * Math.PI) / 180;
    const a = c * Math.cos(hRad);
    const b = c * Math.sin(hRad);

    // OKLab → non-linear LMS → linear LMS (cube).
    const l_ = l + 0.3963377774 * a + 0.2158037573 * b;
    const m_ = l - 0.1055613458 * a - 0.0638541728 * b;
    const s_ = l - 0.0894841775 * a - 1.291485548 * b;
    const lCube = l_ ** 3;
    const mCube = m_ ** 3;
    const sCube = s_ ** 3;

    // Linear LMS → linear sRGB.
    const rLin = 4.0767416621 * lCube - 3.3077115913 * mCube + 0.2309699292 * sCube;
    const gLin = -1.2684380046 * lCube + 2.6097574011 * mCube - 0.3413193965 * sCube;
    const bLin = -0.0041960863 * lCube - 0.7034186147 * mCube + 1.707614701 * sCube;

    const toByte = (channel: number) =>
        Math.round(Math.max(0, Math.min(1, linearToGamma(channel))) * 255);

    return { r: toByte(rLin), g: toByte(gLin), b: toByte(bLin) };
}
