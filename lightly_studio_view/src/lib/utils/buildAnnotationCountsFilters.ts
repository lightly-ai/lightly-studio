import {
    type VideoFieldsBoundsView,
    type VideoFilter,
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

export function buildVideoAnnotationCountsFilter({
    metadataFilters,
    annotationFilter,
    videoBoundsValues,
    sampleIds
}: {
    metadataFilters: MetadataFilters | undefined;
    annotationFilter: AnnotationsFilter | undefined;
    videoBoundsValues: VideoFieldsBoundsView | null | undefined;
    sampleIds?: string[];
}): VideoFilter {
    console.log('Building video annotation counts filter with:', {
        sampleIds
    });
    return {
        sample_filter: {
            metadata_filters: metadataFilters,
            ...(sampleIds && sampleIds.length > 0 ? { sample_ids: sampleIds } : {})
        },
        ...(annotationFilter ? { frame_annotation_filter: annotationFilter } : {}),
        ...(videoBoundsValues ?? {})
    };
}
