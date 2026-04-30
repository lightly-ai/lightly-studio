<script lang="ts">
    import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';
    import { type TextEmbedding, useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import { useSettings } from '$lib/hooks/useSettings';
    import { useSelectedAnnotationsFilter } from '$lib/hooks/useAnnotationsFilter/useAnnotationsFilter';
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
    import type {
        GetEvaluationSampleCountsResponse,
        ImageView
    } from '$lib/api/lightly_studio_local';
    import { goto } from '$app/navigation';
    import { omit, isEqual } from 'lodash-es';
    import { GridContainer } from '../GridContainer';
    import { Grid } from '../Grid';
    import { GridItem } from '../GridItem';
    import { selectRangeByAnchor } from '$lib/utils/selectRangeByAnchor';
    import { page } from '$app/state';
    import SampleImageGridItem from '../SampleImageGridItem/SampleImageGridItem.svelte';
    import { useEvaluationSampleCounts } from '$lib/hooks/useEvaluationSampleCounts/useEvaluationSampleCounts';
    import { sortSamplesByEvaluationCount } from './sortSamplesByEvaluationCount';

    // Import the settings hook
    const { gridViewSampleRenderingStore, showSampleFilenamesStore } = useSettings();

    type ImagesProps = {
        collection_id: string;
        sampleWidth: number;
        textEmbedding: Readable<TextEmbedding | undefined>;
    };
    const { collection_id, textEmbedding }: ImagesProps = $props();

    const { selectedAnnotationFilterIdsArray: selectedAnnotationFilterIds } =
        useSelectedAnnotationsFilter();

    const { tagsSelected } = useTags({
        collection_id,
        kind: ['sample']
    });

    const { dimensionsValues: dimensions } = useDimensions();
    const { metadataValues } = useMetadataFilters(collection_id);

    const {
        getCollectionVersion,
        setfilteredSampleCount,
        getSelectedSampleIds,
        toggleSampleSelection,
        sampleSize,
        activeEvaluationId,
        evaluationSampleSort
    } = useGlobalStorage();
    const columnCount = $derived($sampleSize.width);

    const samplesParams = $derived({
        collection_id,
        mode: 'normal' as const,
        filters: {
            annotation_label_ids: $selectedAnnotationFilterIds?.length
                ? $selectedAnnotationFilterIds
                : undefined,
            tag_ids: $tagsSelected.size > 0 ? Array.from($tagsSelected) : undefined,
            dimensions: $dimensions ?? undefined
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

    const { filterParams, updateFilterParams, imageQueryExpression } = useImageFilters();

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
        useImagesInfinite({
            ...$filterParams,
            collection_id: collection_id,
            query_expr: $imageQueryExpression?.query_expr
        })
    );
    // Derived list of samples from TanStack infinite query
    const samples: ImageView[] = $derived(
        $infiniteSamples && $infiniteSamples.data
            ? $infiniteSamples.data.pages.flatMap((page: { data?: ImageView[] }) => page.data ?? [])
            : []
    );
    const selectedSampleIds = getSelectedSampleIds(collection_id);
    let selectionAnchorSampleId = $state<string | null>(null);

    let isReady = $state(false);
    const sampleGridOverscan = 30;

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
            $imageQueryExpression?.query_expr_str || '',
            Array.from($tagsSelected).join(','),
            `${$dimensions?.min_width}-${$dimensions?.max_width}`,
            `${$dimensions?.min_height}-${$dimensions?.max_height}`,
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
    const evaluationSampleCountsQuery = $derived(
        useEvaluationSampleCounts({
            datasetId,
            evaluationId: $activeEvaluationId
        })
    );
    const evaluationSampleCounts = $derived(
        (($evaluationSampleCountsQuery.data as GetEvaluationSampleCountsResponse | undefined)
            ?.counts ?? {}) as Record<string, Record<string, number>>
    );
    const sortedSamples = $derived(
        sortSamplesByEvaluationCount(samples, evaluationSampleCounts, $evaluationSampleSort)
    );

    function handleOnDoubleClick(sampleId: string) {
        if (datasetId && collectionType) {
            goto(
                routeHelpers.toSample({
                    sampleId,
                    datasetId,
                    collectionType,
                    collectionId: collection_id
                })
            );
        }
    }

    function handleSampleSelect({
        sampleId,
        index,
        shiftKey
    }: {
        sampleId: string;
        index: number;
        shiftKey: boolean;
    }) {
        selectionAnchorSampleId = selectRangeByAnchor({
            sampleIdsInOrder: sortedSamples.map((sample) => sample.sample_id),
            selectedSampleIds: $selectedSampleIds,
            clickedSampleId: sampleId,
            clickedIndex: index,
            shiftKey,
            anchorSampleId: selectionAnchorSampleId,
            onSelectSample: (selectedSampleId) =>
                toggleSampleSelection(selectedSampleId, collection_id)
        });
    }

    function handleGridItemSelect(
        event: MouseEvent | KeyboardEvent,
        sampleId: string,
        index: number
    ) {
        handleSampleSelect({ sampleId, index, shiftKey: event.shiftKey });
    }

    const scrollResetKey = $derived(filterHash + ($textEmbedding?.queryText ?? ''));
</script>

<GridContainer
    message={{
        loading: 'Loading images...',
        error: 'Error loading images',
        empty: {
            title: 'No images found',
            description: "This collection doesn't contain any images."
        }
    }}
    status={{
        loading: $infiniteSamples.isPending,
        error: $infiniteSamples.isError,
        empty: $infiniteSamples.isSuccess && sortedSamples.length === 0,
        success: isReady
    }}
    loader={{
        loadMore: handleLoadMore,
        disabled: !$infiniteSamples.hasNextPage || $infiniteSamples.isFetchingNextPage,
        loading: $infiniteSamples.isFetchingNextPage
    }}
    itemCount={sortedSamples.length}
>
    {#snippet children({ footer })}
        <Grid
            itemCount={sortedSamples.length}
            {columnCount}
            overScan={sampleGridOverscan}
            onScroll={handleScroll}
            {initialScrollPosition}
            {scrollResetKey}
            gridProps={{ 'data-testid': 'images-grid', class: 'dark:[color-scheme:dark]' }}
        >
            {#snippet gridItem({ index, style, width, height })}
                {#if sortedSamples[index]}
                    {#key sortedSamples[index].sample_id}
                        {@const displayTextOnImage = $showSampleFilenamesStore
                            ? sortedSamples[index].file_name
                            : sortedSamples[index].captions?.[0]?.text}
                        <GridItem
                            {width}
                            {height}
                            {style}
                            dataSampleName={sortedSamples[index].file_name}
                            dataIndex={index}
                            dataTestId="sample-grid-item"
                            isSelected={$selectedSampleIds.has(sortedSamples[index].sample_id)}
                            ariaLabel={`View image: ${sortedSamples[index].file_name}`}
                            ondblclick={() => handleOnDoubleClick(sortedSamples[index].sample_id)}
                            onSelect={(event) =>
                                handleGridItemSelect(event, sortedSamples[index].sample_id, index)}
                        >
                            <SampleImageGridItem
                                sample={sortedSamples[index]}
                                {objectFit}
                                sampleSize={width}
                                {displayTextOnImage}
                            />
                        </GridItem>
                    {/key}
                {/if}
            {/snippet}
            {#snippet footerItem()}
                {@render footer()}
            {/snippet}
        </Grid>
    {/snippet}
</GridContainer>
