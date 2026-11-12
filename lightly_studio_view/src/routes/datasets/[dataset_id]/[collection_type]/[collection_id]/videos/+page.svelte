<script lang="ts">
    import { useVideos } from '$lib/hooks/useVideos/useVideos.svelte';
    import { page } from '$app/stores';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import VideoItem from '$lib/components/VideoItem/VideoItem.svelte';
    import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import { useSelectedAnnotationsFilter } from '$lib/hooks/useAnnotationsFilter/useAnnotationsFilter';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import { useVideoBounds } from '$lib/hooks/useVideosBounds/useVideosBounds';
    import { buildVideoFilter, useVideoFilters } from '$lib/hooks';
    import { GridContainer } from '$lib/components/GridContainer';
    import { Grid } from '$lib/components/Grid';
    import { GridItem } from '$lib/components/GridItem';
    import type { VideoFilterParams } from '$lib/hooks/useVideoFilters/useVideoFilters';
    import { isEqual } from 'lodash-es';
    import { mergeExternalFilters, paramsWithoutExternalFilters } from './syncFilterParams';
    import { get } from 'svelte/store';
    import { selectRangeByAnchor } from '$lib/utils/selectRangeByAnchor';
    import { onMount } from 'svelte';
    import { useScrollRestoration } from '$lib/hooks/useScrollRestoration/useScrollRestoration';

    const collectionId = $derived($page.params.collection_id!);
    const { tagsSelected } = $derived.by(() =>
        useTags({
            collection_id: collectionId
        })
    );

    const { metadataValues, categoricalMetadataValues } = useMetadataFilters();
    const { selectedAnnotationFilterIdsArray: selectedAnnotationsFilterIds } =
        useSelectedAnnotationsFilter();
    const { videoBoundsValues } = $derived.by(() => useVideoBounds(collectionId));

    const { textEmbedding, getSelectedSampleIds, toggleSampleSelection, sampleSize } =
        useGlobalStorage();
    const columnCount = $derived($sampleSize.width);

    const videosParams = $derived({
        collection_id: collectionId,
        filters: {
            annotation_frames_label_ids: $selectedAnnotationsFilterIds?.length
                ? $selectedAnnotationsFilterIds
                : undefined,
            tag_ids: $tagsSelected.size > 0 ? Array.from($tagsSelected) : undefined,
            metadata_values: $metadataValues,
            categorical_metadata_values: $categoricalMetadataValues
        },
        video_bounds: $videoBoundsValues
    });

    const { filterParams, videoSortBy, updateFilterParams } = useVideoFilters();

    $effect(() => {
        // Synchronize the global filter parameters with the local videos parameters
        const baseParams = videosParams as VideoFilterParams;
        const currentParams = $filterParams;

        // Compare filter controls without the externally-set sample IDs and embedding region.
        if (
            currentParams &&
            isEqual(
                paramsWithoutExternalFilters(baseParams),
                paramsWithoutExternalFilters(currentParams)
            )
        ) {
            return;
        }

        updateFilterParams(mergeExternalFilters(baseParams, currentParams));
    });

    const currentVideoFilter = $derived.by(() => {
        const paramsWithSelection = mergeExternalFilters(videosParams, $filterParams);
        return buildVideoFilter(paramsWithSelection) ?? {};
    });

    const { data, query, loadMore, totalCount } = useVideos(() => ({
        collection_id: collectionId,
        filter: currentVideoFilter,
        text_embedding: $textEmbedding?.embedding,
        sort_by: $textEmbedding ? undefined : ($videoSortBy ?? undefined)
    }));
    const { setfilteredSampleCount } = useGlobalStorage();

    let items = $derived($data);
    const selectedSampleIds = $derived(getSelectedSampleIds(collectionId));
    let selectionAnchorSampleId = $state<string | null>(null);

    $effect(() => {
        setfilteredSampleCount($totalCount);
    });

    function handleSampleSelect({
        sampleId,
        index,
        shiftKey
    }: {
        sampleId: string;
        index: number;
        shiftKey: boolean;
    }) {
        const selectedSampleIdsStore = getSelectedSampleIds(collectionId);
        selectionAnchorSampleId = selectRangeByAnchor({
            sampleIdsInOrder: items.map((item) => item.sample_id),
            selectedSampleIds: get(selectedSampleIdsStore),
            clickedSampleId: sampleId,
            clickedIndex: index,
            shiftKey,
            anchorSampleId: selectionAnchorSampleId,
            onSelectSample: (selectedSampleId) =>
                toggleSampleSelection(selectedSampleId, collectionId)
        });
    }

    function handleGridItemSelect(
        event: MouseEvent | KeyboardEvent,
        sampleId: string,
        index: number
    ) {
        handleSampleSelect({ sampleId, index, shiftKey: event.shiftKey });
    }

    // TODO(Mihnea, 09/2026): hash the effective metadata filters, not raw $filterParams.
    // Same fix as Images.svelte's filterHash.
    const filterHash = $derived(JSON.stringify({ filters: $filterParams, sortBy: $videoSortBy }));
    const { initialize, savePosition, getRestoredPosition } = useScrollRestoration('frames_scroll');
    onMount(async () => {
        initialize();
    });

    const initialScrollPosition = $derived(getRestoredPosition(filterHash));

    function handleScroll(event: Event) {
        const scrollTop = (event.target as HTMLElement).scrollTop;
        savePosition(scrollTop, filterHash);
    }
    const scrollResetKey = $derived(filterHash + ($textEmbedding?.queryText ?? ''));
</script>

<div class="flex flex-1 flex-col space-y-4">
    <GridContainer
        itemCount={items.length}
        message={{
            loading: 'Loading videos...',
            error: 'Error loading videos',
            empty: {
                title: 'No videos found',
                description: "This collection doesn't contain any videos."
            }
        }}
        status={{
            loading: query.isPending && items.length === 0,
            error: query.isError,
            empty: query.isSuccess && items.length === 0,
            success: query.isSuccess && items.length > 0
        }}
        loader={{
            loadMore,
            disabled: !query.hasNextPage || query.isFetchingNextPage,
            loading: query.isFetchingNextPage
        }}
    >
        {#snippet children({ footer })}
            <Grid
                itemCount={items.length}
                {columnCount}
                overScan={2}
                onScroll={handleScroll}
                {initialScrollPosition}
                {scrollResetKey}
                gridProps={{ 'data-testid': 'video-grid', class: 'dark:[color-scheme:dark]' }}
            >
                {#snippet gridItem({ index, style, width, height })}
                    {#if items[index]}
                        {#key items[index].sample_id}
                            <GridItem
                                {width}
                                {height}
                                {style}
                                dataSampleName={items[index].file_name}
                                dataIndex={index}
                                dataTestId="video-grid-item"
                                isSelected={$selectedSampleIds.has(items[index].sample_id)}
                                ariaLabel={`View sample: ${items[index].file_name}`}
                                onSelect={(event) =>
                                    handleGridItemSelect(event, items[index].sample_id, index)}
                            >
                                <VideoItem video={items[index]} size={width} showCaption={true} />
                            </GridItem>
                        {/key}
                    {/if}
                {/snippet}
                {#snippet footerItem()}
                    {@render footer()}
                {/snippet}
            </Grid>
        {/snippet}
    </GridContainer>
</div>
