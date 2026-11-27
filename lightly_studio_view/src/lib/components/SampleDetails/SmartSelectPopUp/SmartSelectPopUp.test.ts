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
    isPending: false,
    needsPositivePoint: false,
    onSave: vi.fn(),
    onClear: vi.fn()
};

describe('SmartSelectPopUp', () => {
    it('shows how to place prompts', () => {
        render(SmartSelectPopUp, { props: defaultProps });
        expect(
            screen.getByText('Click to add, shift-click to remove. Or drag a box.')
        ).toBeInTheDocument();
    });

    it('shows that the preview is loading', () => {
        render(SmartSelectPopUp, { props: { ...defaultProps, isPending: true } });
        expect(screen.getByText('Loading the preview...')).toBeInTheDocument();
    });

    it('asks for a positive point', () => {
        render(SmartSelectPopUp, { props: { ...defaultProps, needsPositivePoint: true } });
        expect(screen.getByText('Click the object to add a point first.')).toBeInTheDocument();
    });
});
