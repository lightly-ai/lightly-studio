import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { useImageFilters } from './useImageFilters';
import type { QueryExpr, SortFieldExpr } from '$lib/api/lightly_studio_local/types.gen';
import { SortDirection } from '$lib/api/lightly_studio_local/types.gen';

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
            const sort: SortFieldExpr[] = [
                {
                    source: 'image',
                    field_name: 'score',
                    direction: SortDirection.DESC,
                    is_numeric: false
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
});
