import { get, type Writable } from 'svelte/store';
import type { AnnotationWithPayloadView } from '$lib/api/lightly_studio_local';
import { selectRangeByAnchor } from '$lib/utils/selectRangeByAnchor';

interface UseAnnotationTileSelectionParams {
    getCollectionId: () => string;
    getAnnotations: () => AnnotationWithPayloadView[];
    pickedAnnotationIds: Writable<Record<string, Set<string>>>;
    toggleSelection: (collectionId: string, annotationId: string) => void;
}

/**
 * Wires per-tile click/shift-click selection to `selectRangeByAnchor`, tracking
 * the click anchor across interactions. The range algorithm itself is tested
 * in isolation by `selectRangeByAnchor.test.ts` - this only tests the wiring.
 */
export function useAnnotationTileSelection({
    getCollectionId,
    getAnnotations,
    pickedAnnotationIds,
    toggleSelection
}: UseAnnotationTileSelectionParams) {
    let selectionAnchorAnnotationId: string | null = null;

    function handleToggleSelection(annotationId: string) {
        if (annotationId) {
            toggleSelection(getCollectionId(), annotationId);
        }
    }

    function handleAnnotationSelect(annotationId: string, index: number, shiftKey: boolean) {
        const collectionId = getCollectionId();
        const annotations = getAnnotations();
        selectionAnchorAnnotationId = selectRangeByAnchor({
            sampleIdsInOrder: annotations.map((annotation) => annotation.annotation.sample_id),
            selectedSampleIds: get(pickedAnnotationIds)[collectionId] ?? new Set<string>(),
            clickedSampleId: annotationId,
            clickedIndex: index,
            shiftKey,
            anchorSampleId: selectionAnchorAnnotationId,
            onSelectSample: (selectedAnnotationId) => handleToggleSelection(selectedAnnotationId)
        });
    }

    function handleGridItemSelect(
        event: MouseEvent | KeyboardEvent,
        annotationId: string,
        index: number
    ) {
        handleAnnotationSelect(annotationId, index, event.shiftKey);
    }

    return {
        handleToggleSelection,
        handleAnnotationSelect,
        handleGridItemSelect
    };
}
