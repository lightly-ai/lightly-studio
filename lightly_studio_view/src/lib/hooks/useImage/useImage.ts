import { readImageOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery, useQueryClient } from '@tanstack/svelte-query';

export const useImage = ({ sampleId }: { sampleId: string }) => {
    const readImage = readImageOptions({
        path: {
            sample_id: sampleId
        }
    });
    const client = useQueryClient();
    const sample = createQuery(readImage);
    const refetch = () => {
        client.invalidateQueries({ queryKey: readImage.queryKey });
    };

    return {
        refetch,
        sample
    };
};
