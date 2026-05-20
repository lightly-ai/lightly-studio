import { deleteAnnotationMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import { useImageAnnotationCountsQueryKey } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';

export const useDeleteAnnotation = ({ collectionId }: { collectionId: string }) => {
    const mutation = createMutation(() => deleteAnnotationMutation());

    const client = useQueryClient();

    const refetch = () => {
        client.invalidateQueries({
            queryKey: useImageAnnotationCountsQueryKey
        });
    };

    const deleteAnnotation = (annotationId: string) =>
        new Promise<void>((resolve, reject) => {
            mutation.mutate(
                {
                    path: {
                        collection_id: collectionId,
                        annotation_id: annotationId
                    }
                },
                {
                    onSuccess: () => {
                        refetch();
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
