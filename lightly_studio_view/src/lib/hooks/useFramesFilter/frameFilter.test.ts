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
            filter_type: 'video_frame',
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
            filter_type: 'video_frame',
            video_id: 'vid-1',
            frame_number: { min: 1, max: 5 },
            sample_filter: {
                sample_ids: ['s1', 's2'],

                annotations_filter: {
                    filter_type: 'annotations',
                    annotation_label_ids: ['a1']
                },
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
            filter_type: 'video_frame',
            sample_filter: {
                metadata_filters: [{ key: 'temp', value: 10, op: '>=' }]
            },
            frame_number: {}
        });
    });

    describe('pinned output', () => {
        const M = { key: 'temp', value: 10, op: '>=' as const };

        it('pins every field', async () => {
            const { createMetadataFilters } =
                await import('../useMetadataFilters/useMetadataFilters');
            vi.mocked(createMetadataFilters).mockReturnValueOnce([M]);

            expect(
                getFrameFilter({
                    collection_id: 'coll-1',
                    video_id: 'vid-1',
                    frame_bounds: { frame_number: { min: 0, max: 9 } },
                    filters: {
                        annotation_label_ids: ['l'],
                        tag_ids: ['t'],
                        sample_ids: ['s'],
                        metadata_values: { temp: { min: 10, max: 20 } }
                    }
                })
            ).toEqual({
                filter_type: 'video_frame',
                video_id: 'vid-1',
                frame_number: { min: 0, max: 9 },
                sample_filter: {
                    annotations_filter: { filter_type: 'annotations', annotation_label_ids: ['l'] },
                    tag_ids: ['t'],
                    sample_ids: ['s'],
                    metadata_filters: [M]
                }
            });
        });

        it('drops empty lists', () => {
            expect(
                getFrameFilter({
                    collection_id: 'coll-1',
                    filters: { tag_ids: [], sample_ids: [], annotation_label_ids: [] }
                })
            ).toEqual({ filter_type: 'video_frame', frame_number: {} });
        });

        it('omits a null or empty video id', () => {
            const expected = { filter_type: 'video_frame', frame_number: {} };
            expect(getFrameFilter({ collection_id: 'coll-1', video_id: null })).toEqual(expected);
            expect(getFrameFilter({ collection_id: 'coll-1', video_id: '' })).toEqual(expected);
        });

        it('passes categorical-only metadata', async () => {
            const { createMetadataFilters } =
                await import('../useMetadataFilters/useMetadataFilters');
            vi.mocked(createMetadataFilters).mockClear();
            vi.mocked(createMetadataFilters).mockReturnValueOnce([M]);
            const C = { color: ['red'] };

            const filter = getFrameFilter({
                collection_id: 'coll-1',
                filters: { categorical_metadata_values: C }
            });

            expect(createMetadataFilters).toHaveBeenCalledWith({}, C);
            expect(filter?.sample_filter?.metadata_filters).toEqual([M]);
        });
    });
});
