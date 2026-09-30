import { deleteAnnotationMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation } from '@tanstack/svelte-query';
import { usePostHog } from '$lib/hooks';
import { useInvalidateAnnotationDeleteQueries } from '$lib/hooks/useInvalidateAnnotationDeleteQueries/useInvalidateAnnotationDeleteQueries';

export const useDeleteAnnotation = ({ getCollectionId }: { getCollectionId: () => string }) => {
    const mutation = createMutation(() => deleteAnnotationMutation());

    const { trackEvent } = usePostHog();
    const refetch = useInvalidateAnnotationDeleteQueries();

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
