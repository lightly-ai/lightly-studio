import { beforeEach, describe, expect, it } from 'vitest';
import { GRID_PAGE_SIZE } from '$lib/constants';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { buildRequestBody } from './buildRequestBody';

type Params = Parameters<typeof buildRequestBody>[0];

const region = {
    polygon: [
        { x: 0, y: 0 },
        { x: 1, y: 0 },
        { x: 0, y: 1 }
    ]
};
const cell = { evaluation_run_id: 'run-1', gt_label: 'car', pred_label: 'truck' };
const metadataValues = { temp: { min: 10, max: 100 } };
const metadataFilter = { key: 'temp', op: '>=', value: 10 };
const categoricalValues = { color: ['red'] };
const queryExpr = { field: 'width', op: '>', value: 10 } as unknown as Params['query_expr'];

describe('buildRequestBody', () => {
    beforeEach(() => {
        useGlobalStorage().updateMetadataBounds({ temp: { min: 0, max: 100 } });
    });

    describe('pins', () => {
        it('pins every normal-mode field', () => {
            const sort = [
                { source: 'image' as const, field_name: 'score', direction: 'desc' as const }
            ];
            const result = buildRequestBody(
                {
                    collection_id: 'col-1',
                    mode: 'normal',
                    query_expr: queryExpr,
                    metadata_values: metadataValues,
                    sort_by: sort,
                    text_embedding: [0.1, 0.2],
                    filters: {
                        annotation_label_ids: ['lbl-1'],
                        collection_ids: ['coll-1'],
                        tag_ids: ['t1'],
                        sample_ids: ['s1'],
                        confusion_cell: cell,
                        embedding_region: region,
                        dimensions: {
                            min_width: 100,
                            max_width: 800,
                            min_height: 50,
                            max_height: 600
                        }
                    }
                },
                40
            );

            expect(result).toEqual({
                pagination: { offset: 40, limit: GRID_PAGE_SIZE },
                text_embedding: [0.1, 0.2],
                sort_by: sort,
                filters: {
                    width: { min: 100, max: 800 },
                    height: { min: 50, max: 600 },
                    sample_filter: {
                        sample_ids: ['s1'],
                        tag_ids: ['t1'],
                        annotations_filter: {
                            annotation_label_ids: ['lbl-1'],
                            collection_ids: ['coll-1'],
                            filter_type: 'annotations'
                        },
                        embedding_region: region,
                        confusion_cell: cell,
                        metadata_filters: [metadataFilter],
                        query_expr: queryExpr
                    }
                }
            });
        });

        it('pins the classifier body', () => {
            const result = buildRequestBody(
                {
                    collection_id: 'col-1',
                    mode: 'classifier',
                    query_expr: queryExpr,
                    metadata_values: metadataValues,
                    classifierSamples: { positiveSampleIds: ['p1'], negativeSampleIds: ['n1'] }
                },
                0
            );

            expect(result).toEqual({
                pagination: { offset: 0, limit: GRID_PAGE_SIZE },
                sample_ids: ['p1', 'n1'],
                filters: {
                    sample_filter: {
                        query_expr: queryExpr,
                        metadata_filters: [metadataFilter]
                    }
                }
            });
        });

        it('sends empty sample ids for empty classifier lists', () => {
            const result = buildRequestBody(
                {
                    collection_id: 'col-1',
                    mode: 'classifier',
                    classifierSamples: { positiveSampleIds: [], negativeSampleIds: [] }
                },
                0
            );
            expect(result.sample_ids).toEqual([]);
        });

        it('sends no sample ids without classifier samples', () => {
            const result = buildRequestBody({ collection_id: 'col-1', mode: 'classifier' }, 0);
            expect('sample_ids' in result).toBe(false);
        });

        it('passes categorical-only metadata', () => {
            const result = buildRequestBody(
                {
                    collection_id: 'col-1',
                    mode: 'normal',
                    categorical_metadata_values: categoricalValues
                },
                0
            );
            expect(result.filters?.sample_filter?.metadata_filters).toEqual([
                { key: 'color', op: 'in', value: ['red'] }
            ]);
        });
    });

    describe('wire changes', () => {
        it('sends no sample filter when nothing is set', () => {
            const result = buildRequestBody({ collection_id: 'col-1', mode: 'normal' }, 0);
            expect(result.filters).toEqual({});
        });

        it('sends no empty metadata filters', () => {
            const result = buildRequestBody(
                { collection_id: 'col-1', mode: 'normal', metadata_values: {} },
                0
            );
            expect(result.filters?.sample_filter).toBeUndefined();
        });
    });

    describe('normal mode', () => {
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

        it('omits tag_ids when empty', () => {
            const result = buildRequestBody(
                { collection_id: 'col-1', mode: 'normal', filters: { tag_ids: [] } },
                0
            );
            expect(result.filters?.sample_filter?.tag_ids).toBeUndefined();
        });

        it('omits sample_ids when empty', () => {
            const result = buildRequestBody(
                { collection_id: 'col-1', mode: 'normal', filters: { sample_ids: [] } },
                0
            );
            expect(result.filters?.sample_filter?.sample_ids).toBeUndefined();
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
    });

    describe('common fields', () => {
        it('converts null sort_by to undefined', () => {
            const result = buildRequestBody(
                { collection_id: 'col-1', mode: 'normal', sort_by: null },
                0
            );
            expect(result.sort_by).toBeUndefined();
        });
    });
});
