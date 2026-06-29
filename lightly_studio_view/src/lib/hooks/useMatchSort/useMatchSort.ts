import { readonly, writable, type Readable } from 'svelte/store';
import { EvaluationMatchSortField, SortDirection } from '$lib/api/lightly_studio_local';

// Module-level so the header control and the grid share one selection.
const sortField = writable<EvaluationMatchSortField>(EvaluationMatchSortField.IOU);
const sortDirection = writable<SortDirection>(SortDirection.DESC);

export const MATCH_SORT_FIELD_ORDER: EvaluationMatchSortField[] = [
    EvaluationMatchSortField.IOU,
    EvaluationMatchSortField.CONFIDENCE
];

export const MATCH_SORT_FIELD_LABELS: Record<EvaluationMatchSortField, string> = {
    [EvaluationMatchSortField.IOU]: 'IoU',
    [EvaluationMatchSortField.CONFIDENCE]: 'Confidence'
};

export function useMatchSort(): {
    sortField: Readable<EvaluationMatchSortField>;
    sortDirection: Readable<SortDirection>;
    setField: (field: EvaluationMatchSortField) => void;
    toggleDirection: () => void;
} {
    const setField = (field: EvaluationMatchSortField) => sortField.set(field);

    const toggleDirection = () =>
        sortDirection.update((direction) =>
            direction === SortDirection.DESC ? SortDirection.ASC : SortDirection.DESC
        );

    return {
        sortField: readonly(sortField),
        sortDirection: readonly(sortDirection),
        setField,
        toggleDirection
    };
}
