import type { PageLoad } from './$types';
import { getFrameById } from '$lib/api/lightly_studio_local';

export const load: PageLoad = async ({ params }) => {
    const sample = await getFrameById({
        path: {
            sample_id: params.sample_id,
        }
    });

    return {
        sample: sample.data
    };
};
