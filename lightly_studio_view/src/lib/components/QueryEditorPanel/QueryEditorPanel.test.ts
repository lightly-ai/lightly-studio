import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import QueryEditorPanel from './QueryEditorPanel.svelte';

const {
    updateQueryExpr,
    invalidateQueries,
    imageQueryExpression,
    queryExpr,
    setTagNames,
    useTags,
    isLoading
} = await vi.hoisted(async () => {
    const { writable } = await import('svelte/store');
    const isLoading = writable(false);
    return {
        updateQueryExpr: vi.fn(),
        invalidateQueries: vi.fn(),
        imageQueryExpression: writable({ query_expr_str: 'width < 500' }),
        queryExpr: { match_expr: { type: 'string_expr' } },
        setTagNames: vi.fn(),
        useTags: vi.fn(() => ({
            tags: writable([{ name: 'train' }, { name: 'val' }]),
            isLoading,
            error: writable(null)
        })),
        isLoading
    };
});

vi.mock('$lib/components/QueryEditor/useQueryEditor', () => ({
    useQueryEditor: () => ({
        mount: () => () => {},
        translateQuery: () => ({ status: 'ok', queryExpr }),
        setTagNames
    })
}));
vi.mock('$lib/hooks/useTags/useTags', () => ({ useTags }));
vi.mock('$lib/hooks/useImageFilters/useImageFilters', () => ({
    useImageFilters: () => ({ imageQueryExpression, updateQueryExpr })
}));
vi.mock('@tanstack/svelte-query', () => ({
    useQueryClient: () => ({ invalidateQueries })
}));

const defaultProps = { onClose: vi.fn(), collectionId: 'collection-1' };

describe('QueryEditorPanel', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        isLoading.set(false);
    });

    it('gives the editor the tag names of the collection', () => {
        render(QueryEditorPanel, { props: defaultProps });

        expect(useTags).toHaveBeenCalledWith({ collection_id: 'collection-1' });
        expect(setTagNames).toHaveBeenLastCalledWith(['train', 'val']);
    });

    it('gives the editor no tag names while the tags load', () => {
        isLoading.set(true);

        render(QueryEditorPanel, { props: defaultProps });

        expect(setTagNames).toHaveBeenLastCalledWith(undefined);
    });

    it('updates the query and invalidates all queries when re-applying the same query', async () => {
        render(QueryEditorPanel, { props: defaultProps });

        expect(screen.getByText('metadata["quality_score"] >= 0.8')).toBeInTheDocument();

        await fireEvent.click(screen.getByRole('button', { name: 'Re-apply' }));

        expect(updateQueryExpr).toHaveBeenCalledWith({
            query_expr: queryExpr,
            query_expr_str: 'width < 500'
        });
        await waitFor(() => expect(invalidateQueries).toHaveBeenCalledExactlyOnceWith());
    });
});
