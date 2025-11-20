import { type CaptionCreateInput, type CreateCaptionResponse } from '$lib/api/lightly_studio_local';
import { createCaptionMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation } from '@tanstack/svelte-query';

import { get } from 'svelte/store';

export const useCreateCaption = () => {
    const mutation = createMutation(createCaptionMutation());

    // We need to have this subscription to get onSuccess/onError events
    mutation.subscribe(() => undefined);

    const createCaption = (inputs: CaptionCreateInput) =>
        new Promise<CreateCaptionResponse>((resolve, reject) => {
            get(mutation).mutate(
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
