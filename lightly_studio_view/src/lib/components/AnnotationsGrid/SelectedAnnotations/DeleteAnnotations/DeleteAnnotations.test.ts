import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { toast } from 'svelte-sonner';
import DeleteAnnotations from './DeleteAnnotations.svelte';

const mocks = await vi.hoisted(async () => {
    const { writable } = await import('svelte/store');
    return {
        deleteAnnotations: vi.fn(),
        clearSelectedSampleAnnotationCrops: vi.fn(),
        hasMinimumRole: vi.fn(),
        isEditingMode: writable(true),
        snapshot: { filter: { filter_type: 'annotations' as const }, size: 2 }
    };
});

vi.mock('$app/state', () => ({ page: { params: { dataset_id: 'root-1' } } }));

vi.mock('$lib/hooks', () => ({
    useBulkDeleteAnnotations: () => ({
        deleteAnnotations: mocks.deleteAnnotations,
        isPending: readable(false)
    })
}));

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        isEditingMode: mocks.isEditingMode,
        selectedSampleAnnotationCropIds: readable({ 'col-1': new Set(['a', 'b']) }),
        getSelectAllAnnotationSnapshot: () => readable(mocks.snapshot),
        clearSelectedSampleAnnotationCrops: mocks.clearSelectedSampleAnnotationCrops
    })
}));

vi.mock('$lib/hooks/useAuth/useAuth', () => ({
    default: () => ({ user: { role: 'labeler' } })
}));

vi.mock('$lib/hooks/useAuth/hasMinimumRole', () => ({ hasMinimumRole: mocks.hasMinimumRole }));

vi.mock('svelte-sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const confirmDelete = async () => {
    await fireEvent.click(screen.getByRole('button', { name: 'Delete 2 annotations' }));
    await fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
};

describe('DeleteAnnotations', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.isEditingMode.set(true);
        mocks.hasMinimumRole.mockReturnValue(true);
        mocks.deleteAnnotations.mockResolvedValue({ data: { deleted_count: 2 } });
    });

    it('shows the button to labelers in editing mode', () => {
        render(DeleteAnnotations, { props: { collectionId: 'col-1' } });

        expect(screen.getByRole('button', { name: 'Delete 2 annotations' })).toBeInTheDocument();
        expect(mocks.hasMinimumRole).toHaveBeenCalledWith('labeler', 'labeler');
    });

    it('hides the button below the labeler role', () => {
        mocks.hasMinimumRole.mockReturnValue(false);
        render(DeleteAnnotations, { props: { collectionId: 'col-1' } });

        expect(screen.queryByRole('button', { name: /Delete/ })).toBeNull();
    });

    it('hides the button outside editing mode', () => {
        mocks.isEditingMode.set(false);
        render(DeleteAnnotations, { props: { collectionId: 'col-1' } });

        expect(screen.queryByRole('button', { name: /Delete/ })).toBeNull();
    });

    it('deletes the selection, clears it and reports the deleted count', async () => {
        mocks.deleteAnnotations.mockResolvedValue({ data: { deleted_count: 1 } });
        render(DeleteAnnotations, { props: { collectionId: 'col-1' } });

        await confirmDelete();

        expect(mocks.deleteAnnotations).toHaveBeenCalledWith({
            collectionId: 'col-1',
            rootCollectionId: 'root-1',
            selectedIds: new Set(['a', 'b']),
            selectAllSnapshot: mocks.snapshot
        });
        await waitFor(() => expect(toast.success).toHaveBeenCalledWith('Deleted 1 annotation'));
        expect(mocks.clearSelectedSampleAnnotationCrops).toHaveBeenCalledWith('col-1');
    });

    it('keeps the selection and shows an error when deleting fails', async () => {
        mocks.deleteAnnotations.mockResolvedValue({ error: { detail: 'Boom' } });
        render(DeleteAnnotations, { props: { collectionId: 'col-1' } });

        await confirmDelete();

        await waitFor(() =>
            expect(toast.error).toHaveBeenCalledWith(
                'Failed to delete annotations. Please try again.'
            )
        );
        expect(mocks.clearSelectedSampleAnnotationCrops).not.toHaveBeenCalled();
    });
});
