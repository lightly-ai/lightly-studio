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

    // Hash the label deterministically into the palette so a given label always maps
    // to the same color across sessions.
    const hash = Array.from(label).reduce((h, char) => (h << 5) - h + char.charCodeAt(0), 0);
    const index = Math.abs(hash) % COLOR_PALETTE.length;
    const [r, g, b] = COLOR_PALETTE[index];

    return getColorPair({ r, g, b }, alpha);
};
