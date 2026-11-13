import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
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

describe('QueryEditorPanel', () => {
    it('updates the query and invalidates all queries when re-applying the same query', async () => {
        render(QueryEditorPanel, {
            props: {
                onClose: vi.fn(),
                sampleType: 'image',
                queryExpression: { query_expr: queryExpr, query_expr_str: 'width < 500' },
                updateQueryExpr
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
        render(QueryEditorPanel, {
            props: { onClose: vi.fn(), sampleType: 'video', queryExpression: null, updateQueryExpr }
        });

        expect(screen.getByText('duration_s')).toBeInTheDocument();
        expect(screen.getByText(/Frame annotations are not supported yet/)).toBeInTheDocument();
        await fireEvent.click(screen.getByRole('button', { name: 'Apply' }));
        expect(updateQueryExpr).toHaveBeenCalledWith({
            query_expr: queryExpr,
            query_expr_str: 'duration_s > 10'
        });
    });
});
