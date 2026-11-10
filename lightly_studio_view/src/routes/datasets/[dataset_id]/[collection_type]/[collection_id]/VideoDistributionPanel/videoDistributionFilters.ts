import type { VideoFilter } from '$lib/api/lightly_studio_local';
import { buildVideoFilter } from '$lib/hooks';
import { withFilterOverrides } from '$lib/utils/withFilterOverrides';

type VideoFilterParams = Parameters<typeof buildVideoFilter>[0];

// The metadata requests take image or video filters, so they need the filter type.
const withFilterType = (value: VideoFilter | null) =>
    value ? { ...value, filter_type: 'video' as const } : undefined;

/**
 * Builds the two filters of the video distribution panel from the filter params of the
 * videos grid.
 */
export function buildVideoDistributionFilters(filterParams: VideoFilterParams) {
    const videoFilter = buildVideoFilter(filterParams);
    return {
        // The filter of the videos grid, with every sidebar filter applied.
        filter: withFilterType(videoFilter),
        // The grid filter without the sidebar filters, so the totals stay stable. It keeps the
        // tags, sample ids and plot selection.
        baseFilter: withFilterOverrides('video', videoFilter, {
            width: undefined,
            height: undefined,
            fps: undefined,
            duration_s: undefined,
            frame_annotation_filter: undefined,
            sample_filter: { metadata_filters: undefined }
        })
    };
}
