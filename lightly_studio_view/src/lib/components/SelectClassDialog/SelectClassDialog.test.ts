import { describe, it, expect, vi, beforeAll, afterAll } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

import SelectClassDialog from './SelectClassDialog.svelte';
import type { ComponentProps } from 'svelte';

const defaultTrackProps = {
    showTrackSelect: true,
    tracks: [{ object_track_id: 'track-1', object_track_number: 1, annotation_class_name: 'car' }]
};

// bits-ui Select uses pointer-capture and scrollIntoView APIs that jsdom doesn't implement.
const originalHasPointerCapture = Element.prototype.hasPointerCapture;
const originalSetPointerCapture = Element.prototype.setPointerCapture;
const originalReleasePointerCapture = Element.prototype.releasePointerCapture;
const originalScrollIntoView = Element.prototype.scrollIntoView;

beforeAll(() => {
    Element.prototype.hasPointerCapture = vi.fn(() => false);
    Element.prototype.setPointerCapture = vi.fn();
    Element.prototype.releasePointerCapture = vi.fn();
    Element.prototype.scrollIntoView = vi.fn();
});

afterAll(() => {
    Element.prototype.hasPointerCapture = originalHasPointerCapture;
    Element.prototype.setPointerCapture = originalSetPointerCapture;
    Element.prototype.releasePointerCapture = originalReleasePointerCapture;
    Element.prototype.scrollIntoView = originalScrollIntoView;
});

describe('SelectClassDialog', () => {
    const renderDialog = (
        propOverrides: Partial<ComponentProps<typeof SelectClassDialog>> = {}
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

    it('confirms a newly typed class name when Enter is pressed', async () => {
        const user = userEvent.setup();
        const { onConfirm } = renderDialog();
        const input = await screen.findByTestId('select-list-input');

        expect(input).toHaveFocus();

        await user.type(input, 'fish{Enter}');

        expect(onConfirm).toHaveBeenCalledTimes(1);
        expect(onConfirm).toHaveBeenCalledWith('fish');
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

    it('selects a newly typed class name before explicit mouse confirmation', async () => {
        const user = userEvent.setup();
        const { onConfirm } = renderDialog();

        await user.type(await screen.findByTestId('select-list-input'), 'fish');
        await user.click(screen.getByRole('option', { name: /Create:\s*fish/i }));

        const confirmButton = screen.getByRole('button', { name: 'Confirm' });
        await waitFor(() => expect(confirmButton).toBeEnabled());
        await user.click(confirmButton);

        expect(onConfirm).toHaveBeenCalledWith('fish');
    });

    it('does not render an annotation source selector', () => {
        renderDialog();

        expect(screen.queryByTestId('annotation-source-trigger')).not.toBeInTheDocument();
    });

    it('shows track select when showTrackSelect is true', () => {
        renderDialog(defaultTrackProps);

        expect(screen.getByTestId('track-select')).toBeInTheDocument();
        expect(screen.getByText('Track')).toBeInTheDocument();
    });

    it('includes track selection in onConfirm when showTrackSelect is enabled', async () => {
        const user = userEvent.setup();
        const { onConfirm } = renderDialog(defaultTrackProps);

        // Select a class
        await user.click(await screen.findByRole('option', { name: 'cat' }));

        // Select a track
        await user.click(
            within(screen.getByTestId('track-select')).getByTestId('select-list-trigger')
        );
        await user.click(screen.getByRole('option', { name: 'car - 1' }));

        // Confirm
        const confirmButton = screen.getByRole('button', { name: 'Confirm' });
        await waitFor(() => expect(confirmButton).toBeEnabled());
        await user.click(confirmButton);

        expect(onConfirm).toHaveBeenCalledWith('cat', {
            objectTrackId: 'track-1',
            isNewTrack: false
        });
    });

    it('resets track selection when class changes', async () => {
        const user = userEvent.setup();
        const { onConfirm } = renderDialog(defaultTrackProps);

        // Select "cat" class
        await user.click(await screen.findByRole('option', { name: 'cat' }));

        // Select a track
        await user.click(
            within(screen.getByTestId('track-select')).getByTestId('select-list-trigger')
        );
        await user.click(screen.getByRole('option', { name: 'car - 1' }));

        // Change to a different class - this should reset the track
        // First trigger in DOM order is the class SelectList
        await user.click(screen.getAllByTestId('select-list-trigger')[0]);
        await user.click(await screen.findByRole('option', { name: 'dog' }));

        // Confirm
        const confirmButton = screen.getByRole('button', { name: 'Confirm' });
        await waitFor(() => expect(confirmButton).toBeEnabled());
        await user.click(confirmButton);

        expect(onConfirm).toHaveBeenCalledWith('dog', {
            objectTrackId: null,
            isNewTrack: false
        });
    });
});
