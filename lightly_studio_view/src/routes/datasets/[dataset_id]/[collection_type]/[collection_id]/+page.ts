import { error, redirect } from '@sveltejs/kit';
import { SampleType } from '$lib/api/lightly_studio_local';
import { routeHelpers } from '$lib/routes';
import type { PageLoad } from './$types';

const sampleTypeRoutes: Record<
    SampleType,
    (datasetId: string, collectionType: string, collectionId: string) => string
> = {
    [SampleType.VIDEO]: routeHelpers.toVideos,
    [SampleType.VIDEO_FRAME]: routeHelpers.toFrames,
    [SampleType.IMAGE]: routeHelpers.toSamples,
    [SampleType.ANNOTATION]: routeHelpers.toAnnotations,
    [SampleType.CAPTION]: routeHelpers.toCaptions,
    [SampleType.GROUP]: routeHelpers.toGroups
};

export const load: PageLoad = async ({ parent }) => {
    const { collection, datasetId, collectionType } = await parent();

    if (!collection) {
        error(500, 'Collection not loaded by layout');
    }

    const routeBuilder = sampleTypeRoutes[collection.sample_type];
    if (!routeBuilder) {
        error(404, `Unknown sample type: ${collection.sample_type}`);
    }

    redirect(
        307,
        routeBuilder(datasetId, collection.sample_type.toLowerCase(), collection.collection_id)
    );
};
