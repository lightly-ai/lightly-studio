import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import DeleteAnnotationSource from './DeleteAnnotationSource.svelte';

const mocks = vi.hoisted(() => ({
    remove: vi.fn(),
    onClose: vi.fn(),
    count: undefined as number | undefined
}));

vi.mock('./useDeleteAnnotationSource.svelte', () => ({
    useDeleteAnnotationSource: () => ({
        mutation: { isPending: false },
        remove: mocks.remove,
        annotationCount: () => mocks.count
    })
}));

describe('DeleteAnnotationSource', () => {
    const defaultProps = {
        collectionId: 'col-1',
        source: { id: 's1', name: 'predictions' },
        onClose: mocks.onClose
    };

    beforeEach(() => {
        vi.clearAllMocks();
        mocks.count = undefined;
    });

    it('asks for confirmation with the annotation count and deletes on confirm', async () => {
        mocks.count = 12;
        render(DeleteAnnotationSource, defaultProps);

        expect(
            screen.getByText(/Delete “predictions” and its 12 annotations\? Evaluation runs/)
        ).toBeInTheDocument();
        expect(mocks.remove).not.toHaveBeenCalled();

        await fireEvent.click(screen.getByRole('button', { name: 'Delete' }));

        expect(mocks.remove).toHaveBeenCalledOnce();
    });

    it('names a single annotation in the singular', async () => {
        mocks.count = 1;
        render(DeleteAnnotationSource, defaultProps);

        expect(screen.getByText(/and its 1 annotation\?/)).toBeInTheDocument();
    });

    it('closes on cancel without deleting', async () => {
        render(DeleteAnnotationSource, defaultProps);

        await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

        expect(mocks.onClose).toHaveBeenCalled();
        expect(mocks.remove).not.toHaveBeenCalled();
    });
});
