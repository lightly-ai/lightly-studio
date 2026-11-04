import {
    type AnnotationCreateInput,
    type CreateAnnotationResponse
} from '$lib/api/lightly_studio_local';
import {
    createAnnotationMutation,
    readAnnotationCollectionsQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import { useImageAnnotationCountsQueryKey } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';
import { usePostHog } from '$lib/hooks';
import { useInvalidateAnnotationGridQueries } from '$lib/hooks/useInvalidateAnnotationGridQueries';
import { useInvalidateEvaluationRunsQueries } from '$lib/hooks/useEvaluationRuns/useEvaluationRuns';
import { page } from '$app/state';

export const useCreateAnnotation = ({ getCollectionId }: { getCollectionId: () => string }) => {
    const mutation = createMutation(() => createAnnotationMutation());
    const client = useQueryClient();
    const { trackEvent } = usePostHog();
    const invalidateAnnotationGridQueries = useInvalidateAnnotationGridQueries();
    const invalidateEvaluationRunsQueries = useInvalidateEvaluationRunsQueries();

    const refetch = (collectionId: string) => {
        invalidateAnnotationGridQueries(collectionId);
        client.invalidateQueries({
            queryKey: useImageAnnotationCountsQueryKey
        });
        // An annotation can be written to a brand-new source (collection) by name, so refresh
        // the source list to surface it in the pill and the side panel.
        client.invalidateQueries({
            queryKey: readAnnotationCollectionsQueryKey({ path: { collection_id: collectionId } })
        });
        // Annotation mutations can mark evaluation runs as stale, so refresh the runs list.
        invalidateEvaluationRunsQueries();
    };

    // Pass `skipRefetch` to create many annotations and call `refetch` once at the end.
    const createAnnotation = async (
        inputs: AnnotationCreateInput,
        { skipRefetch = false }: { skipRefetch?: boolean } = {}
    ): Promise<CreateAnnotationResponse> => {
        const collectionId = getCollectionId();
        // No per-call callbacks: TanStack drops them when the observer unmounts.
        const data = await mutation.mutateAsync({
            path: {
                collection_id: collectionId
            },
            body: inputs
        });
        if (!skipRefetch) refetch(collectionId);
        trackEvent('annotation_created', {
            collection_id: collectionId,
            annotation_type: data.annotation_type,
            parent_sample_type: page.params.collection_type,
            label_name: data.annotation_label.annotation_label_name
        });
        return data;
    };

    return {
        createAnnotation,
        refetch: () => refetch(getCollectionId())
    };
};
