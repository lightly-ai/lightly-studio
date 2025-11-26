import { readRootDataset, type DatasetView } from '$lib/api/lightly_studio_local';
import { readRootDatasetOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery, useQueryClient } from '@tanstack/svelte-query';

export const useRootDataset = async (): Promise<DatasetView> => {
    const { data } = await readRootDataset();

    if (!data) throw 'No dataset found';

    return data;
};

export const useRootDatasetOptions = () => {
    const options = readRootDatasetOptions()
    const client = useQueryClient()

    const rootDataset = createQuery(options)

    const refetch = () => {
        client.invalidateQueries({ queryKey: options.queryKey })
    }

    return {
        rootDataset,
        refetch,
    }
}
