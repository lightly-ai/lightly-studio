import type { PageLoad } from './$types';
import { getVideoById } from '$lib/api/lightly_studio_local';

export const load: PageLoad = async ({ params }) => {
    const sample = await getVideoById({
        path: {
            sample_id: params.sample_id
        }
    });

    return {
        sample: sample.data
    };
};
