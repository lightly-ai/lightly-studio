import { error, redirect } from '@sveltejs/kit';
import { SampleType } from '$lib/api/lightly_studio_local';
import { routeHelpers } from '$lib/routes';
import type { PageLoad } from './$types';

const sampleTypeRoutes: Record<SampleType, (datasetId: string) => string> = {
    [SampleType.VIDEO]: routeHelpers.toVideos,
    [SampleType.VIDEO_FRAME]: routeHelpers.toFrames,
    [SampleType.IMAGE]: routeHelpers.toSamples,
    [SampleType.ANNOTATION]: routeHelpers.toAnnotations,
    [SampleType.CAPTION]: routeHelpers.toCaptions
};

export const load: PageLoad = async ({ parent }) => {
    const { dataset } = await parent();

    if (!dataset) {
        error(500, 'Dataset not loaded by layout');
    }

    const routeBuilder = sampleTypeRoutes[dataset.sample_type];
    if (!routeBuilder) {
        error(404, `Unknown sample type: ${dataset.sample_type}`);
    }

    redirect(307, routeBuilder(dataset.dataset_id));
};
