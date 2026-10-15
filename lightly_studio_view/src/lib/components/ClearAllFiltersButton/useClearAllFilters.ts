import { derived, get, readable, type Readable } from 'svelte/store';
import {
    useAnnotationCollectionsFilter,
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

interface UseClearAllFiltersReturn {
    hasActiveFilters: Readable<boolean>;
    clearAllFilters: () => void;
}

/**
 * Tracks whether any sidebar filter is active and resets all of them at once.
 *
 * Covers tags, annotation classes and sources, numeric and categorical metadata,
 * dimensions, video and frame bounds, the embedding plot region, the confusion cell
 * and the query filter. The sample selection is kept.
 */
export function useClearAllFilters(collectionId: string): UseClearAllFiltersReturn {
    const groups = [
        useRangeFilters(),
        useSelectionFilters(collectionId),
        useImageFilterParams(collectionId)
    ];
    return {
        hasActiveFilters: derived(
            groups.map((group) => group.isActive),
            (active) => active.some(Boolean)
        ),
        clearAllFilters: () => groups.forEach((group) => group.clear())
    };
}

// Range sliders: numeric metadata, image dimensions, video and frame bounds.
function useRangeFilters(): FilterGroup {
    const { metadataBounds, metadataValues, updateMetadataValues } = useGlobalStorage();
    const dimensions = useDimensions();
    const video = useVideoBounds();
    const frames = useVideoFramesBounds();

    const isActive = derived(
        [
            metadataBounds,
            metadataValues,
            video.videoBounds,
            video.videoBoundsValues,
            frames.videoFramesBounds,
            frames.videoFramesBoundsValues,
            dimensions.dimensionsBounds,
            dimensions.dimensionsValues
        ],
        ([$metadataB, $metadataV, $videoB, $videoV, $framesB, $framesV, $dimB, $dimV]) =>
            isAnyRangeNarrowed($metadataB, $metadataV) ||
            isAnyRangeNarrowed($videoB, $videoV) ||
            isAnyRangeNarrowed($framesB, $framesV) ||
            !isSameDimensions($dimB, $dimV)
    );

    const clear = () => {
        resetToBounds(metadataBounds, updateMetadataValues);
        resetToBounds(dimensions.dimensionsBounds, dimensions.updateDimensionsValues);
        resetToBounds(video.videoBounds, video.updateVideoBoundsValues);
        resetToBounds(frames.videoFramesBounds, frames.updateVideoFramesBoundsValues);
    };

    return { isActive, clear };
}

// Checkbox lists: tags, annotation classes, annotation sources, categorical metadata.
function useSelectionFilters(collectionId: string): FilterGroup {
    const storage = useGlobalStorage();
    const { tagsSelected, clearTagsSelected } = useTags({ collection_id: collectionId });
    const sources = useAnnotationCollectionsFilter();

    const isActive = derived(
        [
            tagsSelected,
            storage.selectedAnnotationFilterIds,
            storage.categoricalMetadataValues,
            sources.selectedCollectionIds,
            sources.collectionIdToName
        ],
        ([$tags, $labels, $categorical, $sourceIds, $sourceNames]) =>
            $tags.size > 0 ||
            $labels.size > 0 ||
            Object.values($categorical).some((values) => values.length > 0) ||
            Object.keys($sourceNames).some((id) => !$sourceIds.includes(id))
    );

    const clear = () => {
        clearTagsSelected();
        storage.clearSelectedAnnotationFilterIds();
        storage.updateCategoricalMetadataValues({});
        sources.setSelectedCollectionIds(Object.keys(get(sources.collectionIdToName)));
    };

    return { isActive, clear };
}

// Chips: embedding plot region, confusion cell and query filter.
function useImageFilterParams(collectionId: string): FilterGroup {
    const { setRangeSelectionForCollection } = useGlobalStorage();
    const { filterParams, imageQueryExpression, updateConfusionCell, updateQueryExpr } =
        useImageFilters();
    const collectionIdStore = readable(collectionId);
    const embeddingFilters = [
        useEmbeddingFilterForImages(collectionIdStore, setRangeSelectionForCollection),
        useEmbeddingFilterForVideos(collectionIdStore, setRangeSelectionForCollection),
        useEmbeddingFilterForAnnotations(collectionIdStore, setRangeSelectionForCollection)
    ];

    const isActive = derived(
        [getPlotSelectionCount(collectionIdStore), filterParams, imageQueryExpression],
        ([$plotCount, $filterParams, $query]) =>
            $plotCount > 0 ||
            ($filterParams?.mode === 'normal' && !!$filterParams.filters?.confusion_cell) ||
            !!$query?.query_expr_str
    );

    const clear = () => {
        embeddingFilters.forEach((filter) => filter.clearFilter());
        updateConfusionCell(null);
        updateQueryExpr(undefined);
    };

    return { isActive, clear };
}

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
