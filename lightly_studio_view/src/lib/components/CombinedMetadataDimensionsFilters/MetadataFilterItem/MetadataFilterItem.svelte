<script lang="ts">
    import { Slider } from '$lib/components/ui/slider/index.js';
    import MetadataFieldHeader from '$lib/components/MetadataFieldHeader/MetadataFieldHeader.svelte';
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
        /** Whether the slider shows. */
        expanded?: boolean;
        /** Lets the user show or hide the slider from the field header. */
        onToggleExpanded?: () => void;
    }

    const {
        metadataKey,
        displayName,
        unit,
        bound,
        value,
        isInteger,
        onValueCommit,
        expanded = true,
        onToggleExpanded
    }: MetadataFilterItemProps = $props();

    const label = $derived(displayName ?? metadataKey);
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
    <MetadataFieldHeader title={label} {expanded} {onToggleExpanded} />
    {#if expanded}
        <!-- Indented under the chevron. -->
        <div class={onToggleExpanded ? 'pl-6' : undefined}>
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
    {/if}
</div>
