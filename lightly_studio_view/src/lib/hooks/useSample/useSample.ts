import { readSampleOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery, useQueryClient } from '@tanstack/svelte-query';

export const useSample = ({ sampleId }: { sampleId: string }) => {
    const readSample = readSampleOptions({
        path: {
            sample_id: sampleId
        }
    });
    const client = useQueryClient();
    const sample = createQuery(readSample);
    const refetch = () => {
        client.invalidateQueries({ queryKey: readSample.queryKey });
    };

    return {
        refetch,
        sample
    };
};
