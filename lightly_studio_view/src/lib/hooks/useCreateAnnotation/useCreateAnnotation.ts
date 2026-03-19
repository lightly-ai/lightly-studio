import {
    type AnnotationCreateInput,
    type CreateAnnotationResponse
} from '$lib/api/lightly_studio_local';
import { createAnnotationMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import { useAnnotationCountsQueryKey } from '$lib/hooks/useAnnotationCounts/useAnnotationCounts';

import { get } from 'svelte/store';

export const useCreateAnnotation = ({ collectionId }: { collectionId: string }) => {
    const mutation = createMutation(createAnnotationMutation());
    const client = useQueryClient();

    const refetch = () => {
        client.invalidateQueries({
            queryKey: useAnnotationCountsQueryKey
        });
    };
    // We need to have this subscription to get onSuccess/onError events
    mutation.subscribe(() => undefined);

    const createAnnotation = (inputs: AnnotationCreateInput) =>
        new Promise<CreateAnnotationResponse>((resolve, reject) => {
            get(mutation).mutate(
                {
                    path: {
                        collection_id: collectionId
                    },
                    body: inputs
                },
                {
                    onSuccess: (data) => {
                        refetch();
                        resolve(data);
                    },
                    onError: (error) => {
                        reject(error);
                    }
                }
            );
        });

    return {
        createAnnotation
    };
};
