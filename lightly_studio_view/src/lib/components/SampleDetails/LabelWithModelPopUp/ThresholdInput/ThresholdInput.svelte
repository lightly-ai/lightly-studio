<script lang="ts">
    import { Slider } from '$lib/components/ui/slider';

    interface Props {
        value: number;
        onChange: (value: number) => void;
    }

    let { value, onChange }: Props = $props();
</script>

<div class="grid gap-1.5 py-0.5">
    <div class="flex items-center justify-between text-xs text-muted-foreground">
        <span>Confidence</span>
        <span class="tabular-nums text-foreground">{value.toFixed(2)}</span>
    </div>
    <div class="slider-small">
        <Slider
            type="single"
            {value}
            min={0}
            max={1}
            step={0.05}
            thumbLabel="Minimum confidence"
            onValueChange={(next) => onChange(Math.round(next * 100) / 100)}
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
