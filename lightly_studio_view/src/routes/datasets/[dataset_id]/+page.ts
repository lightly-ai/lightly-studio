import { redirect } from '@sveltejs/kit';
import { SampleType } from '$lib/api/lightly_studio_local';
import { routeHelpers } from '$lib/routes';
import { readCollection } from '$lib/api/lightly_studio_local/sdk.gen';
import type { PageLoad } from './$types';

const rootCollectionRoutes: Partial<
    Record<SampleType, (datasetId: string, collectionType: string, collectionId: string) => string>
> = {
    [SampleType.IMAGE]: routeHelpers.toSamples,
    [SampleType.VIDEO]: routeHelpers.toVideos,
    [SampleType.GROUP]: routeHelpers.toGroups
};

export const load: PageLoad = async ({ params: { dataset_id } }) => {
    // Fetch collection to get sample_type
    const { data: collectionData } = await readCollection({
        path: { collection_id: dataset_id }
    }).catch(() => ({ data: undefined }));

    // Get route builder for valid root collection types
    const routeBuilder = collectionData
        ? rootCollectionRoutes[collectionData.sample_type]
        : undefined;

    // Redirect to home if:
    // - Collection not found
    // - Not a root collection
    // - Invalid root collection type (ANNOTATION, VIDEO_FRAME, CAPTION)
    if (!collectionData || !routeBuilder) {
        throw redirect(307, routeHelpers.toHome());
    }

    // Redirect to proper URL
    const collectionType = collectionData.sample_type.toLowerCase();
    throw redirect(307, routeBuilder(dataset_id, collectionType, dataset_id));
};
