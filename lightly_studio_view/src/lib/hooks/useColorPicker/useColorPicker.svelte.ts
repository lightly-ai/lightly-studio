import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import { getColorByLabel, hexToRgba, rgbaToHex } from '$lib/utils';
import { fromStore } from 'svelte/store';

/**
 * Resolves the swatch colors for a label (with custom-color overrides applied),
 * plus the initial values to seed a color picker, and a setter to persist picks.
 *
 * `getLabel` is a function so the hook stays reactive when the consumer's label changes.
 */
export function useColorPicker(getLabel: () => string) {
    const { setCustomColor, customLabelColorsStore } = useCustomLabelColors();
    const colors = fromStore(customLabelColorsStore);

    const customColor = $derived(colors.current[getLabel()]);
    const defaultBorder = $derived(getColorByLabel(getLabel(), 1).color);
    const defaultBackground = $derived(getColorByLabel(getLabel(), 0.35).color);

    const borderColor = $derived(customColor?.color ?? defaultBorder);
    const backgroundColor = $derived.by(() => {
        if (!customColor) return defaultBackground;
        return hexToRgba(customColor.color, customColor.alpha * 0.35);
    });

    const initialColor = $derived(customColor?.color ?? rgbaToHex(defaultBorder) ?? '#ff0000');
    const initialAlpha = $derived(customColor?.alpha ?? 1);

    return {
        get borderColor() {
            return borderColor;
        },
        get backgroundColor() {
            return backgroundColor;
        },
        get initialColor() {
            return initialColor;
        },
        get initialAlpha() {
            return initialAlpha;
        },
        setColor(color: string, alpha: number) {
            setCustomColor(getLabel(), color, alpha);
        }
    };
}
