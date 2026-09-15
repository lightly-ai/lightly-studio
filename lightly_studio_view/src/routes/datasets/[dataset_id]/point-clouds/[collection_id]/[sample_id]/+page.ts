import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, url }) => {
    return {
        datasetId: params.dataset_id,
        collectionType: url.searchParams.get('collection_type') ?? undefined,
        collectionId: params.collection_id,
        sampleId: params.sample_id,
        groupId: url.searchParams.get('group_id') ?? undefined
    };
};
