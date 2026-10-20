import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import PlotAxesEditor from './PlotAxesEditor.svelte';

const AXES = {
    x: { negative: 'night', positive: 'day' },
    y: { negative: 'indoors', positive: 'outdoors' }
};

const defaultProps = () => {
    const draft = $state({
        xNegative: 'night',
        xPositive: 'day',
        yNegative: 'indoors',
        yPositive: 'outdoors'
    });
    return {
        draft,
        active: false,
        isPending: false,
        onCommit: vi.fn().mockResolvedValue(true),
        onReset: vi.fn()
    };
};

describe('PlotAxesEditor', () => {
    it('stays open with an error when applying fails, until the user cancels', async () => {
        const user = userEvent.setup();
        const props = defaultProps();
        props.onCommit.mockResolvedValueOnce(false);
        render(PlotAxesEditor, props);

        await user.click(screen.getByRole('button', { name: 'Define axes' }));
        await user.click(screen.getByRole('button', { name: 'Apply axes' }));
        expect(props.onCommit).toHaveBeenCalledWith(AXES);
        expect(screen.getByRole('alert')).toHaveTextContent('Could not apply axes');

        // Cancel closes the popover and clears the error.
        await user.click(screen.getByRole('button', { name: 'Cancel' }));
        expect(screen.queryByRole('button', { name: 'Apply axes' })).not.toBeInTheDocument();
        await user.click(screen.getByRole('button', { name: 'Define axes' }));
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();

        await user.click(screen.getByRole('button', { name: 'Apply axes' }));
        expect(screen.queryByRole('button', { name: 'Apply axes' })).not.toBeInTheDocument();
    });

    it('resets the active axes from the toolbar only', async () => {
        const user = userEvent.setup();
        const props = { ...defaultProps(), active: true };
        render(PlotAxesEditor, props);

        // The popover does not add a second reset button.
        await user.click(screen.getByRole('button', { name: 'Edit axes' }));
        expect(screen.getAllByRole('button', { name: 'Reset axes' })).toHaveLength(1);

        // Keyboard focus shows the hint, not only mouse hover.
        await user.keyboard('{Escape}');
        screen.getByRole('button', { name: 'Reset axes' }).focus();
        expect(await screen.findByRole('tooltip')).toHaveTextContent(
            'Your descriptions will be kept.'
        );

        await user.click(screen.getByRole('button', { name: 'Reset axes' }));
        expect(props.onReset).toHaveBeenCalledOnce();
        expect(screen.queryByRole('button', { name: 'Apply axes' })).not.toBeInTheDocument();
    });

    it('blocks closing and resetting while the axes are applied', async () => {
        const user = userEvent.setup();
        const props = { ...defaultProps(), active: true };
        const view = render(PlotAxesEditor, props);
        await user.click(screen.getByRole('button', { name: 'Edit axes' }));

        await view.rerender({ ...props, isPending: true });

        expect(screen.getByRole('button', { name: 'Edit axes' })).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Reset axes' })).toBeDisabled();
        await user.keyboard('{Escape}');
        expect(screen.getByRole('button', { name: 'Applying…' })).toBeInTheDocument();
    });
});
