import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import { useCustomSourceColors } from '$lib/hooks/useCustomSourceColors/useCustomSourceColors';
import { getColorByLabel, getColorBySource, hexToRgba, rgbaToHex } from '$lib/utils';
import { onDestroy } from 'svelte';
import { fromStore } from 'svelte/store';

type SessionColor = NonNullable<
    Parameters<ReturnType<typeof useCustomLabelColors>['setPreviewColor']>[1]
>;

/**
 * Resolves the swatch colors for a class or source (with custom-color overrides applied),
 * plus the initial values to seed a color picker, and a setter to persist picks.
 *
 * `getLabel` is a function so the hook stays reactive when the consumer's label changes.
 */
export function useColorPicker(getLabel: () => string, options: { kind: 'class' | 'source' }) {
    const isSource = options.kind === 'source';
    const classColors = useCustomLabelColors();
    const sourceColors = useCustomSourceColors();
    const { setCustomColor, setPreviewColor, clearPreviewColor } = isSource
        ? sourceColors
        : classColors;
    const colorsStore = isSource
        ? sourceColors.customSourceColorsStore
        : classColors.customLabelColorsStore;
    const getColor = isSource ? getColorBySource : getColorByLabel;
    const colors = fromStore(colorsStore);
    // A session starts at the first setColor after a finished one. It keeps the name it
    // started with, because a rename can change the label while the picker stays mounted.
    let session: { owner: symbol; name: string; color: SessionColor } | undefined;

    onDestroy(() => {
        if (session) clearPreviewColor(session.name, session.owner);
    });

    const customColor = $derived(colors.current[getLabel()]);
    const defaultBorder = $derived(getColor(getLabel(), 1).color);
    const defaultBackground = $derived(getColor(getLabel(), 0.35).color);

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
