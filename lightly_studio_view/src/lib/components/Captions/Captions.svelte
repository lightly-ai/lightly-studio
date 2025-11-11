<script lang="ts">
    import { useCaptionsInfinite } from '$lib/hooks/useCaptionsInfinite/useCaptionsInfinite';
    import { Separator } from '../ui/separator';
    import { ImageSizeControl, LazyTrigger, Spinner } from '$lib/components';
    import { List } from 'svelte-virtual';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import CaptionsItem from './CaptionsItem/CaptionsItem.svelte';

    const {
        datasetId
    }: {
        datasetId: string;
    } = $props();

    const { data, query, loadMore } = $derived(
        useCaptionsInfinite({
            path: { dataset_id: datasetId }
        })
    );

    let viewport: HTMLElement | null = $state(null);
    $inspect($data);

    const { sampleSize } = useGlobalStorage();
    let viewportHeight = $state(0);
    let size = $state(0);
    let captionSize = $state(0);
    let clientWidth = $state(0);

    // Add a resize observer effect to update viewport dimensions
    $effect(() => {
        if (!viewport) return;
        size = clientWidth / $sampleSize.width;
        captionSize = size - GridGap;
        // Set initial height
        viewportHeight = viewport.clientHeight;

        // Create resize observer to update height when container resizes
        const resizeObserver = new ResizeObserver(() => {
            if (!viewport) return;
            viewportHeight = viewport.clientHeight;
        });

        resizeObserver.observe(viewport);

        return () => {
            resizeObserver.disconnect();
        };
    });

    let items = $derived($data);
    const GridGap = 16;

    const height = $derived(viewportHeight + GridGap);
</script>

<div class="flex flex-1 flex-col space-y-4">
    <div class="my-2 flex items-center space-x-4">
        <div class="flex-1">
            <!-- Header -->
            <div class="text-2xl font-semibold">Captions</div>
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
                <div>Loading samples...</div>
            </div>
        {:else if $query.isSuccess && items.length > 0}
            <List
                itemCount={items.length}
                {height}
                itemSize={captionSize + GridGap}
                class="dark:[color-scheme:dark]"
                style="--sample-width: {captionSize}px; --sample-height: {captionSize}px;"
            >
                {#snippet item({ index, style })}
                    <div {style} class={`pb-[${GridGap}]`}>
                        <CaptionsItem item={items[index]} />
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
            </List>
        {/if}
    </div>
</div>
