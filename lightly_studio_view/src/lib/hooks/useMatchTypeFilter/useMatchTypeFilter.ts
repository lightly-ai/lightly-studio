import { derived, readonly, writable, type Readable } from 'svelte/store';
import { EvaluationMatchType } from '$lib/api/lightly_studio_local';

// Module-level so the sidebar control and the grid share one selection.
// An empty set means "no filter" (show all match types).
const selectedMatchTypes = writable<Set<EvaluationMatchType>>(new Set());

const selectedMatchTypesArray: Readable<EvaluationMatchType[]> = derived(
    selectedMatchTypes,
    ($set) => Array.from($set)
);

export const MATCH_TYPE_ORDER: EvaluationMatchType[] = [
    EvaluationMatchType.TP,
    EvaluationMatchType.FP,
    EvaluationMatchType.FN
];

export const MATCH_TYPE_LABELS: Record<EvaluationMatchType, string> = {
    [EvaluationMatchType.TP]: 'True positive',
    [EvaluationMatchType.FP]: 'False positive',
    [EvaluationMatchType.FN]: 'False negative'
};

export function useMatchTypeFilter() {
    const toggle = (matchType: EvaluationMatchType) => {
        selectedMatchTypes.update((set) => {
            const next = new Set(set);
            if (next.has(matchType)) {
                next.delete(matchType);
            } else {
                next.add(matchType);
            }
            return next;
        });
    };

    const clear = () => selectedMatchTypes.set(new Set());

    return {
        selectedMatchTypes: readonly(selectedMatchTypes),
        selectedMatchTypesArray,
        toggle,
        clear
    };
}
