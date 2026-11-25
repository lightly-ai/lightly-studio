import {
    type VideoFrameFieldsBoundsView,
    type VideoFrameFilter
} from '$lib/api/lightly_studio_local';
import { createMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters.js';
import type { AnnotationsFilter } from '$lib/api/lightly_studio_local/types.gen.js';

type MetadataFilters = ReturnType<typeof createMetadataFilters>;

export function buildVideoFrameAnnotationCountsFilter({
    metadataFilters,
    annotationFilter,
    videoFramesBoundsValues
}: {
    metadataFilters: MetadataFilters | undefined;
    annotationFilter: AnnotationsFilter | undefined;
    videoFramesBoundsValues: VideoFrameFieldsBoundsView | null | undefined;
}): VideoFrameFilter {
    return {
        sample_filter: {
            metadata_filters: metadataFilters,
            ...(annotationFilter ? { annotations_filter: annotationFilter } : {})
        },
        ...(videoFramesBoundsValues ?? {})
    };
}
