<script lang="ts">
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import Button from '$lib/components/ui/button/button.svelte';
    import {
        EmbeddingView,
        type Point,
        type Rectangle,
        type ViewportState
    } from 'embedding-atlas/svelte';
    import { useEmbeddings } from '$lib/hooks/useEmbeddings/useEmbeddings';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
    import { useAnnotationPlotSelection } from '$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForAnnotations';
    import { useArrowData } from './useArrowData/useArrowData';
    import { usePlotData } from './usePlotData/usePlotData';
    import PlotPanelLegend from './PlotPanelLegend.svelte';
    import PlotColorByPopover from './PlotColorByPopover/PlotColorByPopover.svelte';
    import { useCategoryVisibility } from './useCategoryVisibility/useCategoryVisibility';
    import { isEqual } from 'lodash-es';
    import { getCategoryColors, getCategoryCount, getLegendEntries } from './plotColorUtils';
    import {
        EXCLUDED_BY_FILTERS_CATEGORY,
        INCLUDED_BY_FILTERS_CATEGORY,
        INCLUDED_BY_FILTERS_LABEL,
        NO_CATEGORY_LABEL
    } from './plotCategories';
    import { page } from '$app/state';
    import { isAnnotationsRoute, isVideosRoute } from '$lib/routes';
    import { usePlotColorByType } from './PlotColorByPopover/usePlotColorByType/usePlotColorByType';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import { usePlotColorBy } from './usePlotColorBy/usePlotColorBy';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useSelectedAnnotationsFilter } from '$lib/hooks/useAnnotationsFilter/useAnnotationsFilter';
    import { writable } from 'svelte/store';

    let { collectionId }: { collectionId: string } = $props();
    const { setShowEmbeddingPlot, getRangeSelection, setRangeSelectionForCollection } =
        useGlobalStorage();
    const rangeSelection = getRangeSelection(collectionId);
    const setRangeSelection = (selection: Point[] | null) => {
        setRangeSelectionForCollection(collectionId, selection);
    };

    function handleClose() {
        setShowEmbeddingPlot(false);
    }

    // Detect if we're on the videos route
    const isVideos = $derived(isVideosRoute(page.route?.id ?? null));
    // Detect if we're on the annotations route
    const isAnnotations = $derived(isAnnotationsRoute(page.route?.id ?? null));

    // Use appropriate filter hook based on route
    const imageFilters = useImageFilters();
    const videoFilters = useVideoFilters();
    const { annotationPlotSampleIds, saveSampleIds: saveAnnotationPlotSampleIds } =
        useAnnotationPlotSelection();

    const updateSampleIds = $derived(
        isAnnotations
            ? saveAnnotationPlotSampleIds
            : isVideos
              ? videoFilters.updateSampleIds
              : imageFilters.updateSampleIds
    );
    const imageFilter = $derived(isVideos ? null : imageFilters.imageFilter);
    const videoFilter = $derived(isVideos ? videoFilters.videoFilter : null);
    const activeSampleIds = $derived(
        isAnnotations
            ? $annotationPlotSampleIds
            : ((isVideos ? $videoFilter : $imageFilter)?.sample_filter?.sample_ids ?? [])
    );

    // The active annotation label/tag filter, mirroring what the annotations grid applies.
    const { annotationFilter: selectedAnnotationsFilter } =
        useSelectedAnnotationsFilter(collectionId);

    // Prepare filter for embeddings API - use VideoFilter for videos, ImageFilter for images
    const filter = $derived.by(() => {
        // On the annotations route, send the active annotation label/tag filter (or an
        // empty annotations filter so all points count as included).
        if (isAnnotations) {
            return $selectedAnnotationsFilter ?? { filter_type: 'annotations' as const };
        }
        const currentFilter = isVideos ? $videoFilter : $imageFilter;
        if (!currentFilter) return null;

        if (!currentFilter.sample_filter) {
            return currentFilter;
        }

        return {
            ...currentFilter,
            sample_filter: {
                ...currentFilter.sample_filter,
                sample_ids: []
            }
        };
    });

    const { selectedColorByType } = usePlotColorByType(collectionId);
    // Annotation samples carry annotation-kind tags. Captured once at mount, like
    // collectionId above.
    const { tags } = useTags({
        collection_id: collectionId,
        kind: isAnnotationsRoute(page.route?.id ?? null) ? ['annotation'] : ['sample']
    });
    const annotationLabelsQuery = useAnnotationLabels(() => ({ collectionId }));
    const annotationLabels = writable<{ annotation_label_id: string }[]>([]);
    $effect(() => {
        annotationLabels.set(
            (annotationLabelsQuery.data ?? []).filter(
                (l): l is { annotation_label_id: string } & typeof l =>
                    l.annotation_label_id !== undefined
            )
        );
    });
    const { colorBy, selectedColorByKey, setSelectedColorByKey } = usePlotColorBy({
        selectedColorByType,
        tags,
        annotationLabels
    });

    const embeddingsData = $derived(useEmbeddings(collectionId, filter, $colorBy));

    const {
        data: arrowData,
        colorLegend,
        error: arrowError
    } = $derived(
        useArrowData({
            blobData: embeddingsData.data as Blob
        })
    );
    // Category 1 means "passes the filter but has no color value". Its label tracks the same
    // `color_by` signal that drives its color (see `getCategoryColors` below), so the two never disagree.
    const includedLabel = $derived(
        $colorBy !== null ? NO_CATEGORY_LABEL : INCLUDED_BY_FILTERS_LABEL
    );
    const {
        hiddenCategories,
        toggleCategoryVisibility,
        focusCategoryVisibility,
        resetCategoryVisibility
    } = useCategoryVisibility();

    // The backend re-ranks color slots per request, so a stale toggle would hide the wrong slot;
    // reset hidden categories on every legend change. EXCLUDED keeps its meaning, so it always
    // survives. INCLUDED is relabeled with the color-by mode, so it survives only a filter-only
    // change — else a hidden "No category" would empty the plot once all points collapse into it.
    let previousColorByKey: string | undefined = undefined;
    $effect(() => {
        void $colorLegend;
        const colorByKey = JSON.stringify($colorBy);
        const colorByChanged = colorByKey !== previousColorByKey;
        previousColorByKey = colorByKey;
        resetCategoryVisibility(
            colorByChanged
                ? [EXCLUDED_BY_FILTERS_CATEGORY]
                : [EXCLUDED_BY_FILTERS_CATEGORY, INCLUDED_BY_FILTERS_CATEGORY]
        );
    });

    const hasActiveFilter = $derived(filter !== null || activeSampleIds.length > 0);

    // Activating a lasso unhides the Excluded category, otherwise out-of-selection points (which
    // get demoted to Excluded) would vanish and blank out the canvas mid-draw. The legend keeps
    // showing the user's real toggle state.
    const effectiveHiddenCategories = $derived.by(() => {
        if ($rangeSelection === null || !$hiddenCategories.has(EXCLUDED_BY_FILTERS_CATEGORY)) {
            return $hiddenCategories;
        }
        const next = new Set($hiddenCategories);
        next.delete(EXCLUDED_BY_FILTERS_CATEGORY);
        return next;
    });

    let { data: plotData, selectedSampleIds } = $derived(
        usePlotData({
            arrowData: $arrowData,
            rangeSelection: $rangeSelection,
            highlightedSampleIds: activeSampleIds,
            hasActiveFilter: hasActiveFilter,
            hiddenCategories: effectiveHiddenCategories
        })
    );
    const categoryCount = $derived.by(() => getCategoryCount($colorLegend));
    const useLabelColors = $derived($selectedColorByType === 'annotation_label');
    const categoryColors = $derived.by(() =>
        getCategoryColors($colorLegend, useLabelColors, $colorBy !== null)
    );
    const legendEntries = $derived.by(() =>
        getLegendEntries($colorLegend, $hiddenCategories, useLabelColors)
    );
    const handleMouseUp = () => {
        const hadRangeSelection = $rangeSelection !== null;
        if (!hadRangeSelection) {
            return;
        }

        const currentSampleIds = isAnnotations
            ? $annotationPlotSampleIds
            : ((isVideos ? $videoFilter : $imageFilter)?.sample_filter?.sample_ids ?? []);
        const selectableCount =
            ($arrowData?.fulfils_filter as Uint8Array | undefined)?.reduce((count, fulfils) => {
                return fulfils !== 0 ? count + 1 : count;
            }, 0) ?? null;

        if ($selectedSampleIds.length === 0) {
            if (currentSampleIds.length > 0) {
                updateSampleIds([]);
            }
            setRangeSelection(null);
            return;
        }

        if (selectableCount !== null && $selectedSampleIds.length === selectableCount) {
            if (currentSampleIds.length > 0) {
                updateSampleIds([]);
            }
            setRangeSelection(null);
            return;
        }

        if (!isEqual($selectedSampleIds, currentSampleIds)) {
            updateSampleIds($selectedSampleIds);
        }
        setRangeSelection(null);
    };

    let plotContainer: HTMLDivElement | null = $state(null);
    let width = $state(0);
    let height = $state(0);

    // Require at least 50px in each dimension to avoid unstable first-frame canvas rendering.
    const MIN_RENDER_SIZE = 50;
    const embeddingConfig = {
        colorScheme: 'dark',
        autoLabelEnabled: false
    } as const;
    const embeddingTheme = {
        brandingLink: null
    } as const;

    const setPlotSize = (nextWidth: number, nextHeight: number) => {
        const normalizedWidth = Math.max(0, Math.floor(nextWidth));
        const normalizedHeight = Math.max(0, Math.floor(nextHeight));

        // Ignore transient zero-size measurements while pane layout settles.
        if (normalizedWidth === 0 || normalizedHeight === 0) return;
        if (normalizedWidth === width && normalizedHeight === height) return;

        width = normalizedWidth;
        height = normalizedHeight;
    };

    $effect(() => {
        if (!plotContainer) return;

        const { width: containerWidth, height: containerHeight } =
            plotContainer.getBoundingClientRect();
        setPlotSize(containerWidth, containerHeight);

        const resizeObserver = new ResizeObserver((entries) => {
            const [entry] = entries;
            if (!entry) return;

            setPlotSize(entry.contentRect.width, entry.contentRect.height);
        });

        resizeObserver.observe(plotContainer);

        return () => {
            resizeObserver.disconnect();
        };
    });

    const reset = () => {
        viewportState = null;
    };

    const isReady = true;

    type RangeSelection = Rectangle | Point[] | null;

    const isRectangleSelection = (selection: RangeSelection): selection is Rectangle => {
        return selection !== null && !Array.isArray(selection);
    };

    const getPolygonFromRectangle = (rect: Rectangle) => {
        return [
            { x: rect.xMin, y: rect.yMin },
            { x: rect.xMax, y: rect.yMin },
            { x: rect.xMax, y: rect.yMax },
            { x: rect.xMin, y: rect.yMax }
        ];
    };

    const clearSelection = () => {
        setRangeSelection(null);
        updateSampleIds([]);
    };
    const hasActiveSelection = $derived($rangeSelection !== null || activeSampleIds.length > 0);

    const onWindowKeyDown = (event: KeyboardEvent) => {
        if (event.key !== 'Escape') {
            return;
        }
        if (!hasActiveSelection) {
            return;
        }
        clearSelection();
    };

    const onRangeSelection = (selection: RangeSelection) => {
        // we clear selection
        if (!selection && $rangeSelection) {
            clearSelection();
            return;
        }
        const normalizedSelection = isRectangleSelection(selection)
            ? getPolygonFromRectangle(selection)
            : selection;
        setRangeSelection(normalizedSelection);
    };

    let viewportState: ViewportState | null = $state(null);
    const onViewportState = (state: ViewportState) => {
        viewportState = state;
    };

    const errorText = $derived.by(() => {
        if (embeddingsData.isError) {
            return embeddingsData.error?.message ?? 'Unknown error';
        }
        if ($arrowError) {
            return $arrowError;
        }
        return null;
    });
</script>

<div class="flex min-h-0 flex-1 flex-col rounded-[1vw] bg-card p-4" data-testid="plot-panel">
    <div class="mb-5 mt-2 flex items-center justify-between">
        <div class="text-lg font-semibold">Embedding Plot</div>
        <Button
            variant="ghost"
            size="icon"
            onclick={handleClose}
            class="h-8 w-8"
            data-testid="plot-close-button"
        >
            ✕
        </Button>
    </div>
    <div class="flex min-h-0 flex-1 flex-col space-y-6">
        {#if embeddingsData.isLoading}
            <div class="flex items-center justify-center p-8">
                <div class="text-lg">Loading embeddings data...</div>
            </div>
        {:else if errorText}
            <div class="flex items-center justify-center p-8 text-red-500">
                <div class="text-lg">Error loading embeddings: {errorText}</div>
            </div>
        {:else if isReady}
            <div
                class="embedding-plot-wrapper relative min-h-0 flex-1 overflow-hidden bg-black"
                bind:this={plotContainer}
            >
                {#if $plotData && width >= MIN_RENDER_SIZE && height >= MIN_RENDER_SIZE}
                    <div class="embedding-view h-full w-full">
                        <EmbeddingView
                            config={embeddingConfig}
                            {width}
                            {height}
                            {categoryCount}
                            data={$plotData}
                            {categoryColors}
                            tooltip={null}
                            theme={embeddingTheme}
                            {onRangeSelection}
                            {onViewportState}
                            {viewportState}
                            rangeSelection={$rangeSelection}
                        />
                    </div>

                    <PlotPanelLegend
                        {categoryColors}
                        {includedLabel}
                        {legendEntries}
                        excludedHidden={$hiddenCategories.has(EXCLUDED_BY_FILTERS_CATEGORY)}
                        includedHidden={$hiddenCategories.has(INCLUDED_BY_FILTERS_CATEGORY)}
                        onToggleCategory={toggleCategoryVisibility}
                        onDoubleClickCategory={(category) => {
                            focusCategoryVisibility(
                                legendEntries.map((entry) => entry.cat),
                                category
                            );
                        }}
                    />
                {/if}
            </div>
        {:else}
            <div class="flex items-center justify-center p-8">
                <div class="text-lg">No data available</div>
            </div>
        {/if}
    </div>
    {#if isReady}
        <div
            class="mt-1 flex min-w-0 shrink-0 items-center justify-end gap-2 overflow-x-auto text-sm text-muted-foreground"
            data-testid="plot-panel-controls"
        >
            <PlotColorByPopover
                {collectionId}
                withTags={$tags.length > 0}
                withAnnotationLabels={$annotationLabels.length > 0}
                selectedKey={$selectedColorByKey}
                onSelectedKeyChange={(key) => {
                    setSelectedColorByKey(key);
                }}
            />
            <Button
                variant="outline"
                size="sm"
                onclick={reset}
                data-testid="plot-reset-zoom-button"
                class="px-2.5"
                title="Reset zoom"
            >
                Reset zoom
            </Button>
        </div>
    {/if}
</div>

<svelte:window onmouseup={handleMouseUp} onkeydown={onWindowKeyDown} />

<style>
    :global(.embedding-view button) {
        width: 20px !important;
        height: 20px !important;
    }
    :global(.embedding-view button svg) {
        width: 18px !important;
        height: 18px !important;
    }
    :global(.embedding-view div[style*='bottom: 0px'][style*='position: absolute']) {
        font-size: 15px !important;
        height: 25px !important;
        line-height: 25px !important;
    }
    /* Hide the library's status message slot (e.g. "WebGPU is unavailable. Falling back
       to WebGL.") while keeping the selection tools, scale, and point count visible. */
    :global(
        .embedding-view div[style*='bottom: 0px'][style*='position: absolute'] > div:first-child
    ) {
        display: none !important;
    }
</style>
