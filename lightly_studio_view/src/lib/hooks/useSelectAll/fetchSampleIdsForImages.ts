import { getImageSampleIds } from '$lib/api/lightly_studio_local/sdk.gen';
import type { ImageFilter } from '$lib/api/lightly_studio_local/types.gen';

export async function fetchSampleIdsForImages(
    collectionId: string,
    filter: ImageFilter | null
): Promise<string[]> {
    const { data } = await getImageSampleIds({
        path: { collection_id: collectionId },
        body: { filters: filter }
    });
    return data ?? [];
}
