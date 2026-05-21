<script lang="ts">
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import Button from '$lib/components/ui/button/button.svelte';
    import { Input } from '$lib/components/ui/input';
    import { Select, SelectContent, SelectItem, SelectTrigger } from '$lib/components/ui/select';
    import { ArrowLeft, ArrowRight } from '@lucide/svelte';
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
    import PlotColorByPopover from './PlotColorByPopover/PlotColorByPopover.svelte';
    import { isEqual } from 'lodash-es';
    import { NOT_FILTERED_CATEGORY } from './plotCategories';
    import {
        FILTERED_COLOR,
        getCategoryColors,
        getCategoryCount,
        NOT_FILTERED_COLOR
    } from './plotColorUtils';
    import { page } from '$app/state';
    import { isVideosRoute } from '$lib/routes';
    import { usePlotColorByType } from './PlotColorByPopover/usePlotColorByType/usePlotColorByType';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    type ColorBy = Exclude<Parameters<typeof useEmbeddings>[2], undefined>;

    const collectionId = page.params.collection_id;
    const { setShowPlot, getRangeSelection, setRangeSelectionForCollection } = useGlobalStorage();
    const rangeSelection = getRangeSelection(collectionId);
    const setRangeSelection = (selection: Point[] | null) => {
        setRangeSelectionForCollection(collectionId, selection);
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
    const activeSampleIds = $derived(
        (isVideos ? $videoFilter : $imageFilter)?.sample_filter?.sample_ids ?? []
    );

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

    let selectedColorByKey: string | null = $state(null);
    const { selectedColorByType } = usePlotColorByType(collectionId);
    const colorBy: ColorBy = $derived.by(() => {
        if ($selectedColorByType === 'metadata' && selectedColorByKey) {
            return { type: 'metadata_field', key: selectedColorByKey };
        }

        return null;
    });

    // LIG-9502 prototype: natural-language axes (Variant A) and PCA over active labels (Variant B).
    // Throwaway UI.
    type ProjectionMode = 'pacmap' | 'text' | 'labels';
    let projectionMode = $state<ProjectionMode>('pacmap');
    // Each axis can be a single anchor or a contrastive pair (positive vs negative).
    // Direction = embed(positive) − embed(negative) when both are filled.
    let nlpXPosDraft = $state('');
    let nlpXNegDraft = $state('');
    let nlpYPosDraft = $state('');
    let nlpYNegDraft = $state('');
    type NlpAxisInput = { positive: string; negative: string | null };
    let committedNlpAxes: { x: NlpAxisInput; y: NlpAxisInput } | null = $state(null);

    function commitNlpAxes() {
        const xPos = nlpXPosDraft.trim();
        const yPos = nlpYPosDraft.trim();
        if (!xPos || !yPos) {
            committedNlpAxes = null;
            return;
        }
        const xNeg = nlpXNegDraft.trim();
        const yNeg = nlpYNegDraft.trim();
        committedNlpAxes = {
            x: { positive: xPos, negative: xNeg || null },
            y: { positive: yPos, negative: yNeg || null }
        };
    }

    function onAxisKeyDown(event: KeyboardEvent) {
        if (event.key !== 'Enter') return;
        event.preventDefault();
        commitNlpAxes();
        (event.currentTarget as HTMLInputElement | null)?.blur();
    }

    // Variant B: PCA over text embeddings of all annotation label names in the collection.
    // We deliberately use *all* labels (not just the selected/filtered ones), so that
    // toggling the label filter does not also change the embedding-plot projection.
    const annotationLabelsQuery = useAnnotationLabels(() => ({ collectionId }));
    const allLabelNames = $derived.by(() => {
        const labels = annotationLabelsQuery.data ?? [];
        const names: string[] = [];
        for (const label of labels) {
            const name = label.annotation_label_name;
            if (name) names.push(name);
        }
        return names;
    });
    const MIN_LABELS_FOR_PCA = 2;
    const labelsModeDisabled = $derived(allLabelNames.length < MIN_LABELS_FOR_PCA);

    function onProjectionModeChange(value: string) {
        if (value === 'labels' && labelsModeDisabled) return;
        projectionMode = value as ProjectionMode;
        if (projectionMode !== 'text') {
            committedNlpAxes = null;
        } else {
            commitNlpAxes();
        }
    }

    // Fall back from labels mode automatically if the active labels drop below the threshold.
    $effect(() => {
        if (projectionMode === 'labels' && labelsModeDisabled) {
            projectionMode = 'pacmap';
        }
    });

    const effectiveNlpAxes = $derived(projectionMode === 'text' ? committedNlpAxes : null);
    const effectivePcaAxes = $derived(
        projectionMode === 'labels' && allLabelNames.length >= MIN_LABELS_FOR_PCA
            ? { label_names: allLabelNames }
            : null
    );
    // PacMap mode also shows label centroid markers when the collection has labels.
    const effectiveReferenceLabelNames = $derived(
        projectionMode === 'pacmap' && allLabelNames.length > 0 ? allLabelNames : null
    );

    const embeddingsData = $derived(
        useEmbeddings(
            collectionId,
            filter,
            colorBy,
            effectiveNlpAxes,
            effectivePcaAxes,
            effectiveReferenceLabelNames
        )
    );

    const {
        data: arrowData,
        colorLegend,
        referencePoints,
        error: arrowError
    } = $derived(
        useArrowData({
            blobData: embeddingsData.data as Blob
        })
    );
    const filteredLabel = $derived($colorLegend.get(1) ?? 'Filtered');

    const hasActiveFilter = $derived(filter !== null || activeSampleIds.length > 0);

    let { data: plotData, selectedSampleIds } = $derived(
        usePlotData({
            arrowData: $arrowData,
            rangeSelection: $rangeSelection,
            highlightedSampleIds: activeSampleIds,
            hasActiveFilter: hasActiveFilter
        })
    );
    const categoryCount = $derived.by(() => getCategoryCount($colorLegend));
    const categoryColors = $derived.by(() => getCategoryColors($colorLegend));
    const handleMouseUp = () => {
        const hadRangeSelection = $rangeSelection !== null;
        if (!hadRangeSelection) {
            return;
        }

        const filter = isVideos ? $videoFilter : $imageFilter;
        const currentSampleIds = filter?.sample_filter?.sample_ids || [];
        const selectableCount =
            ($arrowData?.color_category as Uint8Array | undefined)?.reduce((count, category) => {
                return category !== NOT_FILTERED_CATEGORY ? count + 1 : count;
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

    // Reset zoom whenever the projection mode or any axis input changes — the new
    // projection lives in a different coordinate range, so the prior viewport is stale.
    $effect(() => {
        void projectionMode;
        void committedNlpAxes;
        viewportState = null;
    });

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

    // Autofit center+scale that mirrors embedding-atlas's defaultViewportState math
    // (median + 3·σ of the data). Used when viewportState is null so reference markers
    // track the same auto-framing embedding-atlas applies internally.
    const autofit = $derived.by((): ViewportState | null => {
        const xs = $arrowData?.x as Float32Array | undefined;
        const ys = $arrowData?.y as Float32Array | undefined;
        if (!xs || !ys || xs.length === 0) return null;
        const median = (arr: Float32Array): number => {
            const copy = Float32Array.from(arr);
            copy.sort();
            return copy[Math.floor(copy.length / 2)];
        };
        const meanStd = (arr: Float32Array): { mean: number; std: number } => {
            let sum = 0;
            for (let i = 0; i < arr.length; i++) sum += arr[i];
            const mean = sum / arr.length;
            let sq = 0;
            for (let i = 0; i < arr.length; i++) sq += (arr[i] - mean) * (arr[i] - mean);
            return { mean, std: Math.sqrt(sq / arr.length) };
        };
        const xStd = meanStd(xs).std;
        const yStd = meanStd(ys).std;
        const scale = 0.95 / (Math.max(xStd, yStd, 1e-3) * 3);
        return { x: median(xs), y: median(ys), scale };
    });

    // Map (data_x, data_y) to (screen_x, screen_y) mirroring embedding-atlas's transform:
    // the shorter plot axis maps 1 normalized unit to scale; the longer axis is boosted
    // by the aspect ratio so the visible window matches the plot's rectangle.
    const projectedReferences = $derived.by(() => {
        const refs = $referencePoints;
        if (!refs.length) return [];
        const vp = viewportState ?? autofit;
        if (!vp || width === 0 || height === 0) return [];
        const isTall = width < height;
        const aX = isTall ? vp.scale * (height / width) : vp.scale;
        const aY = isTall ? vp.scale : vp.scale * (width / height);
        return refs.map((ref) => ({
            label: ref.label,
            left: width / 2 + (ref.x - vp.x) * aX * (width / 2),
            top: height / 2 - (ref.y - vp.y) * aY * (height / 2)
        }));
    });

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
        <div class="flex items-center gap-3">
            <div class="text-lg font-semibold">Embedding Plot</div>
            <Select type="single" value={projectionMode} onValueChange={onProjectionModeChange}>
                <SelectTrigger class="h-8 w-28" data-testid="plot-projection-mode-trigger">
                    {projectionMode === 'pacmap'
                        ? 'PacMap'
                        : projectionMode === 'text'
                          ? 'Text'
                          : 'Labels'}
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="pacmap">PacMap</SelectItem>
                    <SelectItem value="text">Text</SelectItem>
                    <SelectItem
                        value="labels"
                        disabled={labelsModeDisabled}
                        title={labelsModeDisabled
                            ? 'This collection needs at least 2 annotation labels to enable PCA-over-labels.'
                            : undefined}
                    >
                        Labels
                    </SelectItem>
                </SelectContent>
            </Select>
        </div>
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
            <div class="relative min-h-0 flex-1 overflow-hidden bg-black" bind:this={plotContainer}>
                {#if $plotData && width >= MIN_RENDER_SIZE && height >= MIN_RENDER_SIZE}
                    <EmbeddingView
                        class="h-full w-full"
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
                    <PlotPanelLegend
                        categoryColors={[NOT_FILTERED_COLOR, FILTERED_COLOR]}
                        {filteredLabel}
                    />
                {/if}
                {#if projectedReferences.length > 0}
                    <!-- LIG-9502 prototype: reference markers. The outer div is a zero-size anchor
                         positioned exactly at the data point; the dot is centered on the anchor and
                         the label hangs to its right so labels of different widths don't shift the
                         visible rectangle corners. -->
                    <div class="pointer-events-none absolute inset-0 z-20">
                        {#each projectedReferences as ref (ref.label)}
                            <div
                                class="absolute"
                                style="left: {ref.left}px; top: {ref.top}px;"
                                data-testid="plot-reference-marker"
                            >
                                <div
                                    class="absolute h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full border border-black bg-amber-400"
                                ></div>
                                <span
                                    class="absolute left-2 top-0 -translate-y-1/2 whitespace-nowrap text-xs font-medium text-white"
                                    style="text-shadow: 0 0 2px #000, 0 0 2px #000;"
                                >
                                    {ref.label}
                                </span>
                            </div>
                        {/each}
                    </div>
                {/if}
                {#if projectionMode === 'text'}
                    <!-- LIG-9502 prototype: X-axis poles at bottom: [neg] ← → [pos] -->
                    <div
                        class="pointer-events-none absolute inset-x-0 bottom-3 z-10 flex justify-center"
                    >
                        <div
                            class="pointer-events-auto flex items-center gap-2 rounded bg-black/70 px-2 py-1"
                        >
                            <Input
                                type="text"
                                placeholder="X−  (e.g. young)"
                                bind:value={nlpXNegDraft}
                                onkeydown={onAxisKeyDown}
                                class="h-8 w-32 text-xs"
                                data-testid="plot-nlp-x-neg-input"
                            />
                            <ArrowLeft class="h-4 w-4 text-white" />
                            <ArrowRight class="h-4 w-4 text-white" />
                            <Input
                                type="text"
                                placeholder="X+  (e.g. old)"
                                bind:value={nlpXPosDraft}
                                onkeydown={onAxisKeyDown}
                                class="h-8 w-32 text-xs"
                                data-testid="plot-nlp-x-pos-input"
                            />
                        </div>
                    </div>
                    <!-- LIG-9502 prototype: Y-axis poles flush to the left border. The outer wrapper
                         is a narrow vertical strip; the inner rotated content overflows it horizontally
                         (in the unrotated layout) but visually stays inside the strip after rotation. -->
                    <div
                        class="pointer-events-none absolute inset-y-0 left-0 z-10 flex w-10 items-center justify-center"
                    >
                        <div
                            class="pointer-events-auto flex -rotate-90 items-center gap-2 whitespace-nowrap rounded bg-black/70 px-2 py-1"
                        >
                            <Input
                                type="text"
                                placeholder="Y−  (e.g. sad)"
                                bind:value={nlpYNegDraft}
                                onkeydown={onAxisKeyDown}
                                class="h-8 w-32 text-xs"
                                data-testid="plot-nlp-y-neg-input"
                            />
                            <ArrowLeft class="h-4 w-4 text-white" />
                            <ArrowRight class="h-4 w-4 text-white" />
                            <Input
                                type="text"
                                placeholder="Y+  (e.g. happy)"
                                bind:value={nlpYPosDraft}
                                onkeydown={onAxisKeyDown}
                                class="h-8 w-32 text-xs"
                                data-testid="plot-nlp-y-pos-input"
                            />
                        </div>
                    </div>
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
                selectedKey={selectedColorByKey}
                onSelectedKeyChange={(key) => {
                    selectedColorByKey = key;
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
