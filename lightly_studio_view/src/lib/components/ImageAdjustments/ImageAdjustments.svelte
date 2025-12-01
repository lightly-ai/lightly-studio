<script lang="ts">
    import { Slider } from '$lib/components/ui/slider';

    let {
        brightness = $bindable(1),
        contrast = $bindable(1)
    }: {
        brightness: number;
        contrast: number;
    } = $props();

    let brightnessValue = $state([brightness]);
    let contrastValue = $state([contrast]);

    $effect(() => {
        brightness = brightnessValue[0];
    });

    $effect(() => {
        contrast = contrastValue[0];
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
