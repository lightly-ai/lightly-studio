import { readImageOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { ImageView } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, useQueryClient, type CreateQueryResult } from '@tanstack/svelte-query';

export const useImage = (
    getParams: () => { sampleId: string }
): { image: CreateQueryResult<ImageView, Error>; refetch: () => void } => {
    const client = useQueryClient();
    const image = createQuery(() =>
        readImageOptions({
            path: {
                sample_id: getParams().sampleId
            }
        })
    );
    const refetch = () => {
        const options = readImageOptions({
            path: {
                sample_id: getParams().sampleId
            }
        });
        client.invalidateQueries({ queryKey: options.queryKey });
    };

    return {
        refetch,
        image
    };
};
