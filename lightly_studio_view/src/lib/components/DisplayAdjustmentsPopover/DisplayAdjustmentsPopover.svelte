<script lang="ts">
    import { Sun, RotateCcw } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import { Popover, PopoverContent, PopoverTrigger } from '$lib/components/ui/popover';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { IMAGE_ADJUSTMENT_DEFAULTS } from '$lib/constants';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import AdjustmentSlider from '../ImageAdjustments/AdjustmentSlider/AdjustmentSlider.svelte';

    const { imageBrightness, imageContrast, maskOpacity } = useGlobalStorage();

    const isDefault = $derived(
        $imageBrightness === IMAGE_ADJUSTMENT_DEFAULTS.brightness &&
            $imageContrast === IMAGE_ADJUSTMENT_DEFAULTS.contrast &&
            $maskOpacity === IMAGE_ADJUSTMENT_DEFAULTS.maskOpacity
    );

    const reset = () => {
        $imageBrightness = IMAGE_ADJUSTMENT_DEFAULTS.brightness;
        $imageContrast = IMAGE_ADJUSTMENT_DEFAULTS.contrast;
        $maskOpacity = IMAGE_ADJUSTMENT_DEFAULTS.maskOpacity;
    };
</script>

<Popover>
    <Tooltip content="Display adjustments" position="top" noTriggerRole>
        <PopoverTrigger asChild>
            {#snippet child({ props })}
                <button
                    {...props}
                    class="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-muted/80 shadow-md backdrop-blur-sm"
                    data-testid="display-adjustments-trigger"
                >
                    <Sun class="size-4 text-muted-foreground" />
                </button>
            {/snippet}
        </PopoverTrigger>
    </Tooltip>
    <PopoverContent side="top" sideOffset={8} class="w-72">
        <div class="flex items-center justify-between">
            <span class="text-sm font-medium">Display adjustments</span>
            <Button
                variant="ghost"
                size="icon"
                class="h-7 w-7"
                aria-label="Reset display adjustments"
                title="Reset to defaults"
                disabled={isDefault}
                onclick={reset}
            >
                <RotateCcw class="size-4" />
            </Button>
        </div>
        <div class="sliders-column mt-3 flex flex-col gap-3">
            <AdjustmentSlider label="Brightness" min={0.2} max={2} bind:value={$imageBrightness} />
            <AdjustmentSlider label="Contrast" min={0.2} max={2} bind:value={$imageContrast} />
            <AdjustmentSlider label="Mask opacity" min={0.1} max={1} bind:value={$maskOpacity} />
        </div>
    </PopoverContent>
</Popover>

<style>
    .sliders-column :global(> div) {
        flex-direction: column;
        align-items: flex-start;
    }

    .sliders-column :global(> div > div) {
        width: 100%;
    }
</style>
