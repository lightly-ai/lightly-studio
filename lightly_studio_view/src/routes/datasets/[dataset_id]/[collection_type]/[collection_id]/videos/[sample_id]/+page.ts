import type { PageLoad } from './$types';
export const load: PageLoad = async ({ params, url }) => {
    return {
        groupId: url.searchParams.get('group_id') ?? undefined,
        frameNumber: url.searchParams.get('frame_number') ?? undefined,
        params
    };
};
