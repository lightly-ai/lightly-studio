import { getVideoByIdOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { VideoView } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, useQueryClient } from '@tanstack/svelte-query';
import { writable, type Writable } from 'svelte/store';

export const useVideo = () => {
    const data: Writable<VideoView | undefined> = writable(undefined);
    const error: Writable<Error | null> = writable(null);
    const isLoading: Writable<boolean> = writable(false);
    const refetch: Writable<() => void> = writable(() => {});

    let currentSampleId = $state<string | null>(null);

    const client = useQueryClient();

    const query = createQuery(() => ({
        ...getVideoByIdOptions({
            path: { sample_id: currentSampleId! }
        }),
        enabled: currentSampleId !== null
    }));

    $effect(() => {
        data.set(query.data);
        error.set(query.error);
        isLoading.set(query.isLoading);
        if (currentSampleId) {
            const options = getVideoByIdOptions({ path: { sample_id: currentSampleId } });
            refetch.set(() => client.invalidateQueries({ queryKey: options.queryKey }));
        }
    });

    const loadById = (sample_id: string) => {
        currentSampleId = sample_id;
    };

    return { data, error, isLoading, loadById, refetch };
};
