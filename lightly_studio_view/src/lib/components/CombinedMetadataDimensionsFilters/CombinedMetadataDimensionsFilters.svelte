<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import MetadataFilterChips from '$lib/components/MetadataFilterChips/MetadataFilterChips.svelte';
    import CategoricalMetadataFilters from '$lib/components/CategoricalMetadataFilters/CategoricalMetadataFilters.svelte';
    import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';
    import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import type { ImageFilter } from '$lib/api/lightly_studio_local';
    import type { CategoricalMetadataValue, MetadataValues } from '$lib/services/types';
    import VideoFrameBoundsFilter from '../VideoFrameBoundsFilter/VideoFrameBoundsFilter.svelte';
    import VideoFieldBoundsFilters from '../VideoFieldBoundsFilters/VideoFieldBoundsFilters.svelte';
    import { Input } from '$lib/components/ui/input';
    import MetadataFilterItem from './MetadataFilterItem/MetadataFilterItem.svelte';
    import { MANY_FIELDS, isFieldExpanded, matchesFieldSearch } from './metadataFieldList';

    interface Props {
        /** Collection whose metadata fields are listed. */
        collectionId: string;
        /** Whether to show the width and height sliders. Views whose samples cannot be filtered by size hide them. */
        showDimensions?: boolean;
        /** Whether the collection contains videos; shows video field filters instead of dimension filters. */
        isVideos?: boolean;
        /** Whether the collection contains video frames; shows frame number filter. */
        isVideoFrames?: boolean;
        /** Called when any filter range changes, with the field name and new min/max values. */
        onFilterChanged?: (fieldName: string, min: number, max: number) => void;
        isImageCollection?: boolean;
        categoricalFilter?: ImageFilter;
        categoricalKeys?: string[];
        onCategoricalValueToggle: (field: string, value: CategoricalMetadataValue) => void;
        onCategoricalValuesClear: (field: string) => void;
    }

    const {
        collectionId,
        showDimensions = true,
        isVideos = false,
        isVideoFrames = false,
        onFilterChanged,
        isImageCollection = false,
        categoricalFilter,
        categoricalKeys = [],
        onCategoricalValueToggle,
        onCategoricalValuesClear
    }: Props = $props();

    // Dimension filters logic
    const {
        dimensionsBounds: bounds,
        dimensionsValues: values,
        updateDimensionsValues: onChange
    } = useDimensions();

    // Width and height use the same slider field as numeric metadata.
    const handleDimensionCommit = (dimension: string, [min, max]: number[]) => {
        if (!$values) return;
        onChange(
            dimension === 'width'
                ? { ...$values, min_width: min, max_width: max }
                : { ...$values, min_height: min, max_height: max }
        );
        onFilterChanged?.(dimension, min, max);
    };

    // Metadata filters logic
    const { metadataBounds, metadataValues, updateMetadataValues } = $derived.by(() =>
        useMetadataFilters(collectionId)
    );

    const numericalMetadata = $derived.by(() =>
        Object.keys($metadataBounds).filter((key) => {
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
        })
    );
    const handleMetadataValueCommit = (metadataKey: string, newValues: number[]): void => {
        const currentValues: MetadataValues = { ...$metadataValues };
        currentValues[metadataKey] = { min: newValues[0], max: newValues[1] };
        updateMetadataValues(currentValues);
        onFilterChanged?.(metadataKey, newValues[0], newValues[1]);
    };

    // Every field is listed, with one rule for showing, collapsing and searching them.
    const showImageDimensions = $derived(
        showDimensions && !isVideos && !isVideoFrames && !!$bounds && !!$values
    );
    const categoricalFields = $derived(isImageCollection ? categoricalKeys : []);
    const fieldCount = $derived(
        (showImageDimensions ? 2 : 0) + numericalMetadata.length + categoricalFields.length
    );
    let fieldSearch = $state('');
    let expandedOverrides = $state<Record<string, boolean>>({});
    const isExpanded = (field: string) => isFieldExpanded(expandedOverrides, field, fieldCount);
    const toggleExpanded = (field: string) => {
        expandedOverrides = { ...expandedOverrides, [field]: !isExpanded(field) };
    };
    const matches = (field: string) => matchesFieldSearch(field, fieldSearch);
</script>

<!-- All metadata filters share one section: active filter chips first, then one collapsible
     field per key. Numeric fields, width and height use a slider, categorical fields a value
     list. -->
<Segment title="Metadata">
    <div class="space-y-4">
        <MetadataFilterChips {collectionId} showDimensions={showImageDimensions} />

        {#if fieldCount > MANY_FIELDS}
            <Input
                value={fieldSearch}
                oninput={(event) => (fieldSearch = event.currentTarget.value)}
                placeholder="Search metadata fields…"
                aria-label="Search metadata fields"
                class="h-8"
            />
        {/if}

        {#if showImageDimensions && $bounds && $values}
            {#each [{ key: 'width', title: 'Width' }, { key: 'height', title: 'Height' }] as dimension (dimension.key)}
                {#if matches(dimension.title)}
                    <MetadataFilterItem
                        metadataKey={dimension.key}
                        title={dimension.title}
                        unit="px"
                        bound={dimension.key === 'width'
                            ? { min: $bounds.min_width, max: $bounds.max_width }
                            : { min: $bounds.min_height, max: $bounds.max_height }}
                        value={dimension.key === 'width'
                            ? { min: $values.min_width, max: $values.max_width }
                            : { min: $values.min_height, max: $values.max_height }}
                        onValueCommit={handleDimensionCommit}
                        expanded={isExpanded(dimension.title)}
                        onToggleExpanded={() => toggleExpanded(dimension.title)}
                    />
                {/if}
            {/each}
        {:else if isVideos}
            <VideoFieldBoundsFilters {onFilterChanged} />
        {/if}

        {#if isVideoFrames}
            <VideoFrameBoundsFilter {onFilterChanged} />
        {/if}

        {#each numericalMetadata.filter(matches) as metadataKey (metadataKey)}
            <MetadataFilterItem
                {metadataKey}
                bound={$metadataBounds[metadataKey]}
                value={$metadataValues[metadataKey]}
                onValueCommit={handleMetadataValueCommit}
                expanded={isExpanded(metadataKey)}
                onToggleExpanded={() => toggleExpanded(metadataKey)}
            />
        {/each}

        {#if categoricalFields.length > 0}
            <CategoricalMetadataFilters
                {collectionId}
                filter={categoricalFilter}
                fields={categoricalFields.filter(matches)}
                {isExpanded}
                onToggleExpanded={toggleExpanded}
                onValueToggle={onCategoricalValueToggle}
                onValuesClear={onCategoricalValuesClear}
            />
        {/if}
    </div>
</Segment>
