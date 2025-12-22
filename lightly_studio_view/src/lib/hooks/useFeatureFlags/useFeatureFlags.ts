import client from '$lib/services/collection';
import { readonly, writable } from 'svelte/store';

export const useFeatureFlags = () => {
    const featureFlags = writable([] as string[]);
    const error = writable<Error | null>(null);
    client
        .GET('/api/features')
        .then((response) => {
            if (response.data) {
                featureFlags.set(response.data);
            }
        })
        .catch((err) => {
            error.set(err as Error);
        });

    return {
        error,
        featureFlags: readonly(featureFlags)
    };
};
