<script lang="ts">
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import Grid from 'svelte-virtual/grid';
    import Spinner from '../Spinner/Spinner.svelte';
    import { LazyTrigger } from '../LazyTrigger';
    import type { Snippet } from 'svelte';

    type SampleGridProps = {
        itemCount: number;
        overScan: number;
        scrollPosition?: number;
        gridItem: Snippet<[{ index: number; style: string; sampleSize: number }]>;
        message: {
            loading: string;
            error: string;
            empty: {
                title: string;
                description: string;
            };
        };
        status: {
            loading: boolean;
            error: boolean;
            empty: boolean;
            success: boolean;
        };
        loader: {
            loadMore: () => void;
            disabled: boolean;
            loading: boolean;
        };
        onScroll?: (event: Event) => void;
    };

    const {
        message,
        status,
        itemCount,
        overScan,
        scrollPosition,
        loader,
        onScroll,
        gridItem
    }: SampleGridProps = $props();

    const GRID_GAP = 16;
    let viewport: HTMLElement | null = $state(null);
    let clientWidth = $state(0);
    let clientHeight = $state(0);

    const { sampleSize } = useGlobalStorage();

    const itemSize = $derived.by(() => {
        if (clientWidth === 0) {
            return 0;
        }
        return clientWidth / $sampleSize.width;
    });
    const sampleItemSize = $derived(itemSize - GRID_GAP);
</script>

{#if status.loading}
    <div class="flex h-full w-full items-center justify-center">
        <Spinner />
        <div>{message.loading}</div>
    </div>
{:else if status.empty}
    <!-- Empty state -->
    <div class="flex h-full w-full items-center justify-center">
        <div class="text-center text-muted-foreground">
            <div class="mb-2 text-lg font-medium">{message.empty.title}</div>
            <div class="text-sm">{message.empty.description}</div>
        </div>
    </div>
{:else if status.success}
    <div class="viewport flex-1" bind:this={viewport} bind:clientWidth bind:clientHeight>
        <Grid
            {itemCount}
            itemHeight={itemSize}
            itemWidth={itemSize}
            height={clientHeight}
            {scrollPosition}
            onscroll={onScroll}
            class="overflow-none overflow-y-auto dark:[color-scheme:dark]"
            style="--sample-width: {sampleItemSize}px; --sample-height: {sampleItemSize}px;"
            {overScan}
        >
            {#snippet item({ index, style })}
                {@render gridItem({ index, style, sampleSize: sampleItemSize })}
            {/snippet}
            {#snippet footer()}
                {#key itemCount}
                    <LazyTrigger onIntersect={loader.loadMore} disabled={loader.disabled} />
                {/key}
                {#if loader.loading}
                    <div class="flex justify-center p-4">
                        <Spinner />
                    </div>
                {/if}
            {/snippet}
        </Grid>
    </div>
{/if}

<style>
    .viewport {
        overflow-y: hidden;
    }
</style>
