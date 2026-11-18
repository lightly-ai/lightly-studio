import { describe, expect, it } from 'vitest';
import { buildSequencePlotFilter } from './buildSequencePlotFilter';

describe('buildSequencePlotFilter', () => {
    it('sends the tags and the labels of the grid filter without the region', () => {
        const groupAnnotationFilter = {
            filter_type: 'annotations' as const,
            annotation_label_ids: ['label-1']
        };

        expect(
            buildSequencePlotFilter({
                filter_type: 'mcap_sequence',
                sample_filter: { tag_ids: ['tag-1'], embedding_region: { polygon: [] } },
                group_annotation_filter: groupAnnotationFilter
            })
        ).toEqual({
            filter_type: 'mcap_sequence',
            sample_filter: { tag_ids: ['tag-1'] },
            group_annotation_filter: groupAnnotationFilter
        });
    });

    it('sends an empty sequence filter without a grid filter', () => {
        expect(buildSequencePlotFilter(null)).toEqual({ filter_type: 'mcap_sequence' });
    });
});
