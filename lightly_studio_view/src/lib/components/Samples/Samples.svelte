<script lang="ts">
    import { SampleAnnotations, SampleImage } from '$lib/components';
    import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';
    import { type TextEmbedding, useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import { useSettings } from '$lib/hooks/useSettings';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import { routeHelpers } from '$lib/routes';
    import { onMount } from 'svelte';
    import type { Readable } from 'svelte/store';
    import {
        isNormalModeParams,
        useImagesInfinite,
        type ImagesInfiniteParams
    } from '$lib/hooks/useImagesInfinite/useImagesInfinite';
    import { useScrollRestoration } from '$lib/hooks/useScrollRestoration/useScrollRestoration';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import type { ImageView } from '$lib/api/lightly_studio_local';
    import { goto } from '$app/navigation';
    import { omit, isEqual } from 'lodash-es';
    import SampleGrid from '../SampleGrid/SampleGrid.svelte';
    import SampleGridItem from '../SampleGridItem/SampleGridItem.svelte';
    import { getSimilarityColor } from '$lib/utils';
    import { page } from '$app/state';

    // Import the settings hook
    const { gridViewSampleRenderingStore, showSampleFilenamesStore } = useSettings();

    type SamplesProps = {
        collection_id: string;
        selectedAnnotationFilterIds: Readable<string[]>;
        sampleWidth: number;
        textEmbedding: Readable<TextEmbedding | undefined>;
    };
    const { collection_id, selectedAnnotationFilterIds, textEmbedding }: SamplesProps = $props();

    const { tagsSelected } = useTags({
        collection_id,
        kind: ['sample']
    });

    const { dimensionsBounds, dimensionsValues } = useDimensions();
    const { metadataValues } = useMetadataFilters(collection_id);

    const { getCollectionVersion, setfilteredSampleCount } = useGlobalStorage();

    const dimensionsFilter = $derived.by(() => {
        const bounds = $dimensionsBounds;
        const values = $dimensionsValues;

        // If bounds are not initialized yet, don't send a dimensions filter.
        if (
            bounds == null ||
            (bounds.min_width === 0 &&
                bounds.max_width === 0 &&
                bounds.min_height === 0 &&
                bounds.max_height === 0)
        ) {
            return undefined;
        }

        const isWidthUnchanged =
            values.min_width === bounds.min_width && values.max_width === bounds.max_width;
        const isHeightUnchanged =
            values.min_height === bounds.min_height && values.max_height === bounds.max_height;

        // Only apply dimensions when at least one slider differs from the default bounds.
        if (isWidthUnchanged && isHeightUnchanged) {
            return undefined;
        }

        return values;
    });

    const samplesParams = $derived({
        collection_id,
        mode: 'normal' as const,
        filters: {
            annotation_label_ids: $selectedAnnotationFilterIds?.length
                ? $selectedAnnotationFilterIds
                : undefined,
            tag_ids: $tagsSelected.size > 0 ? Array.from($tagsSelected) : undefined,
            dimensions: dimensionsFilter
        },
        metadata_values: $metadataValues,
        text_embedding: $textEmbedding?.embedding
    });

    const paramsWithoutSampleIds = (params: ImagesInfiniteParams) => {
        return {
            ...params,
            filters: isNormalModeParams(params) ? omit(params.filters, ['sample_ids']) : undefined
        };
    };

    const { filterParams, updateFilterParams } = useImageFilters();

    $effect(() => {
        // Synchronize the global filter parameters with the local samples parameters
        const baseParams = samplesParams as ImagesInfiniteParams;
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
        if (isNormalModeParams(currentParams) && currentParams.filters?.sample_ids) {
            currentSampleIds = currentParams.filters.sample_ids;
        }

        // Merge the existing sample selection into the new parameters
        if (currentSampleIds && currentSampleIds.length > 0 && isNormalModeParams(nextParams)) {
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

    const { samples: infiniteSamples } = $derived(
        useImagesInfinite({ ...$filterParams, collection_id: collection_id })
    );
    // Derived list of samples from TanStack infinite query
    const samples: ImageView[] = $derived(
        $infiniteSamples && $infiniteSamples.data
            ? $infiniteSamples.data.pages.flatMap((page: { data?: ImageView[] }) => page.data ?? [])
            : []
    );

    let isReady = $state(false);

    // Initialize objectFit with default and update when settings are loaded
    let objectFit = $state($gridViewSampleRenderingStore); // Use store value directly

    const { initialize, savePosition, getRestoredPosition } =
        useScrollRestoration('samples_scroll');

    onMount(async () => {
        initialize();
        // Load collection version for caching
        await getCollectionVersion(collection_id);

        // Get the grid view rendering mode from settings

        isReady = true;
    });

    const filterHash = $derived.by(() => {
        const parts = [
            $selectedAnnotationFilterIds.join(','),
            Array.from($tagsSelected).join(','),
            `${$dimensionsValues.min_width}-${$dimensionsValues.max_width}`,
            `${$dimensionsValues.min_height}-${$dimensionsValues.max_height}`,
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

    function handleLoadMore() {
        if ($infiniteSamples.hasNextPage && !$infiniteSamples.isFetchingNextPage) {
            $infiniteSamples.fetchNextPage();
        }
    }

    const datasetId = $derived(page.params.dataset_id!);
    const collectionType = $derived(page.params.collection_type!);

    function handleOnDoubleClick(event: MouseEvent) {
        const sampleId = (event.currentTarget as HTMLElement).dataset.sampleId!;
        const index = (event.currentTarget as HTMLElement).dataset.index!;

        if (datasetId && collectionType) {
            goto(
                routeHelpers.toSample({
                    sampleId,
                    datasetId,
                    collectionType,
                    collectionId: collection_id,
                    sampleIndex: Number(index)
                })
            );
        }
    }
</script>

<SampleGrid
    itemCount={samples.length}
    overScan={100}
    scrollPosition={initialScrollPosition}
    onScroll={handleScroll}
    message={{
        loading: 'Loading samples...',
        error: 'Error loading samples',
        empty: {
            title: 'No samples found',
            description: "This collection doesn't contain any samples."
        }
    }}
    status={{
        loading: $infiniteSamples.isPending,
        error: $infiniteSamples.isError,
        empty: $infiniteSamples.isSuccess && samples.length === 0,
        success: isReady
    }}
    loader={{
        loadMore: handleLoadMore,
        disabled: !$infiniteSamples.hasNextPage || $infiniteSamples.isFetchingNextPage,
        loading: $infiniteSamples.isFetchingNextPage
    }}
>
    {#snippet gridItem({ index, style, sampleSize })}
        {#key $infiniteSamples.dataUpdatedAt}
            {#if samples[index]}
                {@const displayTextOnImage = $showSampleFilenamesStore
                    ? samples[index].file_name
                    : samples[index].captions?.[0]?.text}
                <SampleGridItem
                    {style}
                    {index}
                    dataTestId="sample-grid-item"
                    collectionId={collection_id}
                    sampleId={samples[index].sample_id}
                    dataSampleName={samples[index].file_name}
                    ondblclick={handleOnDoubleClick}
                >
                    {#snippet item()}
                        <SampleImage sample={samples[index]} {objectFit} />
                        <SampleAnnotations
                            sample={samples[index]}
                            containerWidth={sampleSize}
                            sampleImageObjectFit={objectFit}
                            containerHeight={sampleSize}
                        />
                        {#if samples[index].similarity_score !== undefined && samples[index].similarity_score !== null}
                            <div
                                class="absolute right-1 z-10 flex items-center rounded bg-black/60 px-1.5 py-0.5 text-xs font-medium text-white backdrop-blur-sm {displayTextOnImage
                                    ? 'bottom-8'
                                    : 'bottom-1'}"
                            >
                                <span
                                    class="mr-1.5 block h-2 w-2 rounded-full"
                                    style="background-color: {getSimilarityColor(
                                        samples[index].similarity_score
                                    )}"
                                ></span>
                                {samples[index].similarity_score.toFixed(2)}
                            </div>
                        {/if}
                        {#if displayTextOnImage}
                            <div
                                class="pointer-events-none absolute inset-x-0 bottom-0 z-10 rounded-b-lg bg-black/60 px-2 py-1 text-xs font-medium text-white"
                            >
                                <span class="block truncate" title={displayTextOnImage}>
                                    {displayTextOnImage}
                                </span>
                            </div>
                        {/if}
                    {/snippet}
                </SampleGridItem>
            {/if}
        {/key}
    {/snippet}
</SampleGrid>
