<script lang="ts">
    import { browser } from '$app/environment';
    import { page } from '$app/state';
    import {
        AppSidebar,
        CombinedMetadataDimensionsFilters,
        ContentHeader,
        DatasetGridHeader,
        LabelsMenu,
        MetadataFilterChips,
        StatusBar,
        TagsMenu
    } from '$lib/components';
    import { SidePanelTabs } from '$lib/components';
    import Separator from '$lib/components/ui/separator/separator.svelte';
    import { GripVertical } from '@lucide/svelte';
    import { onDestroy, onMount } from 'svelte';
    import { afterNavigate, goto } from '$app/navigation';
    import { toStore } from 'svelte/store';
    import Menu from '$lib/components/Header/Menu.svelte';
    import MenuDialogHost from '$lib/components/Header/MenuDialogHost.svelte';
    import EditModeControls from '$lib/components/EditModeControls/EditModeControls.svelte';
    import UserAvatar from '$lib/components/UserAvatar/UserAvatar.svelte';
    import AnnotationTypesMenu from '$lib/components/AnnotationTypesMenu/AnnotationTypesMenu.svelte';
    import { buildSidebarNavItems } from '$lib/components/AppSidebar/SidebarNav/buildSidebarNavItems';
    import { useAnnotationTypeFilter } from '$lib/hooks/useAnnotationTypeFilter/useAnnotationTypeFilter';
    import { useImageAnnotationTypeCounts } from '$lib/hooks/useImageAnnotationTypeCounts/useImageAnnotationTypeCounts.svelte';
    import {
        useCollectionWithChildren,
        useRootCollection
    } from '$lib/hooks/useCollection/useCollection';
    import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
    import { useExportDialog } from '$lib/hooks/useExportDialog/useExportDialog';
    import { useResetFilters } from '$lib/hooks/useResetFilters/useResetFilters';
    import useAuth from '$lib/hooks/useAuth/useAuth';

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
        isVideoFramesRoute,
        isVideosRoute,
        isGroupsRoute,
        isGroupDetailsRoute,
        isVideoDetailsRoute,
        routeHelpers,
        routes
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
    import {
        AnnotationCountMode,
        AnnotationType,
        SampleType
    } from '$lib/api/lightly_studio_local/types.gen';
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
    import {
        useSelectionSummary,
        useImageAnnotationCounts,
        useImageAnnotationCountsQueryKey,
        useNumericMetadataDistribution,
        usePostHog,
        useCategoricalMetadataDistribution,
        useSeedAnnotationSourceFilter
    } from '$lib/hooks';
    import { useSelectAll } from '$lib/hooks/useSelectAll/useSelectAll';
    import { isInputElement } from '$lib/utils';
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

    const {
        metadataValues,
        metadataBounds,
        metadataInfo,
        categoricalMetadataValues,
        updateMetadataValues,
        updateCategoricalMetadataValues
    } = $derived.by(() => useMetadataFilters(collectionId));
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
    const { annotationTypes: selectedAnnotationTypes } = useAnnotationTypeFilter();

    const annotationFilterForCounts = $derived.by<AnnotationsFilter | undefined>(() => {
        const base = $annotationFilterStore;
        const withTypes: AnnotationsFilter | undefined = $selectedAnnotationTypes
            ? {
                  ...(base ?? { filter_type: 'annotations' }),
                  annotation_types: $selectedAnnotationTypes
              }
            : base;
        const sourceIds =
            isAnnotations || isAnnotationDetails ? [collectionId] : $selectedAnnotationSourceIds;
        // An empty list cannot be sent: the backend skips collection_ids when it is falsy, so
        // it would read as "every source". The unchecked-everything case is handled on the
        // results instead, via allSourcesHidden below.
        if (sourceIds.length === 0) return withTypes;
        return {
            ...(withTypes ?? { filter_type: 'annotations' }),
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

    // Distribution queries always show the full dataset so bar heights stay
    // stable as sidebar filters are applied.  Filtering is communicated through
    // bar colour (green = in selection, grey = out of selection) rather than
    // through shrinking bars, which loses the original distribution context.
    // Tag / sample / confusion-cell / query context is kept so the distributions
    // stay scoped to the collection the user is currently exploring.
    const distributionBaseFilter = $derived(
        buildImageFilter({
            dimensionsValues: null,
            annotationFilter: undefined,
            metadataFilters: undefined,
            sampleIds: isAnnotations ? [] : plotFilterImageSampleIds,
            tagIds: isAnnotations ? [] : plotFilterTagIds,
            confusionCell: isAnnotations ? null : plotFilterConfusionCell,
            queryExpr: isAnnotations ? null : plotFilterQueryExpr
        })
    );

    const imageAnnotationCountsQuery = useImageAnnotationCounts(() => ({
        collectionId: datasetId,
        filter: imageAnnotationCountsFilter,
        enabled: !isVideos && !isVideoFrames
    }));

    // The Annotation Types group counts against every filter *except* its own, so checking a
    // type doesn't zero out the rows next to it and leave the user unable to compare.
    const annotationTypeCountsFilter = $derived(
        buildImageFilter({
            dimensionsValues: $dimensionsValues,
            annotationFilter: $annotationFilterStore,
            metadataFilters,
            sampleIds: plotFilterImageSampleIds,
            tagIds: plotFilterTagIds,
            confusionCell: plotFilterConfusionCell,
            queryExpr: plotFilterQueryExpr
        })
    );

    const annotationTypeCountsQuery = useImageAnnotationTypeCounts(() => ({
        collectionId,
        filter: annotationTypeCountsFilter,
        enabled: isImages
    }));
    const annotationTypeCounts = $derived(annotationTypeCountsQuery.data ?? []);

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
            pruneInvalidSelections();
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
        isImages || isAnnotations || isVideos || isVideoFrames || isGroups
    );

    const panelIsVisible = $derived(isPanelVisible($activePanel, isImages, hasMediaWithEmbeddings));

    // Class counts for the distribution panel. The "All types" source reuses the
    // shared annotation-count query that feeds the labels filter; the per-type
    // sources fetch classification / detection / segmentation counts on demand
    // while the panel is open. We map `current_count` so the plot tracks the
    // active filters, dropping labels with no matches in the current view.
    // Same rule as annotationCountsData: with every source hidden the class distribution has
    // nothing to show, whichever count query it came from.
    const toCategoryCounts = (countsData: unknown[] | undefined) =>
        ($allSourcesHidden ? [] : (countsData ?? []))
            .map((item) => {
                const row = item as { [key: string]: unknown };
                return { label: String(row['label_name']), count: Number(row['current_count']) };
            })
            .filter((item) => item.count > 0);

    const classDistributionCounts = $derived(toCategoryCounts(annotationCounts.data));

    const distributionPanelVisible = $derived($activePanel === 'distribution' && isImages);

    // Global count mode for the distribution panel (applies to all sources).
    let distributionCountMode = $state<AnnotationCountMode>(AnnotationCountMode.OBJECTS);

    // Only create the per-type queries while the panel is open so we don't fetch
    // extra count queries on every collection view.
    // The 'all' query uses a suffixed key so its cache entry is isolated from
    // the shared annotationCounts query (labels filter). TanStack's prefix
    // matching ensures mutation invalidations still reach it.
    const distributionAllQueryKey = [...useImageAnnotationCountsQueryKey, 'distribution'];

    const distributionAllQuery = useImageAnnotationCounts(() => ({
        collectionId: datasetId,
        filter: imageAnnotationCountsFilter,
        countMode: distributionCountMode,
        queryKey: distributionAllQueryKey,
        enabled: distributionPanelVisible
    }));

    const distributionClassificationQuery = useImageAnnotationCounts(() => ({
        collectionId: datasetId,
        annotationType: AnnotationType.CLASSIFICATION,
        filter: imageAnnotationCountsFilter,
        countMode: distributionCountMode,
        enabled: distributionPanelVisible
    }));

    const distributionObjectDetectionQuery = useImageAnnotationCounts(() => ({
        collectionId: datasetId,
        annotationType: AnnotationType.OBJECT_DETECTION,
        filter: imageAnnotationCountsFilter,
        countMode: distributionCountMode,
        enabled: distributionPanelVisible
    }));

    const distributionSegmentationQuery = useImageAnnotationCounts(() => ({
        collectionId: datasetId,
        annotationType: AnnotationType.SEGMENTATION_MASK,
        filter: imageAnnotationCountsFilter,
        countMode: distributionCountMode,
        enabled: distributionPanelVisible
    }));

    // The panel's sources are the distribution *types* (class labels,
    // metadata, …); the subset within a type (annotation type, metadata key)
    // is the source's group, picked in a second, contextual dropdown.

    // Class labels: one source, annotation types as groups. The per-type
    // valueNoun from the count-mode work collapses to the source level: in
    // Samples mode everything counts samples, otherwise annotations.
    const classDistributionSource = $derived.by<DistributionSource>(() => {
        const valueNoun =
            distributionCountMode === AnnotationCountMode.SAMPLES ? 'samples' : 'annotations';
        if (!distributionPanelVisible) {
            return {
                id: 'classes',
                label: 'Annotation classes',
                groupLabel: 'Annotation type',
                valueNoun,
                data: classDistributionCounts
            };
        }

        const base = {
            id: 'classes',
            label: 'Annotation classes',
            groupLabel: 'Annotation type',
            valueNoun
        };

        // Use the distribution-specific "all" query so the "All types" group
        // respects distributionCountMode. Fall back to the shared counts while
        // the distribution query is still loading (data === undefined).
        const allDistributionData =
            distributionAllQuery.data !== undefined
                ? toCategoryCounts(distributionAllQuery.data)
                : classDistributionCounts;
        const allTypesGroup = { id: 'all', label: 'All types', data: allDistributionData };

        const perType: {
            id: AnnotationType;
            label: string;
            query: ReturnType<typeof useImageAnnotationCounts>;
        }[] = [
            {
                id: AnnotationType.CLASSIFICATION,
                label: 'Classification',
                query: distributionClassificationQuery
            },
            {
                id: AnnotationType.OBJECT_DETECTION,
                label: 'Object detection',
                query: distributionObjectDetectionQuery
            },
            {
                id: AnnotationType.SEGMENTATION_MASK,
                label: 'Segmentation',
                query: distributionSegmentationQuery
            }
        ];
        const typeGroups = perType
            .map(({ id, label, query }) => ({
                id,
                label,
                data: toCategoryCounts(query.data)
            }))
            // Skip types with no matches in the current view so the picker stays clean.
            .filter((group) => group.data.length > 0);
        // With zero or one populated type, "All types" would just duplicate it —
        // drop the group picker entirely.
        if (typeGroups.length <= 1) return { ...base, data: allDistributionData };
        return { ...base, groups: [allTypesGroup, ...typeGroups] };
    });

    // Numeric metadata fields as histogram groups. Bin edges and counts both
    // span the full collection (distributionBaseFilter strips analysis filters)
    // so bar heights stay stable while the user adjusts sidebar filters.
    // Disabled while the distribution panel is closed to avoid background fetching.
    // User-configurable bin count for the metadata histograms.
    let histogramBinCount = $state(20);

    const metadataHistogramsQuery = useNumericMetadataDistribution(() => ({
        collectionId: collectionId,
        filter: distributionBaseFilter,
        binCount: histogramBinCount,
        enabled: distributionPanelVisible
    }));
    // query.data is already Record<string, HistogramData> — the hook applies
    // selectDistributions internally via the TanStack Query `select` option.
    const metadataDistributions = $derived(metadataHistogramsQuery.data ?? {});

    const categoricalMetadataQuery = useCategoricalMetadataDistribution(() => ({
        collectionId,
        filter: distributionBaseFilter,
        enabled: distributionPanelVisible
    }));
    const categoricalMetadataDistributions = $derived(categoricalMetadataQuery.data ?? {});

    // Second categorical query with the full sidebar filter applied.  Its counts
    // are passed as `filteredBuckets` so each bar can show a grey background at
    // the unfiltered height with a coloured foreground at the filtered height.
    const categoricalMetadataFilteredQuery = useCategoricalMetadataDistribution(() => ({
        collectionId,
        filter: imageAnnotationCountsFilter,
        enabled: distributionPanelVisible
    }));
    // Keep undefined (not {}) while loading so DatasetDistributionPanel defers
    // rendering the background bars until the filtered data is ready.
    const categoricalMetadataFilteredDistributions = $derived(
        categoricalMetadataFilteredQuery.data
    );

    const metadataDistributionSource = $derived.by<DistributionSource | null>(() => {
        const numericKeys = Object.keys(metadataDistributions);
        const categoricalKeys = ($metadataInfo ?? [])
            .filter((info) => info.type === 'string' || info.type === 'boolean')
            .map((info) => info.name);
        if (numericKeys.length === 0 && categoricalKeys.length === 0) return null;
        return {
            id: 'metadata',
            label: 'Metadata',
            groupLabel: 'Metadata key',
            valueNoun: 'samples',
            groups: [
                ...numericKeys.map((key) => ({
                    id: key,
                    label: key,
                    histogram: metadataDistributions[key],
                    // Highlight the active filter range; bins outside it dim.
                    selectedRange: $metadataValues[key]
                })),
                ...categoricalKeys.map((key) => ({
                    id: key,
                    label: key,
                    categorical: {
                        buckets: categoricalMetadataDistributions[key] ?? [],
                        // undefined until the filtered query has returned so the
                        // distribution panel waits before showing background bars.
                        filteredBuckets: categoricalMetadataFilteredDistributions?.[key],
                        selectedValues: $categoricalMetadataValues[key] ?? [],
                        loading: categoricalMetadataQuery.isFetching,
                        error: categoricalMetadataQuery.error?.message
                    }
                }))
            ]
        };
    });

    // Selecting a histogram range (bin click or press-drag-release) narrows
    // the metadata filter for that key; re-selecting the current range resets it.
    const handleDistributionHistogramRangeSelect = (
        metadataKey: string,
        range: { min: number; max: number }
    ) => {
        const bound = $metadataBounds[metadataKey];
        if (!bound) return;
        const current = $metadataValues[metadataKey];
        // Clamp first, then compare: the stored value is always clamped to
        // bound, so checking raw range.min/max would miss re-clicks on bins
        // whose edges fall outside the collection's value range.
        const clampedMin = Math.max(range.min, bound.min);
        const clampedMax = Math.min(range.max, bound.max);
        const isBinAlreadySelected =
            current && current.min === clampedMin && current.max === clampedMax;
        updateMetadataValues({
            ...$metadataValues,
            [metadataKey]: isBinAlreadySelected
                ? { min: bound.min, max: bound.max }
                : { min: clampedMin, max: clampedMax }
        });
    };

    const handleCategoricalValueToggle = (metadataKey: string, value: string | boolean | null) => {
        const selected = $categoricalMetadataValues[metadataKey] ?? [];
        const exists = selected.some((candidate) => Object.is(candidate, value));
        const next = exists
            ? selected.filter((candidate) => !Object.is(candidate, value))
            : [...selected, value];
        updateCategoricalMetadataValues({
            ...$categoricalMetadataValues,
            [metadataKey]: next
        });
    };

    const clearCategoricalValues = (metadataKey: string) => {
        const next = { ...$categoricalMetadataValues };
        delete next[metadataKey];
        updateCategoricalMetadataValues(next);
    };

    const distributionSources = $derived<DistributionSource[]>(
        metadataDistributionSource
            ? [classDistributionSource, metadataDistributionSource]
            : [classDistributionSource]
    );

    function handleCombinedMetadataFilterChanged(fieldName: string, min: number, max: number) {
        trackEvent('metadata_filter_changed', {
            collection_id: collectionId,
            field_name: fieldName,
            action: 'range_changed',
            min,
            max
        });
    }

    // --- App chrome -------------------------------------------------------------------------

    // The dataset's root collection, used for the sidebar's switcher and nav rows. The old
    // header fetched this for its breadcrumb; the sidebar is now its only consumer.
    const { collection: datasetCollection } = useCollectionWithChildren({
        getCollectionId: () => datasetId
    });
    const datasetName = $derived(datasetCollection.data?.name ?? collection.name);

    // The dataset's own sample count, keyed on the stable dataset id rather than the active
    // `collection`. Opening the Annotations tab swaps `collection` for the annotation collection,
    // whose `total_sample_count` is the annotation total; feeding that to the Images nav row (and
    // the switcher subtitle) is what made those counts jump on tab switches. The collection
    // hierarchy (useCollectionWithChildren) carries no per-collection counts, so read the root
    // collection directly. Keyed reactively on `datasetId` so it also tracks a navigation to a
    // different dataset (this layout component is reused across param changes).
    const { collection: rootCollectionQuery } = useRootCollection({
        getCollectionId: () => datasetId
    });
    // On the Images tab the route `collection` already IS the root and the layout load awaited it,
    // so fall back to its count until the query resolves to avoid the number briefly disappearing.
    const rootSampleCount = $derived(
        rootCollectionQuery.data?.total_sample_count ??
            (collectionId === datasetId ? collection.total_sample_count : undefined)
    );

    const navItems = $derived.by(() =>
        datasetCollection.data
            ? buildSidebarNavItems({
                  rootCollection: datasetCollection.data,
                  currentCollectionId: collectionId,
                  datasetId,
                  sampleCount: rootSampleCount,
                  annotationCount: totalAnnotations
              })
            : []
    );

    const { user } = useAuth();
    const { openExportDialog } = useExportDialog();
    let isOverflowMenuOpen = $state(false);

    const annotationSourcesQuery = useAnnotationCollections(() => ({ collectionId }));
    const annotationSourceIds = $derived(
        (annotationSourcesQuery.data ?? []).map((source) => source.collection_id)
    );

    const { resetFilters } = $derived(
        useResetFilters({ collectionId, gridType, annotationSourceIds })
    );

    const isDetailsRoute = $derived(
        isSampleDetails || isAnnotationDetails || isGroupDetails || isVideoDetails || isFrameDetails
    );
    // Every view under this layout wears the same chrome: the grids, the detail routes the
    // sidebar and rail now persist into, and captions, which is not a "collection grid" but
    // still needs the header's edit toggle.
    const showWorkspaceChrome = $derived(isCollectionGrid || isDetailsRoute || isCaptions);

    // The analysis panels only exist alongside a grid, so picking one from a detail view steps
    // back to the grid rather than leaving the rail button looking broken.
    const returnToGrid = () => {
        goto(routeHelpers.toImages(datasetId, page.params.collection_type!, collectionId));
    };

    // The rail persists into the image detail view, so its entries follow the grid it came from
    // rather than disappearing the moment a sample is opened.
    const railIsImages = $derived(isImages || isSampleDetails);
    const railHasEmbeddings = $derived(
        hasMediaWithEmbeddings || (isSampleDetails && hasEmbeddings)
    );

    const viewTitle = $derived(navItems.find((item) => item.isSelected)?.title ?? collection.name);
    const viewCount = $derived(
        isAnnotations || isAnnotationDetails ? totalAnnotations : collection.total_sample_count
    );
</script>

<MenuDialogHost {isImages} {isVideos} {hasEmbeddings} {collection} />

{#snippet sidebarFilters()}
    {#if isImages}
        <QueryControl
            onOpen={() => {
                setActivePanel($activePanel === 'queryEditor' ? 'none' : 'queryEditor');
            }}
        />
    {/if}

    <TagsMenu collection_id={collectionId} {gridType} />

    <EmbeddingSelectionFilterItem {collectionIdStore} {isVideos} {isImages} {isAnnotations} />
    {#if isImages}
        <ConfusionCellFilterItem />
        <AnnotationCollectionsMenu {collectionId} />
        <AnnotationTypesMenu counts={annotationTypeCounts} />
    {/if}
    <LabelsMenu
        {annotationFilterRows}
        onToggleAnnotationFilter={(label) => toggleAnnotationFilterSelection(label, collectionId)}
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
{/snippet}

{#snippet headerActions()}
    <!--
        Views built on SampleDetailsPanel own this toggle in their own breadcrumb row, next to
        the canvas it acts on. Everywhere else it stays here: edit mode also gates grid-level
        actions such as deleting annotations from the annotations grid and editing captions.
    -->
    {#if !isImages && !isSampleDetails && !isAnnotationDetails && !isFrameDetails}
        <EditModeControls {collectionId} />
    {/if}
    <Menu
        {isImages}
        {isVideos}
        {hasEmbeddings}
        {collection}
        {user}
        bind:open={isOverflowMenuOpen}
    />
    {#if user}
        <div data-testid="header-user-avatar">
            <UserAvatar {user} />
        </div>
    {/if}
{/snippet}

{#snippet gridContent()}
    {#if isCollectionGrid}
        <div class="min-w-0 px-3.5">
            <DatasetGridHeader
                {collectionId}
                {canSelectAll}
                isSelectionActive={$selectedCount > 0}
                {isImages}
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
        <Separator class="bg-border-hard" />
    {/if}

    <div class="flex min-h-0 min-w-0 flex-1 overflow-hidden p-3.5">
        {@render children()}
    </div>
{/snippet}

{#snippet paneResizer()}
    <PaneResizer
        class="group relative flex w-1 cursor-col-resize items-center justify-center bg-border-hard/40 transition-colors hover:bg-border-hard/70"
    >
        <div
            class="z-10 flex h-7 w-[7px] items-center justify-center rounded-full bg-border-hard text-diffuse-foreground"
        >
            <GripVertical class="size-3.5" />
        </div>
    </PaneResizer>
{/snippet}

{#snippet sidePanel()}
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
    {:else if distributionPanelVisible}
        {#await import('$lib/components/DatasetDistributionPanel/DatasetDistributionPanel.svelte') then { default: DatasetDistributionPanel }}
            {#key collectionId}
                <DatasetDistributionPanel
                    sources={distributionSources}
                    initialCountMode={distributionCountMode}
                    onClose={() => setActivePanel('none')}
                    onCountModeChange={(mode) => {
                        distributionCountMode = mode;
                    }}
                    onHistogramRangeSelect={handleDistributionHistogramRangeSelect}
                    onCategoricalValueToggle={handleCategoricalValueToggle}
                    onCategoricalValuesClear={clearCategoricalValues}
                    onCategoricalRetry={() => categoricalMetadataQuery.refetch()}
                    {histogramBinCount}
                    onHistogramBinCountChange={(binCount) => (histogramBinCount = binCount)}
                />
            {/key}
        {/await}
    {/if}
{/snippet}

<div class="flex min-h-0 flex-1" data-testid="workspace-body">
    {#if showWorkspaceChrome}
        <AppSidebar
            {datasetName}
            datasetHref={routes.collection.home(
                datasetId,
                collection.sample_type.toLowerCase(),
                datasetId
            )}
            sampleCount={rootSampleCount}
            {navItems}
            collapsed={$filterPanelCollapsed}
            selectedCount={$selectedCount}
            onClearSelection={clearSelection}
            onExportSelection={() => openExportDialog({ collectionId: collection.collection_id })}
            onMoreActions={() => (isOverflowMenuOpen = true)}
            onResetFilters={resetFilters}
            filters={sidebarFilters}
        />
    {/if}

    <div class="flex min-w-0 flex-1 flex-col">
        {#if showWorkspaceChrome}
            <ContentHeader
                title={viewTitle}
                count={viewCount}
                sidebarCollapsed={$filterPanelCollapsed}
                onToggleSidebar={toggleFilterPanelCollapsed}
                actions={headerActions}
            />
        {/if}

        <div class="relative flex min-h-0 flex-1 flex-col">
            {#if isDetailsRoute}
                {@render children()}
            {:else if panelIsVisible}
                <div data-testid="pane-group-layout" class="contents">
                    <PaneGroup direction="horizontal" class="min-h-0 min-w-0 flex-1">
                        <Pane defaultSize={65} minSize={35} class="flex">
                            <div class="relative flex min-w-0 flex-1 flex-col">
                                {@render gridContent()}
                            </div>
                        </Pane>

                        {@render paneResizer()}

                        <Pane
                            defaultSize={35}
                            minSize={25}
                            class="flex min-h-0 flex-col border-l border-border-hard"
                        >
                            {@render sidePanel()}
                        </Pane>
                    </PaneGroup>
                </div>
            {:else}
                {@render gridContent()}
            {/if}
        </div>

        {#if showWorkspaceChrome}
            <!-- No grid is mounted on a detail route, so its filtered count is stale at 0. -->
            <StatusBar
                totalSamples={collection?.total_sample_count}
                filteredSamples={isCollectionGrid
                    ? $filteredSampleCount
                    : collection?.total_sample_count}
                {totalAnnotations}
                filteredAnnotations={$filteredAnnotationCount}
                selectedCount={$selectedCount}
                sourceCount={$selectedAnnotationSourceIds.length}
                classCount={$annotationFilterRows.length}
            />
        {/if}
    </div>

    {#if showWorkspaceChrome && (railIsImages || railHasEmbeddings)}
        <div data-testid="side-panel-tabs" class="contents">
            <SidePanelTabs
                {collectionId}
                isImages={railIsImages}
                hasMediaWithEmbeddings={railHasEmbeddings}
                supportsEvaluation={railIsImages}
                onLeaveDetails={isDetailsRoute ? returnToGrid : undefined}
            />
        </div>
    {/if}
</div>

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
