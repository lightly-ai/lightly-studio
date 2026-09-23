import { derived, get, writable, type Readable } from 'svelte/store';
import type { AnnotationEvaluationMetricSortExpr } from '$lib/api/lightly_studio_local';

interface AnnotationSortSelection {
    collectionId: string;
    expr: AnnotationEvaluationMetricSortExpr;
}

// Module-level so the grid, its header and its query read one selection. Not persisted.
const selection = writable<AnnotationSortSelection | null>(null);

interface UseAnnotationSortByReturn {
    /**
     * Reads the expression for an annotation source, reactively. Null for any other source, so
     * switching sources drops the sort instead of carrying a run ID it cannot resolve.
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
