<script lang="ts">
    import {
        useGlobalStorage,
        useFrames,
        useTags,
        useVideoFramesBounds,
        useMetadataFilters,
        useFramesFilter
    } from '$lib/hooks';

    import { selectRangeByAnchor } from '$lib/utils/selectRangeByAnchor';
    import { isEqual, omit } from 'lodash-es';
    import { page } from '$app/state';
    import type { VideoFrameFilterParams } from '$lib/hooks/useFramesFilter/frameFilter';
    import {
        GridHeader,
        Typography,
        Separator,
        SampleGrid,
        SampleGridItem,
        VideoFrameItem
    } from '$lib/components';

    const { data: dataProps } = $props();
    const collectionId = $derived(page.params.collection_id);

    const { metadataValues } = $derived(useMetadataFilters(collectionId));
    const { videoFramesBoundsValues } = $derived(useVideoFramesBounds(collectionId));

    const selectedAnnotationFilterIds = $derived(dataProps.selectedAnnotationFilterIds);
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
    const { setfilteredSampleCount, getSelectedSampleIds, toggleSampleSelection } =
        useGlobalStorage();

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
</script>

<div class="flex flex-1 flex-col space-y-4">
    <GridHeader>
        <Typography variant="h2">Frames</Typography>
    </GridHeader>
    <Separator class="mb-4 bg-border-hard" />

    <SampleGrid
        itemCount={items.length}
        overScan={30}
        testId="video-frames-grid"
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
        {#snippet gridItem({ index, style, sampleSize })}
            {#if items[index]}
                <SampleGridItem
                    {style}
                    {index}
                    dataTestId="frame-grid-item"
                    sampleId={items[index].sample_id}
                    {collectionId}
                    dataSampleName={items[index].sample_id}
                    onSelect={handleSampleSelect}
                >
                    {#snippet item()}
                        <VideoFrameItem videoFrame={items[index]} size={sampleSize} />
                    {/snippet}
                </SampleGridItem>
            {/if}
        {/snippet}
    </SampleGrid>
</div>
