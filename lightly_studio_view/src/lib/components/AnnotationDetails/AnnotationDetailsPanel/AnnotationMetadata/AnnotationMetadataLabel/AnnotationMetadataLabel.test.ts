import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';
import AnnotationMetadataLabel from './AnnotationMetadataLabel.svelte';

const mocks = vi.hoisted(() => ({
    refetch: vi.fn(),
    addAnnotationLabelChangeToUndoStack: vi.fn()
}));

vi.mock('$app/state', async () => {
    const { writable } = await import('svelte/store');
    return {
        page: {
            params: { collection_id: 'images' },
            data: { globalStorage: { isEditingMode: writable(true) } }
        }
    };
});
vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () => ({ data: [] })
}));
vi.mock('$lib/hooks/useAnnotation/useAnnotation', () => ({
    useAnnotation: () => ({ updateAnnotation: vi.fn(), refetch: mocks.refetch })
}));
vi.mock('$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation', () => ({
    useUpdateAnnotationsMutation: () => ({ updateAnnotations: vi.fn() })
}));
vi.mock('$lib/services/addAnnotationLabelChangeToUndoStack', () => ({
    addAnnotationLabelChangeToUndoStack: mocks.addAnnotationLabelChangeToUndoStack
}));
vi.mock('$lib/components/SelectList/SelectList.svelte', async () => ({
    default: (
        await import('$lib/components/SampleDetails/SampleDetailsSidePanel/SampleDetailsSidePanelAnnotation/SelectListStub.test.svelte')
    ).default
}));

describe('AnnotationMetadataLabel', () => {
    it('refreshes the annotation details when a class change is undone', async () => {
        const onUpdate = vi.fn();
        render(AnnotationMetadataLabel, {
            label: 'Class',
            value: 'hole',
            isEditingMode: writable(true),
            collectionId: 'images',
            annotationId: 'annotation',
            onUpdate
        });

        await fireEvent.click(screen.getByTestId('pick-class'));
        const { refresh } = mocks.addAnnotationLabelChangeToUndoStack.mock.calls[0][0];
        refresh();

        expect(mocks.refetch).toHaveBeenCalledTimes(1);
        expect(onUpdate).toHaveBeenCalledTimes(1);
    });
});
