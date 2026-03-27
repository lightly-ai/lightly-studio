import { getVideoByIdOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { VideoView } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, useQueryClient } from '@tanstack/svelte-query';
import { writable, type Writable } from 'svelte/store';

export const useVideo = () => {
    const data: Writable<VideoView | undefined> = writable(undefined);
    const error: Writable<Error | null> = writable(null);
    const isLoading: Writable<boolean> = writable(false);
    const refetch: Writable<() => void> = writable(() => {});

    let currentSampleId: string | null = null;
    let unsubscribe: (() => void) | null = null;

    const loadById = (sample_id: string) => {
        // Avoid refetching if we already have the correct video loaded
        if (currentSampleId === sample_id) {
            return;
        }

        // Clean up previous subscription
        if (unsubscribe) {
            unsubscribe();
        }

        currentSampleId = sample_id;

        const options = getVideoByIdOptions({
            path: {
                sample_id
            }
        });
        const client = useQueryClient();
        const query = createQuery(options);
        const refetchFN = () => {
            client.invalidateQueries({ queryKey: options.queryKey });
        };

        unsubscribe = query.subscribe((result) => {
            data.set(result.data);
            error.set(result.error);
            isLoading.set(result.isLoading);
            refetch.set(refetchFN);
        });
    };

    return { data, error, isLoading, loadById, refetch };
};
