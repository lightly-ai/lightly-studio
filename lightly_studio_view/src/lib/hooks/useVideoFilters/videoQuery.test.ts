import { get } from 'svelte/store';
import { beforeEach, describe, expect, it } from 'vitest';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { useVideoFilters } from './useVideoFilters';

const expression = {
    query_expr: { match_expr: { type: 'and' as const, children: [] } },
    query_expr_str: 'duration_s > 10'
};

describe('video query filters', () => {
    beforeEach(() => {
        useVideoFilters().updateQueryExpr();
        useImageFilters().updateQueryExpr();
    });

    it('combines the query with sidebar filters and clears it independently', () => {
        const filters = useVideoFilters();
        const params = { collection_id: 'videos', filters: { tag_ids: ['reviewed'] } };
        filters.updateFilterParams(params);
        filters.updateQueryExpr(expression);
        filters.updateFilterParams({
            ...params,
            video_bounds: {
                width: { min: 100, max: 1920 },
                height: { min: 100, max: 1080 },
                fps: { min: 24, max: 60 },
                duration_s: { min: 10, max: 120 }
            }
        });

        expect(get(filters.videoFilter)?.sample_filter).toEqual({
            tag_ids: ['reviewed'],
            query_expr: expression.query_expr
        });
        expect(get(useImageFilters().imageQueryExpression)).toBeNull();

        filters.updateQueryExpr();
        expect(get(filters.videoFilter)?.sample_filter).toEqual({ tag_ids: ['reviewed'] });
    });

    it('clears the video query when switching collections', () => {
        const filters = useVideoFilters();
        filters.updateFilterParams({ collection_id: 'first' });
        filters.updateQueryExpr(expression);
        filters.updateFilterParams({ collection_id: 'second' });

        expect(get(filters.videoQueryExpression)).toBeNull();
        expect(get(filters.videoFilter)?.sample_filter?.query_expr).toBeUndefined();
    });

    it('clears image queries on collection changes without changing the video query', () => {
        const filters = useImageFilters();
        filters.updateFilterParams({ collection_id: 'first', mode: 'normal' });
        filters.updateQueryExpr({ ...expression, query_expr_str: 'width > 100' });
        useVideoFilters().updateQueryExpr(expression);
        filters.updateFilterParams({ collection_id: 'second', mode: 'normal' });

        expect(get(filters.imageQueryExpression)).toBeNull();
        expect(get(useVideoFilters().videoQueryExpression)).toEqual(expression);
    });
});
