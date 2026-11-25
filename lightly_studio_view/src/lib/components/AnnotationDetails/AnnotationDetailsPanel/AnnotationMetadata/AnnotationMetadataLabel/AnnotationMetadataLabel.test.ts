import { fireEvent, render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import AnnotationMetadataLabel from './AnnotationMetadataLabel.svelte';

const mocks = vi.hoisted(() => ({
    updateAnnotation: vi.fn()
}));

vi.mock('$lib/hooks/useAnnotation/useAnnotation', () => ({
    useAnnotation: () => ({ updateAnnotation: mocks.updateAnnotation, refetch: vi.fn() })
}));

vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () => ({
        data: [{ annotation_label_name: 'car' }, { annotation_label_name: 'pedestrian' }]
    })
}));

vi.mock('$lib/hooks/useAuth/useAuth', () => ({
    default: () => ({ user: { role: 'editor' } })
}));

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({ addReversibleAction: vi.fn() })
}));

vi.mock('$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation', () => ({
    useUpdateAnnotationsMutation: () => ({ updateAnnotations: vi.fn() })
}));

const defaultProps = {
    label: 'Class',
    value: 'car',
    isEditingMode: readable(false),
    collectionId: 'collection-1',
    annotationId: 'annotation-1'
};

describe('AnnotationMetadataLabel', () => {
    it('shows the annotation class and the track id when not in editing mode', () => {
        render(AnnotationMetadataLabel, { props: { ...defaultProps, trackId: 7 } });

        expect(screen.getByText('Class')).toBeInTheDocument();
        expect(screen.getByTestId('annotation-metadata-label')).toHaveTextContent('car #7');
    });

    it('updates the annotation class when a class is selected in editing mode', () => {
        render(AnnotationMetadataLabel, {
            props: { ...defaultProps, isEditingMode: readable(true) }
        });

        fireEvent.click(screen.getByRole('combobox'));
        fireEvent.click(screen.getByRole('option', { name: /pedestrian/i }));

        expect(mocks.updateAnnotation).toHaveBeenCalledWith({
            annotation_id: 'annotation-1',
            collection_id: 'collection-1',
            label_name: 'pedestrian'
        });
    });
});
