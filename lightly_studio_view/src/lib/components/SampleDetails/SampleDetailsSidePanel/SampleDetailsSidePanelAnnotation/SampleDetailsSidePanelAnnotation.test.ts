import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import { page } from '$app/state';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import SampleDetailsSidePanelAnnotation from './SampleDetailsSidePanelAnnotation.svelte';

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
    useAnnotation: () => ({ annotation: {}, updateAnnotation: vi.fn(), refetch: vi.fn() })
}));
vi.mock('$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation', () => ({
    useUpdateAnnotationsMutation: () => ({ updateAnnotations: vi.fn() })
}));
// The copy control mounts in editing mode; keep its data hooks isolated from the API.
vi.mock('$lib/hooks/useAnnotationCollections/useAnnotationCollections', () => ({
    useAnnotationCollections: () => ({ data: [], isSuccess: true })
}));
vi.mock('$lib/hooks/useCreateAnnotation/useCreateAnnotation', () => ({
    useCreateAnnotation: () => ({ createAnnotation: vi.fn() })
}));
vi.mock('$lib/hooks/useMoveAnnotationsToSource/useMoveAnnotationsToSource', async () => {
    const { readable } = await import('svelte/store');
    return {
        useMoveAnnotationsToSource: () => ({ moveToSource: vi.fn(), isPending: readable(false) })
    };
});
vi.mock('$lib/hooks/useDeleteAnnotation/useDeleteAnnotation', () => ({
    useDeleteAnnotation: () => ({ deleteAnnotation: vi.fn() })
}));
const annotation: AnnotationView = {
    sample_id: 'annotation',
    parent_sample_id: 'image',
    annotation_collection_id: 'predictions',
    annotation_type: 'object_detection',
    annotation_label: { annotation_label_name: 'hole' },
    created_at: new Date()
};
const defaultProps = {
    annotation,
    isSelected: false,
    onClick: vi.fn(),
    onUpdate: vi.fn(),
    onToggleShowAnnotation: vi.fn(),
    onDeleteAnnotation: vi.fn()
};

describe('SampleDetailsSidePanelAnnotation', () => {
    it.each([false, true])('keeps confidence visible with editing=%s', async (editing) => {
        page.data.globalStorage.isEditingMode.set(editing);
        const props = { ...defaultProps, annotation: { ...annotation, confidence: 0.41 } };
        const { rerender } = render(SampleDetailsSidePanelAnnotation, props);
        expect(screen.getByText('Confidence: 0.41')).toBeInTheDocument();
        await rerender({ ...props, isHidden: true });
        expect(screen.getByText('Confidence: 0.41')).toBeInTheDocument();
        await rerender({ ...props, annotation: { ...annotation, confidence: 0 } });
        expect(screen.getByText('Confidence: 0')).toBeInTheDocument();
        await rerender({ ...props, annotation: { ...annotation, confidence: null } });
        expect(screen.queryByText(/Confidence:/)).not.toBeInTheDocument();
    });

    it('offers a drag handle in edit mode that carries the annotation ID', async () => {
        page.data.globalStorage.isEditingMode.set(true);
        const onDragStart = vi.fn();
        render(SampleDetailsSidePanelAnnotation, { ...defaultProps, onDragStart });

        const dataTransfer = { setData: vi.fn(), setDragImage: vi.fn(), effectAllowed: '' };
        await fireEvent.dragStart(screen.getByTestId('annotation-drag-handle'), { dataTransfer });

        expect(dataTransfer.setData).toHaveBeenCalledWith(
            'application/x-lightly-annotation-id',
            annotation.sample_id
        );
        expect(onDragStart).toHaveBeenCalled();
    });

    it('hides the drag handle outside edit mode', () => {
        page.data.globalStorage.isEditingMode.set(false);
        render(SampleDetailsSidePanelAnnotation, { ...defaultProps, onDragStart: vi.fn() });
        expect(screen.queryByTestId('annotation-drag-handle')).not.toBeInTheDocument();
    });
});
