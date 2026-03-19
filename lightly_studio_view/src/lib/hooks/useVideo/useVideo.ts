import { getVideoByIdOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

export const useVideo = ({ sampleId }: { sampleId: string; collectionId: string }) => {
    const readVideo = getVideoByIdOptions({
        path: {
            sample_id: sampleId
        }
    });
    const video = createQuery(readVideo);

    return {
        video
    };
};
