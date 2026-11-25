<script lang="ts">
    import { Slider } from '$lib/components/ui/slider';

    // A lower threshold can return hundreds of previews, e.g. every query of a DETR model.
    const MIN_THRESHOLD = 0.05;
    const THRESHOLD_STEP = 0.05;
    // Removes float noise of the slider, e.g. 0.15000000000000002.
    const THRESHOLD_DECIMALS = 2;

    interface Props {
        value: number;
        onChange: (value: number) => void;
    }

    let { value, onChange }: Props = $props();
</script>

<div class="grid gap-1.5 py-0.5">
    <div class="flex items-center justify-between text-xs text-muted-foreground">
        <span>Confidence</span>
        <span class="tabular-nums text-foreground">{value.toFixed(THRESHOLD_DECIMALS)}</span>
    </div>
    <div class="slider-small">
        <Slider
            type="single"
            {value}
            min={MIN_THRESHOLD}
            max={1}
            step={THRESHOLD_STEP}
            thumbLabel="Minimum confidence"
            onValueChange={(next) => onChange(Number(next.toFixed(THRESHOLD_DECIMALS)))}
        />
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
