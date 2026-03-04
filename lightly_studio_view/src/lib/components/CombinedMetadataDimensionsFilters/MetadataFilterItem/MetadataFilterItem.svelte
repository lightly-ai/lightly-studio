<script lang="ts">
    import { Slider } from '$lib/components/ui/slider/index.js';
    import type { MetadataBounds, MetadataValues } from '$lib/services/types';
    import { formatFloat, formatInteger } from '$lib/utils';
    import type { SliderMultipleRootProps } from 'bits-ui/dist/types';
    import {
        clampMetadataValuesToMax,
        getMetadataSliderMax,
        getMetadataSliderStep,
        getSliderDisplayMaxValue
    } from './MetadataFilterItem.helpers';

    type MetadataBound = MetadataBounds[string];
    type MetadataValue = MetadataValues[string];

    interface MetadataFilterItemProps {
        metadataKey: string;
        bound: MetadataBound;
        value: MetadataValue;
        onValueCommit: (metadataKey: string, newValues: number[]) => void;
    }

    const { metadataKey, bound, value, onValueCommit }: MetadataFilterItemProps = $props();

    const isInteger = $derived(Number.isInteger(bound.min) && Number.isInteger(bound.max));
    const sliderStep = $derived(getMetadataSliderStep(bound.min, bound.max, isInteger));
    const sliderMax = $derived(getMetadataSliderMax(bound.min, bound.max, sliderStep));
    const sliderValueMax = $derived(getSliderDisplayMaxValue(value.max, bound.max, sliderMax));

    const handleValueCommit: SliderMultipleRootProps['onValueChange'] = (newValues) => {
        onValueCommit(metadataKey, clampMetadataValuesToMax(newValues, bound.max));
    };

    const formatValue = (sliderValue: number): string => {
        return isInteger ? formatInteger(sliderValue) : formatFloat(sliderValue);
    };
</script>

<div class="space-y-1">
    <h2 class="text-md capitalize">{metadataKey.replace(/_/g, ' ')}</h2>
    <div class="flex justify-between text-sm text-diffuse-foreground">
        <span>{formatValue(value.min)}</span>
        <span>{formatValue(value.max)}</span>
    </div>
    <div class="relative p-2">
        <Slider
            type="multiple"
            class="filter-{metadataKey}"
            min={bound.min}
            max={sliderMax}
            step={sliderStep}
            value={[value.min, sliderValueMax]}
            onValueCommit={handleValueCommit}
        />
    </div>
</div>
