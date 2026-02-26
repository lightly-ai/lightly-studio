<script lang="ts">
    import { useVideos } from '$lib/hooks/useVideos/useVideos';
    import { page } from '$app/stores';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import VideoItem from '$lib/components/VideoItem/VideoItem.svelte';
    import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import { useVideoBounds } from '$lib/hooks/useVideosBounds/useVideosBounds';
    import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
    import SampleGridItem from '$lib/components/SampleGridItem/SampleGridItem.svelte';
    import SampleGrid from '$lib/components/SampleGrid/SampleGrid.svelte';
    import type { VideoFilterParams } from '$lib/hooks/useVideoFilters/useVideoFilters';
    import { isEqual, omit } from 'lodash-es';
    import { get } from 'svelte/store';
    import { selectRangeByAnchor } from '$lib/utils/selectRangeByAnchor';

    const { data: propsData } = $props();

    const collectionId = $derived($page.params.collection_id!);
    const { tagsSelected } = $derived.by(() =>
        useTags({
            collection_id: collectionId,
            kind: ['sample']
        })
    );

    const { metadataValues } = useMetadataFilters();
    const selectedAnnotationsFilterIds = $derived(propsData.selectedAnnotationFilterIds);
    const { videoBounds, videoBoundsValues } = $derived.by(() => useVideoBounds(collectionId));

    const { textEmbedding, getSelectedSampleIds, toggleSampleSelection } = useGlobalStorage();


    // Only apply video_bounds if values differ from bounds
    const videoBoundsFilter = $derived.by(() => {
        const bounds = $videoBounds;
        const values = $videoBoundsValues;
        if (!bounds || !values) {
            return undefined;
        }


        // Helper for int and float range comparison
        function isIntRangeUnchanged(val: { min: number, max: number }, bound: { min: number, max: number }) {
            return val.min === bound.min && val.max === bound.max;
        }
        function isFloatRangeUnchanged(val: { min: number, max: number }, bound: { min: number, max: number }, epsilon = 1e-6) {
            return Math.abs(val.min - bound.min) < epsilon && Math.abs(val.max - bound.max) < epsilon;
        }

        const widthUnchanged = isIntRangeUnchanged(values.width, bounds.width);
        const heightUnchanged = isIntRangeUnchanged(values.height, bounds.height);
        const durationUnchanged = isFloatRangeUnchanged(values.duration_s, bounds.duration_s);
        const fpsUnchanged = isFloatRangeUnchanged(values.fps, bounds.fps);

        if (widthUnchanged && heightUnchanged && durationUnchanged && fpsUnchanged) {
            return undefined;
        }
        return values;
    });

    const videosParams = $derived({
        collection_id: collectionId,
        filters: {
            annotation_frames_label_ids: $selectedAnnotationsFilterIds?.length
                ? $selectedAnnotationsFilterIds
                : undefined,
            tag_ids: $tagsSelected.size > 0 ? Array.from($tagsSelected) : undefined,
            metadata_values: $metadataValues
        },
        video_bounds: videoBoundsFilter,
        text_embedding: $textEmbedding?.embedding
    });

    const paramsWithoutSampleIds = (params: VideoFilterParams) => {
        return {
            ...params,
            filters: params.filters ? omit(params.filters, ['sample_ids']) : undefined
        };
    };

    const { filterParams, videoFilter, updateFilterParams } = useVideoFilters();

    $effect(() => {
        // Synchronize the global filter parameters with the local videos parameters
        const baseParams = videosParams as VideoFilterParams;
        const currentParams = $filterParams;

        // Compare parameters excluding sample_ids to detect if other filters have changed
        if (
            currentParams &&
            isEqual(paramsWithoutSampleIds(baseParams), paramsWithoutSampleIds(currentParams))
        ) {
            return;
        }

        // Start with the base parameters from the component
        let nextParams = baseParams;

        let currentSampleIds: string[] = [];
        if (currentParams?.filters?.sample_ids) {
            currentSampleIds = currentParams.filters.sample_ids;
        }

        // Merge the existing sample selection into the new parameters
        if (currentSampleIds && currentSampleIds.length > 0) {
            nextParams = {
                ...nextParams,
                filters: {
                    ...(nextParams.filters ?? {}),
                    sample_ids: currentSampleIds
                }
            };
        }

        // Update the global filter parameters
        updateFilterParams(nextParams);
    });

    // Make sure the query reacts to filter changes
    const currentVideoFilter = $derived($videoFilter ?? {});
    const { data, query, loadMore, totalCount } = $derived(
        useVideos(collectionId, currentVideoFilter, $textEmbedding?.embedding)
    );
    const { setfilteredSampleCount } = useGlobalStorage();

    let items = $derived($data);
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
        const selectedSampleIds = getSelectedSampleIds(collectionId);
        selectionAnchorSampleId = selectRangeByAnchor({
            sampleIdsInOrder: items.map((item) => item.sample_id),
            selectedSampleIds: get(selectedSampleIds),
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
    <SampleGrid
        itemCount={items.length}
        overScan={20}
        testId="video-grid"
        message={{
            loading: 'Loading videos...',
            error: 'Error loading videos',
            empty: {
                title: 'No videos found',
                description: "This collection doesn't contain any videos."
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
                {#key items[index].sample_id}
                    <SampleGridItem
                        {style}
                        {index}
                        dataTestId="video-grid-item"
                        sampleId={items[index].sample_id}
                        {collectionId}
                        dataSampleName={items[index].file_name}
                        onSelect={handleSampleSelect}
                    >
                        {#snippet item()}
                            <VideoItem
                                video={items[index]}
                                size={sampleSize}
                                {index}
                                showCaption={true}
                            />
                        {/snippet}
                    </SampleGridItem>
                {/key}
            {/if}
        {/snippet}
    </SampleGrid>
</div>
