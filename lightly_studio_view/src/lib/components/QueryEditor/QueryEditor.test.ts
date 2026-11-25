import { beforeEach, describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import { createRawSnippet } from 'svelte';
import { toast } from 'svelte-sonner';
import QueryEditor from './QueryEditor.svelte';
import type { useQueryEditor } from './useQueryEditor';

const mount: ReturnType<typeof useQueryEditor>['mount'] = (el, options) => {
    const input = document.createElement('textarea');
    input.setAttribute('aria-label', 'Query');
    input.value = options.value;
    input.readOnly = options.readOnly ?? false;
    input.oninput = () => options.onChange?.(input.value);
    el.append(input);
    return () => input.remove();
};

// Replace Monaco rendering while keeping the real language hook, parser, and translation.
vi.mock('monaco-editor', () => ({}));
vi.mock('./useQueryEditor', async () => {
    const { useLightlyQueryLanguage } =
        await import('./useLightlyQueryLanguage/useLightlyQueryLanguage');
    return {
        useQueryEditor: () => ({
            mount,
            translateQuery: useLightlyQueryLanguage().translateQuery,
            setTagNames: vi.fn()
        })
    };
});

vi.mock('svelte-sonner', () => ({
    toast: {
        error: vi.fn(),
        success: vi.fn()
    }
}));

async function simulateUserEdit(next: string) {
    await fireEvent.input(screen.getByRole('textbox', { name: 'Query' }), {
        target: { value: next }
    });
}

describe('QueryEditor', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it.each(['image', 'video'] as const)(
        'saves an empty result when all %s query conditions are commented out',
        async (sampleType) => {
            const onSave = vi.fn();
            render(QueryEditor, { props: { value: 'width < 500', sampleType, onSave } });
            const query = '# width < 500\n# AND file_name = "sample#1"';
            await simulateUserEdit(query);
            await fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

            expect(onSave).toHaveBeenCalledExactlyOnceWith(query, { status: 'empty' });
            expect(toast.error).not.toHaveBeenCalled();
        }
    );

    it('starts with an implicit video query, rejects invalid fields, and saves a video query', async () => {
        const onSave = vi.fn();
        render(QueryEditor, { props: { sampleType: 'video', onSave } });
        expect(screen.getByRole('textbox', { name: 'Query' })).toHaveValue('duration_s > 10');

        await simulateUserEdit('created_at = "2025-01-01"');
        await fireEvent.click(screen.getByRole('button', { name: 'Apply' }));
        expect(toast.error).toHaveBeenCalledWith(
            expect.stringContaining('Failed to translate query:')
        );
        expect(onSave).not.toHaveBeenCalled();

        await simulateUserEdit('duration_s > 5');
        await fireEvent.click(screen.getByRole('button', { name: 'Apply' }));
        expect(onSave).toHaveBeenCalledExactlyOnceWith('duration_s > 5', {
            status: 'ok',
            queryExpr: {
                match_expr: {
                    type: 'ordinal_float_expr',
                    field: { table: 'video', name: 'duration_s' },
                    operator: '>',
                    value: 5
                }
            }
        });
    });

    it('keeps the image example and hides the toolbar when onSave is not provided', () => {
        render(QueryEditor);

        expect(screen.getByRole('textbox', { name: 'Query' })).toHaveValue(
            '# Example query\nwidth < 500\nAND "reviewed" IN tags\n' +
                'AND object_detection(class_name = "person" AND x > 10)\n'
        );
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

    it('loads and re-applies the supplied query instead of the default', async () => {
        const onSave = vi.fn();
        render(QueryEditor, { props: { value: 'width < 500', sampleType: 'image', onSave } });
        expect(screen.getByRole('textbox', { name: 'Query' })).toHaveValue('width < 500');

        await fireEvent.click(screen.getByRole('button', { name: 'Re-apply' }));

        expect(onSave).toHaveBeenCalledExactlyOnceWith('width < 500', {
            status: 'ok',
            queryExpr: {
                match_expr: {
                    type: 'integer_expr',
                    field: { table: 'image', name: 'width' },
                    operator: '<',
                    value: 500
                }
            }
        });
    });

    it('shows an error toast without saving an invalid query', async () => {
        const onSave = vi.fn();
        render(QueryEditor, { props: { value: 'width < 500', onSave } });
        await simulateUserEdit('width <');

        await fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

        expect(toast.error).toHaveBeenCalledWith(
            expect.stringContaining('Failed to translate query:')
        );
        expect(onSave).not.toHaveBeenCalled();
    });

    it('follows the applied value from the parent', async () => {
        const onSave = vi.fn();
        const { rerender } = render(QueryEditor, { props: { onSave } });
        expect(screen.getByRole('button', { name: 'Apply' })).toBeEnabled();

        await simulateUserEdit('width < 1000');
        await rerender({ value: 'width < 1000', onSave });
        expect(screen.getByRole('button', { name: 'Re-apply' })).toBeEnabled();

        await rerender({ value: undefined, onSave });
        expect(screen.getByRole('button', { name: 'Apply' })).toBeEnabled();
    });

    it('renders the footer actions before the apply button', () => {
        const footerActions = createRawSnippet(() => ({
            render: () => '<button type="button">History</button>'
        }));
        render(QueryEditor, { props: { onSave: vi.fn(), footerActions } });

        const buttonNames = screen
            .getAllByRole('button')
            .map((button) => button.textContent?.trim());
        expect(buttonNames).toEqual(['History', 'Apply']);
    });

    it('shows the draft in place of the applied value and labels the button Apply', () => {
        render(QueryEditor, { props: { value: 'width < 500', draft: 'width <', onSave: vi.fn() } });

        expect(screen.getByRole('textbox', { name: 'Query' })).toHaveValue('width <');
        expect(screen.getByRole('button', { name: 'Apply' })).toBeEnabled();
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
