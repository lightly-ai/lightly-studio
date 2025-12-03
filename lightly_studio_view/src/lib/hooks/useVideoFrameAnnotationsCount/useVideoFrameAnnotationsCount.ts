import type { VideoFrameAnnotationsCounterFilter } from '$lib/api/lightly_studio_local';
import { countVideoFrameAnnotationsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

export const useVideoFrameAnnotationCounts = ({
    datasetId,
    filter
}: {
    datasetId: string;
    filter: VideoFrameAnnotationsCounterFilter;
}) =>
    createQuery(
        countVideoFrameAnnotationsOptions({
            path: { video_frame_dataset_id: datasetId },
            body: {
                filter
            }
        })
    );
