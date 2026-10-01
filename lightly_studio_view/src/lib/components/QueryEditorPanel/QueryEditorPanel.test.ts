import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import QueryEditorPanel from './QueryEditorPanel.svelte';

const { updateQueryExpr, invalidateQueries, imageQueryExpression, queryExpr } = await vi.hoisted(
    async () => {
        const { writable } = await import('svelte/store');
        return {
            updateQueryExpr: vi.fn(),
            invalidateQueries: vi.fn(),
            imageQueryExpression: writable({ query_expr_str: 'width < 500' }),
            queryExpr: { match_expr: { type: 'string_expr' } }
        };
    }
);

vi.mock('$lib/components/QueryEditor/useQueryEditor', () => ({
    useQueryEditor: () => ({
        mount: () => () => {},
        translateQuery: () => ({ status: 'ok', queryExpr })
    })
}));
vi.mock('$lib/hooks/useImageFilters/useImageFilters', () => ({
    useImageFilters: () => ({ imageQueryExpression, updateQueryExpr })
}));
vi.mock('@tanstack/svelte-query', () => ({
    useQueryClient: () => ({ invalidateQueries })
}));

describe('QueryEditorPanel', () => {
    it('updates the query and invalidates all queries when re-applying the same query', async () => {
        render(QueryEditorPanel, { props: { onClose: vi.fn() } });

        await fireEvent.click(screen.getByRole('button', { name: 'Re-apply' }));

        expect(updateQueryExpr).toHaveBeenCalledWith({
            query_expr: queryExpr,
            query_expr_str: 'width < 500'
        });
        await waitFor(() => expect(invalidateQueries).toHaveBeenCalledExactlyOnceWith());
    });
});
