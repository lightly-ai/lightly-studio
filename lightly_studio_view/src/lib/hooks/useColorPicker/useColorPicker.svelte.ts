import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import { useCustomSourceColors } from '$lib/hooks/useCustomSourceColors';
import { getColorByLabel, getColorBySource, hexToRgba, rgbaToHex } from '$lib/utils';
import { onDestroy, untrack } from 'svelte';
import { fromStore } from 'svelte/store';

type SessionColor = NonNullable<
    Parameters<ReturnType<typeof useCustomLabelColors>['setPreviewColor']>[1]
>;

type ColorStore = Pick<
    ReturnType<typeof useCustomLabelColors>,
    'customColorsStore' | 'setCustomColor' | 'setPreviewColor' | 'clearPreviewColor'
>;

/** A color picker for an annotation class. See `createColorPicker`. */
export const useClassColorPicker = (getName: () => string) =>
    createColorPicker(getName, useCustomLabelColors(), getColorByLabel);

/** A color picker for an annotation source. See `createColorPicker`. */
export const useSourceColorPicker = (getName: () => string) =>
    createColorPicker(getName, useCustomSourceColors(), getColorBySource);

/**
 * Resolves the swatch colors for a name (with custom-color overrides applied),
 * plus the initial values to seed a color picker, and a setter to persist picks.
 *
 * `getName` is a function so the hook stays reactive when the consumer's name changes.
 */
function createColorPicker(
    getName: () => string,
    colorStore: ColorStore,
    getDefaultColor: typeof getColorByLabel
) {
    const { setCustomColor, setPreviewColor, clearPreviewColor } = colorStore;
    const colors = fromStore(colorStore.customColorsStore);
    // A session starts at the first setColor after a finished one. A rename can change the
    // name while the picker stays open, so the session follows the name.
    let session: { owner: symbol; name: string; color: SessionColor } | undefined;

    $effect.pre(() => {
        const name = getName();
        untrack(() => {
            if (!session || session.name === name) return;
            clearPreviewColor(session.name, session.owner);
            session.name = name;
            setPreviewColor(name, session.color, session.owner);
        });
    });

    onDestroy(() => {
        if (session) clearPreviewColor(session.name, session.owner);
    });

    const customColor = $derived(colors.current[getName()]);
    const defaultBorder = $derived(getDefaultColor(getName(), 1).color);
    const defaultBackground = $derived(getDefaultColor(getName(), 0.35).color);

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
            session ??= { owner: Symbol(), name: getName(), color: { color, alpha } };
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
