<script lang="ts">
    import { RotateCcw } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import { IMAGE_ADJUSTMENT_DEFAULTS } from '$lib/hooks';
    import AdjustmentSlider from './AdjustmentSlider/AdjustmentSlider.svelte';

    let {
        brightness = $bindable(IMAGE_ADJUSTMENT_DEFAULTS.brightness),
        contrast = $bindable(IMAGE_ADJUSTMENT_DEFAULTS.contrast),
        maskOpacity = $bindable(IMAGE_ADJUSTMENT_DEFAULTS.maskOpacity)
    }: {
        brightness: number;
        contrast: number;
        maskOpacity: number;
    } = $props();

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
    <AdjustmentSlider label="Brightness" min={0.2} max={2} bind:value={brightness} />
    <AdjustmentSlider label="Contrast" min={0.2} max={2} bind:value={contrast} />
    <AdjustmentSlider label="Mask opacity" min={0} max={1} bind:value={maskOpacity} />
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
