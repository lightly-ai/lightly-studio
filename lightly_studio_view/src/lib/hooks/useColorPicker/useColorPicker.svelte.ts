import { useCustomLabelColors, type CustomColor } from '$lib/hooks/useCustomLabelColors';
import { getColorByLabel, hexToRgba, rgbaToHex } from '$lib/utils';
import { onDestroy } from 'svelte';
import { fromStore } from 'svelte/store';

/**
 * Resolves the swatch colors for a label (with custom-color overrides applied),
 * plus the initial values to seed a color picker, and a setter to persist picks.
 *
 * `getLabel` is a function so the hook stays reactive when the consumer's label changes.
 */
export function useColorPicker(getLabel: () => string) {
    const { setCustomColor, setPreviewColor, clearPreviewColor, customLabelColorsStore } =
        useCustomLabelColors();
    const colors = fromStore(customLabelColorsStore);
    // A session starts at the first setColor after a finished one. It keeps the name it
    // started with, because a rename can change the label while the picker stays mounted.
    let session: { owner: symbol; name: string; color: CustomColor } | undefined;

    onDestroy(() => {
        if (session) clearPreviewColor(session.name, session.owner);
    });

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
            session ??= { owner: Symbol(), name: getLabel(), color: { color, alpha } };
            session.color = { color, alpha };
            setPreviewColor(session.name, session.color, session.owner);
        },
        finishColorChange(applied: boolean) {
            if (!session) return;

            const { owner, name, color } = session;
            session = undefined;
            if (applied) setCustomColor(name, color.color, color.alpha);
            clearPreviewColor(name, owner);
        }
    };
}
