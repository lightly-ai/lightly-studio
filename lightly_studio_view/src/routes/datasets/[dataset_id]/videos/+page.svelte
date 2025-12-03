<script lang="ts">
    import { ImageSizeControl, LazyTrigger, Spinner, SelectableBox } from '$lib/components';
    import Separator from '$lib/components/ui/separator/separator.svelte';
    import { useVideos } from '$lib/hooks/useVideos/useVideos';
    import { page } from '$app/stores';
    import { Grid } from 'svelte-virtual';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import VideoItem from '$lib/components/VideoItem/VideoItem.svelte';
    import {
        createMetadataFilters,
        useMetadataFilters
    } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import type { VideoFilter } from '$lib/api/lightly_studio_local';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import type { SampleView } from '$lib/api/lightly_studio_local';
    const { tagsSelected } = useTags({
        dataset_id: $page.params.dataset_id,
        kind: ['sample']
        });
    import { useVideoBounds } from '$lib/hooks/useVideosBounds/useVideosBounds';

    const { data: propsData } = $props();
    const { metadataValues } = useMetadataFilters();
    const selectedAnnotationsFilterIds = $derived(propsData.selectedAnnotationFilterIds);
    const { videoBoundsValues } = useVideoBounds();
    const filter: VideoFilter = $derived({
        sample: {
            metadata_filters: metadataValues ? createMetadataFilters($metadataValues) : undefined
            tag_ids: $tagsSelected.size > 0 ? Array.from($tagsSelected) : undefined
        },
        annotation_frames_label_ids: $selectedAnnotationsFilterIds,
        ...$videoBoundsValues
    });
    const { data, query, loadMore } = $derived(useVideos($page.params.dataset_id, filter));
    const { sampleSize, selectedSampleIds, toggleSampleSelection } = useGlobalStorage();

    const GRID_GAP = 16;
    let viewport: HTMLElement | null = $state(null);
    let clientWidth = $state(0);

    let items = $derived($data);

    const itemSize = $derived.by(() => {
        if (viewport == null || viewport.clientWidth === 0) {
            return 0;
        }
        return viewport.clientWidth / $sampleSize.width;
    });
    const videoSize = $derived(itemSize - GRID_GAP);

    function handleOnClick(event: MouseEvent) {
        const sampleId = (event.currentTarget as HTMLElement).dataset.sampleId!;
        toggleSampleSelection(sampleId);
    }


    function handleKeyDown(event: KeyboardEvent) {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            const sampleId = (event.currentTarget as HTMLElement).dataset.sampleId!;
            toggleSampleSelection(sampleId);
        }
    }
</script>

<div class="flex flex-1 flex-col space-y-4">
    <div class="my-2 flex items-center space-x-4">
        <div class="flex-1">
            <div class="text-2xl font-semibold">Videos</div>
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
                <div>Loading videos...</div>
            </div>
        {:else if $query.isSuccess && items.length == 0}
            <div class="flex h-full w-full items-center justify-center">
                <div class="text-center text-muted-foreground">
                    <div class="mb-2 text-lg font-medium">No videos found</div>
                    <div class="text-sm">This dataset doesn't contain any videos.</div>
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
                overScan={20}
            >
                {#snippet item({ index, style })}
                    {#if items[index]}
                        {#key items[index].sample_id}
                         <div
                            class="relative"
                            class:video-selected={$selectedSampleIds.has(items[index].sample_id)}
                            {style}
                            data-testid="video-grid-item"
                            data-sample-id={items[index].sample_id}
                            data-dataset-id={(items[index].sample as SampleView).dataset_id}
                            data-video-name={items[index].file_name}
                            data-index={index}
                            onclick={handleOnClick}
                            onkeydown={handleKeyDown}
                            aria-label={`View video: ${items[index].file_name}`}
                            role="button"
                            tabindex="0"
                        >
                            <div class="absolute right-7 top-1 z-10">
                                <SelectableBox
                                    onSelect={() => undefined}
                                    isSelected={$selectedSampleIds.has(items[index].sample_id)}
                                />
                            </div>

                            <div
                                class="relative overflow-hidden rounded-lg"
                                style="width: var(--sample-width); height: var(--sample-height);"
                            >
                                <VideoItem video={items[index]} size={videoSize} />
                            </div>
                        </div>
                        {/key}
                    {/if}
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

<style>
    .video-selected {
        outline: drop-shadow(1px 1px 1px hsl(var(--primary)))
            drop-shadow(1px -1px 1px hsl(var(--primary)))
            drop-shadow(-1px -1px 1px hsl(var(--primary)))
            drop-shadow(-1px 1px 1px hsl(var(--primary)));
    }
</style>
