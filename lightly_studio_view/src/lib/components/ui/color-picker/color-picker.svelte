<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import * as Popover from '$lib/components/ui/popover';
    import { Slider } from '$lib/components/ui/slider';
    import { cn } from '$lib/utils/shadcn.js';
    import { X } from '@lucide/svelte';
    import { onDestroy } from 'svelte';
    import type { Snippet } from 'svelte';
    import { hexToHsl, hslToHex, isHexColor } from './color-picker.helpers';
    import SaturationBox from './saturation-box.svelte';

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

    // Predefined colors for quick selection
    const presetColors = [
        '#ff0000',
        '#ff8000',
        '#ffff00',
        '#80ff00',
        '#00ff00',
        '#00ffff',
        '#0080ff',
        '#0000ff',
        '#8000ff',
        '#ff00ff',
        '#ff0080',
        '#ffffff',
        '#cccccc',
        '#888888',
        '#444444',
        '#000000'
    ];

    // DOM references for interactions
    let hueRef = $state<HTMLDivElement>();

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

    function updateHue(e: MouseEvent) {
        if (!hueRef) return;

        const rect = hueRef.getBoundingClientRect();
        const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));

        setFromHsl({ ...hsl, h: Math.round(x * 360) });
    }

    // Mousemove calls only the updater so a drag cannot register additional listeners.
    function handleHuePick(e: MouseEvent) {
        updateHue(e);
        const onMouseMove = (moveEvent: MouseEvent) => updateHue(moveEvent);

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener(
            'mouseup',
            () => {
                document.removeEventListener('mousemove', onMouseMove);
            },
            { once: true }
        );
    }

    // Handle manual hex input
    function handleHexInput(e: Event) {
        const value = (e.target as HTMLInputElement).value;

        if (isHexColor(value)) setFromHex(value);
    }

    // Handle transparency slider
    function handleTransparencyChange(values: number[]) {
        alphaValue = values[0];
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
                <!-- Header -->
                <div class="flex items-center justify-between border-b px-3 py-2">
                    <h3 class="text-sm font-medium">Color</h3>
                    <Button variant="ghost" size="icon" class="h-6 w-6" onclick={cancelChanges}>
                        <X class="h-4 w-4" />
                    </Button>
                </div>

                <div class="p-3">
                    <!-- Color pickers -->
                    <div class="space-y-3">
                        <SaturationBox
                            {hsl}
                            onPick={(s, l) => setFromHsl({ ...hsl, s, l })}
                        />

                        <!-- Hue slider -->
                        <div
                            class="relative h-4 cursor-pointer rounded"
                            style="background: linear-gradient(to right, #f00, #ff0, #0f0, #0ff, #00f, #f0f, #f00)"
                            bind:this={hueRef}
                            onmousedown={handleHuePick}
                            role="dialog"
                            aria-label="Hue picker"
                            tabindex="0"
                        >
                            <!-- Hue indicator -->
                            <div
                                class="absolute top-0 h-full w-1 -translate-x-1/2 border-x border-white shadow-sm"
                                style={`left: ${(hsl.h / 360) * 100}%`}
                            ></div>
                        </div>

                        <!-- Hex input with color preview -->
                        <div class="flex items-center gap-2">
                            <div
                                class="h-6 w-6 rounded border"
                                style={`background-color: ${hex}`}
                            ></div>
                            <input
                                type="text"
                                value={hex}
                                class="bg-background flex-1 rounded border px-2 py-1 text-xs uppercase"
                                oninput={handleHexInput}
                            />
                        </div>

                        <!-- Transparency -->
                        <div class="space-y-1">
                            <div class="flex items-center justify-between text-xs">
                                <span>Opacity</span>
                                <span>{Math.round(alphaValue * 100)}%</span>
                            </div>
                            <Slider
                                type="multiple"
                                min={0}
                                max={1}
                                step={0.01}
                                value={[alphaValue]}
                                onValueChange={handleTransparencyChange}
                            />
                        </div>

                        <!-- Preset colors -->
                        <div class="space-y-1">
                            <div class="text-xs">Presets</div>
                            <div class="grid grid-cols-8 gap-1">
                                {#each presetColors as color}
                                    <button
                                        type="button"
                                        class={cn(
                                            'h-4 w-4 rounded-sm border',
                                            hex === color ? 'ring-primary ring-1' : ''
                                        )}
                                        style={`background-color: ${color}`}
                                        onclick={() => setFromHex(color)}
                                        title={color}
                                    ></button>
                                {/each}
                            </div>
                        </div>
                    </div>

                    <!-- Actions -->
                    <div class="mt-3 flex justify-end gap-2">
                        <Button
                            size="sm"
                            variant="outline"
                            class="h-7 px-2 py-0 text-xs"
                            onclick={cancelChanges}
                        >
                            Cancel
                        </Button>
                        <Button size="sm" class="h-7 px-2 py-0 text-xs" onclick={applyChanges}>
                            Apply
                        </Button>
                    </div>
                </div>
    </Popover.Content>
</Popover.Root>
