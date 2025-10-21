import { readSampleOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery, useQueryClient } from '@tanstack/svelte-query';

export const useSample = ({ sampleId, datasetId }: { sampleId: string; datasetId: string }) => {
    const readSample = readSampleOptions({
        path: {
            sample_id: sampleId,
            dataset_id: datasetId
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
