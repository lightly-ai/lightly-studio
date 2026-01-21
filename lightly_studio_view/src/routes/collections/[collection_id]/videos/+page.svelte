<script lang="ts">
    import { useVideos } from '$lib/hooks/useVideos/useVideos';
    import { page } from '$app/stores';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import VideoItem from '$lib/components/VideoItem/VideoItem.svelte';
    import {
        createMetadataFilters,
        useMetadataFilters
    } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import type { VideoFilter } from '$lib/api/lightly_studio_local';
    import { useTags } from '$lib/hooks/useTags/useTags';
    const { tagsSelected } = useTags({
        collection_id: $page.params.collection_id,
        kind: ['sample']
    });
    import { useVideoBounds } from '$lib/hooks/useVideosBounds/useVideosBounds';
    import SampleGridItem from '$lib/components/SampleGridItem/SampleGridItem.svelte';
    import SampleGrid from '$lib/components/SampleGrid/SampleGrid.svelte';

    const { data: propsData } = $props();
    const { metadataValues } = useMetadataFilters();
    const selectedAnnotationsFilterIds = $derived(propsData.selectedAnnotationFilterIds);
    const { videoBoundsValues } = useVideoBounds();
    const filter: VideoFilter = $derived({
        sample_filter: {
            metadata_filters: metadataValues ? createMetadataFilters($metadataValues) : undefined,
            tag_ids: $tagsSelected.size > 0 ? Array.from($tagsSelected) : undefined
        },
        annotation_frames_label_ids: $selectedAnnotationsFilterIds,
        ...$videoBoundsValues
    });
    const { textEmbedding } = useGlobalStorage();
    const { data, query, loadMore, totalCount } = $derived(
        useVideos($page.params.collection_id, filter, $textEmbedding?.embedding)
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
                    collectionId={$page.params.collection_id}
                    dataSampleName={items[index].file_name}
                >
                    {#snippet item()}
                        <VideoItem video={items[index]} size={sampleSize} {index} />
                    {/snippet}
                </SampleGridItem>
            {/if}
        {/snippet}</SampleGrid
    >
</div>
