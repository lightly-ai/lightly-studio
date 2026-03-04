import type { PageLoad } from './$types';
import { getVideoById } from '$lib/api/lightly_studio_local';

export const load: PageLoad = async ({ params }) => {
    const sampleId = params.sample_id;

    const sampleResponse = await getVideoById({
        path: { sample_id: sampleId }
    });

    return {
        sample: sampleResponse.data
    };
};
