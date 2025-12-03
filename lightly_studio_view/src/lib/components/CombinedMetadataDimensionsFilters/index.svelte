<script lang="ts">
    import { formatInteger, formatFloat } from '$lib/utils';
    import { Slider } from '$lib/components/ui/slider/index.js';
    import type { SliderMultipleRootProps } from 'bits-ui/dist/types';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';
    import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import { page } from '$app/state';
    import VideoFrameBoundsFilter from '../VideoFrameBoundsFilter/VideoFrameBoundsFilter.svelte';
    import VideoFieldBoundsFilters from '../VideoFieldBoundsFilters/VideoFieldBoundsFilters.svelte';

    const datasetId = page.params.dataset_id;

    const {
        isVideos = false,
        isVideoFrames = false
    }: {
        isVideos: boolean;
        isVideoFrames: boolean,
    } = $props();

    // Dimension filters logic
    const {
        dimensionsBounds: bounds,
        dimensionsValues: values,
        updateDimensionsValues: onChange
    } = useDimensions();

    const handleChangeWidth: SliderMultipleRootProps['onValueChange'] = (newValues) => {
        onChange({
            min_width: newValues[0],
            max_width: newValues[1],
            min_height: $values.min_height,
            max_height: $values.max_height
        });
    };

    const handleChangeHeight: SliderMultipleRootProps['onValueChange'] = (newValues) => {
        onChange({
            min_width: $values.min_width,
            max_width: $values.max_width,
            min_height: newValues[0],
            max_height: newValues[1]
        });
    };

    // Metadata filters logic
    const {
        metadataBounds: metadataBounds,
        metadataValues: metadataValues,
        updateMetadataValues: updateMetadataValues
    } = useMetadataFilters(datasetId);

    const handleChangeMetadata =
        (metadataKey: string) =>
        (newValues: number[]): void => {
            const currentValues = { ...$metadataValues };
            currentValues[metadataKey] = {
                min: newValues[0],
                max: newValues[1]
            };
            updateMetadataValues(currentValues);
        };

    // Get numerical metadata fields
    const numericalMetadata = $derived.by(() => {
        return Object.keys($metadataBounds).filter((key) => {
            const bound = $metadataBounds[key];
            return bound && typeof bound.min === 'number' && typeof bound.max === 'number';
        });
    });

    // Format value based on metadata type
    const formatValue = (value: number, metadataKey: string) => {
        // Try to determine if it's an integer by checking if the bounds are integers
        const bound = $metadataBounds[metadataKey];
        if (bound && Number.isInteger(bound.min) && Number.isInteger(bound.max)) {
            return formatInteger(value);
        }
        return formatFloat(value);
    };
</script>

<Segment title="Metadata FIlters">
    <div class="space-y-4">
        {#if !isVideos && !isVideoFrames}
            <!-- Dimension Filters -->
            <div class="space-y-1">
                <h2 class="text-md">Width</h2>
                <div class="flex justify-between text-sm text-diffuse-foreground">
                    <span>{formatInteger($values.min_width)}px</span>
                    <span>{formatInteger($values.max_width)}px</span>
                </div>
                <div class="relative p-2">
                    <Slider
                        type="multiple"
                        class="filter-width"
                        min={$bounds.min_width}
                        max={$bounds.max_width}
                        value={[$values.min_width, $values.max_width]}
                        onValueCommit={handleChangeWidth}
                    />
                </div>
            </div>

            <div class="space-y-1">
                <h2 class="text-md">Height</h2>
                <div class="flex justify-between text-sm text-diffuse-foreground">
                    <span>{formatInteger($values.min_height)}px</span>
                    <span>{formatInteger($values.max_height)}px</span>
                </div>
                <div class="relative p-2">
                    <Slider
                        type="multiple"
                        class="filter-height"
                        min={$bounds.min_height}
                        max={$bounds.max_height}
                        value={[$values.min_height, $values.max_height]}
                        onValueCommit={handleChangeHeight}
                    />
                </div>
            </div>
        {:else}
            <VideoFieldBoundsFilters />
        {/if}

        {#if isVideoFrames}
            <VideoFrameBoundsFilter />
        {/if}

        <!-- Metadata Filters -->
        {#if numericalMetadata.length > 0}
            {#each numericalMetadata as metadataKey}
                {@const bound = $metadataBounds[metadataKey]}
                {@const value = $metadataValues[metadataKey]}
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
        {/if}
    </div>
</Segment>
