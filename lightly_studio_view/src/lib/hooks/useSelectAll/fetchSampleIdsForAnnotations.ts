import { getAnnotationSampleIds } from '$lib/api/lightly_studio_local/sdk.gen';
import type { AnnotationsFilter } from '$lib/api/lightly_studio_local/types.gen';

export async function fetchSampleIdsForAnnotations(
    collectionId: string,
    filter: AnnotationsFilter | undefined
): Promise<string[]> {
    const { data } = await getAnnotationSampleIds({
        path: { collection_id: collectionId },
        body: { filters: filter }
    });
    return data ?? [];
}
