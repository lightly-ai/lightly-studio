import {
    type AnnotationCreateInput,
    type CreateAnnotationResponse
} from '$lib/api/lightly_studio_local';
import { createAnnotationMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation } from '@tanstack/svelte-query';

import { get } from 'svelte/store';

export const useCreateAnnotation = ({ collectionId }: { collectionId: string }) => {
    const mutation = createMutation(createAnnotationMutation());

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
