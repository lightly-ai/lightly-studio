<script lang="ts">
    import { formatFloat, formatInteger } from '$lib/utils';
    import { Slider } from '$lib/components/ui/slider/index.js';
    import type { SliderMultipleRootProps } from 'bits-ui/dist/types';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import { page } from '$app/stores';

    const datasetId = $page.params.dataset_id;

    const {
        metadataBounds: bounds,
        metadataValues: values,
        updateMetadataValues: onChange
    } = useMetadataFilters(datasetId);

    const handleChangeMetadata =
        (metadataKey: string): SliderMultipleRootProps['onValueCommit'] =>
        (newValues) => {
            const currentValues = { ...$values };
            currentValues[metadataKey] = {
                min: newValues[0],
                max: newValues[1]
            };
            onChange(currentValues);
        };

    // Get numerical metadata fields
    const numericalMetadata = $derived.by(() => {
        return Object.keys($bounds).filter((key) => {
            const bound = $bounds[key];
            return bound && typeof bound.min === 'number' && typeof bound.max === 'number';
        });
    });

    // Format value based on metadata type
    const formatValue = (value: number, metadataKey: string) => {
        // Try to determine if it's an integer by checking if the bounds are integers
        const bound = $bounds[metadataKey];
        if (bound && Number.isInteger(bound.min) && Number.isInteger(bound.max)) {
            return formatInteger(value);
        }
        return formatFloat(value);
    };
</script>

{#if numericalMetadata.length > 0}
    <Segment title="Metadata Filters">
        <div class="space-y-4">
            {#each numericalMetadata as metadataKey}
                {@const bound = $bounds[metadataKey]}
                {@const value = $values[metadataKey]}
                {@const isInteger = Number.isInteger(bound.min) && Number.isInteger(bound.max)}

                <div class="space-y-1">
                    <h2 class="text-md capitalize">{metadataKey.replace(/_/g, ' ')}</h2>
                    <div class="flex justify-between text-sm text-diffuse-foreground">
                        <span>{formatValue(value.min, metadataKey)}</span>
                        <span>{formatValue(value.max, metadataKey)}</span>
                    </div>
                    <div class="relative p-2">
                        <Slider
                            type="multiple"
                            class="filter-{metadataKey}"
                            min={bound.min}
                            max={bound.max}
                            step={isInteger ? 1 : 0.01}
                            value={[value.min, value.max]}
                            onValueCommit={handleChangeMetadata(metadataKey)}
                        />
                    </div>
                </div>
            {/each}
        </div>
    </Segment>
{/if}
