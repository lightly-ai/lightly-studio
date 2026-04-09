import { derived, type Readable } from 'svelte/store';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

interface SelectionSummary {
    selectedCount: Readable<number>;
    clearSelection: () => void;
}

export function useSelectionSummary(collectionId: string): SelectionSummary {
    const {
        getSelectedSampleIds,
        selectedSampleAnnotationCropIds,
        clearSelectedSamples,
        clearSelectedSampleAnnotationCrops
    } = useGlobalStorage();

    const selectedSampleIds = getSelectedSampleIds(collectionId);

    const selectedCount = derived(
        [selectedSampleIds, selectedSampleAnnotationCropIds],
        ([$selectedSampleIds, $selectedSampleAnnotationCropIds]) => {
            const cropIds = $selectedSampleAnnotationCropIds[collectionId] ?? new Set<string>();
            if (cropIds.size !== 0) {
                // If there are selected annotation crops, we display their count.
                // This is a special case we have to handle because sample and annotation
                // selection is stored separately in the global storage.
                return cropIds.size;
            } else {
                return $selectedSampleIds.size;
            }
        }
    );

    const clearSelection = () => {
        clearSelectedSamples(collectionId);
        clearSelectedSampleAnnotationCrops(collectionId);
    };

    return { selectedCount, clearSelection };
}
