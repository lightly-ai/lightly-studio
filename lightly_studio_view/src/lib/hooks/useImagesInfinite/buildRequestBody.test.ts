import { describe, expect, it, vi } from 'vitest';
import { buildRequestBody } from './buildRequestBody';

type Params = Parameters<typeof buildRequestBody>[0];

const metadataFilterFixture = { key: 'temp', op: '>=' as const, value: 10 };

vi.mock('$lib/hooks/useMetadataFilters/useMetadataFilters', () => ({
    createMetadataFilters: vi.fn(() => [metadataFilterFixture])
}));

describe('buildRequestBody', () => {
    describe('pagination', () => {
        it('uses pageParam as offset', () => {
            const result = buildRequestBody({ collection_id: 'col-1', mode: 'normal' }, 40);
            expect(result.pagination?.offset).toBe(40);
        });
    });

    describe('normal mode', () => {
        it('returns base body when no filters provided', () => {
            const result = buildRequestBody({ collection_id: 'col-1', mode: 'normal' }, 0);
            expect(result.sample_ids).toBeUndefined();
            expect(result.filters?.sample_filter?.annotations_filter).toBeUndefined();
            expect(result.filters?.width).toBeUndefined();
            expect(result.filters?.height).toBeUndefined();
        });

        it('propagates collection_ids to annotations_filter', () => {
            const params: Params = {
                collection_id: 'col-1',
                mode: 'normal',
                filters: { collection_ids: ['coll-1', 'coll-2'] }
            };

            const result = buildRequestBody(params, 0);

            expect(result.filters?.sample_filter?.annotations_filter).toEqual({
                collection_ids: ['coll-1', 'coll-2'],
                filter_type: 'annotations'
            });
        });

        it('omits annotations_filter when collection_ids is empty', () => {
            const params: Params = {
                collection_id: 'col-1',
                mode: 'normal',
                filters: { collection_ids: [] }
            };

            const result = buildRequestBody(params, 0);

            expect(result.filters?.sample_filter?.annotations_filter).toBeUndefined();
        });

        it('propagates both annotation_label_ids and collection_ids', () => {
            const params: Params = {
                collection_id: 'col-1',
                mode: 'normal',
                filters: { annotation_label_ids: ['lbl-1'], collection_ids: ['coll-1'] }
            };

            const result = buildRequestBody(params, 0);

            expect(result.filters?.sample_filter?.annotations_filter).toEqual({
                annotation_label_ids: ['lbl-1'],
                collection_ids: ['coll-1'],
                filter_type: 'annotations'
            });
        });

        it('propagates tag_ids', () => {
            const result = buildRequestBody(
                { collection_id: 'col-1', mode: 'normal', filters: { tag_ids: ['t1', 't2'] } },
                0
            );
            expect(result.filters?.sample_filter?.tag_ids).toEqual(['t1', 't2']);
        });

        it('omits tag_ids when empty', () => {
            const result = buildRequestBody(
                { collection_id: 'col-1', mode: 'normal', filters: { tag_ids: [] } },
                0
            );
            expect(result.filters?.sample_filter?.tag_ids).toBeUndefined();
        });

        it('propagates sample_ids', () => {
            const result = buildRequestBody(
                { collection_id: 'col-1', mode: 'normal', filters: { sample_ids: ['s1'] } },
                0
            );
            expect(result.filters?.sample_filter?.sample_ids).toEqual(['s1']);
        });

        it('omits sample_ids when empty', () => {
            const result = buildRequestBody(
                { collection_id: 'col-1', mode: 'normal', filters: { sample_ids: [] } },
                0
            );
            expect(result.filters?.sample_filter?.sample_ids).toBeUndefined();
        });

        it('maps dimensions to width and height filters', () => {
            const result = buildRequestBody(
                {
                    collection_id: 'col-1',
                    mode: 'normal',
                    filters: {
                        dimensions: {
                            min_width: 100,
                            max_width: 800,
                            min_height: 50,
                            max_height: 600
                        }
                    }
                },
                0
            );
            expect(result.filters?.width).toEqual({ min: 100, max: 800 });
            expect(result.filters?.height).toEqual({ min: 50, max: 600 });
        });

        it('omits width and height when dimensions not set', () => {
            const result = buildRequestBody(
                { collection_id: 'col-1', mode: 'normal', filters: {} },
                0
            );
            expect(result.filters?.width).toBeUndefined();
            expect(result.filters?.height).toBeUndefined();
        });
    });

    describe('classifier mode', () => {
        it('merges positive and negative sample ids into sample_ids', () => {
            const result = buildRequestBody(
                {
                    collection_id: 'col-1',
                    mode: 'classifier',
                    classifierSamples: {
                        positiveSampleIds: ['p1', 'p2'],
                        negativeSampleIds: ['n1']
                    }
                },
                0
            );
            expect(result.sample_ids).toEqual(['p1', 'p2', 'n1']);
        });

        it('returns base body when classifierSamples is undefined', () => {
            const result = buildRequestBody({ collection_id: 'col-1', mode: 'classifier' }, 0);
            expect(result.sample_ids).toBeUndefined();
        });
    });

    describe('common fields', () => {
        it('passes sort_by through', () => {
            const sort = [
                {
                    source: 'image' as const,
                    field_name: 'score',
                    direction: 'desc' as const,
                    is_numeric: false
                }
            ];
            const result = buildRequestBody(
                { collection_id: 'col-1', mode: 'normal', sort_by: sort },
                0
            );
            expect(result.sort_by).toEqual(sort);
        });

        it('converts null sort_by to undefined', () => {
            const result = buildRequestBody(
                { collection_id: 'col-1', mode: 'normal', sort_by: null },
                0
            );
            expect(result.sort_by).toBeUndefined();
        });

        it('passes text_embedding through', () => {
            const result = buildRequestBody(
                { collection_id: 'col-1', mode: 'normal', text_embedding: [0.1, 0.2] },
                0
            );
            expect(result.text_embedding).toEqual([0.1, 0.2]);
        });

        it('applies metadata_values via createMetadataFilters', () => {
            const result = buildRequestBody(
                {
                    collection_id: 'col-1',
                    mode: 'normal',
                    metadata_values: { key: { min: 0, max: 1 } }
                },
                0
            );
            expect(result.filters?.sample_filter?.metadata_filters).toEqual([
                metadataFilterFixture
            ]);
        });
    });
});
