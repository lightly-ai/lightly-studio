<script lang="ts">
    import {
        useGlobalStorage,
        useFrames,
        useTags,
        useVideoFramesBounds,
        useMetadataFilters,
        useFramesFilter
    } from '$lib/hooks';
    import { useSelectedAnnotationsFilter } from '$lib/hooks/useAnnotationsFilter/useAnnotationsFilter';

    import { selectRangeByAnchor } from '$lib/utils/selectRangeByAnchor';
    import { isEqual, omit } from 'lodash-es';
    import { page } from '$app/state';
    import type { VideoFrameFilterParams } from '$lib/hooks/useFramesFilter/frameFilter';
    import { GridHeader, Separator, VideoFrameItem } from '$lib/components';
    import { GridContainer } from '$lib/components/GridContainer';
    import { Grid } from '$lib/components/Grid';
    import { GridItem } from '$lib/components/GridItem';
    import { useScrollRestoration } from '$lib/hooks/useScrollRestoration/useScrollRestoration';
    import { onMount } from 'svelte';

    const collectionId = $derived(page.params.collection_id);

    const { metadataValues } = $derived(useMetadataFilters(collectionId));
    const { videoFramesBoundsValues } = $derived(useVideoFramesBounds(collectionId));

    const { selectedAnnotationFilterIdsArray: selectedAnnotationFilterIds } =
        useSelectedAnnotationsFilter();
    const { tagsSelected } = $derived(
        useTags({
            collection_id: collectionId,
            kind: ['sample']
        })
    );

    const framesParams = $derived<VideoFrameFilterParams>({
        collection_id: collectionId,
        filters: {
            annotation_label_ids: $selectedAnnotationFilterIds?.length
                ? $selectedAnnotationFilterIds
                : undefined,
            tag_ids: $tagsSelected.size > 0 ? Array.from($tagsSelected) : undefined,
            metadata_values: $metadataValues
        },
        frame_bounds: $videoFramesBoundsValues
    });

    const paramsWithoutSampleIds = (params: VideoFrameFilterParams) => {
        return {
            ...params,
            filters: params.filters ? omit(params.filters, ['sample_ids']) : undefined
        };
    };

    const { filterParams, frameFilter, updateFilterParams } = useFramesFilter();

    $effect(() => {
        const baseParams = framesParams;
        const currentParams = $filterParams;

        if (
            currentParams &&
            isEqual(paramsWithoutSampleIds(baseParams), paramsWithoutSampleIds(currentParams))
        ) {
            return;
        }

        let nextParams = baseParams;
        const currentSampleIds = currentParams?.filters?.sample_ids ?? [];

        if (currentSampleIds.length > 0) {
            nextParams = {
                ...nextParams,
                filters: {
                    ...(nextParams.filters ?? {}),
                    sample_ids: currentSampleIds
                }
            };
        }

        updateFilterParams(nextParams);
    });

    const currentFrameFilter = $derived($frameFilter ?? {});
    const { data, query, loadMore, totalCount } = $derived(
        useFrames(collectionId, currentFrameFilter)
    );
    const { setfilteredSampleCount, getSelectedSampleIds, toggleSampleSelection, sampleSize } =
        useGlobalStorage();
    const columnCount = $derived($sampleSize.width);

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
        selectionAnchorSampleId = selectRangeByAnchor({
            sampleIdsInOrder: items.map((item) => item.sample_id),
            selectedSampleIds: $selectedSampleIds,
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
    const filterHash = $derived(JSON.stringify($filterParams));
    const { initialize, savePosition, getRestoredPosition } = useScrollRestoration('frames_scroll');
    onMount(async () => {
        initialize();
    });

    const initialScrollPosition = $derived(getRestoredPosition(filterHash));

    function handleScroll(event: Event) {
        const scrollTop = (event.target as HTMLElement).scrollTop;
        savePosition(scrollTop, filterHash);
    }
    const scrollResetKey = $derived(filterHash);
</script>

<div class="flex flex-1 flex-col space-y-4">
    <GridHeader />
    <Separator class="mb-4 bg-border-hard" />

    <GridContainer
        itemCount={items.length}
        message={{
            loading: 'Loading video frames...',
            error: 'Error loading video frames',
            empty: {
                title: 'No video frames found',
                description: "This collection doesn't contain any video frames."
            }
        }}
        status={{
            loading: $query.isPending && items.length === 0,
            error: $query.isError,
            empty: $query.isSuccess && items.length === 0,
            success: $query.isSuccess && items.length > 0
        }}
        loader={{
            loadMore,
            disabled: !$query.hasNextPage || $query.isFetchingNextPage,
            loading: $query.isFetchingNextPage
        }}
    >
        {#snippet children({ footer })}
            <Grid
                itemCount={items.length}
                {columnCount}
                overScan={30}
                onScroll={handleScroll}
                {initialScrollPosition}
                {scrollResetKey}
                gridProps={{
                    'data-testid': 'video-frames-grid',
                    class: 'dark:[color-scheme:dark]'
                }}
            >
                {#snippet gridItem({ index, style, width, height })}
                    {#if items[index]}
                        {#key items[index].sample_id}
                            <GridItem
                                {width}
                                {height}
                                {style}
                                dataTestId="frame-grid-item"
                                isSelected={$selectedSampleIds.has(items[index].sample_id)}
                                ariaLabel={`View sample: ${items[index].sample_id}`}
                                onSelect={(event) =>
                                    handleGridItemSelect(event, items[index].sample_id, index)}
                            >
                                <VideoFrameItem videoFrame={items[index]} size={width} />
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
