import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import SelectedBoxPanel from './SelectedBoxPanel.svelte';

const mocks = vi.hoisted(() => ({ remove: vi.fn() }));

vi.mock('./useSelectedBoxActions.svelte', async () => {
    const { readable } = await import('svelte/store');
    return {
        useSelectedBoxActions: () => ({
            labels: { data: [{ annotation_label_id: 'l1', annotation_label_name: 'bobcat' }] },
            sources: { data: [{ collection_id: 's1', name: 'predictions' }] },
            isMoving: readable(false),
            changeClass: vi.fn(),
            moveTo: vi.fn(),
            remove: mocks.remove
        })
    };
});

vi.mock('$lib/hooks/useAnnotationCollections/useAnnotationCollections', () => ({
    useAnnotationCollections: () => ({
        data: [{ collection_id: 's1', name: 'predictions' }],
        isSuccess: true
    })
}));

const annotation = {
    sample_id: 'a1',
    annotation_collection_id: 's1',
    annotation_type: 'object_detection',
    annotation_label: { annotation_label_name: 'bobcat' }
} as unknown as AnnotationView;

describe('SelectedBoxPanel', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('shows the class and the source of the box and deletes it', async () => {
        render(SelectedBoxPanel, { collectionId: 'col-1', annotation, refetch: vi.fn() });
        // jsdom has no layout, so the panel never finds the box on screen and stays hidden.
        // Hidden elements have no accessible name, so query them by label.

        expect(screen.getByText('bobcat')).toBeInTheDocument();
        expect(screen.getByLabelText('Move to another annotation source')).toHaveTextContent(
            'predictions'
        );

        await fireEvent.click(screen.getByLabelText('Delete annotation'));

        expect(mocks.remove).toHaveBeenCalledOnce();
    });

    it('deletes the box on Delete', async () => {
        render(SelectedBoxPanel, { collectionId: 'col-1', annotation, refetch: vi.fn() });

        await fireEvent.keyDown(window, { key: 'Delete' });

        expect(mocks.remove).toHaveBeenCalledOnce();
    });
});
