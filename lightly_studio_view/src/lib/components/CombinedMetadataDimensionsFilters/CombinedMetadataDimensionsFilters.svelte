<script lang="ts">
    import { X } from '@lucide/svelte';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { FilterActionButton } from '$lib/components/FilterActionButton';
    import { useCategoricalFieldCounts } from '$lib/components/CategoricalMetadataFilters/useCategoricalFieldCounts.svelte';
    import type { MetadataValueCountsFilter } from '$lib/hooks/useCategoricalMetadataDistribution/useCategoricalMetadataDistribution.svelte';
    import type { CategoricalMetadataValue } from '$lib/services/types';
    import { Input } from '$lib/components/ui/input';
    import { setFieldSearchContext } from '$lib/components/MetadataFieldHeader/fieldSearchContext';
    import MetadataFieldRow from './MetadataFieldRow.svelte';
    import { MANY_FIELDS, isFieldExpanded, matchesFieldSearch } from './metadataFieldList';
    import { isFieldActive, orderByActive } from './metadataFields';
    import { keepFocusOnMove } from './keepFocusOnMove.svelte';
    import { useMetadataFieldList } from './useMetadataFieldList.svelte';

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
        /** Filter for the categorical value counts. `undefined` counts all samples. */
        categoricalCountsFilter?: MetadataValueCountsFilter;
        categoricalKeys?: string[];
        onCategoricalValueToggle: (field: string, value: CategoricalMetadataValue) => void;
        onCategoricalValuesSet: (field: string, values: CategoricalMetadataValue[]) => void;
        onCategoricalValuesClear: (field: string) => void;
    }

    const {
        collectionId,
        showDimensions = true,
        isVideos = false,
        isVideoFrames = false,
        onFilterChanged,
        categoricalCountsFilter,
        categoricalKeys = [],
        onCategoricalValueToggle,
        onCategoricalValuesSet,
        onCategoricalValuesClear
    }: Props = $props();

    const list = useMetadataFieldList({
        getCollectionId: () => collectionId,
        getShowImageDimensions: () => showDimensions && !isVideos && !isVideoFrames,
        getIsVideos: () => isVideos,
        getIsVideoFrames: () => isVideoFrames,
        getCategoricalKeys: () => categoricalKeys,
        onRangeCommitted: (key, min, max) => onFilterChanged?.(key, min, max)
    });

    let fieldSearch = $state('');
    setFieldSearchContext(() => fieldSearch);
    let rowsElement = $state<HTMLElement>();
    let rowsMinHeight = $state<number>();
    // While searching, the rows keep their height so the search box does not move.
    const setFieldSearch = (value: string) => {
        if (!fieldSearch && value) rowsMinHeight = rowsElement?.offsetHeight;
        if (!value) rowsMinHeight = undefined;
        fieldSearch = value;
    };
    let expandedOverrides = $state<Record<string, boolean>>({});
    const fieldCount = $derived(list.fields.length);
    const isExpanded = (id: string) => isFieldExpanded(expandedOverrides, id, fieldCount);
    const toggleExpanded = (id: string) => {
        expandedOverrides = { ...expandedOverrides, [id]: !isExpanded(id) };
    };

    const ordered = $derived(
        orderByActive(list.fields.filter((field) => matchesFieldSearch(field.title, fieldSearch)))
    );
    let listElement = $state<HTMLElement>();
    keepFocusOnMove(
        () => listElement,
        () => ordered.fields.map((field) => field.id)
    );
    const hasActiveField = $derived(list.fields.some(isFieldActive));

    // Expanded fields show their values and active fields their "N of M" summary, so only
    // those categorical fields are requested.
    const counts = useCategoricalFieldCounts(() => ({
        collectionId,
        filter: categoricalCountsFilter,
        fields: ordered.fields
            .filter(
                (field) =>
                    field.kind === 'categorical' && (isExpanded(field.id) || isFieldActive(field))
            )
            .map((field) => field.key)
    }));
</script>

<!-- All metadata filters share one section: active fields first, then a line, then the other
     fields. Ranges use a slider, categorical fields a value list. -->
<Segment title="Metadata">
    <div class="space-y-4" bind:this={listElement}>
        {#if fieldCount > MANY_FIELDS}
            <Input
                value={fieldSearch}
                oninput={(event) => setFieldSearch(event.currentTarget.value)}
                placeholder="Search metadata fields…"
                aria-label="Search metadata fields"
                class="h-8"
            />
        {/if}
        <div class="flex">
            <FilterActionButton
                label="Clear"
                icon={X}
                onclick={list.resetAll}
                disabled={!hasActiveField}
            />
        </div>

        <div
            class="space-y-4"
            bind:this={rowsElement}
            style:min-height={rowsMinHeight ? `${rowsMinHeight}px` : undefined}
        >
            {#each ordered.fields as field, index (field.id)}
                {@const expanded = isExpanded(field.id)}
                {#if index === ordered.activeCount && ordered.activeCount > 0}
                    <hr data-testid="metadata-active-separator" class="border-border" />
                {/if}
                <div data-field-id={field.id}>
                    <MetadataFieldRow
                        {field}
                        {expanded}
                        onToggleExpanded={() => toggleExpanded(field.id)}
                        {counts}
                        onCommitRange={(range) => list.commitRange(field.id, range)}
                        onReset={() => list.reset(field.id)}
                        {onCategoricalValueToggle}
                        {onCategoricalValuesSet}
                        {onCategoricalValuesClear}
                    />
                </div>
            {/each}
        </div>
    </div>
</Segment>
