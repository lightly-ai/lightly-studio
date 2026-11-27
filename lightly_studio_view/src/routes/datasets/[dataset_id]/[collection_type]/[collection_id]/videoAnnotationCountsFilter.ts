import type {
    AnnotationsFilter,
    MetadataFilter,
    VideoFieldsBoundsView,
    VideoFilter
} from '$lib/api/lightly_studio_local';
import { withFilterOverrides } from '$lib/utils';

interface VideoAnnotationCountsFilter extends VideoFilter {
    filter_type: 'video';
}

interface BuildVideoAnnotationCountsFilterParams {
    videoFilter: VideoFilter | null | undefined;
    videoBoundsValues: VideoFieldsBoundsView | null | undefined;
    annotationFilter: AnnotationsFilter | undefined;
    metadataFilters: MetadataFilter[] | undefined;
}

/**
 * Builds the video filter for class counts. Starts from the shared video filter so the plot
 * selection and tags carry over. Bounds, annotation filter and metadata filters come from the
 * passed parts.
 */
export function buildVideoAnnotationCountsFilter({
    videoFilter,
    videoBoundsValues,
    annotationFilter,
    metadataFilters
}: BuildVideoAnnotationCountsFilterParams): VideoAnnotationCountsFilter | undefined {
    return withFilterOverrides('video', videoFilter, {
        width: videoBoundsValues?.width,
        height: videoBoundsValues?.height,
        fps: videoBoundsValues?.fps,
        duration_s: videoBoundsValues?.duration_s,
        frame_annotation_filter: annotationFilter,
        sample_filter: { metadata_filters: metadataFilters }
    });
}
