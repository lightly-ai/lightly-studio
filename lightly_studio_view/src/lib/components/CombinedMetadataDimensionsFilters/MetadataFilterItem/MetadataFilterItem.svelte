<script lang="ts">
    import { Slider } from '$lib/components/ui/slider/index.js';
    import type { MetadataBounds, MetadataValues } from '$lib/services/types';
    import { NumericRangeInputs } from '$lib/components/NumericRangeInputs';
    import { fromTick, getSliderTickCount, toTick } from './MetadataFilterItem.helpers';

    type MetadataBound = MetadataBounds[string];
    type MetadataValue = MetadataValues[string];

    interface MetadataFilterItemProps {
        metadataKey: string;
        displayName?: string;
        unit?: string;
        bound: MetadataBound;
        value: MetadataValue;
        isInteger: boolean;
        onValueCommit: (metadataKey: string, newValues: number[]) => void;
    }

    const {
        metadataKey,
        displayName,
        unit,
        bound,
        value,
        isInteger,
        onValueCommit
    }: MetadataFilterItemProps = $props();

    const label = $derived(displayName ?? metadataKey.replace(/_/g, ' '));
    const ticks = $derived(getSliderTickCount(bound, isInteger));

    const sliderValue = $derived([
        toTick(value.min, bound, ticks),
        toTick(value.max, bound, ticks)
    ]);

    const handleValueCommit = (newTicks: number[]) => {
        onValueCommit(metadataKey, [
            newTicks[0] !== sliderValue[0]
                ? fromTick(newTicks[0], bound, ticks, isInteger)
                : value.min,
            newTicks[1] !== sliderValue[1]
                ? fromTick(newTicks[1], bound, ticks, isInteger)
                : value.max
        ]);
    };
</script>

<div class="space-y-1">
    <h2 class="text-md capitalize">{label}</h2>
    <NumericRangeInputs
        {label}
        {bound}
        {value}
        {unit}
        integer={isInteger}
        onValueCommit={(values) => onValueCommit(metadataKey, values)}
    />
    <div class="relative p-2">
        <Slider
            type="multiple"
            class="filter-{metadataKey}"
            min={0}
            max={ticks}
            step={1}
            value={sliderValue}
            onValueCommit={handleValueCommit}
        />
    </div>
</div>
