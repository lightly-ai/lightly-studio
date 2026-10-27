import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import DeleteAnnotationClassDialog from './DeleteAnnotationClassDialog.svelte';

function renderDialog(annotationCount: number, onConfirm = vi.fn().mockResolvedValue(undefined)) {
    render(DeleteAnnotationClassDialog, {
        props: { open: true, name: 'cat', annotationCount, onConfirm }
    });
    return onConfirm;
}

describe('DeleteAnnotationClassDialog', () => {
    afterEach(() => {
        document.body.innerHTML = '';
    });

    it('warns about annotations and out of date evaluation runs', async () => {
        renderDialog(3);

        await waitFor(() => expect(screen.getByText(/This also deletes/)).toBeInTheDocument());
        expect(screen.getByText('3 annotations')).toBeInTheDocument();
        expect(
            screen.getByText(/Evaluation runs that use these annotations become out of date\./)
        ).toBeInTheDocument();
        expect(
            screen.getByRole('button', { name: 'Delete class and 3 annotations' })
        ).toBeInTheDocument();
    });

    it('shows a short message when no annotations use the class', async () => {
        renderDialog(0);

        await waitFor(() =>
            expect(screen.getByText(/No annotations use this class\./)).toBeInTheDocument()
        );
        expect(screen.queryByText(/out of date/)).not.toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Delete annotation class' })).toBeInTheDocument();
    });

    it('calls onConfirm once and closes', async () => {
        const onConfirm = renderDialog(0);

        await fireEvent.click(
            await screen.findByRole('button', { name: 'Delete annotation class' })
        );

        await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
        expect(onConfirm).toHaveBeenCalledTimes(1);
    });

    it('cannot be closed while the deletion runs', async () => {
        let resolveDelete = () => {};
        renderDialog(
            0,
            vi.fn(() => new Promise<void>((resolve) => (resolveDelete = resolve)))
        );

        await fireEvent.click(
            await screen.findByRole('button', { name: 'Delete annotation class' })
        );

        await waitFor(() => expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled());
        await fireEvent.keyDown(document.activeElement ?? document.body, { key: 'Escape' });
        await fireEvent.click(screen.getByRole('button', { name: 'Close' }));
        expect(screen.getByRole('dialog')).toBeInTheDocument();

        resolveDelete();
        await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    });

    it('stays open when onConfirm rejects', async () => {
        const onConfirm = renderDialog(0, vi.fn().mockRejectedValue(new Error('failed')));

        await fireEvent.click(
            await screen.findByRole('button', { name: 'Delete annotation class' })
        );

        await waitFor(() => expect(onConfirm).toHaveBeenCalledTimes(1));
        // Wait for the rejection to settle: the delete button leaves its pending state.
        await waitFor(() =>
            expect(screen.getByRole('button', { name: 'Delete annotation class' })).toBeEnabled()
        );
        expect(screen.getByRole('dialog')).toBeInTheDocument();
    });
});
