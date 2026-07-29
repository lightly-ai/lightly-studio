import { derived, get, writable, type Readable } from 'svelte/store';
import type { AnnotationEvaluationMetricSortExpr } from '$lib/api/lightly_studio_local';

interface AnnotationSortSelection {
    /** The annotation source the expression was chosen for. */
    collectionId: string;
    expr: AnnotationEvaluationMetricSortExpr;
}

// Module-level so the grid, its header and its query all read one selection. Deliberately not
// persisted to the URL or storage.
const selection = writable<AnnotationSortSelection | null>(null);

interface UseAnnotationSortByReturn {
    /**
     * Reads the expression for an annotation source, reactively.
     *
     * Returns null for any other source, so switching sources resets the sort. Scoping the
     * selection makes carrying a run ID into a source that cannot resolve it
     * unrepresentable, rather than relying on a reset call at every navigation path.
     */
    sortByFor: Readable<(collectionId: string) => AnnotationEvaluationMetricSortExpr | null>;
    getSortBy: (collectionId: string) => AnnotationEvaluationMetricSortExpr | null;
    setSortBy: (collectionId: string, expr: AnnotationEvaluationMetricSortExpr | null) => void;
}

export function useAnnotationSortBy(): UseAnnotationSortByReturn {
    const sortByFor = derived(
        selection,
        ($selection) =>
            (collectionId: string): AnnotationEvaluationMetricSortExpr | null =>
                $selection?.collectionId === collectionId ? $selection.expr : null
    );

    const getSortBy = (collectionId: string): AnnotationEvaluationMetricSortExpr | null =>
        get(sortByFor)(collectionId);

    const setSortBy = (
        collectionId: string,
        expr: AnnotationEvaluationMetricSortExpr | null
    ): void => {
        selection.set(expr ? { collectionId, expr } : null);
    };

    return { sortByFor, getSortBy, setSortBy };
}
