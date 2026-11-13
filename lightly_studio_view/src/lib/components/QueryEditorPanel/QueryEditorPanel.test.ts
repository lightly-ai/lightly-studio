import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { useQueryHistory } from '$lib/hooks';
import QueryEditorPanel from './QueryEditorPanel.svelte';

const { updateQueryExpr, invalidateQueries, queryExpr } = await vi.hoisted(async () => {
    return {
        updateQueryExpr: vi.fn(),
        invalidateQueries: vi.fn(),
        queryExpr: { match_expr: { type: 'and' as const, children: [] } }
    };
});

vi.mock('$lib/components/QueryEditor/useQueryEditor', () => ({
    useQueryEditor: () => ({
        mount: () => () => {},
        translateQuery: () => ({ status: 'ok', queryExpr })
    })
}));
vi.mock('@tanstack/svelte-query', () => ({
    useQueryClient: () => ({ invalidateQueries })
}));

const defaultProps = {
    onClose: vi.fn(),
    collectionId: 'collection-1',
    sampleType: 'image' as const,
    queryExpression: null,
    updateQueryExpr
};

describe('QueryEditorPanel', () => {
    it('updates the query and invalidates all queries when re-applying the same query', async () => {
        render(QueryEditorPanel, {
            props: {
                ...defaultProps,
                queryExpression: { query_expr: queryExpr, query_expr_str: 'width < 500' }
            }
        });

        expect(screen.getByText('metadata["quality_score"] >= 0.8')).toBeInTheDocument();

        await fireEvent.click(screen.getByRole('button', { name: 'Re-apply' }));

        expect(updateQueryExpr).toHaveBeenCalledWith({
            query_expr: queryExpr,
            query_expr_str: 'width < 500'
        });
        await waitFor(() => expect(invalidateQueries).toHaveBeenCalledExactlyOnceWith());
    });

    it('applies the video starting query and shows video syntax help', async () => {
        render(QueryEditorPanel, { props: { ...defaultProps, sampleType: 'video' } });

        expect(screen.getByText('duration_s')).toBeInTheDocument();
        expect(screen.getByText(/Frame annotations are not supported yet/)).toBeInTheDocument();
        await fireEvent.click(screen.getByRole('button', { name: 'Apply' }));
        expect(updateQueryExpr).toHaveBeenCalledWith({
            query_expr: queryExpr,
            query_expr_str: 'duration_s > 10'
        });
    });

    it('lists an applied query in the history of its collection only', async () => {
        useQueryHistory().addQuery('other-collection', 'height > 100');
        render(QueryEditorPanel, {
            props: {
                ...defaultProps,
                collectionId: 'applied-collection',
                queryExpression: { query_expr: queryExpr, query_expr_str: 'width < 500' }
            }
        });

        await fireEvent.click(screen.getByRole('button', { name: 'Re-apply' }));
        await fireEvent.click(screen.getByRole('button', { name: 'Query history' }));

        const historyItems = await screen.findAllByTestId('query-history-item');
        expect(historyItems.map((item) => item.textContent?.trim())).toEqual(['width < 500']);
    });

    it('applies a query selected from the history', async () => {
        useQueryHistory().addQuery('history-collection', 'height > 100');
        render(QueryEditorPanel, {
            props: { ...defaultProps, collectionId: 'history-collection' }
        });
        invalidateQueries.mockClear();

        await fireEvent.click(screen.getByRole('button', { name: 'Query history' }));
        await fireEvent.click(await screen.findByText('height > 100'));

        expect(updateQueryExpr).toHaveBeenLastCalledWith({
            query_expr: queryExpr,
            query_expr_str: 'height > 100'
        });
        expect(invalidateQueries).toHaveBeenCalledExactlyOnceWith();
    });
});
