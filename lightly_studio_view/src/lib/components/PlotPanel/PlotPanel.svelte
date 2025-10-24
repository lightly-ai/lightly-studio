<script lang="ts">
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import Button from '$lib/components/ui/button/button.svelte';
    import { EmbeddingView } from 'embedding-atlas/svelte';
    import { onDestroy } from 'svelte';
    import { useEmbeddings } from '$lib/hooks/useEmbeddings/useEmbeddings';
    import { tableFromIPC } from 'apache-arrow';
    import { writable } from 'svelte/store';
    import { useSamplesFilters } from '$lib/hooks/useSamplesFilters/useSamplesFilters';
    import type { SamplesInfiniteParams } from '$lib/hooks/useSamplesInfinite/useSamplesInfinite';
    import _ from 'lodash';

    const { setShowPlot } = useGlobalStorage();

    function handleClose() {
        setShowPlot(false);
    }

    const { filterParams, sampleFilter, updateFilterParams } = useSamplesFilters();

    type LassoPoint = {
        x: number;
        y: number;
    };

    type LassoRectangle = {
        xMin: number;
        xMax: number;
        yMin: number;
        yMax: number;
    };

    type RangeSelectionShape = LassoRectangle | LassoPoint[];

    // TODO(Future PR): Extract embedding selection logic to a custom hook like `useEmbeddingSelection`
    // This would clean up PlotPanel and make the selection logic reusable
    let rangeSelection = $state<RangeSelectionShape | null>(null);
    let pendingRangeSelection = $state<RangeSelectionShape | null>(null);
    let selectionActive = false;
    let detachMouseUpListener: (() => void) | null = null;
    let ignoreNextRangeClear = false;

    const embeddings = writable({
        x: new Float32Array(),
        y: new Float32Array(),
        category: new Uint8Array(),
        sampleIds: [] as string[]
    });

    const hasPersistentSelection = $derived(
        $filterParams?.mode === 'normal' && Boolean($filterParams.filters?.sample_ids?.length)
    );

    $inspect($filterParams);

    const embeddingsData = $derived(useEmbeddings($sampleFilter ?? undefined));

    const categoryColors = ['#9CA3AF', '#2563EB'];
    const readArrowData = async (data: unknown) => {
        try {
            const buf = await (data as Blob).arrayBuffer();
            const table = await tableFromIPC(new Uint8Array(buf));
            if (!table) {
                console.error('Failed to read Arrow table from embeddings data.');
                return;
            }
            // Get column data and convert to typed arrays
            const columnDataX = table.getChild('x');
            const columnDataY = table.getChild('y');
            const columnDataFulfilled = table.getChild('fulfils_filter');
            const columnDataSampleId = table.getChild('sample_id');
            if (!columnDataX || !columnDataY || !columnDataFulfilled || !columnDataSampleId) {
                console.error('Missing required columns in Arrow data.');
                return;
            }
            const xArray = columnDataX.toArray();
            const yArray = columnDataY.toArray();
            const categoryArray = columnDataFulfilled.toArray();
            const sampleIdArray = columnDataSampleId.toArray();
            const inferredCategory = (() => {
                if (categoryArray instanceof Uint8Array) {
                    return categoryArray;
                }
                return Uint8Array.from(categoryArray as ArrayLike<number>);
            })();
            const sampleIds = Array.from(sampleIdArray as ArrayLike<unknown>, (value) =>
                value != null ? String(value) : ''
            );
            embeddings.set({
                x: new Float32Array(xArray),
                y: new Float32Array(yArray),
                category: inferredCategory,
                sampleIds
            });
        } catch (error) {
            console.error('Error reading Arrow data:', error);
        }
    };
    $effect(() => {
        if ($embeddingsData.data) {
            readArrowData($embeddingsData.data);
        }
    });

    function applySampleSelection(selectedSampleIds: string[]): boolean {
        const currentParams = $filterParams;
        if (!currentParams || currentParams.mode !== 'normal') {
            return false;
        }

        const existingSampleIds = currentParams.filters?.sample_ids ?? [];
        if (_.isEqual(existingSampleIds, selectedSampleIds)) {
            return false;
        }

        const nextFilters = {
            ...(currentParams.filters ?? {})
        };

        if (selectedSampleIds.length > 0) {
            nextFilters.sample_ids = selectedSampleIds;
        } else {
            delete nextFilters.sample_ids;
        }

        const nextParams: SamplesInfiniteParams = {
            ...currentParams,
            filters: Object.keys(nextFilters).length > 0 ? nextFilters : undefined
        };

        updateFilterParams(nextParams);
        return true;
    }

    function computeSelectedSampleIds(selection: RangeSelectionShape): string[] {
        const { x, y, sampleIds } = $embeddings;

        if (x.length === 0 || y.length === 0 || sampleIds.length === 0) {
            return [];
        }

        const matches: string[] = [];

        if (Array.isArray(selection)) {
            if (selection.length < 3) {
                return [];
            }

            for (let index = 0; index < x.length; index += 1) {
                if (isPointInPolygon(x[index], y[index], selection)) {
                    const id = sampleIds[index];
                    if (id) {
                        matches.push(id);
                    }
                }
            }

            return matches;
        }

        const { xMin, xMax, yMin, yMax } = selection;
        for (let index = 0; index < x.length; index += 1) {
            const px = x[index];
            const py = y[index];
            if (px >= xMin && px <= xMax && py >= yMin && py <= yMax) {
                const id = sampleIds[index];
                if (id) {
                    matches.push(id);
                }
            }
        }

        return matches;
    }

    function isPointInPolygon(px: number, py: number, polygon: LassoPoint[]): boolean {
        let inside = false;

        for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
            const { x: xi, y: yi } = polygon[i];
            const { x: xj, y: yj } = polygon[j];

            const denominator = yj - yi;
            const intersectionX =
                denominator !== 0 ? ((xj - xi) * (py - yi)) / denominator + xi : xi;

            const intersects = yi > py !== yj > py && px < intersectionX;

            if (intersects) {
                inside = !inside;
            }
        }

        return inside;
    }

    function resetSelection() {
        pendingRangeSelection = null;
        selectionActive = false;
        rangeSelection = null;
        ignoreNextRangeClear = true;

        if (detachMouseUpListener) {
            detachMouseUpListener();
            detachMouseUpListener = null;
        }

        applySampleSelection([]);
    }

    function finalizeRangeSelection() {
        if (!selectionActive) {
            return;
        }

        selectionActive = false;

        if (detachMouseUpListener) {
            detachMouseUpListener();
            detachMouseUpListener = null;
        }

        if (pendingRangeSelection) {
            const selectedSampleIds = computeSelectedSampleIds(pendingRangeSelection);
            applySampleSelection(selectedSampleIds);
        } else {
            applySampleSelection([]);
        }

        pendingRangeSelection = null;
        rangeSelection = null;
        ignoreNextRangeClear = true;
    }

    function handleRangeSelection(value: RangeSelectionShape | null) {
        rangeSelection = value;

        if (value === null) {
            if (selectionActive || pendingRangeSelection) {
                finalizeRangeSelection();
                return;
            }

            if (ignoreNextRangeClear) {
                ignoreNextRangeClear = false;
                return;
            }

            applySampleSelection([]);
            rangeSelection = null;
            return;
        }

        pendingRangeSelection = value;
        ignoreNextRangeClear = false;

        if (!selectionActive) {
            selectionActive = true;

            const handleMouseUp = () => {
                finalizeRangeSelection();
            };

            // TODO(Malte, 10/2025): Review if this window event handling approach is proper for Svelte
            // Consider if there's a more Svelte-idiomatic way to handle global mouse events
            window.addEventListener('mouseup', handleMouseUp, { once: true });
            detachMouseUpListener = () => {
                window.removeEventListener('mouseup', handleMouseUp);
            };
        }
    }

    onDestroy(() => {
        if (detachMouseUpListener) {
            detachMouseUpListener();
            detachMouseUpListener = null;
        }
    });

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

    let viewportStateKey = $state(Date.now());
    const reset = () => {
        viewportStateKey = Date.now();
    };
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
        {:else if $embeddingsData.isError}
            <div class="flex items-center justify-center p-8 text-red-500">
                <div class="text-lg">Error loading embeddings: {$embeddingsData.error.error}</div>
            </div>
        {:else if $embeddings.x.length > 0 && $embeddings.y.length > 0}
            <div class="min-h-0 flex-1" bind:this={plotContainer}>
                {#key viewportStateKey}
                    <EmbeddingView
                        class="h-full w-full"
                        config={{ colorScheme: 'dark', autoLabelEnabled: false }}
                        {width}
                        {height}
                        data={{
                            x: $embeddings.x,
                            y: $embeddings.y,
                            category: $embeddings.category
                        }}
                        {categoryColors}
                        tooltip={null}
                        theme={{
                            brandingLink: null
                        }}
                        {rangeSelection}
                        onRangeSelection={handleRangeSelection}
                    />
                {/key}
            </div>
        {:else}
            <div class="flex items-center justify-center p-8">
                <div class="text-lg">No data available</div>
            </div>
        {/if}
    </div>
    {#if $embeddings.x.length > 0 && $embeddings.y.length > 0}
        <div class="mt-1 flex items-center gap-4 text-sm text-muted-foreground">
            <span class="flex items-center gap-2">
                <span class="legend-dot" style={`background-color: ${categoryColors[0]}`}></span>
                All samples
            </span>
            <span class="flex items-center gap-2">
                <span class="legend-dot" style={`background-color: ${categoryColors[1]}`}></span>
                Filtered samples
            </span>
            <Button variant="outline" size="sm" onclick={reset}>Reset view</Button>
            {#if hasPersistentSelection}
                <Button variant="outline" size="sm" onclick={resetSelection}>Reset selection</Button
                >
            {/if}
        </div>
    {/if}
</div>

<style>
    .legend-dot {
        display: inline-block;
        height: 0.75rem;
        width: 0.75rem;
        border-radius: 9999px;
    }
</style>
