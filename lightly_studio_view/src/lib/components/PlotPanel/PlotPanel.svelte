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
    import { useArrowData } from './useArrowData/useArrowData';
    import { usePlotData } from './usePlotData/usePlotData';
    import PlotPanelLegend from './PlotPanelLegend.svelte';
    import { isEqual } from 'lodash-es';
    import { page } from '$app/state';
    import { isVideosRoute } from '$lib/routes';

    const collectionId = page.params.collection_id;
    const { setShowPlot, getRangeSelection, setRangeSelectionForcollection } = useGlobalStorage();
    const rangeSelection = getRangeSelection(collectionId);
    const setRangeSelection = (selection: Point[] | null) => {
        setRangeSelectionForcollection(collectionId, selection);
    };

    function handleClose() {
        setShowPlot(false);
    }

    // Detect if we're on the videos route
    const isVideos = $derived(isVideosRoute(page.route?.id ?? null));

    // Use appropriate filter hook based on route
    const imageFilters = useImageFilters();
    const videoFilters = useVideoFilters();

    const updateSampleIds = $derived(
        isVideos ? videoFilters.updateSampleIds : imageFilters.updateSampleIds
    );
    const imageFilter = $derived(isVideos ? null : imageFilters.imageFilter);
    const videoFilter = $derived(isVideos ? videoFilters.videoFilter : null);

    // Prepare filter for embeddings API - use VideoFilter for videos, ImageFilter for images
    const filter = $derived.by(() => {
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

    const embeddingsData = $derived(useEmbeddings(filter));

    const categoryColors = ['#9CA3AF', '#2563EB', '#F59E0B'];
    const { data: arrowData, error: arrowError } = $derived(
        useArrowData({
            blobData: $embeddingsData.data as Blob
        })
    );

    let { data: plotData, selectedSampleIds } = $derived(
        usePlotData({
            arrowData: $arrowData,
            rangeSelection: $rangeSelection
        })
    );
    const handleMouseUp = () => {
        if ($selectedSampleIds.length === 0) return;

        const filter = isVideos ? $videoFilter : $imageFilter;
        const currentSampleIds = filter?.sample_filter?.sample_ids || [];

        if (!isEqual($selectedSampleIds, currentSampleIds)) {
            updateSampleIds($selectedSampleIds);
        }
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
        if ($embeddingsData.isError) {
            return $embeddingsData.error?.message ?? 'Unknown error';
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
        <Button variant="ghost" size="icon" onclick={handleClose} class="h-8 w-8">✕</Button>
    </div>
    <div class="flex min-h-0 flex-1 flex-col space-y-6">
        {#if $embeddingsData.isLoading}
            <div class="flex items-center justify-center p-8">
                <div class="text-lg">Loading embeddings data...</div>
            </div>
        {:else if errorText}
            <div class="flex items-center justify-center p-8 text-red-500">
                <div class="text-lg">Error loading embeddings: {errorText}</div>
            </div>
        {:else if isReady}
            <div class="relative min-h-0 flex-1 overflow-hidden bg-black" bind:this={plotContainer}>
                {#if $plotData && width >= MIN_RENDER_SIZE && height >= MIN_RENDER_SIZE}
                    <EmbeddingView
                        class="h-full w-full"
                        config={embeddingConfig}
                        {width}
                        {height}
                        data={$plotData}
                        {categoryColors}
                        tooltip={null}
                        theme={embeddingTheme}
                        {onRangeSelection}
                        {onViewportState}
                        {viewportState}
                        rangeSelection={$rangeSelection}
                    />
                    <PlotPanelLegend {categoryColors} />
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
            <Button
                variant="outline"
                size="sm"
                onclick={clearSelection}
                disabled={!$rangeSelection}
                data-testid="plot-reset-selection-button"
                class="px-2.5"
                title="Clear selection">Clear selection</Button
            >
        </div>
    {/if}
</div>

<svelte:window onmouseup={handleMouseUp} />
