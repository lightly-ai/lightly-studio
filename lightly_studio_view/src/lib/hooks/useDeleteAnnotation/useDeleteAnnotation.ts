import {
    countAnnotationsByCollectionOptions,
    deleteAnnotationMutation
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import { get } from 'svelte/store';

export const useDeleteAnnotation = ({ collectionId }: { collectionId: string }) => {
    const mutation = createMutation(deleteAnnotationMutation());

    // We need to have this subscription to get onSuccess/onError events
    mutation.subscribe(() => undefined);

    const client = useQueryClient();

    const refetch = () => {
        client.invalidateQueries({
            queryKey: countAnnotationsByCollectionOptions({
                path: { collection_id: collectionId }
            }).queryKey
        });
    };

    const deleteAnnotation = (annotationId: string) =>
        new Promise<void>((resolve, reject) => {
            get(mutation).mutate(
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
