import type { ImageFilter } from '$lib/api/lightly_studio_local';
import { withFilterOverrides } from '$lib/utils';

interface DistributionBaseFilter extends ImageFilter {
    filter_type: 'image';
}

/**
 * Keeps the context filters of the image filter and removes the analysis filters
 * (dimensions, labels, metadata). Tags, sample ids, confusion cell, query and the
 * plot selection pass through.
 */
export function buildDistributionBaseFilter(
    imageFilter: ImageFilter | null | undefined
): DistributionBaseFilter | undefined {
    return withFilterOverrides('image', imageFilter, {
        width: undefined,
        height: undefined,
        sample_filter: { annotations_filter: undefined, metadata_filters: undefined }
    });
}
