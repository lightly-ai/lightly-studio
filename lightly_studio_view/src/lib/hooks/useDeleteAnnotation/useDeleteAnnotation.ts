import {
    deleteAnnotationMutation,
    readAnnotationCollectionsQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import { useImageAnnotationCountsQueryKey } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';
import { usePostHog } from '$lib/hooks';
import { useInvalidateAnnotationGridQueries } from '$lib/hooks/useInvalidateAnnotationGridQueries';
import { useInvalidateEvaluationRunsQueries } from '$lib/hooks/useEvaluationRuns/useEvaluationRuns';

export const useDeleteAnnotation = ({ getCollectionId }: { getCollectionId: () => string }) => {
    const mutation = createMutation(() => deleteAnnotationMutation());

    const client = useQueryClient();
    const { trackEvent } = usePostHog();
    const invalidateAnnotationGridQueries = useInvalidateAnnotationGridQueries();
    const invalidateEvaluationRunsQueries = useInvalidateEvaluationRunsQueries();

    const refetch = (collectionId: string) => {
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

    const deleteAnnotation = async (
        annotationId: string,
        annotationType: string,
        collectionId = getCollectionId()
    ): Promise<void> => {
        // No per-call callbacks: TanStack drops them when the observer unmounts.
        await mutation.mutateAsync({
            path: {
                collection_id: collectionId,
                annotation_id: annotationId
            }
        });
        refetch(collectionId);
        trackEvent('annotation_deleted', {
            collection_id: collectionId,
            annotation_type: annotationType
        });
    };

    return {
        deleteAnnotation
    };
};
