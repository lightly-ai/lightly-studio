<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import { Slider } from '$lib/components/ui/slider';
    import { X } from '@lucide/svelte';
    import ColorPickerActions from './color-picker-actions.svelte';
    import { hexToHsl, isHexColor } from './color-picker.helpers';
    import HueSlider from './hue-slider.svelte';
    import PresetSwatches from './preset-swatches.svelte';
    import SaturationBox from './saturation-box.svelte';

    type Hsl = ReturnType<typeof hexToHsl>;

    interface Props {
        hsl: Hsl;
        hex: string;
        alpha: number;
        onHslChange: (value: Hsl) => void;
        onHexChange: (hex: string) => void;
        onAlphaChange: (alpha: number) => void;
        onApply: () => void;
        onCancel: () => void;
        onReset?: () => void;
        isDefaultColor?: boolean;
    }

    let {
        hsl,
        hex,
        alpha,
        onHslChange,
        onHexChange,
        onAlphaChange,
        onApply,
        onCancel,
        onReset,
        isDefaultColor = false
    }: Props = $props();

    function handleHexInput(e: Event): void {
        const value = (e.target as HTMLInputElement).value;
        if (isHexColor(value)) onHexChange(value.toLowerCase());
    }
</script>

<div class="flex items-center justify-between border-b px-3 py-2">
    <h3 class="text-sm font-medium">Color</h3>
    <Button
        variant="ghost"
        size="icon"
        class="h-6 w-6"
        aria-label="Close"
        onclick={onCancel}
    >
        <X class="h-4 w-4" />
    </Button>
</div>

<div class="p-3">
    <div class="space-y-3">
        <SaturationBox {hsl} onPick={(s, l) => onHslChange({ ...hsl, s, l })} />
        <HueSlider hue={hsl.h} onHueChange={(h) => onHslChange({ ...hsl, h })} />

        <div class="flex items-center gap-2">
            <div class="h-6 w-6 rounded border" style={`background-color: ${hex}`}></div>
            <input
                type="text"
                value={hex}
                aria-label="Hex color"
                class="bg-background flex-1 rounded border px-2 py-1 text-xs uppercase"
                oninput={handleHexInput}
            />
        </div>

        <div class="space-y-1">
            <div class="flex items-center justify-between text-xs">
                <span>Opacity</span>
                <span>{Math.round(alpha * 100)}%</span>
            </div>
            <Slider
                type="multiple"
                min={0}
                max={1}
                step={0.01}
                value={[alpha]}
                onValueChange={(values) => onAlphaChange(values[0])}
            />
        </div>

        <PresetSwatches selectedColor={hex} onSelect={onHexChange} />
    </div>

    <ColorPickerActions {onReset} {isDefaultColor} {onCancel} {onApply} />
</div>
