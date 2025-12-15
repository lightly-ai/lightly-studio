import { readRootDatasetOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery, useQueryClient } from '@tanstack/svelte-query';

export const useRootDatasetOptions = ({ datasetId }: { datasetId: string }) => {
    const options = readRootDatasetOptions({ path: { dataset_id: datasetId } });
    const client = useQueryClient();

    const rootDataset = createQuery(options);

    const refetch = () => {
        client.invalidateQueries({ queryKey: options.queryKey });
    };

    return {
        rootDataset,
        refetch
    };
};
