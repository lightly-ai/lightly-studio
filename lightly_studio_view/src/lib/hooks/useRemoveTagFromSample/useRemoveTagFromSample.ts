import { removeTagFromSampleMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation } from '@tanstack/svelte-query';
import { get } from 'svelte/store';

export const useRemoveTagFromSample = ({ collectionId }: { collectionId: string }) => {
    const mutation = createMutation(removeTagFromSampleMutation());

    // Subscribe so onSuccess/onError handlers fire
    mutation.subscribe(() => undefined);

    const removeTagFromSample = (sampleId: string, tagId: string) =>
        new Promise<void>((resolve, reject) => {
            get(mutation).mutate(
                {
                    path: {
                        collection_id: collectionId,
                        sample_id: sampleId,
                        tag_id: tagId
                    }
                },
                {
                    onSuccess: () => resolve(),
                    onError: (error) => reject(error)
                }
            );
        });

    return {
        removeTagFromSample
    };
};
