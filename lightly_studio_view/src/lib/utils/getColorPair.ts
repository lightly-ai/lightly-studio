interface RGB {
    r: number;
    g: number;
    b: number;
}

interface ColorPair {
    // The RGBA color string.
    color: string;
    // The RGB-inverted contrast color string.
    contrastColor: string;
}

/** Returns an RGBA color and its RGB-inverted contrast color. */
export const getColorPair = ({ r, g, b }: RGB, alpha: number): ColorPair => ({
    color: `rgba(${r}, ${g}, ${b}, ${alpha})`,
    contrastColor: `rgba(${255 - r}, ${255 - g}, ${255 - b}, ${alpha})`
});
