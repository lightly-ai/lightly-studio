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
            sourceNames?: string[];
            selectedSource?: string;
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
        expect(
            screen.getByText('Choose an existing class or type a new one to create it.')
        ).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Confirm' })).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Cancel' })).toBeEnabled();
    });

    it('deduplicates and sorts labels alphabetically', async () => {
        const user = userEvent.setup();
        renderDialog({ labels: ['dog', 'cat', 'dog', 'bird'] });

        await user.click(screen.getByTestId('select-list-trigger'));

        const options = await screen.findAllByRole('option');
        expect(options.map((o) => o.textContent?.trim())).toEqual(['bird', 'cat', 'dog']);
    });

    it('calls onConfirm with the selected label when Confirm is clicked', async () => {
        const user = userEvent.setup();
        const { onConfirm, onCancel } = renderDialog();

        await user.click(screen.getByTestId('select-list-trigger'));
        await user.click(await screen.findByRole('option', { name: 'cat' }));

        const confirmButton = screen.getByRole('button', { name: 'Confirm' });
        await waitFor(() => expect(confirmButton).toBeEnabled());
        await user.click(confirmButton);

        expect(onConfirm).toHaveBeenCalledTimes(1);
        expect(onConfirm).toHaveBeenCalledWith('cat', undefined);
        expect(onCancel).not.toHaveBeenCalled();
    });

    it('calls onCancel when Cancel is clicked', async () => {
        const user = userEvent.setup();
        const { onConfirm, onCancel } = renderDialog();

        await user.click(screen.getByRole('button', { name: 'Cancel' }));

        expect(onCancel).toHaveBeenCalledTimes(1);
        expect(onConfirm).not.toHaveBeenCalled();
    });

    it('passes a newly typed class name to onConfirm', async () => {
        const user = userEvent.setup();
        const { onConfirm } = renderDialog();

        await user.click(screen.getByTestId('select-list-trigger'));
        await user.type(screen.getByTestId('select-list-input'), 'fish{Enter}');

        const confirmButton = screen.getByRole('button', { name: 'Confirm' });
        await waitFor(() => expect(confirmButton).toBeEnabled());
        await user.click(confirmButton);

        expect(onConfirm).toHaveBeenCalledWith('fish', undefined);
    });

    it('hides the source selector with fewer than two sources', () => {
        renderDialog({ sourceNames: [] });
        expect(screen.queryByTestId('annotation-source-trigger')).not.toBeInTheDocument();

        renderDialog({ sourceNames: ['ground_truth'] });
        expect(screen.queryByTestId('annotation-source-trigger')).not.toBeInTheDocument();
    });

    it('adds to the only existing source when the selector is hidden', async () => {
        const user = userEvent.setup();
        const { onConfirm } = renderDialog({ sourceNames: ['predictions'] });

        // Selector is hidden, but the lone source is used rather than creating a new one.
        expect(screen.queryByTestId('annotation-source-trigger')).not.toBeInTheDocument();

        await user.click(screen.getByTestId('select-list-trigger'));
        await user.click(await screen.findByRole('option', { name: 'cat' }));

        const confirmButton = screen.getByRole('button', { name: 'Confirm' });
        await waitFor(() => expect(confirmButton).toBeEnabled());
        await user.click(confirmButton);

        expect(onConfirm).toHaveBeenCalledWith('cat', 'predictions');
    });

    it('shows the source selector with the pre-selected source when two or more exist', () => {
        renderDialog({
            sourceNames: ['ground_truth', 'predictions'],
            selectedSource: 'predictions'
        });

        const trigger = screen.getByTestId('annotation-source-trigger');
        expect(trigger).toBeInTheDocument();
        expect(trigger).toHaveTextContent('predictions');
    });

    it('keeps Confirm disabled until both a class and a source are chosen', async () => {
        const user = userEvent.setup();
        renderDialog({ sourceNames: ['ground_truth', 'predictions'] });

        // Neither class nor source chosen yet.
        expect(screen.getByRole('button', { name: 'Confirm' })).toBeDisabled();

        // Choosing only a class is not enough while a source must still be picked.
        await user.click(screen.getByTestId('select-list-trigger'));
        await user.click(await screen.findByRole('option', { name: 'cat' }));

        await waitFor(() => expect(screen.getByRole('button', { name: 'Confirm' })).toBeDisabled());
    });

    it('passes the selected source to onConfirm', async () => {
        const user = userEvent.setup();
        const { onConfirm } = renderDialog({
            sourceNames: ['ground_truth', 'predictions'],
            selectedSource: 'predictions'
        });

        await user.click(screen.getByTestId('select-list-trigger'));
        await user.click(await screen.findByRole('option', { name: 'cat' }));

        const confirmButton = screen.getByRole('button', { name: 'Confirm' });
        await waitFor(() => expect(confirmButton).toBeEnabled());
        await user.click(confirmButton);

        expect(onConfirm).toHaveBeenCalledWith('cat', 'predictions');
    });
});
