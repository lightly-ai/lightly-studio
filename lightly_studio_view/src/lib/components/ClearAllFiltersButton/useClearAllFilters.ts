import { derived, get, readable, type Readable } from 'svelte/store';
import {
    useAnnotationCollectionsFilter,
    useFiltersClearedSignal,
    useGlobalStorage,
    useImageFilters,
    useTags,
    useVideoFramesBounds
} from '$lib/hooks';
import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';
import { useVideoBounds } from '$lib/hooks/useVideosBounds/useVideosBounds';
import { useEmbeddingFilterForImages } from '$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForImages';
import { useEmbeddingFilterForVideos } from '$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForVideos';
import { useEmbeddingFilterForAnnotations } from '$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForAnnotations';
import { getPlotSelectionCount } from '$lib/hooks/useEmbeddingFilter/useEmbeddingPlotSelection';

type Range = { min: number; max: number };
type RangeMap = Partial<Record<string, Range>>;
type Dimensions = Parameters<ReturnType<typeof useDimensions>['updateDimensionsValues']>[0];

interface FilterGroup {
    isActive: Readable<boolean>;
    clear: () => void;
}

interface UseClearAllFiltersParams {
    collectionId: string;
    isImages: boolean;
    isVideos: boolean;
    isVideoFrames: boolean;
}

interface UseClearAllFiltersReturn {
    hasActiveFilters: Readable<boolean>;
    clearAllFilters: () => void;
}

/**
 * Tracks whether any sidebar filter of the current grid is active and resets all of
 * them at once.
 *
 * Covers tags, annotation classes and sources, numeric and categorical metadata,
 * dimensions, video and frame bounds, the embedding plot region, the confusion cell
 * and the query filter, as far as the grid shows them. The sample selection is kept.
 */
export function useClearAllFilters(params: UseClearAllFiltersParams): UseClearAllFiltersReturn {
    const groups = useFilterGroups(params);
    const { signalFiltersCleared } = useFiltersClearedSignal();
    return {
        hasActiveFilters: derived(
            groups.map((group) => group.isActive),
            (active) => active.some(Boolean)
        ),
        clearAllFilters: () => {
            groups.forEach((group) => group.clear());
            signalFiltersCleared();
        }
    };
}

// Only the filters that the sidebar of the current grid shows.
function useFilterGroups(params: UseClearAllFiltersParams): FilterGroup[] {
    const { collectionId, isImages, isVideos, isVideoFrames } = params;
    const groups = [useTagAndLabelFilters(collectionId), useEmbeddingPlotFilter(collectionId)];
    if (isImages || isVideos || isVideoFrames) groups.push(useMetadataFilterGroup());
    if (isImages) {
        groups.push(useDimensionsFilter(), useAnnotationSourcesFilter());
        groups.push(useConfusionCellAndQueryFilter(collectionId));
    }
    if (isVideos) {
        const { videoBounds, videoBoundsValues, updateVideoBoundsValues } = useVideoBounds();
        groups.push(rangeFilter(videoBounds, videoBoundsValues, updateVideoBoundsValues));
    }
    if (isVideoFrames) {
        const frames = useVideoFramesBounds();
        groups.push(
            rangeFilter(
                frames.videoFramesBounds,
                frames.videoFramesBoundsValues,
                frames.updateVideoFramesBoundsValues
            )
        );
    }
    return groups;
}

function useTagAndLabelFilters(collectionId: string): FilterGroup {
    const storage = useGlobalStorage();
    const { tagsSelected, clearTagsSelected } = useTags({
        collection_id: collectionId,
        autoLoad: false
    });
    return {
        isActive: derived(
            [tagsSelected, storage.selectedAnnotationFilterIds],
            ([$tags, $labels]) => $tags.size > 0 || $labels.size > 0
        ),
        clear: () => {
            clearTagsSelected();
            storage.clearSelectedAnnotationFilterIds();
        }
    };
}

function useMetadataFilterGroup(): FilterGroup {
    const storage = useGlobalStorage();
    const numeric = rangeFilter(
        storage.metadataBounds,
        storage.metadataValues,
        storage.updateMetadataValues
    );
    return {
        isActive: derived(
            [numeric.isActive, storage.categoricalMetadataValues],
            ([$numericActive, $categorical]) =>
                $numericActive || Object.values($categorical).some((values) => values.length > 0)
        ),
        clear: () => {
            numeric.clear();
            storage.updateCategoricalMetadataValues({});
        }
    };
}

function useDimensionsFilter(): FilterGroup {
    const { dimensionsBounds, dimensionsValues, updateDimensionsValues } = useDimensions();
    return {
        isActive: derived(
            [dimensionsBounds, dimensionsValues],
            ([$bounds, $values]) => !isSameDimensions($bounds, $values)
        ),
        clear: () => resetToBounds(dimensionsBounds, updateDimensionsValues)
    };
}

function useAnnotationSourcesFilter(): FilterGroup {
    const { selectedCollectionIds, collectionIdToName, setSelectedCollectionIds } =
        useAnnotationCollectionsFilter();
    return {
        isActive: derived([selectedCollectionIds, collectionIdToName], ([$selectedIds, $names]) =>
            Object.keys($names).some((id) => !$selectedIds.includes(id))
        ),
        clear: () => setSelectedCollectionIds(Object.keys(get(collectionIdToName)))
    };
}

function useEmbeddingPlotFilter(collectionId: string): FilterGroup {
    const { setRangeSelectionForCollection } = useGlobalStorage();
    const collectionIdStore = readable(collectionId);
    const embeddingFilters = [
        useEmbeddingFilterForImages(collectionIdStore, setRangeSelectionForCollection),
        useEmbeddingFilterForVideos(collectionIdStore, setRangeSelectionForCollection),
        useEmbeddingFilterForAnnotations(collectionIdStore, setRangeSelectionForCollection)
    ];
    return {
        isActive: derived(getPlotSelectionCount(collectionIdStore), ($count) => $count > 0),
        clear: () => embeddingFilters.forEach((filter) => filter.clearFilter())
    };
}

function useConfusionCellAndQueryFilter(collectionId: string): FilterGroup {
    const { filterParams, imageQueryExpression, updateConfusionCell, updateQueryExpr } =
        useImageFilters();
    const hasConfusionCell = derived(
        filterParams,
        ($params) =>
            $params?.collection_id === collectionId &&
            $params.mode === 'normal' &&
            !!$params.filters?.confusion_cell
    );
    return {
        isActive: derived(
            [hasConfusionCell, imageQueryExpression],
            ([$hasConfusionCell, $query]) => $hasConfusionCell || !!$query?.query_expr_str
        ),
        clear: () => {
            if (get(hasConfusionCell)) updateConfusionCell(null);
            updateQueryExpr(undefined);
        }
    };
}

const rangeFilter = <T extends RangeMap>(
    bounds: Readable<T | null>,
    values: Readable<T | null>,
    update: (value: T) => void
): FilterGroup => ({
    isActive: derived([bounds, values], ([$bounds, $values]) =>
        isAnyRangeNarrowed($bounds, $values)
    ),
    clear: () => resetToBounds(bounds, update)
});

const isAnyRangeNarrowed = (bounds: RangeMap | null, values: RangeMap | null) =>
    !!bounds &&
    !!values &&
    Object.entries(values).some(([key, value]) => {
        const bound = bounds[key];
        return !!bound && !!value && (value.min > bound.min || value.max < bound.max);
    });

const isSameDimensions = (bounds: Dimensions | null, values: Dimensions | null) =>
    !bounds ||
    !values ||
    (bounds.min_width === values.min_width &&
        bounds.max_width === values.max_width &&
        bounds.min_height === values.min_height &&
        bounds.max_height === values.max_height);

const resetToBounds = <T extends object>(
    bounds: Readable<T | null>,
    update: (value: T) => void
) => {
    const value = get(bounds);
    if (value) update(structuredClone(value));
};
