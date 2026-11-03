<script lang="ts">
    import * as Popover from '$lib/components/ui/popover';
    import { cn } from '$lib/utils/shadcn.js';
    import { onDestroy } from 'svelte';
    import type { Snippet } from 'svelte';
    import ColorPickerPanel from './color-picker-panel.svelte';
    import { hexToHsl, hslToHex } from './color-picker.helpers';

    type Hsl = ReturnType<typeof hexToHsl>;

    let {
        initialColor = '#ff0000',
        initialAlpha = 1,
        onChange,
        onClose,
        position = 'right',
        class: className,
        children
    }: {
        initialColor?: string;
        initialAlpha?: number;
        onChange?: (color: string, alpha: number) => void;
        onClose?: (applied: boolean) => void;
        position?: 'top' | 'bottom' | 'left' | 'right';
        class?: string;
        children: Snippet;
    } = $props();

    let isOpen = $state(false);
    let alphaValue = $state(initialAlpha);
    let originalColor = initialColor;
    let originalAlpha = initialAlpha;
    let previewFrame: number | undefined;
    let hasPreviewed = false;

    // One color state: HSL drives the picker UI, hex is the value that gets previewed.
    let hsl = $state<Hsl>(hexToHsl(initialColor));
    let hex = $state(initialColor);

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
        alphaValue = value;
        schedulePreview();
    }

    // Coalesce canvas redraws to the browser's paint cadence while preserving live feedback.
    function schedulePreview() {
        if (!onChange || previewFrame !== undefined) return;

        previewFrame = requestAnimationFrame(() => {
            previewFrame = undefined;
            hasPreviewed = true;
            onChange(hex, alphaValue);
        });
    }

    function cancelScheduledPreview() {
        if (previewFrame === undefined) return;
        cancelAnimationFrame(previewFrame);
        previewFrame = undefined;
    }

    onDestroy(cancelScheduledPreview);

    // Keep clicks in the picker away from document-level listeners, for example the canvas.
    function stopPropagation(e: Event) {
        e.stopPropagation();
    }

    function resetState(): void {
        originalColor = initialColor;
        originalAlpha = initialAlpha;
        hex = initialColor;
        hsl = hexToHsl(initialColor);
        alphaValue = initialAlpha;
        hasPreviewed = false;
    }

    // bits-ui calls this only for user actions: the trigger, Escape or a click outside.
    function handleOpenChange(open: boolean): void {
        if (open) {
            resetState();
        } else {
            cancelChanges();
        }
    }

    // Apply changes and close
    function applyChanges() {
        cancelScheduledPreview();
        onChange?.(hex, alphaValue);
        onClose?.(true);
        hasPreviewed = false;
        isOpen = false;
    }

    // Close without applying
    function cancelChanges() {
        cancelScheduledPreview();
        if (hasPreviewed) {
            if (onClose) {
                onClose(false);
            } else {
                onChange?.(originalColor, originalAlpha);
            }
        }
        hasPreviewed = false;
        isOpen = false;
    }
</script>

<Popover.Root bind:open={isOpen} onOpenChange={handleOpenChange}>
    <Popover.Trigger class="m-0 border-0 bg-transparent p-0" onclick={stopPropagation}>
        {@render children()}
    </Popover.Trigger>
    <Popover.Content
        side={position}
        sideOffset={8}
        collisionPadding={10}
        role="dialog"
        aria-label="Color picker"
        class={cn('w-56 p-0', className)}
        onclick={stopPropagation}
        onmousedown={stopPropagation}
    >
        <ColorPickerPanel
            {hsl}
            {hex}
            alpha={alphaValue}
            onHslChange={setFromHsl}
            onHexChange={setFromHex}
            onAlphaChange={setAlpha}
            onApply={applyChanges}
            onCancel={cancelChanges}
        />
    </Popover.Content>
</Popover.Root>
