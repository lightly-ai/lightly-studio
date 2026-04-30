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
                    field: { table: 'object_detection', name: 'label' },
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
        expect(translateQuery).toHaveBeenCalledWith('my query');
        expect(onSave).toHaveBeenCalledOnce();
        expect(onSave).toHaveBeenCalledWith('my query', parsed);
    });

    it('does not render the toolbar when onSave is not provided', () => {
        render(QueryEditor, { props: { value: 'query' } });

        expect(screen.queryByRole('button', { name: 'Apply' })).not.toBeInTheDocument();
    });

    it('renders the Apply button when onSave is provided', () => {
        render(QueryEditor, { props: { value: 'query', onSave: vi.fn() } });

        expect(screen.getByRole('button', { name: 'Apply' })).toBeInTheDocument();
    });

    it('disables the Apply button when the editor value has not been modified', () => {
        render(QueryEditor, { props: { value: 'query', onSave: vi.fn() } });

        expect(screen.getByRole('button', { name: 'Apply' })).toBeDisabled();
    });

    it('enables the Apply button after the editor value is modified', async () => {
        render(QueryEditor, { props: { value: 'query', onSave: vi.fn() } });

        await simulateUserEdit('query changed');

        expect(screen.getByRole('button', { name: 'Apply' })).toBeEnabled();
    });

    it('disables the Apply button again when the editor value matches the original', async () => {
        render(QueryEditor, { props: { value: 'query', onSave: vi.fn() } });

        await simulateUserEdit('query changed');
        expect(screen.getByRole('button', { name: 'Apply' })).toBeEnabled();

        await simulateUserEdit('query');
        expect(screen.getByRole('button', { name: 'Apply' })).toBeDisabled();
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
        expect(translateQuery).toHaveBeenCalledWith('my query');
        expect(toast.error).toHaveBeenCalledWith(
            'Failed to translate query: unexpected token (line 1, column 5)'
        );
        expect(onSave).not.toHaveBeenCalled();
    });

    it('disables the Apply button when readOnly is true even after modification', async () => {
        render(QueryEditor, {
            props: { value: 'query', readOnly: true, onSave: vi.fn() }
        });

        await simulateUserEdit('query changed');

        expect(screen.getByRole('button', { name: 'Apply' })).toBeDisabled();
    });
});
