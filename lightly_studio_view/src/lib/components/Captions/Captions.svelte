<script lang="ts">
    import { List } from 'svelte-virtual';
    import { readCollectionOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
    import { createQuery } from '@tanstack/svelte-query';

    import {
        useSamplesInfinite,
        useGlobalStorage,
        useTags,
        createMetadataFilters,
        useMetadataFilters
    } from '$lib/hooks';
    import {
        LazyTrigger,
        Spinner,
        GridHeader,
        Separator,
        CaptionsItem,
        ShowFiltersButton
    } from '$lib/components';

    const {
        collectionId
    }: {
        collectionId: string;
    } = $props();

    // Fetch collection details to get parent_collection_id
    const collectionQuery = createQuery(() =>
        readCollectionOptions({
            path: { collection_id: collectionId }
        })
    );

    // Determine the parent collection ID to use for fetching samples
    const parentCollectionId = $derived.by(() => {
        const collection = collectionQuery.data;
        if (!collection) return collectionId; // Fallback to collectionId while loading
        // If no parent_collection_id, use the current collection_id
        if (!collection.parent_collection_id) {
            return collection.collection_id;
        }
        return collection.parent_collection_id;
    });

    // Tags and metadata filters are kept per parent collection, so they match the images tab.
    const { tagsSelected } = $derived(useTags({ collection_id: parentCollectionId }));
    const { metadataValues, categoricalMetadataValues } = $derived(
        useMetadataFilters(parentCollectionId)
    );

    const { data, query, loadMore, refresh } = useSamplesInfinite(() => ({
        path: { collection_id: parentCollectionId },
        body: {
            filters: {
                has_captions: true,
                tag_ids: $tagsSelected.size > 0 ? Array.from($tagsSelected) : undefined,
                metadata_filters: createMetadataFilters($metadataValues, $categoricalMetadataValues)
            }
        }
    }));

    let viewport: HTMLElement | null = $state(null);

    const { sampleSize, setfilteredSampleCount, setfilteredCaptionCount, filterPanelCollapsed } =
        useGlobalStorage();

    $effect(() => {
        if (query.isSuccess && query.data?.pages.length > 0) {
            setfilteredSampleCount(query.data.pages[0].total_count);
            setfilteredCaptionCount(query.data.pages[0].total_caption_count);
        }
    });
    let viewportHeight = $state(0);

    // Add a resize observer effect to update viewport dimensions
    $effect(() => {
        if (!viewport) return;
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
    const GridGap = 8;
    const innerCardMargin = 32;
    // The zoom control sets 1 to 16 columns. Thumbnails use fixed pixel sizes (96px at 16 columns,
    // +16px per step down to 1 column), so they do not change when the filter panel resizes the grid.
    const thumbnailSide = $derived(96 + (16 - $sampleSize.width) * 16);
    // Rows never go below 120px, so the caption text stays readable on small thumbnails.
    const minRowHeight = 120;
    const rowHeight = $derived(Math.max(minRowHeight, thumbnailSide + innerCardMargin));
    let activeDraftSampleId = $state<string | null>(null);

    const height = $derived(viewportHeight + GridGap);

    const onCreatingCaptionChange = (sampleId: string, isOpen: boolean) => {
        if (isOpen) {
            activeDraftSampleId = sampleId;
            return;
        }
        if (activeDraftSampleId === sampleId) {
            activeDraftSampleId = null;
        }
    };
</script>

<div class="flex flex-1 flex-col space-y-4">
    <!-- Same flex row as the images header, so the zoom slider lines up across both tabs. -->
    <div class="flex min-w-0 items-center gap-x-4">
        {#if $filterPanelCollapsed}
            <ShowFiltersButton />
        {/if}
        <div class="min-w-0 flex-1">
            <GridHeader />
        </div>
    </div>
    <Separator class="mb-4 bg-border-hard" />

    <div class="h-full w-full flex-1 overflow-hidden" bind:this={viewport}>
        {#if query.isPending && items.length === 0}
            <div class="flex h-full w-full items-center justify-center gap-2">
                <Spinner />
                <div>Loading samples...</div>
            </div>
        {:else if query.isSuccess && items.length > 0}
            <List
                itemCount={items.length}
                {height}
                itemSize={rowHeight + GridGap}
                class="dark:[color-scheme:dark]"
                style="--sample-width: {thumbnailSide}px; --sample-height: {thumbnailSide}px;"
            >
                {#snippet item({ index, style })}
                    {#if items[index]}
                        {#key items[index].sample_id}
                            <div
                                {style}
                                class={`w-full pb-[${GridGap}]`}
                                data-testid="caption-grid-item"
                            >
                                <CaptionsItem
                                    maxHeight={`${rowHeight}px`}
                                    item={items[index]}
                                    onUpdate={refresh}
                                    isCreatingCaption={activeDraftSampleId ===
                                        items[index].sample_id}
                                    canStartDraft={activeDraftSampleId === null ||
                                        activeDraftSampleId === items[index].sample_id}
                                    onCreatingCaptionChange={(isOpen) =>
                                        onCreatingCaptionChange(items[index].sample_id, isOpen)}
                                />
                            </div>
                        {/key}
                    {/if}
                {/snippet}
                {#snippet footer()}
                    {#key items.length}
                        <LazyTrigger
                            onIntersect={loadMore}
                            disabled={!query.hasNextPage || query.isFetchingNextPage}
                        />
                    {/key}
                    {#if query.isFetchingNextPage}
                        <div class="flex justify-center p-4">
                            <Spinner />
                        </div>
                    {/if}
                {/snippet}
            </List>
        {/if}
    </div>
</div>
