import { readCollections } from '$lib/api/lightly_studio_local/sdk.gen';
import { redirect } from '@sveltejs/kit';

export const load = async () => {
    const { data } = await readCollections();

    if (!data || data.length === 0) {
        throw new Error('No datasets found');
    }
    const mostRecentRootDataset = data
        .filter((collection) => collection.parent_collection_id == null)
        .toSorted(
            (a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
        )[0];

    if (!mostRecentRootDataset?.collection_id) {
        throw new Error('No valid root collection found');
    }

    redirect(
        307,
        `/datasets/${mostRecentRootDataset.collection_id}/${mostRecentRootDataset.sample_type.toLowerCase()}/${mostRecentRootDataset.collection_id}`
    );
};
