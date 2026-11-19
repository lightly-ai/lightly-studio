import type { McapSequenceFilter } from '$lib/api/lightly_studio_local';

/**
 * Builds the filter of the sequence embedding plot from the grid filter. The plot highlights
 * its own region selection rather than filtering by it, so the region is not sent.
 */
export const buildSequencePlotFilter = (
    gridFilter: McapSequenceFilter | null | undefined
): McapSequenceFilter => {
    const tagIds = gridFilter?.sample_filter?.tag_ids;
    const groupAnnotationFilter = gridFilter?.group_annotation_filter;
    return {
        filter_type: 'mcap_sequence',
        ...(tagIds ? { sample_filter: { tag_ids: tagIds } } : {}),
        ...(groupAnnotationFilter ? { group_annotation_filter: groupAnnotationFilter } : {})
    };
};
