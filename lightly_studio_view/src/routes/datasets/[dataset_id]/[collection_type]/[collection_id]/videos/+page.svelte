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
    const { videoBoundsValues } = $derived.by(() => useVideoBounds(collectionId));

    const { textEmbedding } = useGlobalStorage();

    const videosParams = $derived({
        collection_id: collectionId,
        filters: {
            annotation_frames_label_ids: $selectedAnnotationsFilterIds?.length
                ? $selectedAnnotationsFilterIds
                : undefined,
            tag_ids: $tagsSelected.size > 0 ? Array.from($tagsSelected) : undefined,
            metadata_values: $metadataValues
        },
        video_bounds: $videoBoundsValues,
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

    $effect(() => {
        setfilteredSampleCount($totalCount);
    });
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
                <SampleGridItem
                    {style}
                    {index}
                    dataTestId="video-grid-item"
                    sampleId={items[index].sample_id}
                    {collectionId}
                    dataSampleName={items[index].file_name}
                >
                    {#snippet item()}
                        <VideoItem video={items[index]} size={sampleSize} {index} />
                    {/snippet}
                </SampleGridItem>
            {/if}
        {/snippet}
    </SampleGrid>
</div>
