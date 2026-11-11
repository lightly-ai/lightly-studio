import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { useImageFilters } from './useImageFilters';
import type { QueryExpr, ImageSortFieldExpr } from '$lib/api/lightly_studio_local/types.gen';
import { SortDirection } from '$lib/api/lightly_studio_local/types.gen';
import { createMetadataFilters } from '../useMetadataFilters/useMetadataFilters';

const queryExpr = {
    match_expr: {
        type: 'string_expr',
        field: { table: 'image', name: 'caption' },
        operator: '==',
        value: 'cat'
    }
} satisfies QueryExpr;

const normalFilterParams = {
    collection_id: 'collection-1',
    mode: 'normal'
} as Parameters<ReturnType<typeof useImageFilters>['updateFilterParams']>[0];

vi.mock('../useMetadataFilters/useMetadataFilters', () => ({
    createMetadataFilters: vi.fn(() => [])
}));

describe('useImageFilters', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        const { updateFilterParams, updateQueryExpr } = useImageFilters();
        updateFilterParams({} as Parameters<typeof updateFilterParams>[0]);
        updateQueryExpr(undefined);
    });

    describe('updateSortBy', () => {
        it('sets imageSortBy to the provided sort fields', () => {
            const { imageSortBy, updateSortBy } = useImageFilters();
            const sort: ImageSortFieldExpr[] = [
                {
                    source: 'image',
                    field_name: 'score',
                    direction: SortDirection.DESC
                }
            ];

            updateSortBy(sort);

            expect(get(imageSortBy)).toEqual(sort);
        });

        it('sets imageSortBy to null when called with null', () => {
            const { imageSortBy, updateSortBy } = useImageFilters();

            updateSortBy(null);

            expect(get(imageSortBy)).toBeNull();
        });
    });

    describe('imageFilter query expression', () => {
        it('includes query_expr when set and omits it when toggled off', () => {
            const { imageFilter, updateFilterParams, updateQueryExpr } = useImageFilters();
            updateFilterParams(normalFilterParams);

            updateQueryExpr({ query_expr: queryExpr, query_expr_str: 'caption == cat' });
            expect(get(imageFilter)?.sample_filter?.query_expr).toEqual(queryExpr);

            updateQueryExpr(undefined);
            expect(get(imageFilter)?.sample_filter?.query_expr).toBeUndefined();
        });
    });

    describe('updateConfusionCell', () => {
        const cell = {
            evaluation_run_id: 'run-1',
            gt_label: 'car',
            pred_label: 'truck'
        };

        it('adds confusion_cell alongside an existing sample_ids selection', () => {
            const { imageFilter, updateFilterParams, updateSampleIds, updateConfusionCell } =
                useImageFilters();
            updateFilterParams(normalFilterParams);

            updateSampleIds(['sample-1', 'sample-2']);
            updateConfusionCell(cell);

            const sampleFilter = get(imageFilter)?.sample_filter;
            expect(sampleFilter?.sample_ids).toEqual(['sample-1', 'sample-2']);
            expect(sampleFilter?.confusion_cell).toEqual(cell);
        });

        it('clears confusion_cell when called with null, leaving sample_ids intact', () => {
            const { imageFilter, updateFilterParams, updateSampleIds, updateConfusionCell } =
                useImageFilters();
            updateFilterParams(normalFilterParams);

            updateSampleIds(['sample-1']);
            updateConfusionCell(cell);
            updateConfusionCell(null);

            const sampleFilter = get(imageFilter)?.sample_filter;
            expect(sampleFilter?.confusion_cell).toBeUndefined();
            expect(sampleFilter?.sample_ids).toEqual(['sample-1']);
        });
    });

    describe('imageFilter output', () => {
        const REGION = {
            polygon: [
                { x: 0, y: 0 },
                { x: 1, y: 0 },
                { x: 0, y: 1 }
            ]
        };
        const CELL = { evaluation_run_id: 'run-1', gt_label: 'car', pred_label: 'truck' };
        const M = { filter_type: 'metadata', key: 'k', value: 1 } as unknown as ReturnType<
            typeof createMetadataFilters
        >[number];
        const C = { cat: ['a'] } as unknown as Parameters<typeof createMetadataFilters>[1];

        const setParams = (params: object) => {
            const { updateFilterParams } = useImageFilters();
            updateFilterParams({
                ...normalFilterParams,
                ...params
            } as typeof normalFilterParams);
        };

        it('returns null without a collection id', () => {
            const { imageFilter } = useImageFilters();
            setParams({ collection_id: undefined });
            expect(get(imageFilter)).toBeNull();
        });

        it('returns null in classifier mode', () => {
            const { imageFilter } = useImageFilters();
            setParams({ mode: 'classifier' });
            expect(get(imageFilter)).toBeNull();
        });

        it('returns only the filter type when nothing is set', () => {
            const { imageFilter } = useImageFilters();
            setParams({});
            expect(get(imageFilter)).toEqual({ filter_type: 'image' });
        });

        it('pins every field', () => {
            const { imageFilter, updateQueryExpr } = useImageFilters();
            vi.mocked(createMetadataFilters).mockReturnValueOnce([M]);
            updateQueryExpr({ query_expr: queryExpr, query_expr_str: 'caption == cat' });
            setParams({
                filters: {
                    dimensions: { min_width: 1, max_width: 2, min_height: 3, max_height: 4 },
                    sample_ids: ['s'],
                    embedding_region: REGION,
                    annotation_label_ids: ['l'],
                    tag_ids: ['t'],
                    confusion_cell: CELL
                },
                metadata_values: { k: { min: 0, max: 1 } }
            });
            expect(get(imageFilter)).toEqual({
                filter_type: 'image',
                width: { min: 1, max: 2 },
                height: { min: 3, max: 4 },
                sample_filter: {
                    sample_ids: ['s'],
                    embedding_region: REGION,
                    annotations_filter: {
                        filter_type: 'annotations',
                        annotation_label_ids: ['l']
                    },
                    tag_ids: ['t'],
                    confusion_cell: CELL,
                    metadata_filters: [M],
                    query_expr: queryExpr
                }
            });
        });

        it('drops empty lists', () => {
            const { imageFilter } = useImageFilters();
            vi.mocked(createMetadataFilters).mockReturnValueOnce([]);
            setParams({
                filters: { sample_ids: [], annotation_label_ids: [], tag_ids: [] },
                metadata_values: {}
            });
            expect(get(imageFilter)).toEqual({ filter_type: 'image' });
        });

        it('sends only annotation label ids', () => {
            const { imageFilter } = useImageFilters();
            setParams({ filters: { annotation_label_ids: ['l'], collection_ids: ['c'] } });
            expect(get(imageFilter)).toEqual({
                filter_type: 'image',
                sample_filter: {
                    annotations_filter: {
                        filter_type: 'annotations',
                        annotation_label_ids: ['l']
                    }
                }
            });
        });

        it('passes categorical-only metadata', () => {
            const { imageFilter } = useImageFilters();
            vi.mocked(createMetadataFilters).mockReturnValueOnce([M]);
            setParams({ categorical_metadata_values: C });
            expect(get(imageFilter)?.sample_filter?.metadata_filters).toEqual([M]);
            expect(createMetadataFilters).toHaveBeenCalledWith({}, C);
        });
    });
});
