import type { ImageFilter } from '$lib/api/lightly_studio_local/types.gen.js';
import { withFilterOverrides } from '$lib/utils/withFilterOverrides';

/**
 * Keeps the context filters of the image filter and removes the analysis filters
 * (dimensions, labels, metadata). Tags, sample ids, confusion cell, query and the
 * plot selection pass through.
 */
export function buildDistributionBaseFilter(
    imageFilter: ImageFilter | null | undefined
): (ImageFilter & { filter_type: 'image' }) | undefined {
    return withFilterOverrides('image', imageFilter, {
        width: undefined,
        height: undefined,
        sample_filter: { annotations_filter: undefined, metadata_filters: undefined }
    });
}
