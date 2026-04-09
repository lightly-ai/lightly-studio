import { derived, get, writable, type Readable } from 'svelte/store';
import {
    isNormalModeParams
} from '$lib/hooks/useImagesInfinite/useImagesInfinite';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import {
    useVideoFilters
} from '$lib/hooks/useVideoFilters/useVideoFilters';

type UseEmbeddingSelectionParams = {
    collectionId: Readable<string>;
    isVideos: Readable<boolean>;
    isSamples: Readable<boolean>;
    setRangeSelectionForcollection: (collectionId: string, selection: null) => void;
};

export function useEmbeddingSelection({
    collectionId,
    isVideos,
    isSamples,
    setRangeSelectionForcollection
}: UseEmbeddingSelectionParams) {
    const { filterParams: imageFilterParams, updateSampleIds: updateImageSampleIds } =
        useImageFilters();
    const { filterParams: videoFilterParams, updateSampleIds: updateVideoSampleIds } =
        useVideoFilters();
    const hiddenEmbeddingSelectionsByCollection = writable<Record<string, string[]>>({});

    const activePlotSelectionSampleIds = derived(
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

    const hiddenEmbeddingSelectionSampleIds = derived(
        [hiddenEmbeddingSelectionsByCollection, collectionId],
        ([$hiddenEmbeddingSelectionsByCollection, $collectionId]) =>
            $hiddenEmbeddingSelectionsByCollection[$collectionId] ?? []
    );

    const isPlotSelectionApplied = derived(
        activePlotSelectionSampleIds,
        ($activeIds) => $activeIds.length > 0
    );
    const effectiveEmbeddingSelectionIds = derived(
        [activePlotSelectionSampleIds, hiddenEmbeddingSelectionSampleIds],
        ([$activeIds, $hiddenIds]) => ($activeIds.length > 0 ? $activeIds : $hiddenIds)
    );
    const plotSelectionCount = derived(
        effectiveEmbeddingSelectionIds,
        ($effectiveEmbeddingSelectionIds) => $effectiveEmbeddingSelectionIds.length
    );
    const hasPlotSelectionContext = derived(
        [isSamples, isVideos, effectiveEmbeddingSelectionIds],
        ([$isSamples, $isVideos, $effectiveEmbeddingSelectionIds]) =>
            ($isSamples || $isVideos) && $effectiveEmbeddingSelectionIds.length > 0
    );
    const plotSelectionItemLabel = derived(isVideos, ($isVideos) =>
        $isVideos ? 'video' : 'sample'
    );

    function updateEmbeddingSelectionSampleIds(sampleIds: string[]) {
        if (get(isVideos)) {
            updateVideoSampleIds(sampleIds);
            return;
        }
        if (get(isSamples)) {
            updateImageSampleIds(sampleIds);
        }
    }

    function setHiddenEmbeddingSelections(sampleIds: string[]) {
        hiddenEmbeddingSelectionsByCollection.update((current) => ({
            ...current,
            [get(collectionId)]: sampleIds
        }));
    }

    function clearHiddenEmbeddingSelections() {
        setHiddenEmbeddingSelections([]);
    }

    function showEmbeddingSelections() {
        const hiddenSampleIds = get(hiddenEmbeddingSelectionSampleIds);
        if (hiddenSampleIds.length === 0) {
            return;
        }

        updateEmbeddingSelectionSampleIds(hiddenSampleIds);
        clearHiddenEmbeddingSelections();
    }

    function hideEmbeddingSelections() {
        const activeSampleIds = get(activePlotSelectionSampleIds);
        if (activeSampleIds.length === 0) {
            return;
        }

        setHiddenEmbeddingSelections(activeSampleIds);
        updateEmbeddingSelectionSampleIds([]);
    }

    function setEmbeddingSelectionVisibility(shouldShow: boolean) {
        if (!shouldShow) {
            hideEmbeddingSelections();
            return;
        }
        const alreadyApplied = get(activePlotSelectionSampleIds).length > 0;
        const hasHidden = get(hiddenEmbeddingSelectionSampleIds).length > 0;
        if (!alreadyApplied && hasHidden) showEmbeddingSelections();
    }

    function clearPlotSelection() {
        const currentCollectionId = get(collectionId);
        setRangeSelectionForcollection(currentCollectionId, null);
        clearHiddenEmbeddingSelections();
        updateEmbeddingSelectionSampleIds([]);
    }

    return {
        activePlotSelectionSampleIds,
        hiddenEmbeddingSelectionSampleIds,
        isPlotSelectionApplied,
        effectiveEmbeddingSelectionIds,
        plotSelectionCount,
        hasPlotSelectionContext,
        plotSelectionItemLabel,
        setEmbeddingSelectionVisibility,
        clearPlotSelection
    };
}
