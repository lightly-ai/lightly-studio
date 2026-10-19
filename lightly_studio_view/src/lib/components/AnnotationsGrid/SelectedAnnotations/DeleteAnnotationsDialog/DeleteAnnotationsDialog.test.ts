import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import DeleteAnnotationsDialog from './DeleteAnnotationsDialog.svelte';

const defaultProps = { selectedCount: 3, isDeleting: false, onDelete: vi.fn() };

describe('DeleteAnnotationsDialog', () => {
    it('deletes only after confirming', async () => {
        const onDelete = vi.fn();
        render(DeleteAnnotationsDialog, { props: { ...defaultProps, onDelete } });

        await fireEvent.click(screen.getByRole('button', { name: 'Delete 3 annotations' }));

        expect(onDelete).not.toHaveBeenCalled();
        expect(screen.getByRole('heading', { name: 'Delete 3 annotations?' })).toBeInTheDocument();
        expect(screen.getByText('This cannot be undone.')).toBeInTheDocument();

        await fireEvent.click(screen.getByRole('button', { name: 'Delete' }));

        expect(onDelete).toHaveBeenCalledOnce();
        expect(screen.queryByRole('heading', { name: 'Delete 3 annotations?' })).toBeNull();
    });

    it('does not delete on cancel', async () => {
        const onDelete = vi.fn();
        render(DeleteAnnotationsDialog, { props: { ...defaultProps, onDelete } });

        await fireEvent.click(screen.getByRole('button', { name: 'Delete 3 annotations' }));
        await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

        expect(onDelete).not.toHaveBeenCalled();
        expect(screen.queryByRole('heading', { name: 'Delete 3 annotations?' })).toBeNull();
    });

    it('uses the singular for one annotation', () => {
        render(DeleteAnnotationsDialog, { props: { ...defaultProps, selectedCount: 1 } });

        expect(screen.getByRole('button', { name: 'Delete 1 annotation' })).toBeInTheDocument();
    });

    it('disables the trigger while deleting or without a selection', () => {
        const { rerender } = render(DeleteAnnotationsDialog, {
            props: { ...defaultProps, isDeleting: true }
        });
        expect(screen.getByRole('button', { name: 'Delete 3 annotations' })).toBeDisabled();

        rerender({ ...defaultProps, selectedCount: 0 });
        expect(screen.getByRole('button', { name: 'Delete 0 annotations' })).toBeDisabled();
    });
});
