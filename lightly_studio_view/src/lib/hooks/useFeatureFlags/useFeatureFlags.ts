import { getFeatures } from '$lib/api/lightly_studio_local/sdk.gen';
import { readonly, writable } from 'svelte/store';

export const useFeatureFlags = () => {
    const featureFlags = writable([] as string[]);
    const error = writable<Error | null>(null);
    // Handed back as `ready` so a caller that has to act on the answer can await it instead of
    // reading the store before the request lands.
    const ready = getFeatures()
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
        featureFlags: readonly(featureFlags),
        ready
    };
};
