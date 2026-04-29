import { beforeEach, describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import { toast } from 'svelte-sonner';
import QueryEditor from './QueryEditor.svelte';
import type { QueryExprTranslationResult } from './language/query-expr-translation.js';

const translateQuery = vi.fn();

vi.mock('./useQueryEditor', () => ({
    useQueryEditor: () => ({ mount: vi.fn(), translateQuery })
}));

vi.mock('svelte-sonner', () => ({
    toast: {
        error: vi.fn(),
        success: vi.fn()
    }
}));

describe('QueryEditor', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('calls onSave with the latest parsed result when the Save button is clicked', async () => {
        const onSave = vi.fn();
        const parsed = {
            status: 'ok',
            queryExpr: {
                match_expr: {
                    type: 'string_expr',
                    field: { table: 'object_detection', name: 'label' },
                    operator: '==',
                    value: 'cat'
                }
            }
        } as QueryExprTranslationResult;
        translateQuery.mockReturnValueOnce(parsed);

        render(QueryEditor, { props: { value: 'my query', onSave } });

        await fireEvent.click(screen.getByRole('button', { name: 'Save' }));

        expect(translateQuery).toHaveBeenCalledOnce();
        expect(translateQuery).toHaveBeenCalledWith('my query');
        expect(onSave).toHaveBeenCalledOnce();
        expect(onSave).toHaveBeenCalledWith('my query', parsed);
    });

    it('does not render the toolbar when onSave is not provided', () => {
        render(QueryEditor, { props: { value: 'query' } });

        expect(screen.queryByRole('button', { name: 'Save' })).not.toBeInTheDocument();
    });

    it('renders the Save button when onSave is provided', () => {
        render(QueryEditor, { props: { value: 'query', onSave: vi.fn() } });

        expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument();
    });

    it('shows an error toast when translation returns an error result', async () => {
        const onSave = vi.fn();
        const errorResult = {
            status: 'error',
            errors: [{ message: 'unexpected token', line: 1, column: 5 }]
        } as QueryExprTranslationResult;
        translateQuery.mockReturnValueOnce(errorResult);
        render(QueryEditor, { props: { value: 'my query', onSave } });

        await fireEvent.click(screen.getByRole('button', { name: 'Save' }));

        expect(translateQuery).toHaveBeenCalledOnce();
        expect(translateQuery).toHaveBeenCalledWith('my query');
        expect(toast.error).toHaveBeenCalledWith(
            'Failed to translate query: unexpected token (line 1, column 5)'
        );
        expect(onSave).not.toHaveBeenCalled();
    });

    it('disables the Save button when readOnly is true', () => {
        render(QueryEditor, {
            props: { value: 'query', readOnly: true, onSave: vi.fn() }
        });

        expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled();
    });
});
