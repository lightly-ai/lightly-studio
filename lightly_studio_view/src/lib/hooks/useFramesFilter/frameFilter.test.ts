import { describe, it, expect, vi } from 'vitest';
import { getFrameFilter } from './frameFilter';

vi.mock('../useMetadataFilters/useMetadataFilters', () => ({
    createMetadataFilters: vi.fn(() => [])
}));

describe('getFrameFilter', () => {
    it('returns null when params are null', () => {
        expect(getFrameFilter(null)).toBeNull();
    });

    it('returns null when collection_id is missing', () => {
        expect(
            getFrameFilter({
                collection_id: ''
            })
        ).toBeNull();
    });

    it('builds minimal filter with collection_id', () => {
        expect(
            getFrameFilter({
                collection_id: 'coll-1'
            })
        ).toEqual({
            sample_filter: { collection_id: 'coll-1' },
            frame_number: {}
        });
    });

    it('includes frame_bounds, video_id, and ids', () => {
        const filter = getFrameFilter({
            collection_id: 'coll-1',
            video_id: 'vid-1',
            frame_bounds: { frame_number: { min: 1, max: 5 } },
            filters: {
                sample_ids: ['s1', 's2'],
                annotation_label_ids: ['a1'],
                tag_ids: ['t1']
            }
        });

        expect(filter).toEqual({
            video_id: 'vid-1',
            frame_number: { min: 1, max: 5 },
            sample_filter: {
                collection_id: 'coll-1',
                sample_ids: ['s1', 's2'],
                annotation_label_ids: ['a1'],
                tag_ids: ['t1']
            }
        });
    });

    it('adds metadata_filters when createMetadataFilters returns data', async () => {
        const { createMetadataFilters } = await import('../useMetadataFilters/useMetadataFilters');
        vi.mocked(createMetadataFilters).mockReturnValueOnce([
            { key: 'temp', value: 10, op: '>=' as const }
        ]);

        const filter = getFrameFilter({
            collection_id: 'coll-1',
            filters: {
                metadata_values: { temp: { min: 10, max: 20 } }
            }
        });

        expect(filter).toEqual({
            sample_filter: {
                collection_id: 'coll-1',
                metadata_filters: [{ key: 'temp', value: 10, op: '>=' }]
            },
            frame_number: {}
        });
    });
});
