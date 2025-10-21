import { routeHelpers } from '$lib/routes';
import { readDatasets } from '$lib/api/lightly_studio_local/sdk.gen';
import { redirect } from '@sveltejs/kit';

export const load = async () => {
    const { data } = await readDatasets();

    if (!data || data.length === 0) {
        throw new Error('No datasets found');
    }

    const mostRecentDataset = data.toSorted(
        (a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
    )[0];

    const lastDatasetId = mostRecentDataset?.dataset_id;

    if (!lastDatasetId) {
        throw new Error('No valid dataset ID found');
    }

    redirect(307, routeHelpers.toSamples(lastDatasetId));
};
