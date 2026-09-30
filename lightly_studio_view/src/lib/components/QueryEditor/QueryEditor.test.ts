import { beforeEach, describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { tick } from 'svelte';
import '@testing-library/jest-dom';
import { toast } from 'svelte-sonner';
import QueryEditor from './QueryEditor.svelte';
import type { QueryExprTranslationResult } from './language/query-expr-translation.js';

const translateQuery = vi.fn();
let capturedOnChange: ((next: string) => void) | undefined;
const mount = vi.fn(
    (
        _el: HTMLElement,
        options: { value: string; readOnly?: boolean; onChange?: (next: string) => void }
    ) => {
        capturedOnChange = options.onChange;
        return () => {};
    }
);

vi.mock('./useQueryEditor', () => ({
    useQueryEditor: () => ({ mount, translateQuery })
}));

vi.mock('svelte-sonner', () => ({
    toast: {
        error: vi.fn(),
        success: vi.fn()
    }
}));

async function simulateUserEdit(next: string) {
    capturedOnChange?.(next);
    await tick();
}

describe('QueryEditor', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        capturedOnChange = undefined;
    });

    it('calls onSave with the latest parsed result when the Apply button is clicked', async () => {
        const onSave = vi.fn();
        const parsed = {
            status: 'ok',
            queryExpr: {
                match_expr: {
                    type: 'string_expr',
                    field: { table: 'object_detection', name: 'class_name' },
                    operator: '==',
                    value: 'cat'
                }
            }
        } as QueryExprTranslationResult;
        translateQuery.mockReturnValueOnce(parsed);

        render(QueryEditor, { props: { value: 'my query', onSave } });
        await simulateUserEdit('my modified query');

        await fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

        expect(translateQuery).toHaveBeenCalledOnce();
        expect(translateQuery).toHaveBeenCalledWith('my modified query');
        expect(onSave).toHaveBeenCalledOnce();
        expect(onSave).toHaveBeenCalledWith('my modified query', parsed);
    });

    it('does not render the toolbar when onSave is not provided', () => {
        render(QueryEditor, { props: { value: 'query' } });

        expect(screen.queryByTestId('query-editor-apply-button')).not.toBeInTheDocument();
    });

    it('labels the button Re-apply while the text matches the applied value', async () => {
        render(QueryEditor, { props: { value: 'query', onSave: vi.fn() } });
        expect(screen.getByRole('button', { name: 'Re-apply' })).toBeEnabled();

        await simulateUserEdit('query changed');
        expect(screen.getByRole('button', { name: 'Apply' })).toBeEnabled();

        await simulateUserEdit('query');
        expect(screen.getByRole('button', { name: 'Re-apply' })).toBeEnabled();
    });

    it('calls onSave when re-applying unchanged text', async () => {
        const onSave = vi.fn();
        const parsed = { status: 'ok', queryExpr: {} } as QueryExprTranslationResult;
        translateQuery.mockReturnValueOnce(parsed);
        render(QueryEditor, { props: { value: 'query', onSave } });

        await fireEvent.click(screen.getByRole('button', { name: 'Re-apply' }));

        expect(onSave).toHaveBeenCalledExactlyOnceWith('query', parsed);
    });

    it('shows an error toast when translation returns an error result', async () => {
        const onSave = vi.fn();
        const errorResult = {
            status: 'error',
            errors: [{ message: 'unexpected token', line: 1, column: 5 }]
        } as QueryExprTranslationResult;
        translateQuery.mockReturnValueOnce(errorResult);
        render(QueryEditor, { props: { value: 'my query', onSave } });
        await simulateUserEdit('my modified query');

        await fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

        expect(translateQuery).toHaveBeenCalledOnce();
        expect(translateQuery).toHaveBeenCalledWith('my modified query');
        expect(toast.error).toHaveBeenCalledWith(
            'Failed to translate query: unexpected token (line 1, column 5)'
        );
        expect(onSave).not.toHaveBeenCalled();
    });

    it('shows Apply on first open and Re-apply after applying and when reopened', async () => {
        const onSave = vi.fn();
        const parsed = { status: 'ok', queryExpr: {} } as QueryExprTranslationResult;
        translateQuery.mockReturnValue(parsed);

        const { unmount } = render(QueryEditor, { props: { onSave } });
        expect(screen.getByRole('button', { name: 'Apply' })).toBeEnabled();

        await simulateUserEdit('width < 1000');
        await fireEvent.click(screen.getByRole('button', { name: 'Apply' }));
        expect(onSave).toHaveBeenCalledWith('width < 1000', parsed);
        expect(screen.getByRole('button', { name: 'Re-apply' })).toBeEnabled();

        unmount();
        render(QueryEditor, { props: { value: 'width < 1000', onSave } });
        expect(screen.getByRole('button', { name: 'Re-apply' })).toBeEnabled();
    });

    it('disables the button when readOnly is true', async () => {
        render(QueryEditor, {
            props: { value: 'query', readOnly: true, onSave: vi.fn() }
        });
        expect(screen.getByRole('button', { name: 'Re-apply' })).toBeDisabled();

        await simulateUserEdit('query changed');
        expect(screen.getByRole('button', { name: 'Apply' })).toBeDisabled();
    });
});
