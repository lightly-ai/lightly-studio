import { getVideoSampleIds } from '$lib/api/lightly_studio_local/sdk.gen';
import type { VideoFilter } from '$lib/api/lightly_studio_local/types.gen';

export async function fetchSampleIdsForVideos(
    collectionId: string,
    filter: VideoFilter | null
): Promise<string[]> {
    const { data } = await getVideoSampleIds({
        path: { collection_id: collectionId },
        body: { filter }
    });
    return data ?? [];
}
