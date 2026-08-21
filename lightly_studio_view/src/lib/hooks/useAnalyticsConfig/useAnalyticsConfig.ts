import { getAnalyticsConfig } from '$lib/api/lightly_studio_local/sdk.gen';
import { readonly, writable } from 'svelte/store';

type AnalyticsConfig = NonNullable<Awaited<ReturnType<typeof getAnalyticsConfig>>['data']>;

/**
 * Analytics configuration reported by the backend, so that the browser reports against the same
 * person as the Python package instead of a second anonymous one.
 */
export const useAnalyticsConfig = () => {
    const config = writable<AnalyticsConfig | null>(null);
    // Handed back as `ready` so a caller that has to act on the answer can await it instead of
    // reading the store before the request lands. A failed request leaves the config empty, which
    // callers treat as tracking being off, so neither a rejection nor the `error` the client
    // resolves with on an HTTP failure is reported.
    const ready = getAnalyticsConfig()
        .then((response) => {
            if (response.data) {
                config.set(response.data);
            }
        })
        .catch(() => {});

    return {
        config: readonly(config),
        ready
    };
};
