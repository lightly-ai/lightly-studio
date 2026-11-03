import { get } from 'svelte/store';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import type { TagByFilterBody } from '$lib/api/lightly_studio_local';
import type { GridType } from '$lib/types';

export type SelectionTarget =
    | { kind: 'filter'; filter: TagByFilterBody['filter']; size: number }
    | { kind: 'ids'; ids: string[] };

/**
 * Resolves what a selection action should act on. An unmodified select-all targets the
 * snapshot filter (no large ID list); anything else, including a select-all the user then
 * partly unticked, targets the selected IDs.
 */
export function getSelectionTarget(collectionId: string, gridType: GridType): SelectionTarget {
    const {
        getSelectedSampleIds,
        selectedSampleAnnotationCropIds,
        getSelectAllSnapshot,
        getSelectAllAnnotationSnapshot
    } = useGlobalStorage();

    const isAnnotationGrid = gridType === 'annotations';
    const selectedIds = isAnnotationGrid
        ? (get(selectedSampleAnnotationCropIds)[collectionId] ?? new Set<string>())
        : get(getSelectedSampleIds(collectionId));
    const snapshot = get(
        isAnnotationGrid
            ? getSelectAllAnnotationSnapshot(collectionId)
            : getSelectAllSnapshot(collectionId)
    );

    if (snapshot != null && snapshot.size === selectedIds.size) {
        return { kind: 'filter', filter: snapshot.filter, size: snapshot.size };
    }
    return { kind: 'ids', ids: [...selectedIds] };
}
