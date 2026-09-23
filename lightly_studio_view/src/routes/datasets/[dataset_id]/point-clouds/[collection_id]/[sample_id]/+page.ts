import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, url }) => {
    const sequenceId = url.searchParams.get('sequence_id') ?? undefined;

    if (!sequenceId) {
        error(400, 'sequence_id must be provided in the URL.');
    }
    return {
        datasetId: params.dataset_id,
        collectionType: url.searchParams.get('collection_type') ?? undefined,
        collectionId: params.collection_id,
        sampleId: params.sample_id,
        sequenceId,
        groupId: url.searchParams.get('group_id') ?? undefined
    };
};
