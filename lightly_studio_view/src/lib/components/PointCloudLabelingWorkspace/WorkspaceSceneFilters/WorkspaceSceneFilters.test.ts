import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import type { ChannelSummaryView } from '$lib/api/lightly_studio_local/types.gen';
import WorkspaceSceneFilters from './WorkspaceSceneFilters.svelte';

const lidarChannels: ChannelSummaryView[] = [
    {
        channel_id: 1,
        group_component_name: 'lidar_top',
        group_component_index: 0,
        frame_id: 'lidar_top'
    }
];

const defaultProps = {
    referenceFrames: [] as { name: string }[],
    referenceFrameId: '',
    onSelectReferenceFrame: vi.fn(),
    lidarChannels,
    selectedLidarChannels: [] as number[],
    colorMode: 'density' as const,
    onColorModeChange: vi.fn(),
    onToggleLidarChannel: vi.fn(),
    onSetLidarChannels: vi.fn()
};

describe('WorkspaceSceneFilters', () => {
    beforeAll(() => {
        Element.prototype.scrollIntoView = vi.fn();
        Element.prototype.hasPointerCapture = vi.fn(() => false);
        Element.prototype.setPointerCapture = vi.fn();
        Element.prototype.releasePointerCapture = vi.fn();
    });

    it('summarizes the lidar selection in the trigger', () => {
        render(WorkspaceSceneFilters, {
            props: { ...defaultProps, selectedLidarChannels: [1] }
        });

        expect(screen.getByTestId('workspace-lidar-select')).toHaveTextContent('Lidar: lidar_top');
    });

    it('selects a reference frame by its id', async () => {
        const user = userEvent.setup();
        const onSelectReferenceFrame = vi.fn();
        render(WorkspaceSceneFilters, {
            props: {
                ...defaultProps,
                referenceFrames: [{ name: 'map' }, { name: 'CABIN' }],
                referenceFrameId: 'map',
                onSelectReferenceFrame
            }
        });

        expect(screen.getByTestId('workspace-frame-select')).toHaveTextContent('Frame: map');
        await user.click(screen.getByTestId('workspace-frame-select'));
        await user.click(screen.getByText('CABIN'));

        expect(onSelectReferenceFrame).toHaveBeenCalledExactlyOnceWith('CABIN');
    });

    it('selects a point color mode with the shared select control', async () => {
        const user = userEvent.setup();
        const onColorModeChange = vi.fn();
        render(WorkspaceSceneFilters, {
            props: { ...defaultProps, onColorModeChange }
        });

        expect(screen.getByTestId('workspace-color-select')).toHaveTextContent('Color: Density');
        await user.click(screen.getByTestId('workspace-color-select'));
        expect(screen.getByText('Intensity')).toBeInTheDocument();
        await user.click(screen.getByText('Height + Distance'));

        expect(onColorModeChange).toHaveBeenCalledExactlyOnceWith('height-distance');
    });

    it('hides the frame select without reference frames', () => {
        render(WorkspaceSceneFilters, { props: defaultProps });

        expect(screen.queryByTestId('workspace-frame-select')).not.toBeInTheDocument();
    });

    it('says when the tick is shown in the sensor frames', () => {
        render(WorkspaceSceneFilters, {
            props: {
                ...defaultProps,
                referenceFrames: [{ name: 'map' }],
                referenceFrameId: 'map',
                isShowingSensorFrames: true
            }
        });

        expect(screen.getByTestId('workspace-frame-fallback')).toHaveTextContent(
            'Showing sensor frames'
        );
    });

    it('disables the lidar select without lidar channels', () => {
        render(WorkspaceSceneFilters, {
            props: { ...defaultProps, lidarChannels: [] }
        });

        expect(screen.getByTestId('workspace-lidar-select')).toBeDisabled();
    });
});
