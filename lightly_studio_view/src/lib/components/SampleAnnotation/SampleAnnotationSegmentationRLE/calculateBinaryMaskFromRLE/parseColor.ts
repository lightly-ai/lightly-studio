/**
 * Parses a CSS color string into its RGBA components.
 * Uses a temporary canvas to leverage the browser's built-in parsing.
 * @param color The CSS color string (e.g., '#FF0000', 'rgba(255, 0, 0, 0.5)', 'red').
 * @returns An object with r, g, b, a components (0-255).
 */
export default function parseColor(color: string): { r: number; g: number; b: number; a: number } {
    // Ensure this runs only in a browser-like environment or is mocked
    if (typeof document === 'undefined') {
        // Simple fallback for non-browser envs, might need adjustment based on mock needs
        return { r: 0, g: 0, b: 0, a: 255 };
    }
    const canvas = document.createElement('canvas');
    canvas.width = 1;
    canvas.height = 1;
    // Note: 'willReadFrequently' might not be supported/relevant in all mocks
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    if (!ctx) {
        console.error('Failed to get context for color parsing, returning default black');
        return { r: 0, g: 0, b: 0, a: 255 }; // Default to opaque black on error
    }
    ctx.fillStyle = color;
    ctx.fillRect(0, 0, 1, 1);
    // Use try-catch as getImageData might fail in some minimal mocks
    try {
        const data = ctx.getImageData(0, 0, 1, 1).data;
        return { r: data[0], g: data[1], b: data[2], a: data[3] };
    } catch (e) {
        console.error('Failed to getImageData for color parsing, returning default black:', e);
        return { r: 0, g: 0, b: 0, a: 255 };
    }
}
