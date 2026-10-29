import { get } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { useQueryPanelState } from './useQueryPanelState';

describe('useQueryPanelState', () => {
    it('gives each collection its own draft and last query back', () => {
        const expression = { query_expr_str: 'width < 500', query_expr: {} } as never;
        const images = useQueryPanelState('images-1');
        images.draft.set('width < 5');
        images.lastQueryExpression.set(expression);

        // A fresh hook call, like a remounted panel, sees the same values.
        expect(get(useQueryPanelState('images-1').draft)).toBe('width < 5');
        expect(get(useQueryPanelState('images-1').lastQueryExpression)).toBe(expression);

        expect(get(useQueryPanelState('images-2').draft)).toBeNull();
        expect(get(useQueryPanelState('images-2').lastQueryExpression)).toBeNull();
    });
});
