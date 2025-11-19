import type { PageLoad } from './$types';
import { getFrameById } from '$lib/api/lightly_studio_local';
import {
    useFrameAdjacents,
    type FrameAdjacents
} from '$lib/hooks/useFramesAdjacents/useFramesAdjacents';
import type { Writable } from 'svelte/store';

export const load: PageLoad = async ({ params, url }) => {
    const index = url.searchParams.get('index');
    const frameIndex = index ? parseInt(index) : null;
    const frameAdjacents: Writable<FrameAdjacents> | null =
        frameIndex == null
            ? null
            : useFrameAdjacents({
                  video_frame_dataset_id: params.dataset_id,
                  sampleIndex: frameIndex
              });

    return {
        frameAdjacents: frameAdjacents,
        frameIndex: frameIndex,
        dataset_id: params.dataset_id,
        sampleId: params.sample_id
    };
};
