import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import { hexToRgb } from './colorConvert';
import { getColorPair } from './getColorPair';

const COLOR_PALETTE: Array<[number, number, number]> = [
    [255, 0, 0], // Red
    [0, 255, 0], // Green
    [0, 0, 255], // Blue
    [255, 255, 0], // Yellow
    [255, 0, 255], // Magenta
    [0, 255, 255], // Cyan
    [128, 0, 0], // Maroon
    [0, 128, 0], // Dark Green
    [0, 0, 128], // Navy
    [128, 128, 0], // Olive
    [128, 0, 128], // Purple
    [0, 128, 128], // Teal
    [192, 192, 192], // Silver
    [128, 128, 128], // Gray
    [255, 165, 0], // Orange
    [255, 20, 147], // Deep Pink
    [75, 0, 130], // Indigo
    [255, 105, 180], // Hot Pink
    [0, 255, 127], // Spring Green
    [255, 215, 0], // Gold
    [255, 69, 0] // Red-Orange
];

export const getColorByLabel = (label: string, alpha: number = 1) => {
    alpha = Math.max(0, Math.min(alpha, 1));

    const { getCustomColor, hasCustomColor } = useCustomLabelColors();

    if (hasCustomColor(label)) {
        const customColor = getCustomColor(label);
        if (customColor) {
            // Apply the requested alpha, but respect the custom alpha.
            return getColorPair(hexToRgb(customColor.color), customColor.alpha * alpha);
        }
    }

    // Hash the label into the palette. Indexing matches the previous implementation
    // (`(|hash| % (palette.length - 1)) + 1` mapped to `palette[index - 1]`), which
    // uses 20 of the 21 palette entries — preserved here to keep label colors stable.
    const hash = Array.from(label).reduce((h, char) => (h << 5) - h + char.charCodeAt(0), 0);
    const index = (Math.abs(hash) % (COLOR_PALETTE.length - 1)) + 1;
    const [r, g, b] = COLOR_PALETTE[index - 1];

    return getColorPair({ r, g, b }, alpha);
};
