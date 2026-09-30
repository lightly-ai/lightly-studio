import { readAnnotationCollectionsQueryKey } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useQueryClient } from '@tanstack/svelte-query';
import { useImageAnnotationCountsQueryKey } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';
import { useInvalidateAnnotationGridQueries } from '$lib/hooks/useInvalidateAnnotationGridQueries';
import { useInvalidateEvaluationRunsQueries } from '$lib/hooks/useEvaluationRuns/useEvaluationRuns';

/** Returns a function that refreshes the queries that an annotation delete makes stale. */
export const useInvalidateAnnotationDeleteQueries = () => {
    const client = useQueryClient();
    const invalidateAnnotationGridQueries = useInvalidateAnnotationGridQueries();
    const invalidateEvaluationRunsQueries = useInvalidateEvaluationRunsQueries();

    return (collectionId: string) => {
        invalidateAnnotationGridQueries(collectionId);
        client.invalidateQueries({
            queryKey: useImageAnnotationCountsQueryKey
        });
        client.invalidateQueries({
            queryKey: readAnnotationCollectionsQueryKey({ path: { collection_id: collectionId } })
        });
        // Annotation mutations can mark evaluation runs as stale, so refresh the runs list.
        invalidateEvaluationRunsQueries();
    };
};
