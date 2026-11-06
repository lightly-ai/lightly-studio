import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import SmartSelectPopUp from './SmartSelectPopUp.svelte';

vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () => ({ data: [], isLoading: false })
}));

const defaultProps = {
    collectionId: 'collection-1',
    saveAs: 'mask' as const,
    onSaveAsChange: vi.fn(),
    annotationClass: null,
    onAnnotationClassChange: vi.fn(),
    canSave: false,
    onSave: vi.fn(),
    onClear: vi.fn()
};

describe('SmartSelectPopUp', () => {
    it('shows how to place prompts', () => {
        render(SmartSelectPopUp, { props: defaultProps });
        expect(
            screen.getByText(
                'Click to select. Shift-click to exclude. Drawing a box starts a new selection.'
            )
        ).toBeInTheDocument();
    });

    it('keeps the class selector labelled after a class is selected', () => {
        render(SmartSelectPopUp, { props: { ...defaultProps, annotationClass: 'person' } });
        expect(
            screen.getByRole('combobox', { name: 'Annotation class person' })
        ).toBeInTheDocument();
    });
});
