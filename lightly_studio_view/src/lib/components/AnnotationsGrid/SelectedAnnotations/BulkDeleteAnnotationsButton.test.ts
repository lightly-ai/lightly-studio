import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import BulkDeleteAnnotationsButton from './BulkDeleteAnnotationsButton.svelte';

const defaultProps = {
    selectedCount: 3,
    disabled: false,
    isLoading: false,
    onDelete: vi.fn()
};

describe('BulkDeleteAnnotationsButton', () => {
    it('confirms before deleting selected annotations', async () => {
        const onDelete = vi.fn();
        render(BulkDeleteAnnotationsButton, { props: { ...defaultProps, onDelete } });

        await fireEvent.click(screen.getByTestId('bulk-delete-annotations-trigger'));

        expect(onDelete).not.toHaveBeenCalled();
        expect(screen.getByText(/Delete 3 annotations/)).toBeInTheDocument();

        await fireEvent.click(screen.getByTestId('bulk-delete-annotations-confirm'));

        expect(onDelete).toHaveBeenCalledOnce();
    });

    it('disables deletion when there is no selected annotation', () => {
        render(BulkDeleteAnnotationsButton, {
            props: { ...defaultProps, selectedCount: 0 }
        });

        expect(screen.getByTestId('bulk-delete-annotations-trigger')).toBeDisabled();
    });
});
