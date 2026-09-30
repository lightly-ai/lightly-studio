<script lang="ts">
    import { Slider } from '$lib/components/ui/slider/index.js';
    import {
        FLOAT_SLIDER_TICKS,
        fromTick,
        toTick
    } from '$lib/components/CombinedMetadataDimensionsFilters/MetadataFilterItem/MetadataFilterItem.helpers';
    import { formatFloat } from '$lib/utils';

    interface Props {
        range: { min: number; max: number };
        value: number | null;
        onCommit: (value: number) => void;
        onClear: () => void;
    }

    const { range, value, onCommit, onClear }: Props = $props();

    const sliderValue = $derived(value === null ? 0 : toTick(value, range, FLOAT_SLIDER_TICKS));

    // The slider at the range minimum means no threshold.
    const handleValueCommit = (tick: number) => {
        if (tick === 0) {
            if (value !== null) onClear();
            return;
        }
        if (tick !== sliderValue) {
            onCommit(fromTick(tick, range, FLOAT_SLIDER_TICKS, false));
        }
    };
</script>

<div class="space-y-1" data-testid="similarity-threshold-filter">
    <div class="flex justify-between text-sm text-diffuse-foreground">
        <span>{formatFloat(value ?? range.min)}</span>
        <span>{formatFloat(range.max)}</span>
    </div>
    <div class="relative p-2">
        <Slider
            type="single"
            min={0}
            max={FLOAT_SLIDER_TICKS}
            step={1}
            value={sliderValue}
            onValueCommit={handleValueCommit}
            aria-label="Similarity search threshold"
        />
    </div>
</div>
