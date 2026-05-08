import { getColorPair } from './getColorPair';

const COLOR_PALETTE = [
    [255, 0, 0],
    [0, 255, 0],
    [0, 0, 255],
    [255, 255, 0],
    [255, 0, 255],
    [0, 255, 255],
    [128, 0, 0],
    [0, 128, 0],
    [0, 0, 128],
    [128, 128, 0],
    [128, 0, 128],
    [0, 128, 128],
    [192, 192, 192],
    [128, 128, 128],
    [255, 165, 0],
    [255, 20, 147],
    [75, 0, 130],
    [255, 105, 180],
    [0, 255, 127],
    [255, 215, 0],
    [255, 69, 0]
];

/** Deterministically picks a color from the preset palette by hashing `key`, applying `alpha` to both the color and its contrast. */
export const computeColorByKey = (key: string, alpha: number = 1) => {
    alpha = Math.max(0, Math.min(alpha, 1));

    const hash = Array.from(key).reduce((h, char) => (h << 5) - h + char.charCodeAt(0), 0);
    const index = (Math.abs(hash) % (COLOR_PALETTE.length - 1)) + 1;

    if (index >= 1 && index <= COLOR_PALETTE.length - 1) {
        const [r, g, b] = COLOR_PALETTE[index - 1];
        return getColorPair({ r, g, b }, alpha);
    }

    const r = (index * 30 + 20) % 256;
    const g = (index * 60 + 100) % 256;
    const b = (index * 90 + 150) % 256;

    const maxColor = Math.max(r, g, b);
    const minColor = Math.min(r, g, b);

    if (maxColor === minColor) {
        return getColorPair({ r: 255, g: 255, b: 255 }, alpha);
    }

    const scale = 255 / maxColor;
    return getColorPair(
        { r: Math.round(r * scale), g: Math.round(g * scale), b: Math.round(b * scale) },
        alpha
    );
};
