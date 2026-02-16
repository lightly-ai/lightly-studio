import { type AnnotationUpdateInput } from '$lib/api/lightly_studio_local';
import {
    countAnnotationsByCollectionOptions,
    updateAnnotationsMutation
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import { get } from 'svelte/store';

export const useUpdateAnnotationsMutation = ({ collectionId }: { collectionId: string }) => {
    const mutation = createMutation(updateAnnotationsMutation());

    const client = useQueryClient();

    const refetch = () => {
        client.invalidateQueries({
            queryKey: countAnnotationsByCollectionOptions({
                path: { collection_id: collectionId }
            }).queryKey
        });
    };
    // We need to have this subscription to get onSuccess/onError events
    mutation.subscribe(() => undefined);

    const updateAnnotations = (inputs: AnnotationUpdateInput[]) =>
        new Promise<void>((resolve, reject) => {
            get(mutation).mutate(
                {
                    path: {
                        collection_id: collectionId
                    },
                    body: inputs
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
        updateAnnotations
    };
};
