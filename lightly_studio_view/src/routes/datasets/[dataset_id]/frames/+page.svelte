<script lang="ts">
    import { ImageSizeControl, LazyTrigger, Spinner } from '$lib/components';
    import Separator from '$lib/components/ui/separator/separator.svelte';
    import { page } from '$app/stores';
    import { Grid } from 'svelte-virtual';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useFrames } from '$lib/hooks/useFrames/useFrames';
    import VideoFrameItem from '$lib/components/VideoFrameItem/VideoFrameItem.svelte';

    const { data, query, loadMore } = $derived(
        useFrames({
            path: { dataset_id: $page.params.dataset_id }
        })
    );
    const { sampleSize } = useGlobalStorage();

    const GRID_GAP = 16;
    let viewport: HTMLElement | null = $state(null);
    let clientWidth = $state(0);

    let items = $derived($data);

    const itemSize = $derived(viewport == null ? 0 : viewport.clientWidth / $sampleSize.width);
    const videoSize = $derived(itemSize - GRID_GAP);
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
    <Separator class="bg-border-hard mb-4" />

    <div class="h-full w-full flex-1 overflow-hidden" bind:this={viewport} bind:clientWidth>
        {#if $query.isPending && items.length === 0}
            <div class="flex h-full w-full items-center justify-center">
                <Spinner />
                <div>Loading frames...</div>
            </div>
        {:else if $query.isSuccess && items.length > 0}
            <Grid
                itemCount={items.length}
                itemHeight={itemSize}
                itemWidth={itemSize}
                height={viewport?.clientHeight}
                class="overflow-none overflow-y-auto dark:[color-scheme:dark]"
                style="--sample-width: {videoSize}px; --sample-height: {videoSize}px;"
                overScan={100}
            >
                {#snippet item({ index, style })}
                    <div {style}>
                        <div
                            class="relative overflow-hidden rounded-lg"
                            style="width: var(--sample-width); height: var(--sample-height);"
                        >
                            <VideoFrameItem videoFrame={items[index]} />
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
