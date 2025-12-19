import {
    type AnnotationLabelCreate,
    type CreateAnnotationLabelResponse
} from '$lib/api/lightly_studio_local';
import { createAnnotationLabelMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation } from '@tanstack/svelte-query';
import { get } from 'svelte/store';

export const useCreateLabel = ({ collectionId }: { collectionId: string }) => {
    const mutation = createMutation(createAnnotationLabelMutation());
    // We need to have this subscription to get onSuccess/onError events
    // Subscribing to the mutation store is necessary to ensure that onSuccess/onError handlers
    // are triggered, even if we do not use the value directly. Without a subscription,
    // these side effects may not fire as expected.
    mutation.subscribe(() => undefined);

    const createLabel = (inputs: AnnotationLabelCreate) =>
        new Promise<CreateAnnotationLabelResponse>((resolve, reject) => {
            get(mutation).mutate(
                {
                    path: { collection_id: collectionId },
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
        createLabel
    };
};
