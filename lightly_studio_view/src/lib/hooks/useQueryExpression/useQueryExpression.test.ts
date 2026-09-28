import { describe, expect, it } from 'vitest';
import { get } from 'svelte/store';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
import { useQueryExpression } from './useQueryExpression';

const expression = {
    query_expr: {
        match_expr: {
            type: 'integer_expr' as const,
            field: { table: 'video', name: 'width' },
            operator: '>' as const,
            value: 100
        }
    },
    query_expr_str: 'width > 100'
};

describe('useQueryExpression', () => {
    it('keeps the image and the video query state separate', () => {
        const video = useQueryExpression('video');
        const image = useQueryExpression('image');

        video.updateQueryExpr(expression);

        expect(get(video.queryExpression)).toEqual(expression);
        expect(get(useVideoFilters().videoQueryExpression)).toEqual(expression);
        expect(get(image.queryExpression)).toBeNull();
        expect(get(useImageFilters().imageQueryExpression)).toBeNull();

        video.updateQueryExpr(undefined);
        expect(get(video.queryExpression)).toBeNull();
    });
});
