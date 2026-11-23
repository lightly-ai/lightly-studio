import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { toast } from 'svelte-sonner';
import { get } from 'svelte/store';
import { useQueryHistory } from '$lib/hooks';
import type { QueryExprTranslationResult } from '$lib/components/QueryEditor/language/query-expr-translation';
import QueryEditorPanel from './QueryEditorPanel.svelte';

const { updateQueryExpr, invalidateQueries, queryExpr, translateQuery } = await vi.hoisted(
    async () => {
        const queryExpr = { match_expr: { type: 'and' as const, children: [] } };
        return {
            updateQueryExpr: vi.fn(),
            invalidateQueries: vi.fn(),
            queryExpr,
            translateQuery: vi.fn((): QueryExprTranslationResult => ({ status: 'ok', queryExpr }))
        };
    }
);

vi.mock('$lib/components/QueryEditor/useQueryEditor', () => ({
    useQueryEditor: () => ({
        mount: (el: HTMLElement, options: { value: string; onChange: (value: string) => void }) => {
            const input = document.createElement('textarea');
            input.setAttribute('aria-label', 'Query');
            input.value = options.value;
            input.addEventListener('input', () => options.onChange(input.value));
            el.append(input);
            return () => input.remove();
        },
        translateQuery
    })
}));
vi.mock('@tanstack/svelte-query', () => ({
    useQueryClient: () => ({ invalidateQueries })
}));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn() } }));

const defaultProps = {
    onClose: vi.fn(),
    collectionId: 'collection-1',
    sampleType: 'image' as const,
    queryExpression: null,
    updateQueryExpr
};

describe('QueryEditorPanel', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it.each([
        ['image', ''],
        ['video', ' \n\t '],
        ['image', '# width < 500'],
        ['video', '# width < 500\n# AND height > 10']
    ] as const)('clears the %s query when applying blank input', async (sampleType, value) => {
        const collectionId = `empty-${sampleType}`;
        render(QueryEditorPanel, {
            props: {
                ...defaultProps,
                collectionId,
                sampleType,
                queryExpression: { query_expr: queryExpr, query_expr_str: 'width < 500' }
            }
        });

        await fireEvent.input(screen.getByRole('textbox', { name: 'Query' }), {
            target: { value }
        });
        translateQuery.mockReturnValueOnce({ status: 'empty' });
        await fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

        expect(updateQueryExpr).toHaveBeenCalledExactlyOnceWith(undefined);
        expect(invalidateQueries).toHaveBeenCalledExactlyOnceWith();
        expect(toast.error).not.toHaveBeenCalled();
        expect(get(useQueryHistory().queryHistory)[collectionId] ?? []).toEqual([]);
    });

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
        expect(
            screen.getByText(
                'frame(object_detection(class_name = "person") AND frame_timestamp_s < 5)'
            )
        ).toBeInTheDocument();
        expect(
            screen.getByText('event(class_name = "run" AND start_time_s < 5)')
        ).toBeInTheDocument();
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

    it('loads a history query that does not translate into the editor without applying it', async () => {
        useQueryHistory().addQuery('invalid-collection', 'removed_field > 1');
        render(QueryEditorPanel, {
            props: { ...defaultProps, collectionId: 'invalid-collection' }
        });
        updateQueryExpr.mockClear();
        translateQuery.mockReturnValueOnce({ status: 'error', errors: [] });

        await fireEvent.click(screen.getByRole('button', { name: 'Query history' }));
        await fireEvent.click(await screen.findByText('removed_field > 1'));

        expect(toast.error).toHaveBeenCalledOnce();
        expect(updateQueryExpr).not.toHaveBeenCalled();
        expect(screen.getByRole('textbox', { name: 'Query' })).toHaveValue('removed_field > 1');
    });
});
