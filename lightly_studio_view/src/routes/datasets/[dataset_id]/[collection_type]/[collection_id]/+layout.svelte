<script lang="ts">
    import { browser } from '$app/environment';
    import { page } from '$app/state';
    import {
        Button,
        CombinedMetadataDimensionsFilters,
        DatasetGridHeader,
        Footer,
        LabelsMenu,
        SelectionPill,
        ShowFiltersButton,
        TagsMenu
    } from '$lib/components';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import QueryEditorPanel from '$lib/components/QueryEditorPanel/QueryEditorPanel.svelte';
    import { SidePanelTabs } from '$lib/components';
    import Separator from '$lib/components/ui/separator/separator.svelte';
    import { GripVertical, PanelLeftClose, SlidersHorizontal } from '@lucide/svelte';
    import { onDestroy, onMount } from 'svelte';
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
        isSampleDetailsRoute,
        isImagesRoute,
        isVideoFramesRoute,
        isVideosRoute,
        isGroupsRoute,
        isGroupDetailsRoute,
        isVideoDetailsRoute
    } from '$lib/routes';
    import type { GridType } from '$lib/types';
    import { useImageAnnotationCounts } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';
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
    import { AnnotationType, SampleType } from '$lib/api/lightly_studio_local/types.gen';
    import type { AnnotationsFilter } from '$lib/api/lightly_studio_local/types.gen';
    import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
    import type { DistributionSource } from '$lib/components/DatasetDistributionPanel';
    import { buildImageFilter } from '$lib/utils/buildImageFilter';
    import {
        buildVideoAnnotationCountsFilter,
        buildVideoFrameAnnotationCountsFilter
    } from '$lib/utils/buildAnnotationCountsFilters';
    import EmbeddingSelectionFilterItem from '$lib/components/EmbeddingSelectionFilterItem/EmbeddingSelectionFilterItem.svelte';
    import ConfusionCellFilterItem from '$lib/components/ConfusionCellFilterItem';
    import { useSelectionSummary } from '$lib/hooks';
    import { useSelectAll } from '$lib/hooks/useSelectAll/useSelectAll';
    import { isInputElement } from '$lib/utils';
    import { shutdownMaskRendererPool } from '$lib/workers/maskRendererPool';
    import { GRID_IMAGE_SEARCH_DROP_EVENT, type GridItemDragData } from '$lib/components/GridItem';
    import { readAnnotationEmbedding } from '$lib/api/lightly_studio_local/sdk.gen';
    import { useSearchEmbedding } from '$lib/hooks/useSearchEmbedding/useSearchEmbedding';
    import { useEvaluationRuns } from '$lib/hooks/useEvaluationRuns/useEvaluationRuns';
    import { clearAnnotationPlotSelection } from '$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForAnnotations';
    const { data, children } = $props();
    const {
        collection,
        globalStorage: { setLastGridType, clearSelectedSamples, clearSelectedSampleAnnotationCrops }
    } = $derived(data);

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
    const isCaptions = $derived(isCaptionsRoute(page.route.id));
    const isVideos = $derived(isVideosRoute(page.route.id));
    const isVideoFrames = $derived(isVideoFramesRoute(page.route.id));
    const isVideoDetails = $derived(isVideoDetailsRoute(page.route.id));
    const canSelectAll = $derived(isImages || isVideos || isVideoFrames || isAnnotations);
    const showAnnotationVisibilityToggle = $derived(
        isAnnotations || isImages || isVideos || isVideoFrames
    );

    let gridType = $state<GridType>('images');
    let lastCollectionId: string | null = null;

    // Select-all hook
    let selectAllHandle = $derived(useSelectAll(collectionId, gridType));

    function handleSelectAllKeydown(event: KeyboardEvent) {
        if (isInputElement(event.target) || (event.target as HTMLElement)?.isContentEditable)
            return;
        if (event.key !== 'a' || (!event.ctrlKey && !event.metaKey)) return;
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

    const { metadataValues } = $derived.by(() => useMetadataFilters(collectionId));
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
        toggleAnnotationFilterSelection,
        setAnnotationCounts
    } = useAnnotationsFilter({
        annotationLabels: annotationLabelsStore
    });

    const metadataFilters = $derived(
        metadataValues ? createMetadataFilters($metadataValues) : undefined
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

    // Selected annotation sources (annotation collections). When a subset is
    // selected the distribution counts only annotations from those sources; the
    // backend restricts the counted annotations by their own collection id.
    const { selectedCollectionIds: selectedAnnotationSourceIds } = useAnnotationCollectionsFilter();
    const annotationFilterForCounts = $derived.by<AnnotationsFilter | undefined>(() => {
        const base = $annotationFilterStore;
        const sourceIds = isAnnotations ? [] : $selectedAnnotationSourceIds;
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

    const annotationCounts = $derived.by(() => {
        if (
            isVideoFrames ||
            (isAnnotations && parentCollection?.sampleType == SampleType.VIDEO_FRAME)
        ) {
            let videoFrameCollectionId = collectionId;
            if (isAnnotations && parentCollection?.sampleType == SampleType.VIDEO_FRAME) {
                videoFrameCollectionId = parentCollection?.collectionId ?? collectionId;
            }
            return useVideoFrameAnnotationCounts({
                collectionId: videoFrameCollectionId,
                filter: buildVideoFrameAnnotationCountsFilter({
                    metadataFilters,
                    annotationFilter: $annotationFilterStore,
                    videoFramesBoundsValues: $videoFramesBoundsValues
                })
            });
        } else if (isVideos) {
            return useVideoAnnotationCounts({
                collectionId,
                filter: buildVideoAnnotationCountsFilter({
                    metadataFilters,
                    annotationFilter: $annotationFilterStore,
                    videoBoundsValues: $videoBoundsValues,
                    sampleIds: plotFilterVideoSampleIds
                })
            });
        }
        return useImageAnnotationCounts({
            collectionId: datasetId,
            filter: imageAnnotationCountsFilter
        });
    });

    // Feed annotation counts back into the hook for UI-ready filter rows.
    // Only update when data is present to avoid flicker during query refetch.
    $effect(() => {
        const countsData = annotationCounts.data;
        if (countsData) {
            setAnnotationCounts(
                countsData as { label_name: string; total_count: number; current_count?: number }[]
            );
        }
    });

    const totalAnnotations = $derived.by(() => {
        const countsData = annotationCounts.data;
        if (!countsData) return 0;
        return countsData.reduce(
            (sum: number, item: { [key: string]: string | number }) =>
                sum + Number(item.total_count),
            0
        );
    });

    const isCollectionGrid = $derived(
        isImages || isAnnotations || isVideos || isVideoFrames || isGroups
    );

    const panelIsVisible = $derived(
        ($activePanel === 'evaluationRuns' && supportsEvaluation) ||
            ($activePanel === 'embeddingPlot' && hasMediaWithEmbeddings) ||
            ($activePanel === 'queryEditor' && isImages) ||
            ($activePanel === 'distribution' && isImages)
    );

    // Class counts for the distribution panel. The "All types" source reuses the
    // shared annotation-count query that feeds the labels filter; the per-type
    // sources fetch classification / detection / segmentation counts on demand
    // while the panel is open. We map `current_count` so the plot tracks the
    // active filters, dropping labels with no matches in the current view.
    const toCategoryCounts = (
        countsData: { label_name: string; current_count: number }[] | undefined
    ) =>
        (countsData ?? [])
            .map((item) => ({
                label: item.label_name,
                count: Number(item.current_count)
            }))
            .filter((item) => item.count > 0);

    const classDistributionCounts = $derived(
        toCategoryCounts(annotationCounts.data as { label_name: string; current_count: number }[])
    );

    const distributionPanelVisible = $derived($activePanel === 'distribution' && isImages);

    // Only create the per-type queries while the panel is open so we don't fetch
    // three extra count queries on every collection view.
    const distributionTypeQueries = $derived.by(() => {
        if (!distributionPanelVisible) return null;
        return {
            [AnnotationType.CLASSIFICATION]: useImageAnnotationCounts({
                collectionId: datasetId,
                annotationType: AnnotationType.CLASSIFICATION,
                filter: imageAnnotationCountsFilter
            }),
            [AnnotationType.OBJECT_DETECTION]: useImageAnnotationCounts({
                collectionId: datasetId,
                annotationType: AnnotationType.OBJECT_DETECTION,
                filter: imageAnnotationCountsFilter
            }),
            [AnnotationType.SEGMENTATION_MASK]: useImageAnnotationCounts({
                collectionId: datasetId,
                annotationType: AnnotationType.SEGMENTATION_MASK,
                filter: imageAnnotationCountsFilter
            })
        };
    });

    const allTypesSource = $derived<DistributionSource>({
        id: 'all',
        label: 'All types',
        data: classDistributionCounts
    });

    const distributionSources = $derived.by<DistributionSource[]>(() => {
        const typeQueries = distributionTypeQueries;
        if (!typeQueries) return [allTypesSource];
        const perType = [
            { id: AnnotationType.CLASSIFICATION, label: 'Classification' },
            { id: AnnotationType.OBJECT_DETECTION, label: 'Object detection' },
            { id: AnnotationType.SEGMENTATION_MASK, label: 'Segmentation' }
        ];
        const typeSources: DistributionSource[] = [];
        for (const { id, label } of perType) {
            const data = toCategoryCounts(
                typeQueries[id].data as { label_name: string; current_count: number }[]
            );
            // Skip types with no matches in the current view so the selector stays clean.
            if (data.length > 0) typeSources.push({ id, label, data });
        }
        // With a single type, "All types" would just duplicate it — show only
        // the type so the panel's selector stays hidden.
        if (typeSources.length <= 1)
            return typeSources.length === 1 ? typeSources : [allTypesSource];
        return [allTypesSource, ...typeSources];
    });
</script>

<div class="flex-none">
    <Header {collection} />
    <MenuDialogHost {isImages} {isVideos} {hasEmbeddings} {collection} />
</div>

<div class="relative flex min-h-0 flex-1 flex-col">
    {#if isSampleDetails || isAnnotationDetails || isGroupDetails || isVideoDetails}
        {@render children()}
    {:else}
        <div class="flex min-h-0 flex-1 gap-4 px-4">
            {#if isCollectionGrid}
                <!--
                    Keep the panel mounted while collapsed (only visually hidden). Children such as
                    AnnotationCollectionsMenu run mount-time $effects (e.g. seeding the annotation
                    source selection) that must still fire after a reload with the panel collapsed.
                -->
                <div
                    class="h-full min-h-0 w-80 flex-col {$filterPanelCollapsed ? 'hidden' : 'flex'}"
                    data-testid="filter-panel-body"
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
                                onToggleAnnotationFilter={toggleAnnotationFilterSelection}
                                showVisibilityToggle={showAnnotationVisibilityToggle}
                            />

                            {#if isImages || isVideos || isVideoFrames}
                                {#key collectionId}
                                    <CombinedMetadataDimensionsFilters {isVideos} {isVideoFrames} />
                                {/key}
                            {/if}
                        </div>
                    </div>
                </div>
            {/if}

            {#snippet mainContent()}
                {#if isCollectionGrid}
                    <div class="flex min-w-0 items-center gap-x-4">
                        {#if $filterPanelCollapsed}
                            <ShowFiltersButton />
                        {/if}
                        <div class="min-w-0 flex-1">
                            <DatasetGridHeader
                                {canSelectAll}
                                isSelectionActive={$selectedCount > 0}
                                {isImages}
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
                            <QueryEditorPanel onClose={() => setActivePanel('none')} />
                        {:else if distributionPanelVisible}
                            {#await import('$lib/components/DatasetDistributionPanel/DatasetDistributionPanel.svelte') then { default: DatasetDistributionPanel }}
                                <DatasetDistributionPanel
                                    sources={distributionSources}
                                    onClose={() => setActivePanel('none')}
                                />
                            {/await}
                        {/if}
                    </Pane>
                </PaneGroup>
            {:else}
                <!-- Normal layout (no side panel) -->
                <div
                    class="relative flex min-w-0 flex-1 flex-col space-y-4 rounded-[1vw] bg-card p-4 pb-2"
                >
                    {@render mainContent()}
                </div>
            {/if}
            {#if isCollectionGrid && (isImages || hasMediaWithEmbeddings)}
                <SidePanelTabs {isImages} {hasMediaWithEmbeddings} {supportsEvaluation} />
            {/if}
            {#if hasEmbeddings}
                {#await import('$lib/components/FewShotClassifier/CreateClassifierDialog.svelte') then { default: CreateClassifierDialog }}
                    <CreateClassifierDialog />
                {/await}
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
