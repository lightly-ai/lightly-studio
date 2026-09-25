<script lang="ts">
    import { browser } from '$app/environment';
    import { page } from '$app/state';
    import {
        Button,
        CombinedMetadataDimensionsFilters,
        DatasetGridHeader,
        Footer,
        LabelsMenu,
        MetadataFilterChips,
        SelectionPill,
        ShowFiltersButton,
        TagsMenu
    } from '$lib/components';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { SidePanelTabs } from '$lib/components';
    import Separator from '$lib/components/ui/separator/separator.svelte';
    import { GripVertical, PanelLeftClose, SlidersHorizontal } from '@lucide/svelte';
    import { onDestroy, onMount } from 'svelte';
    import { afterNavigate } from '$app/navigation';
    import { toStore } from 'svelte/store';
    import { Header } from '$lib/components';
    import MenuDialogHost from '$lib/components/Header/MenuDialogHost.svelte';

    import { useHasEmbeddings } from '$lib/hooks/useHasEmbeddings/useHasEmbeddings';
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useAnnotationsFilter } from '$lib/hooks/useAnnotationsFilter/useAnnotationsFilter';
    import AnnotationCollectionsMenu from '$lib/components/AnnotationCollectionsMenu/AnnotationCollectionsMenu.svelte';
    import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';
    import {
        isAnnotationDetailsRoute,
        isAnnotationsRoute,
        isCaptionsRoute,
        isFrameDetailsRoute,
        isSampleDetailsRoute,
        isImagesRoute,
        isPointCloudsRoute,
        isVideoFramesRoute,
        isVideosRoute,
        isGroupsRoute,
        isGroupDetailsRoute,
        isVideoDetailsRoute
    } from '$lib/routes';
    import type { GridType } from '$lib/types';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage.js';
    import QueryControl from '$lib/components/QueryControl/QueryControl.svelte';
    import { PaneGroup, Pane, PaneResizer } from 'paneforge';
    import { useVideoAnnotationCounts } from '$lib/hooks/useVideoAnnotationsCount/useVideoAnnotationsCount.js';
    import {
        createMetadataFilters,
        useMetadataFilters
    } from '$lib/hooks/useMetadataFilters/useMetadataFilters.js';
    import { useVideoFrameAnnotationCounts } from '$lib/hooks/useVideoFrameAnnotationsCount/useVideoFrameAnnotationsCount.js';
    import { useVideoFramesBounds } from '$lib/hooks/useVideoFramesBounds/useVideoFramesBounds.js';
    import { useVideoBounds } from '$lib/hooks/useVideosBounds/useVideosBounds.js';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
    import { AnnotationCountMode, SampleType } from '$lib/api/lightly_studio_local/types.gen';
    import type { AnnotationsFilter } from '$lib/api/lightly_studio_local/types.gen';
    import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
    import type { CategoryCount } from '$lib/components/BarChart';
    import { buildImageFilter } from '$lib/utils/buildImageFilter';
    import {
        buildVideoAnnotationCountsFilter,
        buildVideoFrameAnnotationCountsFilter
    } from '$lib/utils/buildAnnotationCountsFilters';
    import EmbeddingSelectionFilterItem from '$lib/components/EmbeddingSelectionFilterItem/EmbeddingSelectionFilterItem.svelte';
    import ConfusionCellFilterItem from '$lib/components/ConfusionCellFilterItem';
    import {
        useSelectionSummary,
        useImageAnnotationCounts,
        usePostHog,
        useSeedAnnotationSourceFilter
    } from '$lib/hooks';
    import { useSelectAll } from '$lib/hooks/useSelectAll/useSelectAll';
    import { isEditableTarget, isSelectAllShortcut } from './selectAllShortcut';
    import { shutdownMaskRendererPool } from '$lib/workers/maskRendererPool';
    import { GRID_IMAGE_SEARCH_DROP_EVENT, type GridItemDragData } from '$lib/components/GridItem';
    import { readAnnotationEmbedding } from '$lib/api/lightly_studio_local/sdk.gen';
    import { useSearchEmbedding } from '$lib/hooks/useSearchEmbedding/useSearchEmbedding';
    import { useEvaluationRuns } from '$lib/hooks/useEvaluationRuns/useEvaluationRuns';
    import { clearAnnotationPlotSelection } from '$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForAnnotations';
    import { useCreateClassifiersPanel } from '$lib/hooks/useClassifiers/useCreateClassifiersPanel';
    import { useRefineClassifiersPanel } from '$lib/hooks/useClassifiers/useRefineClassifiersPanel';
    import { isPanelVisible } from './panelVisibility';
    const { data, children } = $props();
    const {
        collection,
        globalStorage: { setLastGridType, clearSelectedSamples, clearSelectedSampleAnnotationCrops }
    } = $derived(data);

    const { trackEvent } = usePostHog();
    const { isCreateClassifiersPanelOpen } = useCreateClassifiersPanel();
    const { isRefineClassifiersPanelOpen } = useRefineClassifiersPanel();

    // The dataset ID actually contains the collection ID.
    const datasetId = $derived(page.params.dataset_id!);
    const collectionId = $derived(page.params.collection_id!);
    const collectionIdStore = toStore(() => collectionId);

    const { selectedCount, clearSelection } = $derived(useSelectionSummary(collectionId));

    // Use hideAnnotations hook
    const { handleKeyEvent } = useHideAnnotations();

    const {
        retrieveParentCollection,
        collections,
        activePanel,
        setActivePanel,
        filterPanelCollapsed,
        toggleFilterPanelCollapsed,
        filteredSampleCount,
        filteredAnnotationCount,
        // Sourced from the stable singleton (not `$derived(data)`) so `search`, created once below,
        // captures a store reference that never goes stale.
        textEmbedding
    } = useGlobalStorage();

    const evaluationRunsQuery = useEvaluationRuns(() => ({ datasetId: collection.dataset_id }));
    const evaluationRuns = $derived(evaluationRunsQuery.data ?? []);

    const parentCollection = $derived.by(() =>
        retrieveParentCollection($collections, collectionId)
    );

    const isImages = $derived(isImagesRoute(page.route.id));
    // Evaluation is currently supported for image collections only. The panel is
    // reachable even with zero runs so users can trigger the first one from the GUI.
    const supportsEvaluation = $derived(isImages);
    const isGroups = $derived(isGroupsRoute(page.route.id));
    const isGroupDetails = $derived(isGroupDetailsRoute(page.route.id));
    const isAnnotations = $derived(isAnnotationsRoute(page.route.id));
    const isSampleDetails = $derived(isSampleDetailsRoute(page.route.id));
    const isAnnotationDetails = $derived(isAnnotationDetailsRoute(page.route.id));
    const isFrameDetails = $derived(isFrameDetailsRoute(page.route.id));
    const isCaptions = $derived(isCaptionsRoute(page.route.id));
    const isVideos = $derived(isVideosRoute(page.route.id));
    const isVideoFrames = $derived(isVideoFramesRoute(page.route.id));
    const isVideoDetails = $derived(isVideoDetailsRoute(page.route.id));
    const isPointClouds = $derived(isPointCloudsRoute(page.route.id));
    // The distribution panel is available on the images and videos grids.
    const supportsDistribution = $derived(isImages || isVideos);
    const canSelectAll = $derived(isImages || isVideos || isVideoFrames || isAnnotations);
    const showAnnotationVisibilityToggle = $derived(
        isAnnotations || isImages || isVideos || isVideoFrames
    );

    let gridType = $state<GridType>('images');
    let lastCollectionId: string | null = null;

    // Select-all hook
    let selectAllHandle = $derived(useSelectAll(collectionId, gridType));

    function handleSelectAllKeydown(event: KeyboardEvent) {
        if (isEditableTarget(event.target) || !isSelectAllShortcut(event)) return;
        if (!isImages && !isVideos && !isVideoFrames && !isAnnotations) return;

        event.preventDefault();
        selectAllHandle.handleSelectAll();
    }

    // Instantiate once (not `$derived`) so the active search survives collection changes: the image
    // and annotation tabs are separate collections, and re-creating the hook per collection would
    // reset the preview chip. `collectionId` is read lazily via the getter when a request fires.
    const search = useSearchEmbedding({
        getCollectionId: () => collectionId,
        embedding: textEmbedding
    });
    const searchImage = search.image;
    const searchPending = search.isPending;

    // Copy a blob object URL into an independent one the caller owns. Used for annotation crop
    // previews, whose source URL is owned by the annotation grid tile and revoked when that grid
    // unmounts (e.g. switching to the images tab). The copy keeps the search chip alive afterwards.
    async function copyBlobObjectUrl(url: string): Promise<string | undefined> {
        try {
            const response = await fetch(url);
            if (!response.ok) return undefined;
            return URL.createObjectURL(await response.blob());
        } catch {
            return undefined;
        }
    }

    async function handleGridImageSearchDrop(event: Event) {
        const { url, fileName, annotationSampleId, annotationCollectionId } = (
            event as CustomEvent<GridItemDragData>
        ).detail;
        try {
            if (annotationSampleId) {
                // Copy the crop preview up front, while the source URL is still guaranteed valid
                // (before the awaited embedding request gives the source tile a chance to unmount).
                const ownedPreviewUrl = await copyBlobObjectUrl(url);
                try {
                    const { data: storedEmbedding } = await readAnnotationEmbedding({
                        path: {
                            collection_id: annotationCollectionId ?? collectionId,
                            sample_id: annotationSampleId
                        },
                        throwOnError: true
                    });
                    search.setEmbedding({
                        queryText: fileName,
                        embedding: storedEmbedding,
                        imagePreview: ownedPreviewUrl
                            ? { name: fileName, previewUrl: ownedPreviewUrl }
                            : undefined
                    });
                } catch (err) {
                    // The copied preview never reached the search, so revoke it here to avoid a leak.
                    if (ownedPreviewUrl) URL.revokeObjectURL(ownedPreviewUrl);
                    throw err;
                }
                return;
            }

            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Failed to fetch dragged image: ${response.statusText}`);
            }
            const blob = await response.blob();
            await search.setImage(new File([blob], fileName, { type: blob.type || 'image/jpeg' }));
        } catch (err: unknown) {
            const message =
                err instanceof Error ? err.message : 'Failed to load dragged image for search';
            search.onError(message);
        }
    }

    afterNavigate(() => {
        trackEvent('collection_opened', {
            dataset_id: collection.dataset_id,
            collection_id: collection.collection_id,
            collection_type: `${collection.sample_type}s`,
            sample_count: collection.total_sample_count
        });
    });

    // Setup event handlers for keyboard shortcuts
    onMount(() => {
        if (browser) {
            window.addEventListener('keydown', handleKeyEvent);
            window.addEventListener('keyup', handleKeyEvent);
            window.addEventListener('keydown', handleSelectAllKeydown);
            window.addEventListener(GRID_IMAGE_SEARCH_DROP_EVENT, handleGridImageSearchDrop);
        }
    });

    onDestroy(() => {
        if (browser) {
            window.removeEventListener('keydown', handleKeyEvent);
            window.removeEventListener('keyup', handleKeyEvent);
            window.removeEventListener('keydown', handleSelectAllKeydown);
            window.removeEventListener(GRID_IMAGE_SEARCH_DROP_EVENT, handleGridImageSearchDrop);
            shutdownMaskRendererPool();
        }
    });
    $effect(() => {
        let nextGridType: GridType | null = null;
        if (isAnnotations) {
            nextGridType = 'annotations';
        } else if (isImages) {
            nextGridType = 'images';
        } else if (isCaptions) {
            nextGridType = 'captions';
        } else if (isVideoFrames) {
            nextGridType = 'video_frames';
        } else if (isVideos) {
            nextGridType = 'videos';
        } else if (isGroups) {
            nextGridType = 'groups';
        }

        if (!nextGridType) {
            return;
        }

        if (lastCollectionId && lastCollectionId !== collectionId) {
            clearSelectedSamples(lastCollectionId);
            clearSelectedSampleAnnotationCrops(lastCollectionId);
            clearAnnotationPlotSelection(lastCollectionId);
        }

        gridType = nextGridType;
        lastCollectionId = collectionId;

        // Temporary hack to remember where the user was when navigating
        // TODO: also remember state of tags, labels, metadata filters etc. Possible store it in pagestate
        setLastGridType(gridType);
    });

    const hasEmbeddingsQuery = useHasEmbeddings(() => ({ collectionId }));
    const hasEmbeddings = $derived(!!hasEmbeddingsQuery.data);
    const hasMediaWithEmbeddings = $derived(
        (isImages || isVideos || isAnnotations) && hasEmbeddings
    );
    const collectionSearchPlaceholder = $derived(
        isAnnotations
            ? 'Search annotations by description or image'
            : 'Search samples by description or image'
    );

    const { metadataValues, categoricalMetadataValues } = $derived.by(() =>
        useMetadataFilters(collectionId)
    );
    const { dimensionsValues } = useDimensions(collectionIdStore);

    const annotationLabelsQuery = useAnnotationLabels(() => ({
        collectionId: collectionId ?? ''
    }));
    const annotationLabelsData = $derived(annotationLabelsQuery?.data);
    const annotationLabelsStore = toStore(() => annotationLabelsData);

    // Initialize annotation filter hook (must be before annotationCounts to avoid init-order crash)
    const {
        annotationFilter: annotationFilterStore,
        annotationFilterRows,
        selectedAnnotationFilterNames,
        toggleAnnotationFilterSelection,
        setAnnotationCounts,
        pruneInvalidSelections
    } = useAnnotationsFilter({
        annotationLabels: annotationLabelsStore
    });

    const metadataFilters = $derived(
        metadataValues
            ? createMetadataFilters($metadataValues, $categoricalMetadataValues)
            : undefined
    );
    const { videoFramesBoundsValues } = useVideoFramesBounds();
    const { videoBoundsValues } = useVideoBounds();

    const { imageFilter: imageFilterFromHook } = useImageFilters();

    const { videoFilter: videoFilterFromHook } = useVideoFilters();
    const plotFilterImageSampleIds = $derived(
        $imageFilterFromHook?.sample_filter?.sample_ids ?? []
    );
    const plotFilterVideoSampleIds = $derived(
        $videoFilterFromHook?.sample_filter?.sample_ids ?? []
    );
    // Query, tag and confusion-cell selections live on the shared image filter's
    // sample_filter. Pull them out so the distribution counts track them too
    // (previously only sample_ids from this filter were forwarded).
    const plotFilterTagIds = $derived($imageFilterFromHook?.sample_filter?.tag_ids ?? []);
    const plotFilterConfusionCell = $derived(
        $imageFilterFromHook?.sample_filter?.confusion_cell ?? null
    );
    const plotFilterQueryExpr = $derived($imageFilterFromHook?.sample_filter?.query_expr ?? null);

    // Fill the annotation source filter for whatever collection is on screen. Every grid draws
    // its boxes against this one selection, so seeding only from the images-grid menu left the
    // other tabs filtering against another tab's sources.
    useSeedAnnotationSourceFilter(() => collectionId);

    // Selected annotation sources (annotation collections). When a subset is
    // selected the distribution counts only annotations from those sources; the
    // backend restricts the counted annotations by their own collection id.
    const { selectedCollectionIds: selectedAnnotationSourceIds, allSourcesHidden } =
        useAnnotationCollectionsFilter();
    const annotationFilterForCounts = $derived.by<AnnotationsFilter | undefined>(() => {
        const base = $annotationFilterStore;
        const sourceIds =
            isAnnotations || isAnnotationDetails ? [collectionId] : $selectedAnnotationSourceIds;
        // An empty list cannot be sent: the backend skips collection_ids when it is falsy, so
        // it would read as "every source". The unchecked-everything case is handled on the
        // results instead, via allSourcesHidden below.
        if (sourceIds.length === 0) return base;
        return {
            ...(base ?? { filter_type: 'annotations' }),
            collection_ids: sourceIds
        };
    });

    // Image-count filter shared by the mix and per-type distribution queries so
    // the distribution plot tracks the active filters (dimensions, labels,
    // metadata, query, tags, confusion cell and annotation sources).
    const imageAnnotationCountsFilter = $derived(
        buildImageFilter({
            dimensionsValues: $dimensionsValues,
            annotationFilter: annotationFilterForCounts,
            metadataFilters,
            sampleIds: isAnnotations ? [] : plotFilterImageSampleIds,
            tagIds: isAnnotations ? [] : plotFilterTagIds,
            confusionCell: isAnnotations ? null : plotFilterConfusionCell,
            queryExpr: isAnnotations ? null : plotFilterQueryExpr
        })
    );

    // Annotations of video frames are counted against the frame collection, which
    // is the parent of the annotation collection the route points at.
    const isVideoFrameAnnotations = $derived(
        isAnnotations && parentCollection?.sampleType == SampleType.VIDEO_FRAME
    );

    // The count queries skip the request while every annotation source is unchecked:
    // their results are replaced with an empty list (see annotationCountsData).
    const imageAnnotationCountsQuery = useImageAnnotationCounts(() => ({
        collectionId: datasetId,
        filter: imageAnnotationCountsFilter,
        enabled: !isVideos && !isVideoFrames && !isVideoFrameAnnotations && !$allSourcesHidden
    }));

    const videoAnnotationCountsQuery = useVideoAnnotationCounts(() => ({
        collectionId,
        filter: buildVideoAnnotationCountsFilter({
            metadataFilters,
            annotationFilter: $annotationFilterStore,
            videoBoundsValues: $videoBoundsValues,
            sampleIds: plotFilterVideoSampleIds
        }),
        enabled: isVideos
    }));

    const videoFrameCountsCollectionId = $derived(
        isVideoFrameAnnotations ? (parentCollection?.collectionId ?? collectionId) : collectionId
    );

    const annotationCounts = $derived.by(() => {
        if (isVideoFrames || isVideoFrameAnnotations) {
            return useVideoFrameAnnotationCounts({
                collectionId: videoFrameCountsCollectionId,
                filter: buildVideoFrameAnnotationCountsFilter({
                    metadataFilters,
                    annotationFilter: $annotationFilterStore,
                    videoFramesBoundsValues: $videoFramesBoundsValues
                })
            });
        }
        if (isVideos) {
            return videoAnnotationCountsQuery;
        }
        return imageAnnotationCountsQuery;
    });

    // With every known source unchecked nothing is drawn, so nothing is counted either.
    // The request itself cannot say that, so the empty result is produced here.
    const annotationCountsData = $derived($allSourcesHidden ? [] : annotationCounts.data);

    // Feed annotation counts back into the hook for UI-ready filter rows.
    // Only update when data is present to avoid flicker during query refetch.
    $effect(() => {
        const countsData = annotationCountsData;
        if (countsData) {
            setAnnotationCounts(
                countsData as { label_name: string; total_count: number; current_count?: number }[]
            );
            // Drop selected label filters whose label is absent from the fresh,
            // source-scoped counts (e.g. after switching to a source that doesn't
            // contain the label) so the active filter never points at a hidden label.
            // Cached rows can be stale while their refetch runs. Pruning on them would
            // move the query to another key and abort that refetch, so wait for it.
            if (!annotationCounts.isFetching) {
                pruneInvalidSelections();
            }
        }
    });

    const totalAnnotations = $derived.by(() => {
        const countsData = annotationCountsData;
        if (!countsData) return 0;
        return countsData.reduce(
            (sum: number, item: { [key: string]: string | number }) =>
                sum + Number(item.total_count),
            0
        );
    });

    const isCollectionGrid = $derived(
        isImages || isAnnotations || isVideos || isVideoFrames || isGroups || isPointClouds
    );
    const hasFilterPanel = $derived(isCollectionGrid && !isPointClouds);

    const panelIsVisible = $derived(
        isPanelVisible($activePanel, isImages, hasMediaWithEmbeddings, supportsDistribution)
    );

    // False only once annotation labels have loaded and come back empty — not
    // while loading, and not just because current filters hide every class.
    const hasAnnotationClasses = $derived(
        annotationLabelsData === undefined || annotationLabelsData.length > 0
    );

    // Clicking a class bar toggles the same annotation-label filter as the
    // sidebar's LabelsMenu, so the plot and sidebar stay in sync.
    const handleClassBarClick = (item: CategoryCount) => {
        toggleAnnotationFilterSelection(item.label, collectionId);
    };

    const distributionPanelVisible = $derived(
        $activePanel === 'distribution' && supportsDistribution
    );

    // The distribution settings live here, so they stay when the panel closes and opens again.
    let distributionCountMode = $state<AnnotationCountMode>(AnnotationCountMode.OBJECTS);
    let distributionSampleTagIds = $state<string[]>([]);
    let histogramBinCount = $state(20);

    function handleCombinedMetadataFilterChanged(fieldName: string, min: number, max: number) {
        trackEvent('metadata_filter_changed', {
            collection_id: collectionId,
            field_name: fieldName,
            action: 'range_changed',
            min,
            max
        });
    }
</script>

<div class="flex-none">
    <Header {collection} />
    <MenuDialogHost {isImages} {isVideos} {hasEmbeddings} {collection} />
</div>

<div class="relative flex min-h-0 flex-1 flex-col">
    {#if isSampleDetails || isAnnotationDetails || isGroupDetails || isVideoDetails || isFrameDetails}
        {@render children()}
    {:else}
        <div class="flex min-h-0 flex-1 gap-4 px-4" data-testid="workspace-body">
            {#if hasFilterPanel}
                <!--
                    Keep the panel mounted while collapsed (only visually hidden). Its children
                    run mount-time $effects that must still fire after a reload with the panel
                    collapsed.
                -->
                <div
                    class="h-full min-h-0 w-80 flex-col {$filterPanelCollapsed ? 'hidden' : 'flex'}"
                    data-testid="filter-panel-body"
                    aria-hidden={$filterPanelCollapsed}
                >
                    <div class="flex min-h-0 flex-1 flex-col rounded-[1vw] bg-card py-4">
                        <div
                            class="min-h-0 flex-1 space-y-2 overflow-y-auto px-4 pb-2 dark:[color-scheme:dark]"
                        >
                            <h2
                                class="flex items-center justify-between py-2 text-lg font-semibold"
                            >
                                <span class="flex items-center space-x-2">
                                    <SlidersHorizontal class="size-5" />
                                    <span>Filters</span>
                                </span>
                                <Tooltip content="Hide filters" position="bottom" class="w-max">
                                    <Button
                                        variant="ghost"
                                        icon={PanelLeftClose}
                                        ariaLabel="Hide filters"
                                        buttonProps={{
                                            onclick: toggleFilterPanelCollapsed,
                                            'aria-expanded': true,
                                            'data-testid': 'filter-panel-collapse',
                                            class: 'size-6 p-0'
                                        }}
                                    />
                                </Tooltip>
                            </h2>

                            {#if isImages}
                                <QueryControl
                                    onOpen={() => {
                                        setActivePanel(
                                            $activePanel === 'queryEditor' ? 'none' : 'queryEditor'
                                        );
                                    }}
                                />
                            {/if}

                            <div>
                                <TagsMenu collection_id={collectionId} {gridType} />
                            </div>

                            <EmbeddingSelectionFilterItem
                                {collectionIdStore}
                                {isVideos}
                                {isImages}
                                {isAnnotations}
                            />
                            {#if isImages}
                                <ConfusionCellFilterItem />
                            {/if}
                            {#if isImages}
                                <AnnotationCollectionsMenu {collectionId} />
                            {/if}
                            <LabelsMenu
                                {annotationFilterRows}
                                onToggleAnnotationFilter={(label) =>
                                    toggleAnnotationFilterSelection(label, collectionId)}
                                showVisibilityToggle={showAnnotationVisibilityToggle}
                            />

                            {#if isImages || isVideos || isVideoFrames}
                                {#key collectionId}
                                    <MetadataFilterChips {collectionId} />
                                    <CombinedMetadataDimensionsFilters
                                        {isVideos}
                                        {isVideoFrames}
                                        onFilterChanged={handleCombinedMetadataFilterChanged}
                                    />
                                {/key}
                            {/if}
                        </div>
                    </div>
                </div>
            {/if}

            {#snippet mainContent()}
                {#if isCollectionGrid}
                    <div class="flex min-w-0 items-center gap-x-4">
                        {#if hasFilterPanel && $filterPanelCollapsed}
                            <ShowFiltersButton />
                        {/if}
                        <div class="min-w-0 flex-1">
                            <DatasetGridHeader
                                {collectionId}
                                {canSelectAll}
                                isSelectionActive={$selectedCount > 0}
                                {isImages}
                                {isVideos}
                                {isAnnotations}
                                {hasMediaWithEmbeddings}
                                collectionDatasetId={collection.dataset_id}
                                onSelectAll={selectAllHandle.handleSelectAll}
                                onDeselectAll={clearSelection}
                                searchImage={$searchImage}
                                searchPending={$searchPending}
                                searchPlaceholder={collectionSearchPlaceholder}
                                initialQueryText={$textEmbedding?.queryText ?? ''}
                                onSubmitText={search.setText}
                                onSubmitFile={search.setImage}
                                onSearchClear={search.clear}
                                onSearchError={search.onError}
                            />
                        </div>
                    </div>
                    <Separator class="mb-4 bg-border-hard" />
                {/if}

                <div class="flex min-h-0 min-w-0 flex-1 overflow-hidden">
                    {@render children()}
                </div>
                {#if isCollectionGrid}
                    <SelectionPill selectedCount={$selectedCount} onClear={clearSelection} />
                {/if}
            {/snippet}

            {#snippet paneResizer()}
                <PaneResizer
                    class="relative mx-2 flex w-1 cursor-col-resize items-center justify-center"
                >
                    <div class="bg-brand z-10 flex h-7 min-w-5 items-center justify-center">
                        <GripVertical class="text-diffuse-foreground" />
                    </div>
                </PaneResizer>
            {/snippet}

            {#if panelIsVisible}
                <div data-testid="pane-group-layout" class="contents">
                    <PaneGroup direction="horizontal" class="min-w-0 flex-1">
                        <Pane defaultSize={65} minSize={35} class="flex">
                            <div
                                class="relative flex min-w-0 flex-1 flex-col space-y-4 rounded-[1vw] bg-card p-4 pb-2"
                            >
                                {@render mainContent()}
                            </div>
                        </Pane>

                        {@render paneResizer()}

                        <Pane defaultSize={35} minSize={25} class="flex min-h-0 flex-col">
                            {#if $activePanel === 'evaluationRuns' && supportsEvaluation}
                                {#await import('$lib/components/EvaluationRunsPanel/EvaluationRunsPanel.svelte') then { default: EvaluationRunsPanel }}
                                    <EvaluationRunsPanel
                                        onClose={() => setActivePanel('none')}
                                        {evaluationRuns}
                                        isLoading={evaluationRunsQuery.isLoading}
                                        error={evaluationRunsQuery.error?.message}
                                        datasetId={collection.dataset_id}
                                        {collectionId}
                                    />
                                {/await}
                            {:else if $activePanel === 'embeddingPlot' && hasMediaWithEmbeddings}
                                {#await import('$lib/components/PlotPanel/PlotPanel.svelte') then { default: PlotPanel }}
                                    <!-- PlotPanel captures collectionId at mount; remount it when
                                     switching collections (e.g. images <-> annotations tab). -->
                                    {#key collectionId}
                                        <PlotPanel {collectionId} />
                                    {/key}
                                {/await}
                            {:else if $activePanel === 'queryEditor' && isImages}
                                {#await import('$lib/components/QueryEditorPanel/QueryEditorPanel.svelte') then { default: QueryEditorPanel }}
                                    <QueryEditorPanel onClose={() => setActivePanel('none')} />
                                {/await}
                            {:else if distributionPanelVisible && isVideos}
                                {#await import('./VideoDistributionPanel/VideoDistributionPanel.svelte') then { default: VideoDistributionPanel }}
                                    {#key collectionId}
                                        <VideoDistributionPanel
                                            {collectionId}
                                            {hasAnnotationClasses}
                                            selectedClassNames={$selectedAnnotationFilterNames}
                                            onClassBarClick={handleClassBarClick}
                                            onClose={() => setActivePanel('none')}
                                            bind:histogramBinCount
                                        />
                                    {/key}
                                {/await}
                            {:else if distributionPanelVisible}
                                {#await import('./ImageDistributionPanel/ImageDistributionPanel.svelte') then { default: ImageDistributionPanel }}
                                    {#key collectionId}
                                        <ImageDistributionPanel
                                            {collectionId}
                                            {datasetId}
                                            filter={imageAnnotationCountsFilter}
                                            annotationCounts={annotationCounts.data}
                                            {hasAnnotationClasses}
                                            selectedClassNames={$selectedAnnotationFilterNames}
                                            onClassBarClick={handleClassBarClick}
                                            onClose={() => setActivePanel('none')}
                                            bind:countMode={distributionCountMode}
                                            bind:histogramBinCount
                                            bind:comparisonTagIds={distributionSampleTagIds}
                                        />
                                    {/key}
                                {/await}
                            {/if}
                        </Pane>
                    </PaneGroup>
                </div>
            {:else}
                <!-- Normal layout (no side panel) -->
                <div
                    class="relative flex min-w-0 flex-1 flex-col space-y-4 rounded-[1vw] bg-card p-4 pb-2"
                >
                    {@render mainContent()}
                </div>
            {/if}
            {#if isCollectionGrid && (isImages || supportsDistribution || hasMediaWithEmbeddings)}
                <div data-testid="side-panel-tabs" class="contents">
                    <SidePanelTabs
                        {collectionId}
                        {isImages}
                        {hasMediaWithEmbeddings}
                        {supportsEvaluation}
                        {supportsDistribution}
                    />
                </div>
            {/if}
            {#if hasEmbeddings && $isCreateClassifiersPanelOpen}
                {#await import('$lib/components/FewShotClassifier/CreateClassifierDialog.svelte') then { default: CreateClassifierDialog }}
                    <CreateClassifierDialog />
                {/await}
            {/if}
            {#if hasEmbeddings && $isRefineClassifiersPanelOpen}
                {#await import('$lib/components/FewShotClassifier/RefineClassifierDialog.svelte') then { default: RefineClassifierDialog }}
                    <RefineClassifierDialog />
                {/await}
            {/if}
        </div>
        <Footer
            totalSamples={collection?.total_sample_count}
            filteredSamples={$filteredSampleCount}
            {totalAnnotations}
            filteredAnnotations={$filteredAnnotationCount}
        />
    {/if}
</div>
