import { deleteCaptionMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation } from '@tanstack/svelte-query';

export const useDeleteCaption = () => {
    const mutation = createMutation(() => deleteCaptionMutation());

    const deleteCaption = (sampleId: string) =>
        new Promise<void>((resolve, reject) => {
            mutation.mutate(
                {
                    path: {
                        sample_id: sampleId
                    }
                },
                {
                    onSuccess: () => {
                        resolve();
                    },
                    onError: (error) => {
                        reject(error);
                    }
                }
            );
        });

    return {
        deleteCaption
    };
};
