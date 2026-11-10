import { readAnnotationCollectionsQueryKey } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useQueryClient } from '@tanstack/svelte-query';
import { useInvalidateEvaluationRunsQueries } from '$lib/hooks/useEvaluationRuns/useEvaluationRuns';
import { useImageAnnotationCountsQueryKey } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';
import { useInvalidateAnnotationGridQueries } from '$lib/hooks/useInvalidateAnnotationGridQueries';

/**
 * Returns the function that refreshes what an annotation created or deleted in a collection
 * changes: the grids, the annotation counts, the annotation sources and the evaluation runs.
 */
export const useInvalidateAnnotationQueries = () => {
    const client = useQueryClient();
    const invalidateAnnotationGridQueries = useInvalidateAnnotationGridQueries();
    const invalidateEvaluationRunsQueries = useInvalidateEvaluationRunsQueries();

    return (collectionId: string) => {
        invalidateAnnotationGridQueries(collectionId);
        client.invalidateQueries({ queryKey: useImageAnnotationCountsQueryKey });
        // An annotation can be written to a brand-new source by name, so refresh the sources.
        client.invalidateQueries({
            queryKey: readAnnotationCollectionsQueryKey({ path: { collection_id: collectionId } })
        });
        // Annotation mutations can mark evaluation runs as stale.
        invalidateEvaluationRunsQueries();
    };
};
