import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import type { ChannelSummaryView } from '$lib/api/lightly_studio_local/types.gen';
import WorkspaceChannelSelect from './WorkspaceChannelSelect.svelte';

const channels: ChannelSummaryView[] = [
    { channel_id: 2, group_component_name: 'front', group_component_index: 0, frame_id: 'front' },
    { channel_id: 3, group_component_name: 'rear', group_component_index: 1, frame_id: 'rear' }
];

const defaultProps = {
    label: 'Camera',
    channels,
    selectedChannels: [] as number[],
    onToggleChannel: vi.fn(),
    testId: 'workspace-camera-select'
};

describe('WorkspaceChannelSelect', () => {
    beforeAll(() => {
        Element.prototype.scrollIntoView = vi.fn();
    });

    it('shows the bare label when nothing is selected', () => {
        render(WorkspaceChannelSelect, { props: defaultProps });

        expect(screen.getByTestId('workspace-camera-select')).toHaveTextContent('Camera');
        expect(screen.getByTestId('workspace-camera-select')).not.toHaveTextContent(':');
    });

    it('names the single selected channel in the trigger', () => {
        render(WorkspaceChannelSelect, {
            props: { ...defaultProps, selectedChannels: [2] }
        });

        expect(screen.getByTestId('workspace-camera-select')).toHaveTextContent('Camera: front');
    });

    it('summarizes the count when several channels are selected', () => {
        render(WorkspaceChannelSelect, {
            props: { ...defaultProps, selectedChannels: [2, 3] }
        });

        expect(screen.getByTestId('workspace-camera-select')).toHaveTextContent(
            'Camera: 2 selected'
        );
    });

    it('lists each channel once opened', async () => {
        const user = userEvent.setup();
        render(WorkspaceChannelSelect, { props: defaultProps });

        await user.click(screen.getByTestId('workspace-camera-select'));

        expect(screen.getByText('front')).toBeInTheDocument();
        expect(screen.getByText('rear')).toBeInTheDocument();
    });

    it('toggles the clicked channel by its channel_id', async () => {
        const user = userEvent.setup();
        const onToggleChannel = vi.fn();
        render(WorkspaceChannelSelect, { props: { ...defaultProps, onToggleChannel } });

        await user.click(screen.getByTestId('workspace-camera-select'));
        await user.click(screen.getByText('rear'));

        expect(onToggleChannel).toHaveBeenCalledExactlyOnceWith(3);
    });

    it('toggles an already selected channel off', async () => {
        const user = userEvent.setup();
        const onToggleChannel = vi.fn();
        render(WorkspaceChannelSelect, {
            props: { ...defaultProps, selectedChannels: [2], onToggleChannel }
        });

        await user.click(screen.getByTestId('workspace-camera-select'));
        await user.click(screen.getByText('front'));

        expect(onToggleChannel).toHaveBeenCalledExactlyOnceWith(2);
    });

    it('disables the trigger when there are no channels', () => {
        render(WorkspaceChannelSelect, { props: { ...defaultProps, channels: [] } });

        expect(screen.getByTestId('workspace-camera-select')).toBeDisabled();
    });
});
