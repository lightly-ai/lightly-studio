import {
    type AnnotationLabelCreate,
    type CreateAnnotationLabelResponse
} from '$lib/api/lightly_studio_local';
import { createAnnotationLabelMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation } from '@tanstack/svelte-query';

export const useCreateLabel = ({ collectionId }: { collectionId: string }) => {
    const mutation = createMutation(() => createAnnotationLabelMutation());

    const createLabel = (inputs: AnnotationLabelCreate) =>
        new Promise<CreateAnnotationLabelResponse>((resolve, reject) => {
            mutation.mutate(
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
