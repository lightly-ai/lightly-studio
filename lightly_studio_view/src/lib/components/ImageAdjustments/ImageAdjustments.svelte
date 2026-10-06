<script lang="ts">
    import { RotateCcw } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import { Slider } from '$lib/components/ui/slider';
    import { IMAGE_ADJUSTMENT_DEFAULTS } from '$lib/hooks/useGlobalStorage';

    let {
        brightness = $bindable(IMAGE_ADJUSTMENT_DEFAULTS.brightness),
        contrast = $bindable(IMAGE_ADJUSTMENT_DEFAULTS.contrast),
        maskOpacity = $bindable(IMAGE_ADJUSTMENT_DEFAULTS.maskOpacity)
    }: {
        brightness: number;
        contrast: number;
        maskOpacity: number;
    } = $props();

    let brightnessValue = $state([brightness]);
    let contrastValue = $state([contrast]);
    let maskOpacityValue = $state([maskOpacity]);

    $effect(() => {
        brightness = brightnessValue[0];
    });

    $effect(() => {
        contrast = contrastValue[0];
    });

    $effect(() => {
        maskOpacity = maskOpacityValue[0];
    });

    $effect(() => {
        if (brightness !== brightnessValue[0]) {
            brightnessValue = [brightness];
        }
    });

    $effect(() => {
        if (contrast !== contrastValue[0]) {
            contrastValue = [contrast];
        }
    });

    $effect(() => {
        if (maskOpacity !== maskOpacityValue[0]) {
            maskOpacityValue = [maskOpacity];
        }
    });

    const isDefault = $derived(
        brightness === IMAGE_ADJUSTMENT_DEFAULTS.brightness &&
            contrast === IMAGE_ADJUSTMENT_DEFAULTS.contrast &&
            maskOpacity === IMAGE_ADJUSTMENT_DEFAULTS.maskOpacity
    );

    const reset = () => {
        brightness = IMAGE_ADJUSTMENT_DEFAULTS.brightness;
        contrast = IMAGE_ADJUSTMENT_DEFAULTS.contrast;
        maskOpacity = IMAGE_ADJUSTMENT_DEFAULTS.maskOpacity;
    };
</script>

<div class="flex items-center gap-6">
    <div class="flex items-center gap-2">
        <span class="text-sm text-muted-foreground">Brightness</span>
        <div class="slider-small w-28">
            <Slider type="multiple" min={0.2} max={2} step={0.05} bind:value={brightnessValue} />
        </div>
    </div>
    <div class="flex items-center gap-2">
        <span class="text-sm text-muted-foreground">Contrast</span>
        <div class="slider-small w-28">
            <Slider type="multiple" min={0.2} max={2} step={0.05} bind:value={contrastValue} />
        </div>
    </div>
    <div class="flex items-center gap-2">
        <span class="text-sm text-muted-foreground">Mask opacity</span>
        <div class="slider-small w-28">
            <Slider type="multiple" min={0} max={1} step={0.05} bind:value={maskOpacityValue} />
        </div>
    </div>
    <Button
        variant="ghost"
        size="icon"
        class="h-7 w-7"
        aria-label="Reset image adjustments"
        title="Reset to defaults"
        disabled={isDefault}
        onclick={reset}
    >
        <RotateCcw class="size-4" />
    </Button>
</div>

<style>
    .slider-small :global([data-slider-thumb]) {
        width: 14px !important;
        height: 14px !important;
    }

    .slider-small :global(span[data-orientation]) {
        height: 6px !important;
    }
</style>
