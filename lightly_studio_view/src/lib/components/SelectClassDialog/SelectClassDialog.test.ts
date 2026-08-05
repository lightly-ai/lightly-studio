import { describe, it, expect, vi, beforeAll } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

import SelectClassDialog from './SelectClassDialog.svelte';

describe('SelectClassDialog', () => {
    beforeAll(() => {
        Element.prototype.scrollIntoView = vi.fn();
    });

    const renderDialog = (
        propOverrides: {
            open?: boolean;
            labels?: string[];
        } = {}
    ) => {
        const onConfirm = vi.fn();
        const onCancel = vi.fn();

        const result = render(SelectClassDialog, {
            props: {
                open: true,
                labels: ['cat', 'dog', 'bird'],
                onConfirm,
                onCancel,
                ...propOverrides
            }
        });

        return { ...result, onConfirm, onCancel };
    };

    it('renders nothing when closed', () => {
        renderDialog({ open: false, labels: [] });

        expect(screen.queryByText('Select a Class')).not.toBeInTheDocument();
    });

    it('renders title, description and disabled Confirm button when open', () => {
        renderDialog();

        expect(screen.getByText('Select a Class')).toBeInTheDocument();
        expect(screen.getByText('Choose an existing annotation class.')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Confirm' })).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Cancel' })).toBeEnabled();
    });

    it('deduplicates and sorts labels alphabetically', async () => {
        renderDialog({ labels: ['dog', 'cat', 'dog', 'bird'] });

        const options = await screen.findAllByRole('option');
        expect(options.map((o) => o.textContent?.trim())).toEqual(['bird', 'cat', 'dog']);
    });

    it('calls onConfirm with the selected label when Confirm is clicked', async () => {
        const user = userEvent.setup();
        const { onConfirm, onCancel } = renderDialog();

        await user.click(await screen.findByRole('option', { name: 'cat' }));

        const confirmButton = screen.getByRole('button', { name: 'Confirm' });
        await waitFor(() => expect(confirmButton).toBeEnabled());
        await user.click(confirmButton);

        expect(onConfirm).toHaveBeenCalledTimes(1);
        expect(onConfirm).toHaveBeenCalledWith('cat');
        expect(onCancel).not.toHaveBeenCalled();
    });

    it('does not confirm a newly typed class name when Enter is pressed', async () => {
        const user = userEvent.setup();
        const { onConfirm } = renderDialog();
        const input = await screen.findByTestId('select-list-input');

        expect(input).toHaveFocus();

        await user.type(input, 'fish{Enter}');

        expect(onConfirm).not.toHaveBeenCalled();
    });

    it('confirms the keyboard-highlighted class instead of the filter text', async () => {
        const user = userEvent.setup();
        const { onConfirm } = renderDialog();
        const input = await screen.findByTestId('select-list-input');

        await user.type(input, 'do');
        await waitFor(() =>
            expect(screen.getByRole('option', { name: 'dog' })).toHaveAttribute(
                'aria-selected',
                'true'
            )
        );
        await user.keyboard('{Enter}');

        expect(onConfirm).toHaveBeenCalledTimes(1);
        expect(onConfirm).toHaveBeenCalledWith('dog');
    });

    it('calls onCancel when Cancel is clicked', async () => {
        const user = userEvent.setup();
        const { onConfirm, onCancel } = renderDialog();

        await user.click(screen.getByRole('button', { name: 'Cancel' }));

        expect(onCancel).toHaveBeenCalledTimes(1);
        expect(onConfirm).not.toHaveBeenCalled();
    });

    it('does not offer a create option for a newly typed class name', async () => {
        const user = userEvent.setup();
        const { onConfirm } = renderDialog();

        await user.type(await screen.findByTestId('select-list-input'), 'fish');

        expect(screen.queryByRole('option', { name: /Create:\s*fish/i })).not.toBeInTheDocument();
        expect(onConfirm).not.toHaveBeenCalled();
    });

    it('does not render an annotation source selector', () => {
        renderDialog();

        expect(screen.queryByTestId('annotation-source-trigger')).not.toBeInTheDocument();
    });
});
