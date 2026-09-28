import { describe, expect, it } from 'vitest';
import { buildVideoDistributionFilters } from './videoDistributionFilters';

describe('buildVideoDistributionFilters', () => {
    it('returns no filters without filter params', () => {
        expect(buildVideoDistributionFilters(null)).toEqual({
            filter: undefined,
            baseFilter: undefined
        });
    });

    it('keeps only the tags and sample ids in the base filter', () => {
        const { filter, baseFilter } = buildVideoDistributionFilters({
            collection_id: 'collection-1',
            filters: {
                tag_ids: ['tag-1'],
                sample_ids: ['sample-1'],
                annotation_frames_label_ids: ['label-1']
            },
            video_bounds: { width: { min: 100, max: 200 } } as never
        });

        expect(filter?.filter_type).toBe('video');
        expect(filter?.width).toEqual({ min: 100, max: 200 });
        expect(filter?.frame_annotation_filter).toBeDefined();
        expect(baseFilter).toEqual({
            filter_type: 'video',
            sample_filter: { sample_ids: ['sample-1'], tag_ids: ['tag-1'] }
        });
    });
});
