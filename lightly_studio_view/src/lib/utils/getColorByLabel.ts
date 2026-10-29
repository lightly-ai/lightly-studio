import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import { hexToRgb, oklchHueWheelColor } from './colorConvert';
import { getColorPair } from './getColorPair';

// 32 perceptually-uniform colors: the union of two equal-hue OKLCH wheels. Each
// wheel fixes lightness and chroma and sweeps 16 evenly-spaced hues, so colors
// within a wheel differ only in hue, while the two wheels differ in
// brightness/saturation. The second wheel is rotated by half a hue step so its
// hues fall in the first wheel's gaps, spreading all 32 hues evenly around the
// circle. Generated rather than hand-tuned to keep the spec explicit.
const COLORS_PER_WHEEL = 16;
const HUE_STEP = 360 / COLORS_PER_WHEEL;
const WHEELS: Array<{ lightness: number; chroma: number; hueOffset: number }> = [
    { lightness: 0.65, chroma: 0.3, hueOffset: 0 },
    { lightness: 0.8, chroma: 0.22, hueOffset: HUE_STEP / 2 }
];
const COLOR_PALETTE: Array<[number, number, number]> = WHEELS.flatMap(
    ({ lightness, chroma, hueOffset }) =>
        Array.from({ length: COLORS_PER_WHEEL }, (_, i) => {
            const { r, g, b } = oklchHueWheelColor({
                index: i,
                count: COLORS_PER_WHEEL,
                lightness,
                chroma,
                hueOffset
            });
            return [r, g, b] as [number, number, number];
        })
);

// 20 categorical colors that stay distinct from each other on the dark plot and image
// backgrounds. Labels with a known position (see `setLabelColorOrder`) take these in order, so a
// collection with up to 20 classes never repeats a color.
export const CATEGORICAL_PALETTE: readonly string[] = [
    '#e6194b',
    '#3cb44b',
    '#ffe119',
    '#4363d8',
    '#f58231',
    '#b04ee0',
    '#42d4f4',
    '#f032e6',
    '#bfef45',
    '#fabed4',
    '#469990',
    '#dcbeff',
    '#b5762a',
    '#fffac8',
    '#a83232',
    '#aaffc3',
    '#9e9e1a',
    '#ffd8b1',
    '#7f8cff',
    '#c47ab0'
];

// Position of each known label in the categorical palette.
const labelColorIndex = new Map<string, number>();

/**
 * Assigns the categorical palette to labels in the given order (e.g. annotation classes in
 * creation order). Plot legends, boxes and pills then share one color per class. Labels past the
 * palette take the hue wheel in order; labels not in the list keep a hashed color.
 */
export const setLabelColorOrder = (labels: readonly string[]) => {
    const unchanged =
        labels.length === labelColorIndex.size &&
        labels.every((label, index) => labelColorIndex.get(label) === index);
    if (unchanged) return;
    labelColorIndex.clear();
    labels.forEach((label, index) => labelColorIndex.set(label, index));
    // Components derive label colors from the custom color store, so a change there re-renders
    // them with the new colors.
    useCustomLabelColors().refreshColors();
};

// FNV-1a 32-bit hash. Mixes each byte into all 32 bits, so the result distributes
// well even when reduced modulo a power-of-two table length.
const fnv1aHash = (value: string) => {
    let hash = 0x811c9dc5; // FNV-1a 32-bit offset basis
    for (let i = 0; i < value.length; i++) {
        hash ^= value.charCodeAt(i);
        hash = Math.imul(hash, 0x01000193); // FNV-1a 32-bit prime
    }
    return hash >>> 0; // coerce to unsigned 32-bit
};

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

    const paletteIndex = labelColorIndex.get(label);
    if (paletteIndex !== undefined && paletteIndex < CATEGORICAL_PALETTE.length) {
        return getColorPair(hexToRgb(CATEGORICAL_PALETTE[paletteIndex]), alpha);
    }
    if (paletteIndex !== undefined) {
        // Later classes take the hue wheel in order, which repeats less than hashing.
        const [r, g, b] =
            COLOR_PALETTE[(paletteIndex - CATEGORICAL_PALETTE.length) % COLOR_PALETTE.length];
        return getColorPair({ r, g, b }, alpha);
    }

    // Hash the label deterministically into the palette so a given label always maps
    // to the same color across sessions.
    const index = fnv1aHash(label) % COLOR_PALETTE.length;
    const [r, g, b] = COLOR_PALETTE[index];

    return getColorPair({ r, g, b }, alpha);
};
