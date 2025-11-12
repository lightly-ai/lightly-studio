<script lang="ts">
    import { LazyTrigger, SampleAnnotations, SampleImage, SelectableBox } from '$lib/components';
    import Spinner from '$lib/components/Spinner/Spinner.svelte';
    import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';
    import { type TextEmbedding, useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import { useSettings } from '$lib/hooks/useSettings';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import { routeHelpers } from '$lib/routes';
    import type { DimensionBounds } from '$lib/services/loadDimensionBounds';
    import { onMount } from 'svelte';
    import { Grid } from 'svelte-virtual';
    import type { Readable } from 'svelte/store';
    import {
        useSamplesInfinite,
        type SamplesInfiniteParams
    } from '$lib/hooks/useSamplesInfinite/useSamplesInfinite';
    import { useScrollRestoration } from '$lib/hooks/useScrollRestoration/useScrollRestoration';
    import { useSamplesFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import type { ImageView } from '$lib/api/lightly_studio_local';
    import { goto } from '$app/navigation';
    import _ from 'lodash';

    // Import the settings hook
    const { gridViewSampleRenderingStore, showSampleFilenamesStore } = useSettings();

    type SamplesProps = {
        dataset_id: string;
        selectedAnnotationFilterIds: Readable<string[]>;
        dimensions: Readable<DimensionBounds>;
        sampleWidth: number;
        textEmbedding: Readable<TextEmbedding>;
    };
    const { dataset_id, selectedAnnotationFilterIds, sampleWidth, textEmbedding }: SamplesProps =
        $props();

    const { tagsSelected } = useTags({
        dataset_id,
        kind: ['sample']
    });

    const { dimensionsValues: dimensions } = useDimensions();
    const { metadataValues } = useMetadataFilters(dataset_id);

    const { selectedSampleIds, toggleSampleSelection, getDatasetVersion, setfilteredSampleCount } =
        useGlobalStorage();
    let clientWidth = $state(0);

    const samplesParams = $derived({
        dataset_id,
        mode: 'normal' as const,
        filters: {
            annotation_label_ids: $selectedAnnotationFilterIds?.length
                ? $selectedAnnotationFilterIds
                : undefined,
            tag_ids: $tagsSelected.size > 0 ? Array.from($tagsSelected) : undefined,
            dimensions: $dimensions
        },
        metadata_values: $metadataValues,
        text_embedding: $textEmbedding?.embedding
    });

    const paramsWithoutSampleIds = (params: SamplesInfiniteParams) => {
        return {
            ...params,
            filters: params.filters ? _.omit(params.filters, ['sample_ids']) : undefined
        };
    };

    const { filterParams, updateFilterParams } = useSamplesFilters();

    $effect(() => {
        // Synchronize the global filter parameters with the local samples parameters
        const baseParams = samplesParams as SamplesInfiniteParams;
        const currentParams = $filterParams;

        // Compare parameters excluding sample_ids to detect if other filters have changed
        if (
            currentParams &&
            _.isEqual(paramsWithoutSampleIds(baseParams), paramsWithoutSampleIds(currentParams))
        ) {
            return;
        }

        // Start with the base parameters from the component
        let nextParams = baseParams;

        // Preserve existing sample_ids selection when other parameters change
        const currentSampleIds = currentParams?.filters?.sample_ids;

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

    const { samples: infiniteSamples } = $derived(useSamplesInfinite($filterParams));
    // Derived list of samples from TanStack infinite query
    const samples: ImageView[] = $derived(
        $infiniteSamples && $infiniteSamples.data
            ? $infiniteSamples.data.pages.flatMap((page) => page.data)
            : []
    );

    let viewport: HTMLElement | null = $state(null);
    let isReady = $state(false);

    // Initialize objectFit with default and update when settings are loaded
    let objectFit = $state($gridViewSampleRenderingStore); // Use store value directly

    // Add these variables to track viewport dimensions
    let viewportHeight = $state(0);

    const { initialize, savePosition, getRestoredPosition } =
        useScrollRestoration('samples_scroll');

    onMount(async () => {
        initialize();
        // Load dataset version for caching
        await getDatasetVersion(dataset_id);

        // Get the grid view rendering mode from settings

        isReady = true;
    });

    const filterHash = $derived.by(() => {
        const parts = [
            $selectedAnnotationFilterIds.join(','),
            Array.from($tagsSelected).join(','),
            `${$dimensions.min_width}-${$dimensions.max_width}`,
            `${$dimensions.min_height}-${$dimensions.max_height}`,
            JSON.stringify($metadataValues),
            $textEmbedding?.queryText || ''
        ];

        return parts.filter(Boolean).join('|');
    });

    const initialScrollPosition = $derived(getRestoredPosition(filterHash));

    function handleScroll(event: Event) {
        const scrollTop = (event.target as HTMLElement).scrollTop;
        savePosition(scrollTop, filterHash);
    }

    // Add reactive effect to update objectFit when settings change
    $effect(() => {
        // Update objectFit whenever the grid view rendering setting changes
        objectFit = $gridViewSampleRenderingStore;
    });

    // Set total count when data is available
    $effect(() => {
        if ($infiniteSamples.isSuccess && $infiniteSamples.data?.pages.length > 0) {
            setfilteredSampleCount($infiniteSamples.data.pages[0].total_count);
        }
    });

    let size = $state(0);
    let sampleSize = $state(0);

    // Add a resize observer effect to update viewport dimensions
    $effect(() => {
        if (!viewport) return;
        size = clientWidth / sampleWidth;
        sampleSize = size - GridGap;
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

    function handleLoadMore() {
        if ($infiniteSamples.hasNextPage && !$infiniteSamples.isFetchingNextPage) {
            $infiniteSamples.fetchNextPage();
        }
    }

    function handleOnClick(event: MouseEvent) {
        const sampleId = (event.currentTarget as HTMLElement).dataset.sampleId!;
        toggleSampleSelection(sampleId);
    }

    function handleOnDoubleClick(event: MouseEvent) {
        const sampleId = (event.currentTarget as HTMLElement).dataset.sampleId!;
        const index = (event.currentTarget as HTMLElement).dataset.index!;

        goto(
            routeHelpers.toSample({
                sampleId,
                datasetId: dataset_id,
                sampleIndex: Number(index)
            })
        );
    }

    function handleKeyDown(event: KeyboardEvent) {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            const sampleId = (event.currentTarget as HTMLElement).dataset.sampleId!;
            toggleSampleSelection(sampleId);
        }
    }

    // Gap between grid items
    const GridGap = 16;
</script>

{#if $infiniteSamples.isPending}
    <!-- Initial loading state -->
    <div class="flex h-full w-full items-center justify-center">
        <div>Loading samples...</div>
    </div>
{:else if $infiniteSamples.isError}
    <!-- Error state -->
    <div class="flex h-full w-full items-center justify-center">
        <div class="mb-2 font-medium">Error loading samples</div>
    </div>
{:else if $infiniteSamples.isSuccess && samples.length === 0}
    <!-- Empty state -->
    <div class="flex h-full w-full items-center justify-center">
        <div class="text-center text-muted-foreground">
            <div class="mb-2 text-lg font-medium">No samples found</div>
            <div class="text-sm">This dataset doesn't contain any samples.</div>
        </div>
    </div>
{:else if isReady}
    <!-- Main content -->
    <div class="viewport flex-1" bind:this={viewport} bind:clientWidth>
        <Grid
            itemCount={samples.length}
            itemHeight={size}
            itemWidth={size}
            height={viewportHeight}
            scrollPosition={initialScrollPosition}
            onscroll={handleScroll}
            class="overflow-none overflow-y-auto dark:[color-scheme:dark]"
            style="--sample-width: {sampleSize}px; --sample-height: {sampleSize}px;"
            overScan={100}
        >
            {#snippet item({ index, style }: { index: number; style: string })}
                {#key $infiniteSamples.dataUpdatedAt}
                    {#if samples[index]}
                        {@const displayTextOnImage = $showSampleFilenamesStore
                            ? samples[index].file_name
                            : samples[index].captions?.[0]?.text}
                        <div
                            class="relative"
                            class:sample-selected={$selectedSampleIds.has(samples[index].sample_id)}
                            {style}
                            data-testid="sample-grid-item"
                            data-sample-id={samples[index].sample_id}
                            data-sample-name={samples[index].file_name}
                            data-index={index}
                            onclick={handleOnClick}
                            ondblclick={handleOnDoubleClick}
                            onkeydown={handleKeyDown}
                            aria-label={`View sample: ${samples[index].file_name}`}
                            role="button"
                            tabindex="0"
                        >
                            <div class="absolute right-7 top-1 z-10">
                                <SelectableBox
                                    onSelect={() => undefined}
                                    isSelected={$selectedSampleIds.has(samples[index].sample_id)}
                                />
                            </div>

                            <div
                                class="relative overflow-hidden rounded-lg"
                                style="width: var(--sample-width); height: var(--sample-height);"
                            >
                                <SampleImage sample={samples[index]} {objectFit} />
                                <SampleAnnotations
                                    sample={samples[index]}
                                    containerWidth={sampleSize}
                                    sampleImageObjectFit={objectFit}
                                    containerHeight={sampleSize}
                                />
                                {#if displayTextOnImage}
                                    <div
                                        class="pointer-events-none absolute inset-x-0 bottom-0 z-10 rounded-b-lg bg-black/60 px-2 py-1 text-xs font-medium text-white"
                                    >
                                        <span class="block truncate" title={displayTextOnImage}>
                                            {displayTextOnImage}
                                        </span>
                                    </div>
                                {/if}
                            </div>
                        </div>
                    {/if}
                {/key}
            {/snippet}
            {#snippet footer()}
                {#key samples.length}
                    <LazyTrigger
                        onIntersect={handleLoadMore}
                        disabled={!$infiniteSamples.hasNextPage ||
                            $infiniteSamples.isFetchingNextPage}
                    />
                {/key}
                {#if $infiniteSamples.isFetchingNextPage}
                    <div class="flex justify-center p-4">
                        <Spinner />
                    </div>
                {/if}
            {/snippet}
        </Grid>
    </div>
{:else}
    <div class="flex h-full w-full items-center justify-center" data-testid="samples-loading">
        <div>Loading...</div>
    </div>
{/if}

<style>
    .viewport {
        overflow-y: hidden;
    }

    .sample-selected {
        outline: drop-shadow(1px 1px 1px hsl(var(--primary)))
            drop-shadow(1px -1px 1px hsl(var(--primary)))
            drop-shadow(-1px -1px 1px hsl(var(--primary)))
            drop-shadow(-1px 1px 1px hsl(var(--primary)));
    }
</style>
