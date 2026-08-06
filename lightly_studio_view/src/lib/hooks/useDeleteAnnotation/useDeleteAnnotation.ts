import { deleteAnnotationMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import { useImageAnnotationCountsQueryKey } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';
import { usePostHog } from '$lib/hooks';
import { useInvalidateAnnotationGridQueries } from '$lib/hooks/useInvalidateAnnotationGridQueries';

export const useDeleteAnnotation = ({ getCollectionId }: { getCollectionId: () => string }) => {
    const mutation = createMutation(() => deleteAnnotationMutation());

    const client = useQueryClient();
    const { trackEvent } = usePostHog();
    const invalidateAnnotationGridQueries = useInvalidateAnnotationGridQueries();

    const refetch = (collectionId: string) => {
        invalidateAnnotationGridQueries(collectionId);
        client.invalidateQueries({
            queryKey: useImageAnnotationCountsQueryKey
        });
    };

    const deleteAnnotation = (annotationId: string, annotationType: string) =>
        new Promise<void>((resolve, reject) => {
            const collectionId = getCollectionId();
            mutation.mutate(
                {
                    path: {
                        collection_id: collectionId,
                        annotation_id: annotationId
                    }
                },
                {
                    onSuccess: () => {
                        refetch(collectionId);
                        trackEvent('annotation_deleted', {
                            collection_id: collectionId,
                            annotation_type: annotationType
                        });
                        resolve();
                    },
                    onError: (error) => {
                        reject(error);
                    }
                }
            );
        });

    return {
        deleteAnnotation
    };
};
