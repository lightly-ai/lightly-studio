<script lang="ts">
    import { untrack, type Component } from 'svelte';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { Button } from '$lib/components';
    import { cn } from '$lib/utils';
    import { Hand, Lasso, SquareDashed } from '@lucide/svelte';
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
    import { createQuerySelection, createThumbnailResolver } from './PlotHoverPreview';
    import { useEmbeddings } from '$lib/hooks/useEmbeddings/useEmbeddings';
    import type { EmbeddingRegion } from '$lib/api/lightly_studio_local';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
    import { useAnnotationPlotSelection } from '$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForAnnotations';
    import {
        clearPlotSelectionCount,
        setPlotSelectionCount
    } from '$lib/hooks/useEmbeddingFilter/useEmbeddingPlotSelection';
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
    import { writable, get } from 'svelte/store';
    import { usePostHog } from '$lib/hooks';

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
    // Everything that isn't videos or annotations is the images grid.
    const isImages = $derived(!isVideos && !isAnnotations);

    // Use appropriate filter hook based on route
    const imageFilters = useImageFilters();
    const videoFilters = useVideoFilters();
    const { annotationPlotRegion, saveRegion: saveAnnotationRegion } = useAnnotationPlotSelection();

    const imageFilter = $derived(isVideos ? null : imageFilters.imageFilter);
    const videoFilter = $derived(isVideos ? videoFilters.videoFilter : null);
    // Only videos still track their lasso selection as a resolved sample-id list; images and
    // annotations send it to the backend as region geometry (see LIG-9903).
    const activeSampleIds = $derived(
        isVideos ? ($videoFilter?.sample_filter?.sample_ids ?? []) : []
    );

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
        const currentFilter = isVideos ? $videoFilter : $imageFilter;
        if (!currentFilter) return null;

        if (!currentFilter.sample_filter) {
            return currentFilter;
        }

        return {
            ...currentFilter,
            sample_filter: {
                ...currentFilter.sample_filter,
                sample_ids: [],
                // The lasso only scopes the grid, not the plot: the plot shows every point and
                // highlights the in-selection ones, so drop the region from this request.
                embedding_region: undefined
            }
        };
    });

    const { selectedColorByType } = usePlotColorByType(untrack(() => collectionId));
    // Annotation samples carry annotation-kind tags. Captured once at mount, like
    // collectionId above.
    const { tags } = useTags({
        collection_id: untrack(() => collectionId),
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

    // Images and annotations commit the lasso as region geometry, not as sample ids. After the
    // selection is committed the live rangeSelection is cleared, so the plot re-derives the
    // highlight from the stored polygon to keep reflecting the actually selected points. Images
    // keep the region on the image filter store; annotations in the shared plot region store.
    const committedHighlightRegion = $derived(
        isImages
            ? ($imageFilter?.sample_filter?.embedding_region?.polygon ?? null)
            : isAnnotations
              ? ($annotationPlotRegion?.polygon ?? null)
              : null
    );

    // Activating a lasso (or a committed region) unhides the Excluded category, otherwise
    // out-of-selection points (which get demoted to Excluded) would vanish and blank out the
    // canvas. The legend keeps showing the user's real toggle state.
    const effectiveHiddenCategories = $derived.by(() => {
        const hasSelectionHighlight = $rangeSelection !== null || committedHighlightRegion !== null;
        if (!hasSelectionHighlight || !$hiddenCategories.has(EXCLUDED_BY_FILTERS_CATEGORY)) {
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
            highlightRegion: committedHighlightRegion,
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
    // Images and annotations send the lasso to the backend as region geometry rather than a
    // resolved sample-id list (see LIG-9903); the sidebar chip reads the selected count from the
    // plot-propagated count store, and clearing removes the region entirely. Images keep the
    // region on the image filter store; annotations have no such store, so it lives in the
    // shared annotation-plot region store instead.
    const saveRegion = (region: EmbeddingRegion | null) => {
        if (isImages) {
            imageFilters.updateEmbeddingRegion(region);
        } else {
            saveAnnotationRegion(region);
        }
    };
    const commitRegion = (polygon: Point[], count: number) => {
        saveRegion({ polygon });
        setPlotSelectionCount(collectionId, count);
    };
    const clearRegion = () => {
        saveRegion(null);
        clearPlotSelectionCount(collectionId);
    };

    const handleMouseUp = () => {
        if ($rangeSelection === null) {
            return;
        }
        const polygon = $rangeSelection;

        const selectableCount =
            ($arrowData?.fulfils_filter as Uint8Array | undefined)?.reduce((count, fulfils) => {
                return fulfils !== 0 ? count + 1 : count;
            }, 0) ?? null;
        const selectedCount = $selectedSampleIds.length;
        // Selecting nothing, or every selectable point, is equivalent to no filter at all.
        const selectsNothingOrEverything =
            selectedCount === 0 || (selectableCount !== null && selectedCount === selectableCount);

        // Videos still commit the resolved sample-id list; images and annotations send geometry.
        if (isVideos) {
            const currentSampleIds = $videoFilter?.sample_filter?.sample_ids ?? [];
            if (selectsNothingOrEverything) {
                if (currentSampleIds.length > 0) {
                    videoFilters.updateSampleIds([]);
                }
            } else if (!isEqual($selectedSampleIds, currentSampleIds)) {
                videoFilters.updateSampleIds($selectedSampleIds);
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
            return;
        }

        if (selectsNothingOrEverything) {
            clearRegion();
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
        viewportState = null;
    };

    const isReady = true;

    // --- Sticky selection-tool pill ------------------------------------------------
    // embedding-atlas keeps its active selection mode ("none" = pan, "marquee" =
    // rectangle, "lasso") in a component-internal signal. It is not part of
    // EmbeddingViewProps and the class exposes no imperative setter (only
    // update()/destroy()), so the mode can only be changed by driving the library's
    // own toolbar buttons — which we hide via CSS below and click programmatically.
    // Each button toggles its mode on/off (target vs none) and marks the armed tool
    // with an inline `background: color-mix(...)`; we read that back to keep the pill
    // in sync via a MutationObserver.
    type ToolMode = 'pan' | 'rectangle' | 'lasso';

    const tools: { mode: ToolMode; icon: Component; label: string }[] = [
        { mode: 'pan', icon: Hand, label: 'Pan' },
        { mode: 'rectangle', icon: SquareDashed, label: 'Rectangle select' },
        { mode: 'lasso', icon: Lasso, label: 'Lasso select' }
    ];

    let activeTool = $state<ToolMode>('pan');

    // The library sets `background: color-mix(...)` inline on the armed tool button.
    const isButtonActive = (button: Element | null): boolean =>
        button?.getAttribute('style')?.includes('color-mix') ?? false;

    // Resolve the library's rectangle/lasso buttons by their (stable, English) title
    // text, falling back to DOM order if the library ever changes the wording.
    const getToolButtons = (): {
        marquee: HTMLButtonElement | null;
        lasso: HTMLButtonElement | null;
    } => {
        const buttons = Array.from(
            plotContainer?.querySelectorAll<HTMLButtonElement>('.embedding-view button') ?? []
        );
        let marquee: HTMLButtonElement | null = null;
        let lasso: HTMLButtonElement | null = null;
        for (const button of buttons) {
            const title = button.getAttribute('title') ?? '';
            if (title.startsWith('Toggle rectangle selection')) marquee = button;
            else if (title.startsWith('Toggle lasso selection')) lasso = button;
        }
        if (!marquee && !lasso && buttons.length >= 2) {
            marquee = buttons[0];
            lasso = buttons[1];
        }
        return { marquee, lasso };
    };

    // `activeTool` is the user's chosen tool and the pill's source of truth. The library
    // drops its own selection mode back to "none" after each committed selection, so we
    // re-assert `activeTool` onto its hidden buttons whenever they drift. That re-arm is
    // what keeps the tool sticky — pick lasso, stay lasso across selections — until the
    // user picks another tool.
    // Clicking a hidden tool button changes the library's mode asynchronously, so the
    // armed state read right after a click still shows the old value. A second reconcile
    // (fired by the plot's own DOM churn while switching) would then click the same button
    // again before the first click lands and toggle it back off — arm → disarm → re-arm,
    // which reads as a lag when picking a tool. `awaitingLibrary` blocks re-entrant clicks
    // until the style observer confirms the change (or a short safety timeout elapses).
    let awaitingLibrary = false;
    let awaitingTimer: ReturnType<typeof setTimeout> | undefined;

    const clickTool = (button: HTMLButtonElement | null) => {
        if (!button) return;
        awaitingLibrary = true;
        if (awaitingTimer) clearTimeout(awaitingTimer);
        awaitingTimer = setTimeout(() => {
            awaitingLibrary = false;
        }, 250);
        button.click();
    };

    const reconcileLibrary = () => {
        if (awaitingLibrary) return;
        const { marquee, lasso } = getToolButtons();
        const marqueeActive = isButtonActive(marquee);
        const lassoActive = isButtonActive(lasso);
        if (activeTool === 'rectangle') {
            if (!marqueeActive) clickTool(marquee);
        } else if (activeTool === 'lasso') {
            if (!lassoActive) clickTool(lasso);
        } else {
            // Pan is the library's "none" mode: turn off whichever tool is armed.
            if (marqueeActive) clickTool(marquee);
            else if (lassoActive) clickTool(lasso);
        }
    };

    const selectTool = (mode: ToolMode) => {
        activeTool = mode;
        reconcileLibrary();
    };

    // The library owns the buttons but not the intent. Watch the toolbar for (re)creation
    // (childList) and each button's inline-style flips — including the post-selection reset
    // to "none" — and re-assert the chosen tool each time so it stays selected.
    $effect(() => {
        if (!plotContainer) return;
        const observedButtons = new WeakSet<Element>();
        const styleObserver = new MutationObserver(() => {
            // The mode actually changed, so a pending click has landed (or the library
            // reset itself after a selection). Clear the guard and reconcile — this is
            // where the sticky re-arm happens.
            awaitingLibrary = false;
            reconcileLibrary();
        });
        const observeButtons = () => {
            const { marquee, lasso } = getToolButtons();
            for (const button of [marquee, lasso]) {
                if (button && !observedButtons.has(button)) {
                    observedButtons.add(button);
                    styleObserver.observe(button, {
                        attributes: true,
                        attributeFilter: ['style']
                    });
                }
            }
            reconcileLibrary();
        };
        const treeObserver = new MutationObserver(observeButtons);
        treeObserver.observe(plotContainer, { childList: true, subtree: true });
        observeButtons();
        return () => {
            treeObserver.disconnect();
            styleObserver.disconnect();
            if (awaitingTimer) clearTimeout(awaitingTimer);
        };
    });

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
        if (isVideos) {
            videoFilters.updateSampleIds([]);
        } else {
            clearRegion();
        }
    };
    // Images and annotations track their committed selection as region geometry, not sample ids:
    // images on the image filter store, annotations in the shared annotation-plot region store.
    const regionSelected = $derived(
        isImages
            ? ($imageFilter?.sample_filter?.embedding_region ?? null) !== null
            : isAnnotations
              ? $annotationPlotRegion !== null
              : false
    );
    const hasActiveSelection = $derived(
        $rangeSelection !== null || activeSampleIds.length > 0 || regionSelected
    );

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

    let viewportState: ViewportState | null = $state(null);
    const onViewportState = (state: ViewportState) => {
        viewportState = state;
    };

    // Hover preview: a controlled tooltip showing a thumbnail of the hovered point.
    // The array-based EmbeddingView only emits hover tooltips when querySelection
    // is provided; ours returns the nearest visible point with its sample ID.
    let tooltip: DataPoint | null = $state(null);
    const onTooltip = (value: DataPoint | null) => {
        tooltip = value;
    };
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
            x: $arrowData?.x as Float32Array | undefined,
            y: $arrowData?.y as Float32Array | undefined,
            sampleIds: $arrowData?.sample_id as string[] | undefined,
            category: $plotData?.category as Uint8Array | undefined
        })
    );
    const resolveThumbnail = $derived.by(() =>
        createThumbnailResolver({
            route: isAnnotations ? 'annotations' : isVideos ? 'videos' : 'images',
            collectionId
        })
    );

    // "N / M points": M is everything plotted, N is what survives the active filters. Points
    // demoted to EXCLUDED_BY_FILTERS are still drawn, just greyed, so they count as hidden.
    const pointCounts = $derived.by(() => {
        const categories = $plotData?.category as Uint8Array | undefined;
        if (!categories) return { visible: 0, total: 0 };
        let visible = 0;
        for (const category of categories) {
            if (category !== EXCLUDED_BY_FILTERS_CATEGORY) visible++;
        }
        return { visible, total: categories.length };
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

<div class="flex min-h-0 flex-1 flex-col" data-testid="plot-panel">
    <div
        class="flex h-[46px] shrink-0 items-center justify-between border-b border-border-hard px-3"
    >
        <div class="text-[13px] font-semibold">Embedding Plot</div>
        <Button
            variant="ghost"
            buttonProps={{
                size: 'icon',
                onclick: handleClose,
                class: 'size-[26px]',
                'data-testid': 'plot-close-button'
            }}
        >
            ✕
        </Button>
    </div>
    <div class="flex min-h-0 flex-1 flex-col">
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
                class="embedding-plot-wrapper relative mx-3 my-2.5 min-h-0 flex-1 overflow-hidden rounded-lg border border-border-hard bg-black"
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
                            tooltip={$rangeSelection ? null : tooltip}
                            {onTooltip}
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

                    {#if hoverPreview}
                        <div
                            class="pointer-events-none absolute z-10 -translate-x-1/2"
                            style="left: {hoverPreview.left}px; top: {hoverPreview.top}px"
                        >
                            <PlotHoverPreview sampleId={hoverPreview.sampleId} {resolveThumbnail} />
                        </div>
                    {/if}

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

                    <div
                        class="absolute bottom-2 left-1/2 z-10 flex -translate-x-1/2 items-center gap-1 rounded-lg border border-white/10 bg-black/60 p-1 backdrop-blur-sm"
                        data-testid="plot-tool-pill"
                    >
                        {#each tools as tool (tool.mode)}
                            {@const Icon = tool.icon}
                            <button
                                type="button"
                                title={tool.label}
                                aria-label={tool.label}
                                aria-pressed={activeTool === tool.mode}
                                data-testid={`plot-tool-${tool.mode}`}
                                onclick={() => selectTool(tool.mode)}
                                class={cn(
                                    'flex size-[26px] items-center justify-center rounded-md text-muted-foreground transition-colors hover:text-foreground',
                                    activeTool === tool.mode && 'bg-white/[0.14] text-foreground'
                                )}
                            >
                                <Icon class="size-[15px]" />
                            </button>
                        {/each}
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
            class="flex min-w-0 shrink-0 items-center gap-2 overflow-x-auto px-3 pb-2.5 text-sm text-muted-foreground"
            data-testid="plot-panel-controls"
        >
            <!--
                The readout used to sit inside the canvas alongside the legend and the tool pill;
                three overlays sharing that bottom strip collided at narrow widths.
            -->
            <span class="shrink-0 text-[11.5px] tabular-nums" data-testid="plot-point-count">
                {pointCounts.visible} / {pointCounts.total} points
            </span>
            <div class="flex-1"></div>
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
        rectangle + lasso tool buttons, a scale bar, and a point count. The redesign
        replaces all of it — the readout moved to the control row, the legend and hover
        card are our own overlays, and selection tools now live in the glass tool pill.
        Keep the strip in the DOM (so `selectTool` can .click() the hidden tool buttons
        and drive the library's sticky selection mode), but make it invisible and
        non-interactive. Use opacity/pointer-events, NOT display:none or
        visibility:hidden: the buttons stay laid out and clickable, and Playwright still
        reports them visible (LIG-7691 e2e asserts the tool buttons toBeVisible).
    */
    :global(.embedding-view div[style*='bottom: 0px'][style*='position: absolute']) {
        opacity: 0 !important;
        pointer-events: none !important;
    }
</style>
