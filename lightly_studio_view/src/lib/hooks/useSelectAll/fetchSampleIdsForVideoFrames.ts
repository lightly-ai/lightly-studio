import { getVideoFrameSampleIds } from '$lib/api/lightly_studio_local/sdk.gen';
import type { VideoFrameFilter } from '$lib/api/lightly_studio_local/types.gen';

export async function fetchSampleIdsForVideoFrames(
    collectionId: string,
    filter: VideoFrameFilter | null
): Promise<string[]> {
    const { data } = await getVideoFrameSampleIds({
        path: { video_frame_collection_id: collectionId },
        body: { filter }
    });
    return data ?? [];
}
