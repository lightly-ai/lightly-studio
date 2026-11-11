<script lang="ts">
    import * as Popover from '$lib/components/ui/popover';
    import { cn } from '$lib/utils/shadcn.js';
    import type { Snippet } from 'svelte';
    import ColorPickerPanel from './color-picker-panel.svelte';
    import { createColorPickerState } from './color-picker-state.svelte';

    let {
        initialColor = '#ff0000',
        initialAlpha = 1,
        onChange,
        onClose,
        position = 'right',
        triggerLabel,
        class: className,
        children
    }: {
        initialColor?: string;
        initialAlpha?: number;
        onChange?: (color: string, alpha: number) => void;
        onClose?: (applied: boolean) => void;
        position?: 'top' | 'bottom' | 'left' | 'right';
        triggerLabel?: string;
        class?: string;
        children: Snippet;
    } = $props();

    const picker = createColorPickerState({
        getInitialColor: () => initialColor,
        getInitialAlpha: () => initialAlpha,
        getOnChange: () => onChange,
        getOnClose: () => onClose
    });

    // Keep clicks in the picker away from document-level listeners, for example the canvas.
    function stopPropagation(e: Event) {
        e.stopPropagation();
    }
</script>

<Popover.Root bind:open={picker.isOpen} onOpenChange={picker.handleOpenChange}>
    <Popover.Trigger
        class="m-0 border-0 bg-transparent p-0"
        aria-label={triggerLabel}
        onclick={stopPropagation}
    >
        {@render children()}
    </Popover.Trigger>
    <Popover.Content
        side={position}
        align={position === 'left' || position === 'right' ? 'start' : 'center'}
        sideOffset={8}
        collisionPadding={10}
        role="dialog"
        aria-label="Color picker"
        class={cn('w-56 p-0', className)}
        onclick={stopPropagation}
        onmousedown={stopPropagation}
    >
        <ColorPickerPanel
            hsl={picker.hsl}
            hex={picker.hex}
            alpha={picker.alpha}
            onHslChange={picker.setFromHsl}
            onHexChange={picker.setFromHex}
            onAlphaChange={picker.setAlpha}
            onApply={picker.applyChanges}
            onCancel={picker.cancelChanges}
        />
    </Popover.Content>
</Popover.Root>
