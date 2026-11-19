import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import DeleteAnnotationSourceDialog from './DeleteAnnotationSourceDialog.svelte';

const mocks = vi.hoisted(() => ({
    remove: vi.fn(),
    onClose: vi.fn()
}));

vi.mock('./useDeleteAnnotationSource.svelte', () => ({
    useDeleteAnnotationSource: () => ({
        mutation: { isPending: false },
        remove: mocks.remove
    })
}));

describe('DeleteAnnotationSourceDialog', () => {
    const defaultProps = {
        collectionId: 'col-1',
        source: { id: 's1', name: 'predictions', annotationCount: 12 },
        onClose: mocks.onClose
    };

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('asks for confirmation with the annotation count and deletes on confirm', async () => {
        render(DeleteAnnotationSourceDialog, defaultProps);

        expect(
            screen.getByText(
                /Delete “predictions” and its 12 annotations\? This cannot be undone\. An annotation source that evaluation runs use cannot be deleted\./
            )
        ).toBeInTheDocument();
        expect(mocks.remove).not.toHaveBeenCalled();

        await fireEvent.click(screen.getByRole('button', { name: 'Delete' }));

        expect(mocks.remove).toHaveBeenCalledOnce();
    });

    it('names a single annotation in the singular', () => {
        render(DeleteAnnotationSourceDialog, {
            ...defaultProps,
            source: { ...defaultProps.source, annotationCount: 1 }
        });

        expect(screen.getByText(/and its 1 annotation\?/)).toBeInTheDocument();
    });

    it('closes on cancel without deleting', async () => {
        render(DeleteAnnotationSourceDialog, defaultProps);

        await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

        expect(mocks.onClose).toHaveBeenCalled();
        expect(mocks.remove).not.toHaveBeenCalled();
    });
});
