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
    import { useSamplesFilters } from '$lib/hooks/useSamplesFilters/useSamplesFilters';
    import { useArrowData } from './useArrowData/useArrowData';
    import { usePlotData } from './usePlotData/usePlotData';
    // import { isEqual } from 'lodash';

    const { setShowPlot } = useGlobalStorage();

    function handleClose() {
        setShowPlot(false);
    }

    const { updateSampleIds, sampleFilter } = useSamplesFilters();

    const filter = $derived({
        ...$sampleFilter,
        sample_ids: []
    });
    const embeddingsData = $derived(useEmbeddings(filter));

    const categoryColors = ['#9CA3AF', '#2563EB', '#F59E0B'];
    const { data: arrowData, error: arrowError } = $derived(
        useArrowData({
            blobData: $embeddingsData.data as Blob
        })
    );

    let rangeSelection = $state<Point[] | null>(null);

    let { data: plotData, selectedSampleIds } = $derived(
        usePlotData({
            arrowData: $arrowData,
            rangeSelection
        })
    );

    const handleMouseUp = () => {
        if (
            $selectedSampleIds.length > 0 &&
            !isEqual($selectedSampleIds, $sampleFilter?.sample_ids || [])
        ) {
            updateSampleIds($selectedSampleIds);
        }
    };

    let plotContainer: HTMLDivElement | null = $state(null);
    let width = $state(800);
    let height = $state(600);

    $effect(() => {
        if (!plotContainer) return;

        const resizeObserver = new ResizeObserver((entries) => {
            for (const entry of entries) {
                width = entry.contentRect.width;
                height = entry.contentRect.height;
            }
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
        rangeSelection = null;
        updateSampleIds([]);
    };

    const onRangeSelection = (selection: RangeSelection) => {
        // we clear selection
        if (!selection && rangeSelection) {
            clearSelection();
            return;
        }
        rangeSelection = isRectangleSelection(selection)
            ? getPolygonFromRectangle(selection)
            : selection;
    };

    let viewportState: ViewportState | null = $state(null);
    const onViewportState = (state: ViewportState) => {
        viewportState = state;
    };

    const errorText = $derived.by(() => {
        if ($embeddingsData.isError) {
            return $embeddingsData.error.error;
        }
        if ($arrowError) {
            return $arrowError;
        }
        return null;
    });
</script>

<div class="flex flex-1 flex-col rounded-[1vw] bg-card p-4" data-testid="plot-panel">
    <div class="mb-5 mt-2 flex items-center justify-between">
        <div class="text-lg font-semibold">Embedding Plot</div>
        <Button variant="ghost" size="icon" onclick={handleClose} class="h-8 w-8">✕</Button>
    </div>
    <div class="flex flex-1 flex-col space-y-6">
        {#if $embeddingsData.isLoading}
            <div class="flex items-center justify-center p-8">
                <div class="text-lg">Loading embeddings data...</div>
            </div>
        {:else if errorText}
            <div class="flex items-center justify-center p-8 text-red-500">
                <div class="text-lg">Error loading embeddings: {errorText}</div>
            </div>
        {:else if isReady}
            <div class="min-h-0 flex-1" bind:this={plotContainer}>
                {#if $plotData}
                    <EmbeddingView
                        class="h-full w-full"
                        config={{ colorScheme: 'dark', autoLabelEnabled: false }}
                        {width}
                        {height}
                        data={$plotData}
                        {categoryColors}
                        tooltip={null}
                        theme={{
                            brandingLink: null
                        }}
                        {onRangeSelection}
                        {onViewportState}
                        {viewportState}
                        {rangeSelection}
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
        <div class="mt-1 flex items-center gap-4 text-sm text-muted-foreground">
            <span class="flex items-center gap-2">
                <span class="legend-dot" style={`background-color: ${categoryColors[0]}`}></span>
                All
            </span>
            <span class="flex items-center gap-2">
                <span class="legend-dot" style={`background-color: ${categoryColors[1]}`}></span>
                Filtered
            </span>
            <span class="flex items-center gap-2">
                <span class="legend-dot" style={`background-color: ${categoryColors[2]}`}></span>
                Selected
            </span>
            <Button variant="outline" size="sm" onclick={reset}>Reset view</Button>
            <Button variant="outline" size="sm" onclick={clearSelection} disabled={!rangeSelection}
                >Reset selection</Button
            >
        </div>
    {/if}
</div>

<svelte:window onmouseup={handleMouseUp} />

<style>
    .legend-dot {
        display: inline-block;
        height: 0.75rem;
        width: 0.75rem;
        border-radius: 9999px;
    }
</style>
