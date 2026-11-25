import { deleteAnnotationMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation } from '@tanstack/svelte-query';
import { usePostHog } from '$lib/hooks';
import { useInvalidateAnnotationQueries } from '$lib/hooks/useInvalidateAnnotationQueries';

export const useDeleteAnnotation = ({ getCollectionId }: { getCollectionId: () => string }) => {
    const mutation = createMutation(() => deleteAnnotationMutation());
    const { trackEvent } = usePostHog();
    const refetch = useInvalidateAnnotationQueries();

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
