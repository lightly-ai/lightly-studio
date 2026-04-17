import { browser } from '$app/environment';
import { page } from '$app/state';
import { get } from 'svelte/store';
import { onDestroy, onMount } from 'svelte';
import { useHideAnnotations } from '../useHideAnnotations';
import { useGlobalStorage } from '../useGlobalStorage';
import { useSelectionSummary } from '../useSelectionSummary/useSelectionSummary';
import { useRouteType } from '../useRouteType/useRouteType';
import { useGridTypeManagement } from '../useGridTypeManagement/useGridTypeManagement';
import { useHasEmbeddings } from '../useHasEmbeddings/useHasEmbeddings';
import { useEmbeddingSearch } from '../useEmbeddingSearch/useEmbeddingSearch';
import { useCollectionFilters } from '../useCollectionFilters/useCollectionFilters';
import { useCollectionLayoutProps } from '../useCollectionLayoutProps/useCollectionLayoutProps';
import { useAnnotationCountsAggregation } from '../useAnnotationCountsAggregation/useAnnotationCountsAggregation';
import type { Collection } from '$lib/services/types';
import type { TextEmbedding, GridType } from '$lib/types';
import type { Writable } from 'svelte/store';

/**
 * Master orchestrator hook for collection layout state.
 * Combines all collection-related hooks into a single cohesive interface.
 * This is the single source of truth for all collection layout logic.
 */
export function useCollectionLayoutState({
    collection,
    setTextEmbedding,
    textEmbedding,
    setLastGridType,
    clearSelectedSamples,
    clearSelectedSampleAnnotationCrops
}: {
    collection: Collection;
    setTextEmbedding: (_textEmbedding: TextEmbedding | undefined) => void;
    textEmbedding: Writable<TextEmbedding | undefined>;
    setLastGridType: (gridType: GridType) => void;
    clearSelectedSamples: (collectionId: string) => void;
    clearSelectedSampleAnnotationCrops: (collectionId: string) => void;
}) {
    // Params and base state
    const datasetId = page.params.dataset_id!;
    const collectionId = page.params.collection_id!;

    // Global storage
    const globalStorage = useGlobalStorage();
    const { selectedCount, clearSelection } = useSelectionSummary(collectionId);
    const {
        retrieveParentCollection,
        collections,
        showPlot,
        setShowPlot,
        filteredSampleCount,
        filteredAnnotationCount
    } = globalStorage;
    const parentCollection = retrieveParentCollection(get(collections), collectionId);

    // Keyboard shortcuts
    const { handleKeyEvent } = useHideAnnotations();
    onMount(() => {
        if (browser) {
            window.addEventListener('keydown', handleKeyEvent);
            window.addEventListener('keyup', handleKeyEvent);
        }
    });
    onDestroy(() => {
        if (browser) {
            window.removeEventListener('keydown', handleKeyEvent);
            window.removeEventListener('keyup', handleKeyEvent);
        }
    });

    // Route and grid management
    const routeType = useRouteType();
    const { gridType: gridTypeStore } = useGridTypeManagement({
        collectionId,
        routeType,
        setLastGridType,
        clearSelectedSamples,
        clearSelectedSampleAnnotationCrops
    });
    const gridType = get(gridTypeStore);

    // Embeddings and search - call hooks at top level
    const hasEmbeddingsQuery = useHasEmbeddings({ collectionId });
    const hasEmbeddings = !!get(hasEmbeddingsQuery).data;
    const search = useEmbeddingSearch({ collectionId, textEmbedding, setTextEmbedding });

    // Filters
    const filters = useCollectionFilters({ collectionId });
    const {
        annotationFilterStore,
        annotationFilterRows,
        toggleAnnotationFilterSelection,
        setAnnotationCounts,
        metadataFilters: metadataFiltersStore,
        dimensionsValues,
        videoFramesBoundsValues,
        videoBoundsValues,
        plotSelectionImageSampleIds: plotSelectionImageSampleIdsStore,
        plotSelectionVideoSampleIds: plotSelectionVideoSampleIdsStore
    } = filters;

    const metadataFilters = get(metadataFiltersStore);
    const plotSelectionImageSampleIds = get(plotSelectionImageSampleIdsStore);
    const plotSelectionVideoSampleIds = get(plotSelectionVideoSampleIdsStore);

    // Layout props - call hook at top level
    const layoutPropsResult = useCollectionLayoutProps({
        routeType,
        showPlot: get(showPlot),
        selectedCount: get(selectedCount),
        clearSelection
    });

    // Annotation counts - call hook at top level
    const annotationCountsResult = useAnnotationCountsAggregation({
        routeType,
        collectionId,
        datasetId,
        parentCollection,
        metadataFilters,
        annotationFilter: get(annotationFilterStore),
        dimensionsValues: get(dimensionsValues),
        videoFramesBoundsValues,
        videoBoundsValues,
        plotSelectionImageSampleIds,
        plotSelectionVideoSampleIds,
        onAnnotationCountsChange: setAnnotationCounts
    });
    const totalAnnotations = get(annotationCountsResult.totalAnnotations);

    return {
        collectionId,
        datasetId,
        collection,
        parentCollection,
        routeType,
        gridType,
        hasEmbeddings,
        search,
        annotationFilterRows,
        toggleAnnotationFilterSelection,
        layoutProps: layoutPropsResult,
        totalAnnotations,
        filteredSampleCount,
        filteredAnnotationCount,
        showPlot,
        setShowPlot
    };
}
