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
        options: {
            value: string;
            rootScope?: string;
            readOnly?: boolean;
            onChange?: (next: string) => void;
        }
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
        expect(translateQuery).toHaveBeenCalledWith('my modified query', 'image');
        expect(onSave).toHaveBeenCalledOnce();
        expect(onSave).toHaveBeenCalledWith('my modified query', parsed);
    });

    it('does not render the toolbar when onSave is not provided', () => {
        render(QueryEditor, { props: { value: 'query' } });

        expect(screen.queryByRole('button', { name: 'Apply' })).not.toBeInTheDocument();
    });

    it('renders the Apply button when onSave is provided', () => {
        render(QueryEditor, { props: { value: 'query', onSave: vi.fn() } });

        expect(screen.getByRole('button', { name: 'Apply' })).toBeInTheDocument();
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
        expect(translateQuery).toHaveBeenCalledWith('my modified query', 'image');
        expect(toast.error).toHaveBeenCalledWith(
            'Failed to translate query: unexpected token (line 1, column 5)'
        );
        expect(onSave).not.toHaveBeenCalled();
    });

    it('enables Apply on first open, disables after applying, and stays disabled when reopened', async () => {
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
        translateQuery.mockReturnValue(parsed);

        // 1. First open — no value prop, shows default example, Apply is enabled
        const { unmount: unmount } = render(QueryEditor, {
            props: { onSave }
        });
        expect(screen.getByRole('button', { name: 'Apply' })).toBeEnabled();

        // 2. User edits the query
        await simulateUserEdit('width < 1000');
        expect(screen.getByRole('button', { name: 'Apply' })).toBeEnabled();

        // 3. User clicks Apply — Apply becomes disabled
        await fireEvent.click(screen.getByRole('button', { name: 'Apply' }));
        expect(onSave).toHaveBeenCalledWith('width < 1000', parsed);
        expect(screen.getByRole('button', { name: 'Apply' })).toBeDisabled();

        // 4. Simulate "reopen": unmount and re-render with the applied value
        unmount();
        render(QueryEditor, {
            props: { value: 'width < 1000', onSave }
        });
        expect(screen.getByRole('button', { name: 'Apply' })).toBeDisabled();
    });

    it('mounts and translates video queries with the video root scope', async () => {
        const onSave = vi.fn();
        translateQuery.mockReturnValueOnce({ status: 'error', errors: [] });
        render(QueryEditor, { props: { rootScope: 'video', onSave } });

        expect(mount).toHaveBeenCalledWith(
            expect.anything(),
            expect.objectContaining({
                rootScope: 'video',
                value: expect.stringContaining('duration_s > 10')
            })
        );

        await fireEvent.click(screen.getByRole('button', { name: 'Apply' }));
        expect(translateQuery).toHaveBeenCalledWith(expect.any(String), 'video');
    });

    it('remounts with the new scope and translates with it when rootScope changes', async () => {
        const onSave = vi.fn();
        translateQuery.mockReturnValue({ status: 'error', errors: [] });

        const { rerender } = render(QueryEditor, { props: { rootScope: 'image', onSave } });
        expect(mount).toHaveBeenCalledOnce();
        expect(mount).toHaveBeenLastCalledWith(
            expect.anything(),
            expect.objectContaining({ rootScope: 'image' })
        );

        // A collection switch changes the prop while the panel stays alive.
        await rerender({ rootScope: 'video', onSave });

        // The editor remounts so the model scope tracks the prop, and the video
        // default example loads.
        expect(mount).toHaveBeenCalledTimes(2);
        expect(mount).toHaveBeenLastCalledWith(
            expect.anything(),
            expect.objectContaining({
                rootScope: 'video',
                value: expect.stringContaining('duration_s > 10')
            })
        );

        await fireEvent.click(screen.getByRole('button', { name: 'Apply' }));
        expect(translateQuery).toHaveBeenLastCalledWith(expect.any(String), 'video');
    });

    it('disables the Apply button when readOnly is true even after modification', async () => {
        render(QueryEditor, {
            props: { value: 'query', readOnly: true, onSave: vi.fn() }
        });

        await simulateUserEdit('query changed');

        expect(screen.getByRole('button', { name: 'Apply' })).toBeDisabled();
    });
});
