<script lang="ts">
    import { Slider } from '$lib/components/ui/slider';

    interface Props {
        label: string;
        min: number;
        max: number;
        step?: number;
        value: number;
    }

    let { label, min, max, step = 0.05, value = $bindable() }: Props = $props();
</script>

<div class="flex items-center gap-2">
    <span class="text-sm text-muted-foreground">{label}</span>
    <div class="slider-small w-28">
        <Slider type="single" bind:value {min} {max} {step} thumbLabel={label} />
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
