<script lang="ts">
    import { ChevronDown } from '@lucide/svelte';
    import { page } from '$app/state';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { Button } from '$lib/components/ui/button';
    import * as Popover from '$lib/components/ui/popover';
    import { Slider } from '$lib/components/ui/slider/index.js';
    import { MetadataCategoricalFilter } from '$lib/components/MetadataCategoricalFilter';
    import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';
    import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import type { CategoricalMetadataBucket } from '$lib/hooks/useCategoricalMetadataDistribution';
    import type { CategoricalMetadataValue, MetadataValues } from '$lib/services/types';
    import { formatInteger } from '$lib/utils';
    import VideoFrameBoundsFilter from '../VideoFrameBoundsFilter/VideoFrameBoundsFilter.svelte';
    import VideoFieldBoundsFilters from '../VideoFieldBoundsFilters/VideoFieldBoundsFilters.svelte';
    import MetadataFilterItem from './MetadataFilterItem/MetadataFilterItem.svelte';

    const collectionId = page.params.collection_id;

    interface Props {
        /** Whether the collection contains videos; shows video field filters instead of dimension filters. */
        isVideos?: boolean;
        /** Whether the collection contains video frames; shows frame number filter. */
        isVideoFrames?: boolean;
        /** Called when any filter range changes, with the field name and new min/max values. */
        onFilterChanged?: (fieldName: string, min: number, max: number) => void;
        isImageCollection?: boolean;
        categoricalKeys?: string[];
        categoricalDistributions?: Record<string, CategoricalMetadataBucket[]>;
        categoricalLoading?: boolean;
        categoricalUpdating?: boolean;
        categoricalError?: string;
        onCategoricalRetry?: () => void;
        onCategoricalValueToggle?: (field: string, value: CategoricalMetadataValue) => void;
        onCategoricalValuesClear?: (field: string) => void;
    }

    const {
        isVideos = false,
        isVideoFrames = false,
        onFilterChanged,
        isImageCollection = false,
        categoricalKeys = [],
        categoricalDistributions = {},
        categoricalLoading = false,
        categoricalUpdating = false,
        categoricalError,
        onCategoricalRetry,
        onCategoricalValueToggle,
        onCategoricalValuesClear
    }: Props = $props();

    // Dimension filters logic
    const {
        dimensionsBounds: bounds,
        dimensionsValues: values,
        updateDimensionsValues: onChange
    } = useDimensions();

    const handleChangeWidth = (newValues: number[]) => {
        if (!$values) return;
        onChange({
            min_width: newValues[0],
            max_width: newValues[1],
            min_height: $values.min_height,
            max_height: $values.max_height
        });
        onFilterChanged?.('width', newValues[0], newValues[1]);
    };

    const handleChangeHeight = (newValues: number[]) => {
        if (!$values) return;
        onChange({
            min_width: $values.min_width,
            max_width: $values.max_width,
            min_height: newValues[0],
            max_height: newValues[1]
        });
        onFilterChanged?.('height', newValues[0], newValues[1]);
    };

    // Metadata filters logic
    const {
        metadataBounds,
        metadataValues,
        updateMetadataValues,
        categoricalMetadataValues,
        updateCategoricalMetadataValues
    } = useMetadataFilters(collectionId);

    let addedCategoricalFields = $state<string[]>([]);
    let fieldPickerOpen = $state(false);

    const activeCategoricalFields = $derived(
        isImageCollection
            ? categoricalKeys.filter((key) => $categoricalMetadataValues[key]?.length)
            : []
    );
    const numericalMetadata = $derived.by(() =>
        Object.keys($metadataBounds).filter((key) => {
            const bound = $metadataBounds[key];
            const value = $metadataValues[key];
            return bound && value;
        })
    );
    const visibleCategoricalFields = $derived([
        ...new Set([...addedCategoricalFields, ...activeCategoricalFields])
    ]);
    const availableCategoricalFields = $derived(
        categoricalKeys
            .filter((key) => !visibleCategoricalFields.includes(key))
            .sort((a, b) => a.localeCompare(b))
    );

    const addCategoricalField = (metadataKey: string): void => {
        addedCategoricalFields = [...addedCategoricalFields, metadataKey];
        fieldPickerOpen = false;
    };

    const removeCategoricalField = (metadataKey: string): void => {
        if ($categoricalMetadataValues[metadataKey]?.length) {
            const nextValues = { ...$categoricalMetadataValues };
            delete nextValues[metadataKey];
            updateCategoricalMetadataValues(nextValues);
        }
        addedCategoricalFields = addedCategoricalFields.filter((key) => key !== metadataKey);
    };

    const handleMetadataValueCommit = (metadataKey: string, newValues: number[]): void => {
        const currentValues: MetadataValues = { ...$metadataValues };
        currentValues[metadataKey] = { min: newValues[0], max: newValues[1] };
        updateMetadataValues(currentValues);
        onFilterChanged?.(metadataKey, newValues[0], newValues[1]);
    };
</script>

<Segment title="Metadata">
    <div class="space-y-4">
        {#if !isVideos && !isVideoFrames && $bounds && $values}
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
            <VideoFieldBoundsFilters {onFilterChanged} />
        {/if}

        {#if isVideoFrames}
            <VideoFrameBoundsFilter {onFilterChanged} />
        {/if}

        {#if numericalMetadata.length > 0}
            {#each numericalMetadata as metadataKey (metadataKey)}
                <MetadataFilterItem
                    {metadataKey}
                    bound={$metadataBounds[metadataKey]}
                    value={$metadataValues[metadataKey]}
                    onValueCommit={handleMetadataValueCommit}
                />
            {/each}
        {/if}

        {#if isImageCollection && categoricalKeys.length > 0}
            <Popover.Root bind:open={fieldPickerOpen}>
                <Popover.Trigger>
                    {#snippet child({ props })}
                        <Button
                            {...props}
                            variant="outline"
                            size="sm"
                            class="h-8 w-full justify-between px-3 text-xs font-normal"
                            disabled={availableCategoricalFields.length === 0}
                        >
                            Add categorical metadata field
                            <ChevronDown class="size-4 opacity-50" />
                        </Button>
                    {/snippet}
                </Popover.Trigger>
                <Popover.Content class="max-h-64 w-64 overflow-y-auto p-1" align="start">
                    {#each availableCategoricalFields as metadataKey (metadataKey)}
                        <Button
                            variant="ghost"
                            size="sm"
                            class="w-full justify-start text-xs"
                            onclick={() => addCategoricalField(metadataKey)}
                        >
                            {metadataKey}
                        </Button>
                    {/each}
                </Popover.Content>
            </Popover.Root>

            {#each visibleCategoricalFields as metadataKey (metadataKey)}
                <MetadataCategoricalFilter
                    layout="list"
                    fieldLabel={metadataKey}
                    buckets={categoricalDistributions[metadataKey] ?? []}
                    selectedValues={$categoricalMetadataValues[metadataKey] ?? []}
                    loading={categoricalLoading}
                    updating={categoricalUpdating}
                    error={categoricalError}
                    onRetry={onCategoricalRetry}
                    onToggle={(value) => onCategoricalValueToggle?.(metadataKey, value)}
                    onClear={() => onCategoricalValuesClear?.(metadataKey)}
                    onRemove={() => removeCategoricalField(metadataKey)}
                />
            {/each}
        {/if}
    </div>
</Segment>
