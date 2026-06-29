import { readonly, writable, type Readable } from 'svelte/store';
import { EvaluationMatchSortField, SortDirection } from '$lib/api/lightly_studio_local';

// Module-level so the sidebar control and the grid share one selection.
const sortField = writable<EvaluationMatchSortField>(EvaluationMatchSortField.MATCH_TYPE);
const sortDirection = writable<SortDirection>(SortDirection.DESC);

export const MATCH_SORT_FIELD_ORDER: EvaluationMatchSortField[] = [
    EvaluationMatchSortField.MATCH_TYPE,
    EvaluationMatchSortField.IOU
];

export const MATCH_SORT_FIELD_LABELS: Record<EvaluationMatchSortField, string> = {
    [EvaluationMatchSortField.MATCH_TYPE]: 'Match type, then IoU',
    [EvaluationMatchSortField.IOU]: 'IoU'
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
