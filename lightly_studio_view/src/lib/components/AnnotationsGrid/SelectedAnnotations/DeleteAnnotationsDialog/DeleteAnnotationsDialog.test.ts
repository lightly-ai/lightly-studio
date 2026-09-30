import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import DeleteAnnotationsDialog from './DeleteAnnotationsDialog.svelte';

const defaultProps = {
    selectedCount: 3,
    onDelete: vi.fn()
};

describe('DeleteAnnotationsDialog', () => {
    it('disables the trigger when no annotation is selected', () => {
        render(DeleteAnnotationsDialog, { props: { ...defaultProps, selectedCount: 0 } });

        expect(screen.getByRole('button', { name: 'Delete annotations' })).toBeDisabled();
    });

    it('shows the selected count and deletes on confirm', async () => {
        const onDelete = vi.fn().mockResolvedValue(undefined);
        render(DeleteAnnotationsDialog, { props: { ...defaultProps, onDelete } });

        await fireEvent.click(screen.getByRole('button', { name: 'Delete annotations' }));
        expect(
            screen.getByText('Delete 3 annotations? This cannot be undone.')
        ).toBeInTheDocument();
        await fireEvent.click(screen.getByRole('button', { name: 'Delete' }));

        expect(onDelete).toHaveBeenCalledOnce();
        expect(screen.queryByRole('heading', { name: 'Delete annotations' })).toBeNull();
    });

    it('does not delete on cancel', async () => {
        const onDelete = vi.fn();
        render(DeleteAnnotationsDialog, { props: { ...defaultProps, onDelete } });

        await fireEvent.click(screen.getByRole('button', { name: 'Delete annotations' }));
        await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

        expect(onDelete).not.toHaveBeenCalled();
    });
});
