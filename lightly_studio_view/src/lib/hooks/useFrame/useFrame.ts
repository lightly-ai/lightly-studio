import { type VideoFrameView } from '$lib/api/lightly_studio_local';
import { getFrameByIdOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { toReadable, type StoreOrVal } from '$lib/utils/reactiveParams';
import { createQuery, useQueryClient, type CreateQueryResult } from '@tanstack/svelte-query';
import { derived, get } from 'svelte/store';

export const useFrame = (
    sampleId: StoreOrVal<string>
): { refetch: () => void; videoFrame: CreateQueryResult<VideoFrameView, Error> } => {
    const sampleIdStore = toReadable(sampleId);
    const optionsStore = derived(sampleIdStore, (currentSampleId) =>
        getFrameByIdOptions({
            path: {
                sample_id: currentSampleId
            }
        })
    );
    const client = useQueryClient();
    const videoFrame = createQuery(optionsStore);
    const refetch = () => {
        client.invalidateQueries({ queryKey: get(optionsStore).queryKey });
    };

    return {
        refetch,
        videoFrame
    };
};
