import { getVideoByIdOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery, useQueryClient } from '@tanstack/svelte-query';

export const useVideo = ({ sampleId }: { sampleId: string }) => {
    const readVideo = getVideoByIdOptions({
        path: {
            sample_id: sampleId
        }
    });
    const client = useQueryClient();
    const video = createQuery(readVideo);
    const refetch = () => {
        client.invalidateQueries({ queryKey: readVideo.queryKey });
    };

    return {
        refetch,
        video
    };
};
