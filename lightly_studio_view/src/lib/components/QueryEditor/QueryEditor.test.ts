import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import QueryEditor from './QueryEditor.svelte';

vi.mock('./useLightlyQueryEditor.js', () => ({
    useLightlyQueryEditor: () => ({ mount: vi.fn() })
}));

vi.mock('./monaco-lightly-query.js', () => ({
    LIGHTLY_QUERY_DEFAULT_VALUE: '',
    LIGHTLY_QUERY_LANGUAGE_ID: 'lightly-query',
    LIGHTLY_QUERY_THEME_ID: 'lightly-query-theme',
    registerLightlyQueryMonacoLanguage: vi.fn()
}));

describe('QueryEditor', () => {
    it('does not render the toolbar when onSave is not provided', () => {
        render(QueryEditor, { props: { value: 'query' } });

        expect(screen.queryByRole('button', { name: 'Save' })).not.toBeInTheDocument();
    });

    it('renders the Save button when onSave is provided', () => {
        render(QueryEditor, { props: { value: 'query', onSave: vi.fn() } });

        expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument();
    });

    it('calls onSave with the current value when the Save button is clicked', async () => {
        const onSave = vi.fn();
        render(QueryEditor, { props: { value: 'my query', onSave } });

        await fireEvent.click(screen.getByRole('button', { name: 'Save' }));

        expect(onSave).toHaveBeenCalledOnce();
        expect(onSave).toHaveBeenCalledWith('my query');
    });

    it('disables the Save button when readOnly is true', () => {
        render(QueryEditor, {
            props: { value: 'query', readOnly: true, onSave: vi.fn() }
        });

        expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled();
    });
});
