import { removeTagFromSampleMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation } from '@tanstack/svelte-query';

export const useRemoveTagFromSample = ({ getCollectionId }: { getCollectionId: () => string }) => {
    const mutation = createMutation(() => removeTagFromSampleMutation());

    const removeTagFromSample = (sampleId: string, tagId: string) =>
        new Promise<void>((resolve, reject) => {
            mutation.mutate(
                {
                    path: {
                        collection_id: getCollectionId(),
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
