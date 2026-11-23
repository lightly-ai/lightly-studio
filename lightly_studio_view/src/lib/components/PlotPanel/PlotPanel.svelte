<script lang="ts">
    import { untrack } from 'svelte';
    import LoaderCircle from '@lucide/svelte/icons/loader-circle';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { Button } from '$lib/components';
    import PlotToolPill from './PlotToolPill/PlotToolPill.svelte';
    import PlotSelectionChip from './PlotSelectionChip/PlotSelectionChip.svelte';
    import { getPickHint } from './PlotSelectionChip/PlotSelectionChip.helpers';
    import { useLingeringValue } from '$lib/hooks';
    import { PlotAxesEditor } from './PlotAxesEditor';
    import { PlotAxesLabels } from './PlotAxesLabels';
    import PlotAxisLines from './PlotAxisLines/PlotAxisLines.svelte';
    import { usePointPicking } from './usePointPicking/usePointPicking';
    import { areTextAxesEqual } from './PlotTextAxesInputs/textAxesDraft';
    import { usePlotLayout, type PlotLayout } from './usePlotLayout/usePlotLayout';
    import { getDefaultViewport } from './usePlotLayout/textAxesViewport';
    import type { ToolMode } from './PlotToolPill/selectionTool';
    import {
        EmbeddingView,
        type DataPoint,
        type OverlayProxy,
        type Point,
        type Rectangle,
        type ViewportState
    } from 'embedding-atlas/svelte';
    import PlotHoverPreview from './PlotHoverPreview/PlotHoverPreview.svelte';
    import { getHoverPreviewState } from './PlotHoverPreview/hoverPreviewState';
    import { NoopTooltip, createOverlayProxyReporter } from './PlotHoverPreview/overlayProxy';
    import {
        createQuerySelection,
        createSelectablePointCheck,
        createThumbnailResolver
    } from './PlotHoverPreview';
    import { useEmbeddings } from '$lib/hooks/useEmbeddings/useEmbeddings';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
    import { useAnnotationPlotSelection } from '$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForAnnotations';
    import {
        clearPlotSelectionCount,
        EMPTY_PLOT_SELECTION,
        getPlotSelectionCount,
        setPlotSelectionCount,
        type PlotSelection
    } from '$lib/hooks/useEmbeddingFilter/useEmbeddingPlotSelection';
    import { getPlotRequestFilter } from './getPlotRequestFilter/getPlotRequestFilter';
    import { usePlotData } from './usePlotData/usePlotData';
    import PlotPanelLegend from './PlotPanelLegend.svelte';
    import PlotColorByPopover from './PlotColorByPopover/PlotColorByPopover.svelte';
    import { useCategoryVisibility } from './useCategoryVisibility/useCategoryVisibility';
    import { getCategoryColors, getCategoryCount, getLegendEntries } from './plotColorUtils';
    import {
        EXCLUDED_BY_FILTERS_CATEGORY,
        INCLUDED_BY_FILTERS_CATEGORY,
        INCLUDED_BY_FILTERS_LABEL,
        NO_CATEGORY_LABEL
    } from './plotCategories';
    import { page } from '$app/state';
    import { cn } from '$lib/utils';
    import { isAnnotationsRoute, isMcapSequencesRoute, isVideosRoute } from '$lib/routes';
    import { useMcapSequenceFilters } from '$lib/hooks/useMcapSequenceFilters/useMcapSequenceFilters';
    import { buildSequencePlotFilter } from './buildSequencePlotFilter/buildSequencePlotFilter';
    import { usePlotColorByType } from './PlotColorByPopover/usePlotColorByType/usePlotColorByType';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import { usePlotColorBy } from './usePlotColorBy/usePlotColorBy';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useSelectedAnnotationsFilter } from '$lib/hooks/useAnnotationsFilter/useAnnotationsFilter';
    import { writable, get, readable } from 'svelte/store';
    import { usePostHog } from '$lib/hooks';

    const NO_LEGEND = new Map<number, string>();

    let { collectionId }: { collectionId: string } = $props();
    const { trackEvent } = usePostHog();
    const { setShowEmbeddingPlot, getRangeSelection, setRangeSelectionForCollection } =
        useGlobalStorage();
    const rangeSelection = $derived(getRangeSelection(collectionId));
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
    // The MCAP sequences grid lives on the point clouds route.
    const isSequences = $derived(isMcapSequencesRoute(page.route?.id ?? null));
    // Everything that isn't videos, annotations or sequences is the images grid.
    const isImages = $derived(!isVideos && !isAnnotations && !isSequences);
    const itemLabel = $derived(
        isAnnotations ? 'annotation' : isVideos ? 'video' : isSequences ? 'sequence' : 'image'
    );
    const plotSelectionCount = $derived(getPlotSelectionCount(readable(collectionId)));

    // Use appropriate filter hook based on route
    const imageFilters = useImageFilters();
    const videoFilters = useVideoFilters();
    const sequenceFilters = useMcapSequenceFilters();
    const {
        annotationPlotRegion,
        annotationPlotPickedSampleIds,
        savePlotSelection: saveAnnotationPlotSelection
    } = useAnnotationPlotSelection();

    const imageFilter = $derived(isVideos || isSequences ? null : imageFilters.imageFilter);
    const videoFilter = $derived(isVideos ? videoFilters.videoFilter : null);
    const sequenceFilter = $derived(isSequences ? sequenceFilters.mcapSequenceFilter : null);
    const pickedSampleIds = $derived.by(() => {
        if (isVideos) return $videoFilter?.sample_filter?.sample_ids ?? [];
        if (isImages) return $imageFilter?.sample_filter?.sample_ids ?? [];
        if (isAnnotations) return $annotationPlotPickedSampleIds;
        return [];
    });

    // The active annotation label/tag filter, mirroring what the annotations grid applies.
    const { annotationFilter: selectedAnnotationsFilter } = $derived.by(() =>
        useSelectedAnnotationsFilter(collectionId)
    );

    // Prepare filter for embeddings API - use VideoFilter for videos, ImageFilter for images
    const filter = $derived.by(() => {
        // On the annotations route, send the active annotation label/tag filter (or an
        // empty annotations filter so all points count as included).
        if (isAnnotations) {
            return $selectedAnnotationsFilter ?? { filter_type: 'annotations' as const };
        }
        if (isSequences) {
            return buildSequencePlotFilter($sequenceFilter);
        }
        return getPlotRequestFilter(isVideos ? $videoFilter : $imageFilter);
    });

    const { selectedColorByType } = usePlotColorByType(untrack(() => collectionId));
    // Captured once at mount, like collectionId above.
    const { tags } = useTags({
        collection_id: untrack(() => collectionId)
    });
    const annotationLabelsQuery = useAnnotationLabels(() => ({ collectionId }));
    const annotationLabels = writable<{ annotation_label_id: string }[] | undefined>(undefined);
    $effect(() => {
        // Without labels the plot still loads: it colors nothing instead of waiting forever.
        if (annotationLabelsQuery.isError) {
            annotationLabels.set([]);
            return;
        }
        if (!annotationLabelsQuery.isSuccess) return;
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

    const {
        plotLayout,
        textAxesDraft,
        appliedTextAxes,
        isEmbeddingAxes,
        plotAxes,
        commitTextAxes
    } = usePlotLayout(untrack(() => collectionId));
    const showAxesLabels = $derived($plotLayout === 'text' && $appliedTextAxes !== null);

    const embeddingsData = useEmbeddings(() => ({
        collectionId,
        filters: filter,
        colorBy: $colorBy ?? null,
        axes: $plotAxes,
        enabled: $colorBy !== undefined
    }));
    // The query parses the Arrow data. A new color-by or axes is a new query with its own data,
    // so the old points never show under a new layout.
    const arrowData = $derived(embeddingsData.data?.columns);
    const colorLegend = $derived(embeddingsData.data?.legend ?? NO_LEGEND);
    const isWaitingForFirstData = $derived(embeddingsData.isLoading || $colorBy === undefined);
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
    } = useCategoryVisibility({
        getCollectionId: () => collectionId,
        getColorByType: () => get(selectedColorByType)
    });

    // The backend re-ranks color slots per request, so a stale toggle would hide the wrong slot;
    // reset hidden categories on every legend change. EXCLUDED keeps its meaning, so it always
    // survives. INCLUDED is relabeled with the color-by mode, so it survives only a filter-only
    // change — else a hidden "No category" would empty the plot once all points collapse into it.
    let previousColorByKey: string | undefined = undefined;
    $effect(() => {
        void colorLegend;
        const colorByKey = JSON.stringify($colorBy);
        const colorByChanged = colorByKey !== previousColorByKey;
        previousColorByKey = colorByKey;
        resetCategoryVisibility(
            colorByChanged
                ? [EXCLUDED_BY_FILTERS_CATEGORY]
                : [EXCLUDED_BY_FILTERS_CATEGORY, INCLUDED_BY_FILTERS_CATEGORY]
        );
    });

    const hasActiveFilter = $derived(filter !== null || pickedSampleIds.length > 0);

    // Videos, images and annotations commit the lasso as region geometry. After the
    // selection is committed the live rangeSelection is cleared, so the plot re-derives the
    // highlight from the stored polygon to keep reflecting the actually selected points. Videos
    // and images keep the region on their filter stores; annotations use the shared plot store.
    const committedSampleRegion = $derived(
        isSequences
            ? ($sequenceFilter?.sample_filter?.embedding_region ?? null)
            : isVideos
              ? ($videoFilter?.sample_filter?.embedding_region ?? null)
              : isImages
                ? ($imageFilter?.sample_filter?.embedding_region ?? null)
                : null
    );
    const committedHighlightRegion = $derived(
        isAnnotations
            ? ($annotationPlotRegion?.polygon ?? null)
            : (committedSampleRegion?.polygon ?? null)
    );

    // Activating a lasso (or a committed region) unhides the Excluded category, otherwise
    // out-of-selection points (which get demoted to Excluded) would vanish and blank out the
    // canvas. The legend keeps showing the user's real toggle state.
    const effectiveHiddenCategories = $derived.by(() => {
        const hasSelectionHighlight =
            $rangeSelection !== null ||
            committedHighlightRegion !== null ||
            pickedSampleIds.length > 0;
        if (!hasSelectionHighlight || !$hiddenCategories.has(EXCLUDED_BY_FILTERS_CATEGORY)) {
            return $hiddenCategories;
        }
        const next = new Set($hiddenCategories);
        next.delete(EXCLUDED_BY_FILTERS_CATEGORY);
        return next;
    });

    let { data: plotData, selectedSampleIds } = $derived(
        usePlotData({
            arrowData: arrowData,
            rangeSelection: $rangeSelection,
            highlightRegion: committedHighlightRegion,
            highlightedSampleIds: pickedSampleIds,
            hasActiveFilter: hasActiveFilter,
            hiddenCategories: effectiveHiddenCategories
        })
    );
    const categoryCount = $derived.by(() => getCategoryCount(colorLegend));
    const useLabelColors = $derived($selectedColorByType === 'annotation_label');
    const categoryColors = $derived.by(() =>
        getCategoryColors(colorLegend, useLabelColors, $colorBy !== null)
    );
    const legendEntries = $derived.by(() =>
        getLegendEntries(colorLegend, $hiddenCategories, useLabelColors)
    );
    // Videos, images and annotations send the lasso as region geometry rather than a resolved
    // sample-id list. The sidebar chip reads the count from the plot-propagated store, and
    // clearing removes the region entirely.
    const savePlotSelection = (selection: PlotSelection) => {
        if (isImages) {
            imageFilters.updatePlotSelection(selection);
        } else if (isVideos) {
            videoFilters.updatePlotSelection(selection);
        } else if (isSequences) {
            sequenceFilters.updateEmbeddingRegion(selection.embeddingRegion);
        } else {
            saveAnnotationPlotSelection(selection);
        }
    };
    // A region drawn on the plot carries the axes of the layout, so the server resolves the
    // region in the same layout.
    const commitRegion = (polygon: Point[], count: number) => {
        const embeddingRegion = $plotAxes ? { polygon, axes: $plotAxes } : { polygon };
        savePlotSelection({ embeddingRegion, sampleIds: [] });
        setPlotSelectionCount(collectionId, count);
    };
    // A gesture that starts on the old points stays ignored, even when the new points land
    // before the release.
    let isPressOnOldPoints = false;
    const isOnOldPoints = () => embeddingsData.isPlaceholderData || isPressOnOldPoints;
    // The sequences grid has no sample-id filter, so it does not support picks. While new points
    // load, a pick on the old points could select a point that the new filter excludes.
    const commitPickedSampleIds = (sampleIds: string[]) => {
        if (isSequences || isOnOldPoints()) return;
        if (sampleIds.length === 0) {
            clearPlotFilter();
            return;
        }
        savePlotSelection({ embeddingRegion: null, sampleIds });
        setPlotSelectionCount(collectionId, sampleIds.length);
        trackEvent('embedding_selection_made', {
            collection_id: collectionId,
            selection_type: 'pick',
            selected_count: sampleIds.length
        });
    };
    const clearPlotFilter = () => {
        savePlotSelection(EMPTY_PLOT_SELECTION);
        clearPlotSelectionCount(collectionId);
    };

    const selectableCount = $derived(
        (arrowData?.fulfils_filter as Uint8Array | undefined)?.reduce((count, fulfils) => {
            return fulfils !== 0 ? count + 1 : count;
        }, 0) ?? null
    );
    const handleMouseUp = (event: MouseEvent) => {
        if ($rangeSelection === null) {
            return;
        }
        // While new points load, the counts below come from the old points, so the drawn
        // selection is dropped.
        if (isOnOldPoints()) {
            setRangeSelection(null);
            pendingSelectionType = null;
            return;
        }
        if (isShortShiftDrag(event)) {
            setRangeSelection(null);
            pendingSelectionType = null;
            pickPressedPoint();
            return;
        }
        const polygon = $rangeSelection;
        const selectedCount = $selectedSampleIds.length;
        // Selecting nothing, or every selectable point, is equivalent to no filter at all.
        const selectsNothingOrEverything =
            selectedCount === 0 || (selectableCount !== null && selectedCount === selectableCount);

        if (selectsNothingOrEverything) {
            clearPlotFilter();
        } else {
            commitRegion(polygon, selectedCount);
            if (pendingSelectionType) {
                trackEvent('embedding_selection_made', {
                    collection_id: collectionId,
                    selection_type: pendingSelectionType,
                    selected_count: selectedCount
                });
            }
        }
        setRangeSelection(null);
        pendingSelectionType = null;
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
        userViewportState = null;
    };

    const isReady = true;

    // Lives here, not in PlotToolPill: a new color-by, axes or collection shows the full loader,
    // and the plot unmounts while it loads. State inside the pill would not survive that.
    let activeTool = $state<ToolMode>('pan');

    type RangeSelection = Rectangle | Point[] | null;

    const isRectangleSelection = (selection: RangeSelection): selection is Rectangle => {
        return selection !== null && !Array.isArray(selection);
    };

    let pendingSelectionType = $state<'lasso' | 'rectangle' | null>(null);

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
        clearPlotFilter();
    };
    // Videos and images track their committed selection on their filter stores; annotations use
    // the shared plot region store.
    const regionSelected = $derived(
        isAnnotations ? $annotationPlotRegion !== null : committedSampleRegion !== null
    );
    const hasActiveSelection = $derived(
        $rangeSelection !== null || pickedSampleIds.length > 0 || regionSelected
    );

    const onWindowKeyDown = (event: KeyboardEvent) => {
        // An open popover handles Escape itself and prevents the default.
        if (event.defaultPrevented || event.key !== 'Escape') {
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
            pendingSelectionType = null;
            return;
        }
        const nextType = isRectangleSelection(selection) ? 'rectangle' : 'lasso';
        if (pendingSelectionType === null) {
            trackEvent('embedding_selection_started', {
                collection_id: collectionId,
                selection_type: nextType
            });
        }
        pendingSelectionType = nextType;
        const normalizedSelection = isRectangleSelection(selection)
            ? getPolygonFromRectangle(selection)
            : selection;
        setRangeSelection(normalizedSelection);
    };

    // The viewport after the user pans or zooms. Until then, the default follows the plot size,
    // because the size is 0 when the panel mounts and the default scale depends on it.
    let userViewportState: ViewportState | null = $state(null);
    const viewportState = $derived(
        userViewportState ?? getDefaultViewport({ hasTextAxes: $plotAxes !== null, width, height })
    );
    const onViewportState = (state: ViewportState) => {
        userViewportState = state;
    };

    // A new layout has other coordinates. Reset the zoom, and clear the selection, because a
    // region belongs to the layout it was drawn on.
    const resetForNewLayout = () => {
        userViewportState = null;
        if (hasActiveSelection) clearSelection();
    };
    const selectPlotLayout = (layout: PlotLayout) => {
        plotLayout.set(layout);
        resetForNewLayout();
    };
    const commitPlotAxes = async (textAxes: Parameters<typeof commitTextAxes>[0]) => {
        if ($plotLayout === 'text' && areTextAxesEqual(textAxes, $appliedTextAxes)) return true;
        const success = await commitTextAxes(textAxes);
        if (success) resetForNewLayout();
        return success;
    };

    // Hover preview: a controlled tooltip showing a thumbnail of the hovered point.
    // The array-based EmbeddingView only emits hover tooltips when querySelection
    // is provided; ours returns the nearest visible point with its sample ID.
    let tooltip = $state<DataPoint | null>(null);
    const onTooltip = (value: DataPoint | null) => {
        tooltip = value;
    };
    const {
        librarySelection,
        onPointerDown: onPickPointerDown,
        onSelection,
        isShortShiftDrag,
        pickPressedPoint
    } = usePointPicking({
        getPickedSampleIds: () => pickedSampleIds,
        getHoveredSampleId: () =>
            typeof tooltip?.identifier === 'string' ? tooltip.identifier : null,
        commitPickedSampleIds
    });
    const onPlotPointerDown = (event: PointerEvent) => {
        isPressOnOldPoints = embeddingsData.isPlaceholderData;
        onPickPointerDown(event);
    };
    const hoveredSampleId = $derived(
        typeof tooltip?.identifier === 'string' && $rangeSelection === null
            ? tooltip.identifier
            : null
    );
    // Picking does not work on sequences.
    const pickHint = $derived(
        isSequences ? null : getPickHint({ hoveredSampleId, pickedSampleIds })
    );
    // A drag drops the hint at once, so it cannot come back on release.
    const isDragging = () => $rangeSelection !== null;
    const shownPickHint = useLingeringValue(() => pickHint, 400, isDragging);
    const selectionKind = $derived(
        $plotSelectionCount === 0 ? null : pickedSampleIds.length > 0 ? 'picks' : 'region'
    );
    // The card is rendered by this component (not the library's tooltip container)
    // so it always sits directly above the hovered point; the overlay proxy
    // provides the data → pixel conversion.
    let overlayProxy: OverlayProxy | null = $state(null);
    const OverlayProxyReporter = createOverlayProxyReporter((proxy) => {
        overlayProxy = proxy;
    });
    // Tailwind's h-32/w-32 size the card's border box to 128px.
    const PREVIEW_CARD_SIZE = 128;
    const hoverPreview = $derived.by(() =>
        getHoverPreviewState({
            tooltip,
            rangeSelectionActive: $rangeSelection !== null,
            proxy: overlayProxy,
            cardSize: PREVIEW_CARD_SIZE
        })
    );
    const querySelection = $derived.by(() =>
        createQuerySelection({
            x: arrowData?.x as Float32Array | undefined,
            y: arrowData?.y as Float32Array | undefined,
            sampleIds: arrowData?.sample_id as string[] | undefined,
            category: $plotData?.category as Uint8Array | undefined,
            isSelectable: createSelectablePointCheck({
                category: $plotData?.category as Uint8Array | undefined,
                sampleIds: arrowData?.sample_id as string[] | undefined,
                fulfilsFilter: hasActiveFilter
                    ? (arrowData?.fulfils_filter as Uint8Array | undefined)
                    : undefined,
                pickedSampleIds
            })
        })
    );
    const resolveThumbnail = $derived.by(() =>
        createThumbnailResolver({
            route: isAnnotations
                ? 'annotations'
                : isVideos
                  ? 'videos'
                  : isSequences
                    ? 'mcap_sequences'
                    : 'images',
            collectionId
        })
    );

    const errorText = $derived.by(() => {
        if (embeddingsData.isError) {
            return embeddingsData.error?.message || 'Unknown error';
        }
        return null;
    });
</script>

<div class="flex min-h-0 flex-1 flex-col rounded-[1vw] bg-card p-4" data-testid="plot-panel">
    <div class="mb-5 mt-2 flex items-start justify-between gap-2">
        <div class="flex flex-wrap items-center gap-3">
            <div class="text-lg font-semibold">Embedding Plot</div>
            <PlotAxesEditor
                bind:draft={$textAxesDraft}
                active={$plotLayout === 'text'}
                isPending={$isEmbeddingAxes}
                onCommit={commitPlotAxes}
                onReset={() => selectPlotLayout('pacmap')}
            />
        </div>
        <Button
            variant="ghost"
            buttonProps={{
                size: 'icon',
                onclick: handleClose,
                class: 'h-8 w-8',
                'data-testid': 'plot-close-button'
            }}
        >
            ✕
        </Button>
    </div>
    <div class="relative flex min-h-0 flex-1 flex-col">
        {#if isWaitingForFirstData}
            <div class="flex flex-1 items-center justify-center p-8">
                <div class="text-lg">Loading embeddings data...</div>
            </div>
        {:else if errorText}
            <div class="flex flex-1 items-center justify-center p-8 text-red-500">
                <div class="text-lg">Error loading embeddings: {errorText}</div>
            </div>
        {:else if isReady}
            <div
                class="embedding-plot-wrapper relative min-h-0 flex-1 overflow-hidden bg-black"
                bind:this={plotContainer}
                onpointerdowncapture={onPlotPointerDown}
            >
                {#if embeddingsData.isPlaceholderData}
                    <div
                        class="pointer-events-none absolute right-2 top-2 z-10 flex size-[30px] items-center justify-center rounded-lg border border-white/10 bg-black/60 text-white backdrop-blur-sm"
                        data-testid="plot-loading-indicator"
                        role="status"
                        aria-label="Loading embeddings"
                    >
                        <LoaderCircle class="size-3.5 animate-spin" />
                    </div>
                {/if}

                {#if $plotData && width >= MIN_RENDER_SIZE && height >= MIN_RENDER_SIZE}
                    <div class="embedding-view h-full w-full">
                        <EmbeddingView
                            config={embeddingConfig}
                            {width}
                            {height}
                            {categoryCount}
                            data={$plotData}
                            {categoryColors}
                            tooltip={$rangeSelection ? null : tooltip}
                            {onTooltip}
                            selection={$librarySelection}
                            {onSelection}
                            {querySelection}
                            customTooltip={NoopTooltip}
                            customOverlay={OverlayProxyReporter}
                            theme={embeddingTheme}
                            {onRangeSelection}
                            {onViewportState}
                            {viewportState}
                            rangeSelection={$rangeSelection}
                        />
                    </div>

                    <!-- Only the Text layout has a meaningful origin: x = 0 is where a sample is
                         as close to X− as to X+. -->
                    {#if $plotAxes && overlayProxy}
                        <PlotAxisLines proxy={overlayProxy} />
                    {/if}

                    {#if showAxesLabels && $appliedTextAxes}
                        <PlotAxesLabels axes={$appliedTextAxes} />
                    {/if}

                    {#if $plotSelectionCount > 0 || shownPickHint.current !== null}
                        <!-- Below the top axis label, which it would overlap on a narrow plot. -->
                        <div
                            class={cn(
                                'pointer-events-none absolute left-2 right-2 z-10',
                                showAxesLabels ? 'top-11' : 'top-2'
                            )}
                        >
                            <PlotSelectionChip
                                {selectionKind}
                                count={$plotSelectionCount}
                                {itemLabel}
                                onClear={clearSelection}
                                pickHint={shownPickHint.current}
                            />
                        </div>
                    {/if}

                    {#if hoverPreview}
                        <div
                            class="pointer-events-none absolute z-10 -translate-x-1/2"
                            style="left: {hoverPreview.left}px; top: {hoverPreview.top}px"
                        >
                            <PlotHoverPreview sampleId={hoverPreview.sampleId} {resolveThumbnail} />
                        </div>
                    {/if}

                    <!-- Legend and pill share the bottom edge, so they sit in one row rather
                         than in two absolute corners: the legend then shrinks on a narrow plot
                         instead of running under the pill. -->
                    <div
                        class="pointer-events-none absolute inset-2 z-10 flex items-end justify-between gap-2"
                    >
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

                        <PlotToolPill {plotContainer} bind:activeTool />
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
            class="mt-1 flex min-w-0 shrink-0 flex-wrap items-center justify-end gap-2 text-sm text-muted-foreground"
            data-testid="plot-panel-controls"
        >
            <PlotColorByPopover
                {collectionId}
                withTags={$tags.length > 0}
                withAnnotationLabels={($annotationLabels ?? []).length > 0}
                selectedKey={$selectedColorByKey}
                onSelectedKeyChange={(key) => {
                    setSelectedColorByKey(key);
                }}
            />
            <Button
                variant="outline"
                buttonProps={{
                    size: 'sm',
                    onclick: reset,
                    'data-testid': 'plot-reset-zoom-button',
                    class: 'px-2.5',
                    title: 'Reset zoom'
                }}
            >
                Reset zoom
            </Button>
        </div>
    {/if}
</div>

<svelte:window onmouseup={handleMouseUp} onkeydown={onWindowKeyDown} />

<style>
    /*
        embedding-atlas renders its own bottom strip: a WebGPU/WebGL status message, the
        rectangle + lasso tool buttons, a scale bar, and a point count. This hides all of
        it: the selection tools now live in the glass tool pill and the rest is noise.
        Keep the strip in the DOM (so `selectTool` can .click() the hidden
        tool buttons and drive the library's sticky selection mode), but make it invisible
        and non-interactive. Use opacity/pointer-events, NOT display:none or
        visibility:hidden: the buttons stay laid out and clickable, and Playwright still
        reports them visible (LIG-7691 e2e asserts the tool buttons toBeVisible).
    */
    :global(.embedding-view div[style*='bottom: 0px'][style*='position: absolute']) {
        opacity: 0 !important;
        pointer-events: none !important;
    }
</style>
