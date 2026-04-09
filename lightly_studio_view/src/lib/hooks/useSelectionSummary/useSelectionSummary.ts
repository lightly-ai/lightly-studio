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
			return $selectedSampleIds.size + cropIds.size;
		}
	);

	const clearSelection = () => {
		clearSelectedSamples(collectionId);
		clearSelectedSampleAnnotationCrops(collectionId);
	};

	return { selectedCount, clearSelection };
}
