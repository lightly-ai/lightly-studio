<script lang="ts">
    import RangeFilterField from '$lib/components/RangeFilterField/RangeFilterField.svelte';
    import type { MetadataBounds, MetadataValues } from '$lib/services/types';
    import { formatFloat, formatInteger } from '$lib/utils';
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

    const handleValueCommit = (newValues: number[]) => {
        onValueCommit(metadataKey, clampMetadataValuesToMax(newValues, bound.max));
    };

    const formatValue = (sliderValue: number): string => {
        return isInteger ? formatInteger(sliderValue) : formatFloat(sliderValue);
    };
</script>

<RangeFilterField
    label={metadataKey.replace(/_/g, ' ')}
    minText={formatValue(value.min)}
    maxText={formatValue(value.max)}
    min={bound.min}
    max={sliderMax}
    step={sliderStep}
    value={[value.min, sliderValueMax]}
    onValueCommit={handleValueCommit}
    sliderClass={`filter-${metadataKey}`}
/>
