import { createQuery } from '@tanstack/svelte-query';
import { getTracksOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';

export function useTracks(getDatasetId: () => string) {
    const query = createQuery(() =>
        getTracksOptions({
            path: { dataset_id: getDatasetId() }
        })
    );
    return query;
}
