import { type VideoFrameView } from '$lib/api/lightly_studio_local';
import { getFrameByIdOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery, useQueryClient, type CreateQueryResult } from '@tanstack/svelte-query';

export const useFrame = (
    sampleId: string
): { refetch: () => void; videoFrame: CreateQueryResult<VideoFrameView, Error> } => {
    const readFrame = getFrameByIdOptions({
        path: {
            sample_id: sampleId
        }
    });
    const client = useQueryClient();
    const videoFrame = createQuery(readFrame);
    const refetch = () => {
        client.invalidateQueries({ queryKey: readFrame.queryKey });
    };

    return {
        refetch,
        videoFrame
    };
};
