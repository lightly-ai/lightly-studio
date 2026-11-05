import { onDestroy } from 'svelte';
import { hexToHsl, hslToHex } from './color-picker.helpers';

type Hsl = ReturnType<typeof hexToHsl>;

interface Options {
    getInitialColor: () => string;
    getInitialAlpha: () => number;
    getOnChange: () => ((color: string, alpha: number) => void) | undefined;
    getOnClose: () => ((applied: boolean) => void) | undefined;
    getDefaultColor: () => string | undefined;
}

export function createColorPickerState({
    getInitialColor,
    getInitialAlpha,
    getOnChange,
    getOnClose,
    getDefaultColor
}: Options) {
    let isOpen = $state(false);
    let alpha = $state(getInitialAlpha());
    // One color state: HSL drives the picker UI, hex is the value that gets previewed.
    let hsl = $state<Hsl>(hexToHsl(getInitialColor()));
    let hex = $state(getInitialColor());
    let originalColor = getInitialColor();
    let originalAlpha = getInitialAlpha();
    let previewFrame: number | undefined;
    let hasPreviewed = false;

    // Coalesce canvas redraws to the browser's paint cadence while preserving live feedback.
    function schedulePreview(): void {
        const onChange = getOnChange();
        if (!onChange || previewFrame !== undefined) return;

        previewFrame = requestAnimationFrame(() => {
            previewFrame = undefined;
            hasPreviewed = true;
            onChange(hex, alpha);
        });
    }

    function cancelScheduledPreview(): void {
        if (previewFrame === undefined) return;
        cancelAnimationFrame(previewFrame);
        previewFrame = undefined;
    }

    onDestroy(cancelScheduledPreview);

    function setFromHex(value: string): void {
        hex = value;
        hsl = hexToHsl(value);
        schedulePreview();
    }

    function setFromHsl(value: Hsl): void {
        hsl = value;
        hex = hslToHex(value);
        schedulePreview();
    }

    function setAlpha(value: number): void {
        alpha = value;
        schedulePreview();
    }

    function resetState(): void {
        originalColor = getInitialColor();
        originalAlpha = getInitialAlpha();
        hex = originalColor;
        hsl = hexToHsl(originalColor);
        alpha = originalAlpha;
        hasPreviewed = false;
    }

    function applyChanges(): void {
        cancelScheduledPreview();
        getOnChange()?.(hex, alpha);
        getOnClose()?.(true);
        hasPreviewed = false;
        isOpen = false;
    }

    function cancelChanges(): void {
        cancelScheduledPreview();
        if (hasPreviewed) {
            const onClose = getOnClose();
            if (onClose) {
                onClose(false);
            } else {
                getOnChange()?.(originalColor, originalAlpha);
            }
        }
        hasPreviewed = false;
        isOpen = false;
    }

    // Only previews the default color. Apply saves it like any other color.
    function resetToDefault(): void {
        const defaultColor = getDefaultColor();
        if (!defaultColor) return;
        setFromHex(defaultColor);
        setAlpha(1);
    }

    // bits-ui calls this only for user actions: the trigger, Escape or a click outside.
    function handleOpenChange(open: boolean): void {
        if (open) {
            resetState();
        } else {
            cancelChanges();
        }
    }

    return {
        get isOpen() {
            return isOpen;
        },
        set isOpen(value: boolean) {
            isOpen = value;
        },
        get hsl() {
            return hsl;
        },
        get hex() {
            return hex;
        },
        get alpha() {
            return alpha;
        },
        get isDefaultColor() {
            return hex.toLowerCase() === getDefaultColor()?.toLowerCase() && alpha === 1;
        },
        setFromHex,
        setFromHsl,
        setAlpha,
        applyChanges,
        cancelChanges,
        resetToDefault,
        handleOpenChange
    };
}
