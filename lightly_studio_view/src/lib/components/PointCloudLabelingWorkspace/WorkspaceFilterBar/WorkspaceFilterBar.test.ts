import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import type { ChannelSummaryView } from '$lib/api/lightly_studio_local/types.gen';
import WorkspaceFilterBar from './WorkspaceFilterBar.svelte';

const lidarChannels: ChannelSummaryView[] = [
    {
        channel_id: 1,
        group_component_name: 'lidar_top',
        group_component_index: 0,
        frame_id: 'lidar_top'
    }
];

const cameraChannels: ChannelSummaryView[] = [
    { channel_id: 2, group_component_name: 'front', group_component_index: 0, frame_id: 'front' },
    { channel_id: 3, group_component_name: 'rear', group_component_index: 1, frame_id: 'rear' }
];

const defaultProps = {
    referenceFrames: [
        { id: 'map', name: 'Map' },
        { id: 'CABIN', name: 'Cabin' }
    ],
    referenceFrameId: 'map',
    onSelectReferenceFrame: vi.fn(),
    lidarChannels,
    cameraChannels,
    selectedLidarChannels: [] as number[],
    selectedCameraChannels: [] as number[],
    onToggleLidarChannel: vi.fn(),
    onToggleCameraChannel: vi.fn()
};

describe('WorkspaceFilterBar', () => {
    beforeAll(() => {
        // The bits-ui select of the frame uses pointer-capture APIs that jsdom does not implement.
        Element.prototype.hasPointerCapture = vi.fn(() => false);
        Element.prototype.setPointerCapture = vi.fn();
        Element.prototype.releasePointerCapture = vi.fn();
        Element.prototype.scrollIntoView = vi.fn();
    });

    it('opens a lane and lists its channels', async () => {
        const user = userEvent.setup();
        render(WorkspaceFilterBar, { props: defaultProps });

        await user.click(screen.getByTestId('workspace-camera-select'));

        expect(screen.getByText('front')).toBeInTheDocument();
        expect(screen.getByText('rear')).toBeInTheDocument();
    });

    it('summarizes the selection in the trigger', () => {
        render(WorkspaceFilterBar, {
            props: { ...defaultProps, selectedCameraChannels: [2] }
        });

        expect(screen.getByTestId('workspace-camera-select')).toHaveTextContent('Camera: front');
        expect(screen.getByTestId('workspace-lidar-select')).toHaveTextContent('Lidar');
    });

    it('toggles a channel by its channel_id on click', async () => {
        const user = userEvent.setup();
        const onToggleCameraChannel = vi.fn();
        render(WorkspaceFilterBar, {
            props: { ...defaultProps, onToggleCameraChannel }
        });

        await user.click(screen.getByTestId('workspace-camera-select'));
        await user.click(screen.getByText('rear'));

        expect(onToggleCameraChannel).toHaveBeenCalledExactlyOnceWith(3);
    });

    it('shows the selected frame and selects another frame by its id', async () => {
        const user = userEvent.setup();
        const onSelectReferenceFrame = vi.fn();
        render(WorkspaceFilterBar, { props: { ...defaultProps, onSelectReferenceFrame } });

        const trigger = screen.getByTestId('workspace-frame-select');
        expect(trigger).toHaveTextContent('Frame: Map');
        await user.click(trigger);
        await user.click(screen.getByTestId('workspace-frame-select-CABIN'));

        expect(onSelectReferenceFrame).toHaveBeenCalledExactlyOnceWith('CABIN');
    });

    it('disables a lane that has no channels', () => {
        render(WorkspaceFilterBar, {
            props: { ...defaultProps, lidarChannels: [] }
        });

        expect(screen.getByTestId('workspace-lidar-select')).toBeDisabled();
        expect(screen.getByTestId('workspace-camera-select')).toBeEnabled();
    });
});
