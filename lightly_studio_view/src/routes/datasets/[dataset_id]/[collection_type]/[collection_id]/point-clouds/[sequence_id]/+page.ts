import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, url, parent }) => {
    // Point-cloud data is resolved by the dataset entity id, which the collection carries directly.
    // The URL's dataset slot is a collection id, so derive the dataset id from the loaded collection.
    const { collection } = await parent();
    return {
        datasetId: collection.dataset_id,
        collectionName: collection.name,
        collectionType: params.collection_type,
        collectionId: params.collection_id,
        sequenceId: params.sequence_id,
        groupId: url.searchParams.get('group_id') ?? undefined
    };
};
