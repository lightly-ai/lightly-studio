import { deleteCaptionMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation } from '@tanstack/svelte-query';

export const useDeleteCaption = () => {
    const mutation = createMutation(() => deleteCaptionMutation());

    const deleteCaption = async (sampleId: string): Promise<void> => {
        await mutation.mutateAsync({
            path: {
                sample_id: sampleId
            }
        });
    };

    return {
        deleteCaption
    };
};
