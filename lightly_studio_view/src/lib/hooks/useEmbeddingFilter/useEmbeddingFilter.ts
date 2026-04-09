import { derived, get, writable, type Readable } from 'svelte/store';
import { isNormalModeParams } from '$lib/hooks/useImagesInfinite/useImagesInfinite';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';

type UseEmbeddingFilterParams = {
    collectionId: Readable<string>;
    isVideos: Readable<boolean>;
    isSamples: Readable<boolean>;
    setRangeSelectionForcollection: (collectionId: string, selection: null) => void;
};

export function useEmbeddingFilter({
    collectionId,
    isVideos,
    isSamples,
    setRangeSelectionForcollection
}: UseEmbeddingFilterParams) {
    const { filterParams: imageFilterParams, updateSampleIds: updateImageSampleIds } =
        useImageFilters();
    const { filterParams: videoFilterParams, updateSampleIds: updateVideoSampleIds } =
        useVideoFilters();
    const hiddenEmbeddingFiltersByCollection = writable<Record<string, string[]>>({});

    const activePlotFilterSampleIds = derived(
        [isVideos, isSamples, videoFilterParams, imageFilterParams, collectionId],
        ([$isVideos, $isSamples, $videoFilterParams, $imageFilterParams, $collectionId]) => {
            if ($isVideos) {
                if ($videoFilterParams?.collection_id !== $collectionId) {
                    return [];
                }
                return $videoFilterParams.filters?.sample_ids ?? [];
            }

            if ($isSamples) {
                if (
                    !$imageFilterParams?.collection_id ||
                    $imageFilterParams.collection_id !== $collectionId
                ) {
                    return [];
                }
                if (!isNormalModeParams($imageFilterParams)) {
                    return [];
                }
                return $imageFilterParams.filters?.sample_ids ?? [];
            }

            return [];
        }
    );

    const hiddenEmbeddingFilterSampleIds = derived(
        [hiddenEmbeddingFiltersByCollection, collectionId],
        ([$hiddenEmbeddingFiltersByCollection, $collectionId]) =>
            $hiddenEmbeddingFiltersByCollection[$collectionId] ?? []
    );

    const isPlotFilterApplied = derived(
        activePlotFilterSampleIds,
        ($activeIds) => $activeIds.length > 0
    );
    const effectiveEmbeddingFilterIds = derived(
        [activePlotFilterSampleIds, hiddenEmbeddingFilterSampleIds],
        ([$activeIds, $hiddenIds]) => ($activeIds.length > 0 ? $activeIds : $hiddenIds)
    );
    const plotFilterCount = derived(
        effectiveEmbeddingFilterIds,
        ($effectiveEmbeddingFilterIds) => $effectiveEmbeddingFilterIds.length
    );
    const hasPlotFilterContext = derived(
        [isSamples, isVideos, effectiveEmbeddingFilterIds],
        ([$isSamples, $isVideos, $effectiveEmbeddingFilterIds]) =>
            ($isSamples || $isVideos) && $effectiveEmbeddingFilterIds.length > 0
    );
    const plotFilterItemLabel = derived(isVideos, ($isVideos) =>
        $isVideos ? 'video' : 'sample'
    );

    function updateEmbeddingFilterSampleIds(sampleIds: string[]) {
        if (get(isVideos)) {
            updateVideoSampleIds(sampleIds);
            return;
        }
        if (get(isSamples)) {
            updateImageSampleIds(sampleIds);
        }
    }

    function setHiddenEmbeddingFilters(sampleIds: string[]) {
        hiddenEmbeddingFiltersByCollection.update((current) => ({
            ...current,
            [get(collectionId)]: sampleIds
        }));
    }

    function clearHiddenEmbeddingFilters() {
        setHiddenEmbeddingFilters([]);
    }

    function showEmbeddingFilters() {
        const hiddenSampleIds = get(hiddenEmbeddingFilterSampleIds);
        if (hiddenSampleIds.length === 0) {
            return;
        }

        updateEmbeddingFilterSampleIds(hiddenSampleIds);
        clearHiddenEmbeddingFilters();
    }

    function hideEmbeddingFilters() {
        const activeSampleIds = get(activePlotFilterSampleIds);
        if (activeSampleIds.length === 0) {
            return;
        }

        setHiddenEmbeddingFilters(activeSampleIds);
        updateEmbeddingFilterSampleIds([]);
    }

    function setEmbeddingFilterVisibility(shouldShow: boolean) {
        if (!shouldShow) {
            hideEmbeddingFilters();
            return;
        }
        const alreadyApplied = get(activePlotFilterSampleIds).length > 0;
        const hasHidden = get(hiddenEmbeddingFilterSampleIds).length > 0;
        if (!alreadyApplied && hasHidden) showEmbeddingFilters();
    }

    function clearPlotFilter() {
        const currentCollectionId = get(collectionId);
        setRangeSelectionForcollection(currentCollectionId, null);
        clearHiddenEmbeddingFilters();
        updateEmbeddingFilterSampleIds([]);
    }

    return {
        activePlotFilterSampleIds,
        hiddenEmbeddingFilterSampleIds,
        isPlotFilterApplied,
        effectiveEmbeddingFilterIds,
        plotFilterCount,
        hasPlotFilterContext,
        plotFilterItemLabel,
        setEmbeddingFilterVisibility,
        clearPlotFilter
    };
}
