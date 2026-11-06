import { render, screen, fireEvent } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { describe, it, expect, vi } from 'vitest';
import AnnotationToolPopUp from './AnnotationToolPopUp.svelte';

vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () => ({ data: [], isLoading: false })
}));

const children = createRawSnippet(() => ({ render: () => '<div>Tool controls</div>' }));

const defaultProps = {
    title: 'Smart select',
    collectionId: 'collection-1',
    annotationClass: null,
    onAnnotationClassChange: vi.fn(),
    saveAs: 'mask' as const,
    onSaveAsChange: vi.fn(),
    canSave: true,
    onSave: vi.fn(),
    onClear: vi.fn(),
    children
};

describe('AnnotationToolPopUp', () => {
    it('disables Save when canSave is false', () => {
        render(AnnotationToolPopUp, { props: { ...defaultProps, canSave: false } });
        expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled();
    });

    it('reports the chosen save as option', async () => {
        const onSaveAsChange = vi.fn();
        render(AnnotationToolPopUp, { props: { ...defaultProps, onSaveAsChange } });
        await fireEvent.click(screen.getByRole('button', { name: 'Save as Box' }));
        expect(onSaveAsChange).toHaveBeenCalledWith('box');
    });

    it('hides the save controls when showSaveControls is false', () => {
        render(AnnotationToolPopUp, { props: { ...defaultProps, showSaveControls: false } });
        expect(screen.getByText('Tool controls')).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Save' })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Clear' })).not.toBeInTheDocument();
    });

    it('hides the save as toggle when showSaveAs is false', () => {
        render(AnnotationToolPopUp, { props: { ...defaultProps, showSaveAs: false } });
        expect(screen.queryByRole('group', { name: 'Save as' })).not.toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument();
    });

    it('shows the save label', () => {
        render(AnnotationToolPopUp, { props: { ...defaultProps, saveLabel: 'Save 3' } });
        expect(screen.getByRole('button', { name: 'Save 3' })).toBeInTheDocument();
    });

    it('calls onSave and onClear', async () => {
        const onSave = vi.fn();
        const onClear = vi.fn();
        render(AnnotationToolPopUp, { props: { ...defaultProps, onSave, onClear } });
        await fireEvent.click(screen.getByRole('button', { name: 'Save' }));
        await fireEvent.click(screen.getByRole('button', { name: 'Clear' }));
        expect(onSave).toHaveBeenCalledOnce();
        expect(onClear).toHaveBeenCalledOnce();
    });
});
