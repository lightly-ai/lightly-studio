<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import { Slider } from '$lib/components/ui/slider';
    import { cn } from '$lib/utils/shadcn.js';
    import { X } from '@lucide/svelte';
    import { Dialog as DialogPrimitive } from 'bits-ui';
    import type { Snippet } from 'svelte';
    import { fly } from 'svelte/transition';

    let {
        initialColor = '#ff0000',
        initialAlpha = 1,
        onChange,
        position = 'right',
        class: className,
        children
    }: {
        initialColor?: string;
        initialAlpha?: number;
        onChange?: (color: string, alpha: number) => void;
        position?: 'top' | 'bottom' | 'left' | 'right';
        class?: string;
        children: Snippet;
    } = $props();

    let isOpen = $state(false);
    let triggerElement: HTMLElement;
    let colorValue = $state(initialColor);
    let alphaValue = $state(initialAlpha);

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
    let saturationRef = $state<HTMLDivElement>();
    let hueRef = $state<HTMLDivElement>();

    // HSL color model state (for the color picker UI)
    let hue = $state(0);
    let saturation = $state(100);
    let lightness = $state(50);

    // Convert hex to HSL on initialization
    $effect(() => {
        if (colorValue.startsWith('#')) {
            const [h, s, l] = hexToHsl(colorValue);
            hue = h;
            saturation = s;
            lightness = l;
        }
    });

    // Convert HSL to hex when HSL values change
    $effect(() => {
        colorValue = hslToHex(hue, saturation, lightness);
    });

    // Helper: Convert hex to HSL
    function hexToHsl(hex: string): [number, number, number] {
        // Remove # if present
        hex = hex.replace(/^#/, '');

        // Parse hex
        const r = parseInt(hex.slice(0, 2), 16) / 255;
        const g = parseInt(hex.slice(2, 4), 16) / 255;
        const b = parseInt(hex.slice(4, 6), 16) / 255;

        const max = Math.max(r, g, b);
        const min = Math.min(r, g, b);
        const l = (max + min) / 2;

        let h = 0;
        let s = 0;

        if (max !== min) {
            const d = max - min;
            s = l > 0.5 ? d / (2 - max - min) : d / (max + min);

            switch (max) {
                case r:
                    h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
                    break;
                case g:
                    h = ((b - r) / d + 2) / 6;
                    break;
                case b:
                    h = ((r - g) / d + 4) / 6;
                    break;
            }
        }

        return [Math.round(h * 360), Math.round(s * 100), Math.round(l * 100)];
    }

    // Helper: Convert HSL to hex
    function hslToHex(h: number, s: number, l: number): string {
        h /= 360;
        s /= 100;
        l /= 100;

        let r, g, b;

        if (s === 0) {
            r = g = b = l;
        } else {
            const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
            const p = 2 * l - q;

            r = hueToRgb(p, q, h + 1 / 3);
            g = hueToRgb(p, q, h);
            b = hueToRgb(p, q, h - 1 / 3);
        }

        function hueToRgb(p: number, q: number, t: number) {
            if (t < 0) t += 1;
            if (t > 1) t -= 1;
            if (t < 1 / 6) return p + (q - p) * 6 * t;
            if (t < 1 / 2) return q;
            if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
            return p;
        }

        const toHex = (x: number) => {
            const hex = Math.round(x * 255).toString(16);
            return hex.length === 1 ? '0' + hex : hex;
        };

        return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
    }

    // Handle saturation/lightness picker interaction
    function handleSaturationPick(e: MouseEvent) {
        if (!saturationRef) return;

        const rect = saturationRef.getBoundingClientRect();
        const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));

        saturation = Math.round(x * 100);
        lightness = Math.round((1 - y) * 100);

        if (e.buttons !== 1 && e.type !== 'mousedown') return;

        const onMouseMove = (moveEvent: MouseEvent) => handleSaturationPick(moveEvent);

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener(
            'mouseup',
            () => {
                document.removeEventListener('mousemove', onMouseMove);
            },
            { once: true }
        );
    }

    // Handle hue slider interaction
    function handleHuePick(e: MouseEvent) {
        if (!hueRef) return;

        const rect = hueRef.getBoundingClientRect();
        const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));

        hue = Math.round(x * 360);

        if (e.buttons !== 1 && e.type !== 'mousedown') return;

        const onMouseMove = (moveEvent: MouseEvent) => handleHuePick(moveEvent);

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener(
            'mouseup',
            () => {
                document.removeEventListener('mousemove', onMouseMove);
            },
            { once: true }
        );
    }

    // Handle preset color selection
    function selectPresetColor(color: string) {
        colorValue = color;
    }

    // Handle manual hex input
    function handleHexInput(e: Event) {
        const value = (e.target as HTMLInputElement).value;

        // Simple validation for hex color format
        if (/^#[0-9A-Fa-f]{6}$/.test(value)) {
            colorValue = value;
        }
    }

    // Handle transparency slider
    function handleTransparencyChange(values: number[]) {
        alphaValue = values[0];
    }

    // Make sure events don't propagate out from the color picker
    function preventPropagation(e: Event) {
        e.stopPropagation();
        e.preventDefault();
    }

    // Toggle the picker open/closed
    function togglePicker(e: Event) {
        e.stopPropagation();
        e.preventDefault();
        isOpen = !isOpen;

        if (isOpen) {
            // Position the picker in the next frame after it's rendered
            setTimeout(updatePickerPosition, 0);
        }
    }

    // Apply changes and close
    function applyChanges() {
        if (onChange) {
            onChange(colorValue, alphaValue);
        }
        isOpen = false;
    }

    // Close without applying
    function cancelChanges() {
        isOpen = false;
    }

    // Handle escape key
    function handleKeyDown(e: KeyboardEvent) {
        if (e.key === 'Escape') {
            cancelChanges();
        }
    }

    // Handle clicks outside
    function setupClickOutside() {
        function handleClickOutside(e: MouseEvent) {
            if (isOpen && triggerElement) {
                const pickerElement = document.getElementById('color-picker-panel');
                if (
                    pickerElement &&
                    !pickerElement.contains(e.target as Node) &&
                    !triggerElement.contains(e.target as Node)
                ) {
                    isOpen = false;
                }
            }
        }

        document.addEventListener('mousedown', handleClickOutside);

        // Add a window resize listener to reposition if needed
        const handleResize = () => updatePickerPosition();
        window.addEventListener('resize', handleResize);

        return {
            destroy: () => {
                document.removeEventListener('mousedown', handleClickOutside);
                window.removeEventListener('resize', handleResize);
            }
        };
    }

    // Position the picker to ensure it's visible in the viewport
    function updatePickerPosition() {
        if (!triggerElement) return;

        requestAnimationFrame(() => {
            const pickerElement = document.getElementById('color-picker-panel');
            if (!pickerElement) return;

            const triggerRect = triggerElement.getBoundingClientRect();
            const viewportWidth = window.innerWidth;
            const viewportHeight = window.innerHeight;
            const pickerWidth = pickerElement.offsetWidth;
            const pickerHeight = pickerElement.offsetHeight;

            // Initial position calculation based on preferred position
            let left, top;

            switch (position) {
                case 'top':
                    left = triggerRect.left + triggerRect.width / 2 - pickerWidth / 2;
                    top = triggerRect.top - pickerHeight - 8;
                    break;
                case 'bottom':
                    left = triggerRect.left + triggerRect.width / 2 - pickerWidth / 2;
                    top = triggerRect.bottom + 8;
                    break;
                case 'left':
                    left = triggerRect.left - pickerWidth - 8;
                    top = triggerRect.top;
                    break;
                case 'right':
                default:
                    left = triggerRect.right + 8;
                    top = triggerRect.top;
                    break;
            }

            // Adjust if picker would go off-screen
            if (left < 10) left = 10;
            if (top < 10) top = 10;
            if (left + pickerWidth > viewportWidth - 10) left = viewportWidth - pickerWidth - 10;
            if (top + pickerHeight > viewportHeight - 10) top = viewportHeight - pickerHeight - 10;

            // Apply the calculated position
            pickerElement.style.position = 'fixed';
            pickerElement.style.left = `${left}px`;
            pickerElement.style.top = `${top}px`;
        });
    }

    $effect.root(() => {
        if (isOpen) {
            const cleanup = setupClickOutside();
            return cleanup.destroy;
        }
    });
</script>

<div class="relative inline-block">
    <!-- Trigger button with strong event isolation -->
    <button
        type="button"
        class="m-0 border-0 bg-transparent p-0"
        onclick={togglePicker}
        onkeydown={handleKeyDown}
        bind:this={triggerElement}
        tabindex="0"
    >
        {@render children()}
    </button>

    <!-- Color picker panel with portal via fixed positioning -->
    {#if isOpen}
        <DialogPrimitive.Portal>
            <div
                id="color-picker-panel"
                role="dialog"
                aria-label="Color picker"
                class={cn(
                    'bg-popover text-popover-foreground z-50 w-56 rounded-md border shadow-md',
                    className
                )}
                transition:fly={{
                    duration: 150,
                    y: 0,
                    x: 0
                }}
                onkeydown={handleKeyDown}
                onclick={preventPropagation}
                onmousedown={preventPropagation}
                tabindex="-1"
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
                        <!-- Main saturation/lightness picker -->
                        <div
                            class="relative h-28 cursor-crosshair rounded"
                            style={`background-image: linear-gradient(to top, #000, transparent), linear-gradient(to right, #fff, hsl(${hue}, 100%, 50%))`}
                            bind:this={saturationRef}
                            onmousedown={handleSaturationPick}
                            role="dialog"
                            aria-label="Saturation and lightness picker"
                            tabindex="0"
                        >
                            <!-- Selection indicator -->
                            <div
                                class="absolute h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white shadow-md"
                                style={`left: ${saturation}%; top: ${100 - lightness}%; background-color: ${colorValue}`}
                            ></div>
                        </div>

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
                                style={`left: ${(hue / 360) * 100}%`}
                            ></div>
                        </div>

                        <!-- Hex input with color preview -->
                        <div class="flex items-center gap-2">
                            <div
                                class="h-6 w-6 rounded border"
                                style={`background-color: ${colorValue}`}
                            ></div>
                            <input
                                type="text"
                                value={colorValue}
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
                                            colorValue === color ? 'ring-primary ring-1' : ''
                                        )}
                                        style={`background-color: ${color}`}
                                        onclick={() => selectPresetColor(color)}
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
            </div>
        </DialogPrimitive.Portal>
    {/if}
</div>
