import { routeHelpers } from '$lib/routes';
import { readDatasets } from '$lib/api/lightly_studio_local/sdk.gen';
import { redirect } from '@sveltejs/kit';
import { SampleType } from '$lib/api/lightly_studio_local';

export const load = async () => {
    const { data } = await readDatasets();

    if (!data || data.length === 0) {
        throw new Error('No datasets found');
    }

    const mostRecentDataset = data.toSorted(
        (a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
    ).filter((dataset) => dataset.parent_dataset_id == null)[0]

    const lastDatasetId = mostRecentDataset?.dataset_id;

    if (!lastDatasetId) {
        throw new Error('No valid dataset ID found');
    }
    const route = () => {
        switch (mostRecentDataset.sample_type) {
            case SampleType.IMAGE:
                return routeHelpers.toSamples(lastDatasetId)
            default:
                return routeHelpers.toVideos(lastDatasetId)
        }
    }

    redirect(307, route());
};
