import { type CaptionCreateInput, type CreateCaptionResponse } from '$lib/api/lightly_studio_local';
import { createCaptionMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation } from '@tanstack/svelte-query';

export const useCreateCaption = () => {
    const mutation = createMutation(() => createCaptionMutation());

    const createCaption = (inputs: CaptionCreateInput) =>
        new Promise<CreateCaptionResponse>((resolve, reject) => {
            mutation.mutate(
                {
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
        createCaption
    };
};
