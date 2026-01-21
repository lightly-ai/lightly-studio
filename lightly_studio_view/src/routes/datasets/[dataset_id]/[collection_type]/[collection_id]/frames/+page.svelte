<script lang="ts">
    import { ImageSizeControl } from '$lib/components';
    import Separator from '$lib/components/ui/separator/separator.svelte';
    import { page } from '$app/stores';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useFrames } from '$lib/hooks/useFrames/useFrames';
    import VideoFrameItem from '$lib/components/VideoFrameItem/VideoFrameItem.svelte';
    import { type VideoFrameFilter } from '$lib/api/lightly_studio_local';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import { useVideoFramesBounds } from '$lib/hooks/useVideoFramesBounds/useVideoFramesBounds.js';
    import {
        createMetadataFilters,
        useMetadataFilters
    } from '$lib/hooks/useMetadataFilters/useMetadataFilters.js';
    import SampleGrid from '$lib/components/SampleGrid/SampleGrid.svelte';
    import SampleGridItem from '$lib/components/SampleGridItem/SampleGridItem.svelte';

    const { data: dataProps } = $props();
    const { metadataValues } = useMetadataFilters($page.params.collection_id);
    const { videoFramesBoundsValues } = useVideoFramesBounds();

    const selectedAnnotationFilterIds = $derived(dataProps.selectedAnnotationFilterIds);
    const { tagsSelected } = useTags({
        collection_id: $page.params.collection_id,
        kind: ['sample']
    });
    const filter: VideoFrameFilter = $derived({
        sample_filter: {
            annotation_label_ids: $selectedAnnotationFilterIds?.length
                ? $selectedAnnotationFilterIds
                : undefined,
            tag_ids: $tagsSelected.size > 0 ? Array.from($tagsSelected) : undefined,
            metadata_filters: metadataValues ? createMetadataFilters($metadataValues) : undefined
        },
        ...$videoFramesBoundsValues
    });
    const { data, query, loadMore, totalCount } = $derived(
        useFrames($page.params.collection_id, filter)
    );
    const { setfilteredSampleCount } = useGlobalStorage();

    let items = $derived($data);

    $effect(() => {
        setfilteredSampleCount($totalCount);
    });
</script>

<div class="flex flex-1 flex-col space-y-4">
    <div class="my-2 flex items-center space-x-4">
        <div class="flex-1">
            <div class="text-2xl font-semibold">Frames</div>
        </div>

        <div class="w-4/12">
            <ImageSizeControl />
        </div>
    </div>
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
                    collectionId={$page.params.collection_id}
                    dataSampleName={items[index].sample_id}
                >
                    {#snippet item()}
                        <VideoFrameItem videoFrame={items[index]} {index} size={sampleSize} />
                    {/snippet}
                </SampleGridItem>
            {/if}
        {/snippet}
    </SampleGrid>
</div>
