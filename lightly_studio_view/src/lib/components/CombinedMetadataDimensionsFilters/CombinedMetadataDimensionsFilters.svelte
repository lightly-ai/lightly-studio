<script lang="ts">
    import { page } from '$app/state';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { Slider } from '$lib/components/ui/slider/index.js';
    import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';
    import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import type { MetadataValues } from '$lib/services/types';
    import { formatInteger } from '$lib/utils';
    import type { SliderMultipleRootProps } from 'bits-ui/dist/types';
    import MetadataFilterItem from './MetadataFilterItem/MetadataFilterItem.svelte';
    import VideoFrameBoundsFilter from '../VideoFrameBoundsFilter/VideoFrameBoundsFilter.svelte';
    import VideoFieldBoundsFilters from '../VideoFieldBoundsFilters/VideoFieldBoundsFilters.svelte';

    const collectionId = page.params.collection_id;

    const {
        isVideos = false,
        isVideoFrames = false
    }: {
        isVideos: boolean;
        isVideoFrames: boolean;
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
    } = useMetadataFilters(collectionId);

    const handleMetadataValueCommit = (metadataKey: string, newValues: number[]): void => {
        const currentValues: MetadataValues = { ...$metadataValues };
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
            const value = $metadataValues[key];
            return (
                bound &&
                value &&
                typeof bound.min === 'number' &&
                typeof bound.max === 'number' &&
                typeof value.min === 'number' &&
                typeof value.max === 'number'
            );
        });
    });
</script>

<Segment title="Metadata Filters">
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
        {:else if isVideos}
            <VideoFieldBoundsFilters />
        {/if}

        {#if isVideoFrames}
            <VideoFrameBoundsFilter />
        {/if}

        <!-- Metadata Filters -->
        {#if numericalMetadata.length > 0}
            {#each numericalMetadata as metadataKey}
                <MetadataFilterItem
                    {metadataKey}
                    bound={$metadataBounds[metadataKey]}
                    value={$metadataValues[metadataKey]}
                    onValueCommit={handleMetadataValueCommit}
                />
            {/each}
        {/if}
    </div>
</Segment>
