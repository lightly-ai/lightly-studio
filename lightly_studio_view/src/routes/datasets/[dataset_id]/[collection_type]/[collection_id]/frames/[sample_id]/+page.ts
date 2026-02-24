import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params }) => {
    return {
        collection_id: params.collection_id,
        sampleId: params.sample_id
    };
};
