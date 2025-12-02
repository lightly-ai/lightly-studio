import type { VideoFrameAnnotationsCounterFilter } from '$lib/api/lightly_studio_local';
import { countVideoFrameAnnotationsByVideoDatasetOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';


export const useVideoFrameAnnotationCounts = ({
    datasetId,
    filter
}: {
    datasetId: string;
    filter: VideoFrameAnnotationsCounterFilter
}) =>
    createQuery(
        countVideoFrameAnnotationsByVideoDatasetOptions({
            path: { video_frame_dataset_id: datasetId },
            body: {
                filter
            }
        })
    );
