<script lang="ts">
    import { Slider } from '$lib/components/ui/slider/index.js';
    import MetadataFieldHeader from '$lib/components/MetadataFieldHeader/MetadataFieldHeader.svelte';
    import type { MetadataBounds, MetadataValues } from '$lib/services/types';
    import { formatFloat, formatInteger } from '$lib/utils';
    import { fromTick, getSliderTickCount, toTick } from './MetadataFilterItem.helpers';

    type MetadataBound = MetadataBounds[string];
    type MetadataValue = MetadataValues[string];

    interface MetadataFilterItemProps {
        metadataKey: string;
        bound: MetadataBound;
        value: MetadataValue;
        onValueCommit: (metadataKey: string, newValues: number[]) => void;
        /** Shown instead of the metadata key, e.g. "Width". */
        title?: string;
        /** Appended to the shown values, e.g. "px". */
        unit?: string;
        /** Whether the slider shows. */
        expanded?: boolean;
        /** Lets the user show or hide the slider from the field header. */
        onToggleExpanded?: () => void;
    }

    const {
        metadataKey,
        bound,
        value,
        onValueCommit,
        title,
        unit = '',
        expanded = true,
        onToggleExpanded
    }: MetadataFilterItemProps = $props();

    const isInteger = $derived(Number.isInteger(bound.min) && Number.isInteger(bound.max));
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

    const formatValue = (sliderValue: number): string => {
        return isInteger ? formatInteger(sliderValue) : formatFloat(sliderValue);
    };
</script>

<div class="space-y-1">
    <MetadataFieldHeader title={title ?? metadataKey} {expanded} {onToggleExpanded} />
    {#if expanded}
        <div class="pl-6">
            <div class="flex justify-between text-sm text-diffuse-foreground">
                <span>{formatValue(value.min)}{unit}</span>
                <span>{formatValue(value.max)}{unit}</span>
            </div>
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
