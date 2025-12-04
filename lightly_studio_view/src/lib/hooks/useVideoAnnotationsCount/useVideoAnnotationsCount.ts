import { createQuery } from '@tanstack/svelte-query';
import { countVideoFrameAnnotationsByVideoDatasetOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { type VideoCountAnnotationsFilter } from '$lib/api/lightly_studio_local';

export const useVideoAnnotationCounts = ({
    datasetId,
    filter
}: {
    datasetId: string;
    filter: VideoCountAnnotationsFilter;
}) =>
    createQuery(
        countVideoFrameAnnotationsByVideoDatasetOptions({
            path: { dataset_id: datasetId },
            body: {
                filter
            }
        })
    );
