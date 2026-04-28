import { beforeEach, describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import QueryEditor from './QueryEditor.svelte';
import type { QueryExprTranslationResult } from './language/query-expr-translation.js';

const translateLightlyQuery = vi.fn();

vi.mock('./useLightlyQueryEditor.js', () => ({
    useLightlyQueryEditor: () => ({ mount: vi.fn(), translateLightlyQuery })
}));

vi.mock('./monaco-lightly-query.js', () => ({
    LIGHTLY_QUERY_DEFAULT_VALUE: '',
    LIGHTLY_QUERY_LANGUAGE_ID: 'lightly-query',
    LIGHTLY_QUERY_THEME_ID: 'lightly-query-theme',
    registerLightlyQueryMonacoLanguage: vi.fn()
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
        translateLightlyQuery.mockResolvedValueOnce(parsed);

        render(QueryEditor, { props: { value: 'my query', onSave } });

        await fireEvent.click(screen.getByRole('button', { name: 'Save' }));

        expect(translateLightlyQuery).toHaveBeenCalledOnce();
        expect(translateLightlyQuery).toHaveBeenCalledWith('my query');
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

    it('calls onSave with null when no parsed result is available', async () => {
        const onSave = vi.fn();
        translateLightlyQuery.mockResolvedValueOnce(null);
        render(QueryEditor, { props: { value: 'my query', onSave } });

        await fireEvent.click(screen.getByRole('button', { name: 'Save' }));

        expect(translateLightlyQuery).toHaveBeenCalledOnce();
        expect(translateLightlyQuery).toHaveBeenCalledWith('my query');
        expect(onSave).toHaveBeenCalledOnce();
        expect(onSave).toHaveBeenCalledWith('my query', null);
    });

    it('disables the Save button when readOnly is true', () => {
        render(QueryEditor, {
            props: { value: 'query', readOnly: true, onSave: vi.fn() }
        });

        expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled();
    });
});
