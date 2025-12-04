<script lang="ts">
    import { ImageSizeControl, LazyTrigger, Spinner } from '$lib/components';
    import Separator from '$lib/components/ui/separator/separator.svelte';
    import { page } from '$app/stores';
    import { Grid } from 'svelte-virtual';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useFrames } from '$lib/hooks/useFrames/useFrames';
    import VideoFrameItem from '$lib/components/VideoFrameItem/VideoFrameItem.svelte';
    import { type VideoFrameFilter } from '$lib/api/lightly_studio_local';
    import { useVideoFramesBounds } from '$lib/hooks/useVideoFramesBounds/useVideoFramesBounds.js';
    import {
        createMetadataFilters,
        useMetadataFilters
    } from '$lib/hooks/useMetadataFilters/useMetadataFilters.js';

    const { data: dataProps } = $props();
    const { metadataValues } = useMetadataFilters($page.params.dataset_id);
    const { videoFramesBoundsValues } = useVideoFramesBounds();

    const selectedAnnotationFilterIds = $derived(dataProps.selectedAnnotationFilterIds);
    const filter: VideoFrameFilter = $derived({
        sample_filter: {
            annotation_label_ids: $selectedAnnotationFilterIds?.length
                ? $selectedAnnotationFilterIds
                : undefined,
            metadata_filters: metadataValues ? createMetadataFilters($metadataValues) : undefined
        },
        ...$videoFramesBoundsValues
    });
    const { data, query, loadMore, totalCount } = $derived(
        useFrames($page.params.dataset_id, filter)
    );
    const { sampleSize, setfilteredSampleCount } = useGlobalStorage();

    const GRID_GAP = 16;
    let viewport: HTMLElement | null = $state(null);
    let clientWidth = $state(0);

    let items = $derived($data);

    const itemSize = $derived(viewport == null ? 0 : viewport.clientWidth / $sampleSize.width);
    const videoSize = $derived(itemSize - GRID_GAP);

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

    <div class="h-full w-full flex-1 overflow-hidden" bind:this={viewport} bind:clientWidth>
        {#if $query.isPending && items.length === 0}
            <div class="flex h-full w-full items-center justify-center">
                <Spinner />
                <div>Loading video frames...</div>
            </div>
        {:else if $query.isSuccess && items.length === 0}
            <!-- Empty state -->
            <div class="flex h-full w-full items-center justify-center">
                <div class="text-center text-muted-foreground">
                    <div class="mb-2 text-lg font-medium">No video frames found</div>
                    <div class="text-sm">This dataset doesn't contain any video frames.</div>
                </div>
            </div>
        {:else if $query.isSuccess && items.length > 0}
            <Grid
                itemCount={items.length}
                itemHeight={itemSize}
                itemWidth={itemSize}
                height={viewport?.clientHeight}
                class="overflow-none overflow-y-auto dark:[color-scheme:dark]"
                style="--sample-width: {videoSize}px; --sample-height: {videoSize}px;"
                overScan={30}
            >
                {#snippet item({ index, style })}
                    <div {style}>
                        <div
                            class="relative overflow-hidden rounded-lg"
                            style="width: var(--sample-width); height: var(--sample-height);"
                        >
                            <VideoFrameItem videoFrame={items[index]} {index} size={videoSize} />
                        </div>
                    </div>
                {/snippet}
                {#snippet footer()}
                    {#key items.length}
                        <LazyTrigger
                            onIntersect={loadMore}
                            disabled={!$query.hasNextPage || $query.isFetchingNextPage}
                        />
                    {/key}
                    {#if $query.isFetchingNextPage}
                        <div class="flex justify-center p-4">
                            <Spinner />
                        </div>
                    {/if}
                {/snippet}
            </Grid>
        {/if}
    </div>
</div>
