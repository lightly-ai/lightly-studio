import type { VideoFilter } from '$lib/api/lightly_studio_local';
import { buildVideoFilter } from '$lib/hooks';

type VideoFilterParams = Parameters<typeof buildVideoFilter>[0];

// The metadata requests take image or video filters, so they need the filter type.
const withFilterType = (value: VideoFilter | null) =>
    value ? { ...value, filter_type: 'video' as const } : undefined;

/**
 * Builds the two filters of the video distribution panel from the filter params of the
 * videos grid.
 */
export function buildVideoDistributionFilters(filterParams: VideoFilterParams) {
    return {
        // The filter of the videos grid, with every sidebar filter applied.
        filter: withFilterType(buildVideoFilter(filterParams)),
        // Only the tags and sample ids of the grid, so the totals stay stable.
        baseFilter: withFilterType(
            buildVideoFilter(
                filterParams && {
                    collection_id: filterParams.collection_id,
                    filters: {
                        sample_ids: filterParams.filters?.sample_ids,
                        tag_ids: filterParams.filters?.tag_ids
                    }
                }
            )
        )
    };
}
