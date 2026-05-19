import { type VideoFrameView } from '$lib/api/lightly_studio_local';
import { getFrameByIdOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery, useQueryClient, type CreateQueryResult } from '@tanstack/svelte-query';

export const useFrame = (
    getSampleId: () => string
): { refetch: () => void; videoFrame: CreateQueryResult<VideoFrameView, Error> } => {
    const client = useQueryClient();
    const videoFrame = createQuery(() =>
        getFrameByIdOptions({
            path: {
                sample_id: getSampleId()
            }
        })
    );
    const refetch = () => {
        const options = getFrameByIdOptions({
            path: {
                sample_id: getSampleId()
            }
        });
        client.invalidateQueries({ queryKey: options.queryKey });
    };

    return {
        refetch,
        videoFrame
    };
};
