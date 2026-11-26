import { render, screen, waitFor } from '@testing-library/svelte';
import { fireEvent } from '@testing-library/dom';
import { writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { TickDetailView } from '$lib/api/lightly_studio_local/types.gen';
import { useTickCameraFrames } from '$lib/hooks/useTickData/useTickCameraFrames.svelte';
import CameraProjectionStrip from './CameraProjectionStrip.svelte';

// Mock the hooks' source modules so the barrel (`$lib/hooks`) re-exports the stubs and
// each test drives the query results without a live TanStack query.
const tickDetailsResult: { data: TickDetailView | undefined } = { data: undefined };
vi.mock('$lib/hooks/useTickDetails/useTickDetails', () => ({
    useTickDetails: () => ({ tickDetails: tickDetailsResult })
}));
const cameraFramesResult: { data: Record<number, Blob> | undefined } = { data: undefined };
vi.mock('$lib/hooks/useTickData/useTickCameraFrames.svelte', () => ({
    useTickCameraFrames: vi.fn(() => ({ query: cameraFramesResult }))
}));

vi.mock('$lib/hooks/useSettings', () => ({
    useSettings: () => ({
        settingsStore: writable({ key_previous_camera: '[', key_next_camera: ']' })
    })
}));

const defaultProps = {
    datasetId: 'dataset-1',
    sequenceId: 'sequence-1',
    seqNumber: 0,
    cameraChannels: [
        { channel_id: 1, group_component_name: 'front', group_component_index: 0 },
        { channel_id: 2, group_component_name: 'rear', group_component_index: 1 }
    ],
    selectedChannelIds: [1, 2]
};

const tickDetails: TickDetailView = {
    sample_id: 'sample-1',
    collection_id: 'collection-1',
    recording_id: 'recording-1',
    seq_number: 0,
    timestamp_ns: 1000,
    camera_channels: {
        // Camera channel with a keyframe locator: renders, decoding from the keyframe.
        front: {
            channel_id: 1,
            group_component_name: 'front',
            log_time_ns: '2000',
            keyframe_log_time_ns: '1500'
        },
        // Camera channel with no keyframe locator, so its tile is skipped.
        rear: {
            channel_id: 2,
            group_component_name: 'rear',
            log_time_ns: '3000',
            keyframe_log_time_ns: null
        }
    },
    lidar_channels: {},
    annotations: [],
    tags: []
};

const frontImage = new Blob(['front'], { type: 'image/jpeg' });
const rearImage = new Blob(['rear'], { type: 'image/jpeg' });

describe('CameraProjectionStrip', () => {
    beforeEach(() => {
        tickDetailsResult.data = undefined;
        cameraFramesResult.data = undefined;
        // jsdom has no object URLs.
        URL.createObjectURL = vi.fn((blob: Blob) =>
            blob === frontImage ? 'blob:front' : 'blob:rear'
        );
        URL.revokeObjectURL = vi.fn();
    });

    it('keeps every selected summary channel visible when a tick has no frame', () => {
        tickDetailsResult.data = tickDetails;
        cameraFramesResult.data = { 1: frontImage };
        render(CameraProjectionStrip, { props: defaultProps });

        expect(screen.getByRole('img', { name: 'front' })).toBeInTheDocument();
        expect(screen.queryByRole('img', { name: 'rear' })).not.toBeInTheDocument();
        expect(screen.getByText('rear')).toBeInTheDocument();
    });

    it("shows each channel's image from the tick's data", () => {
        tickDetailsResult.data = tickDetails;
        cameraFramesResult.data = { 1: frontImage };
        render(CameraProjectionStrip, { props: defaultProps });

        expect(screen.getByRole('img', { name: 'front' })).toHaveAttribute('src', 'blob:front');
        const getParams = vi.mocked(useTickCameraFrames).mock.lastCall?.[0];
        expect(getParams?.()).toEqual({
            datasetId: 'dataset-1',
            sequenceId: 'sequence-1',
            seqNumber: 0,
            displayFrameId: undefined
        });
    });

    it('renders only the selected camera channels', () => {
        tickDetailsResult.data = {
            ...tickDetails,
            camera_channels: {
                ...tickDetails.camera_channels,
                rear: { ...tickDetails.camera_channels.rear, keyframe_log_time_ns: '2500' }
            }
        };
        cameraFramesResult.data = { 1: frontImage, 2: rearImage };
        render(CameraProjectionStrip, {
            props: { ...defaultProps, selectedChannelIds: [1] }
        });

        expect(screen.getByRole('img', { name: 'front' })).toBeInTheDocument();
        expect(screen.queryByRole('img', { name: 'rear' })).not.toBeInTheDocument();
    });

    it('renders no frames while the tick details are still loading', () => {
        render(CameraProjectionStrip, { props: defaultProps });

        expect(screen.getByTestId('workspace-projection-strip')).toBeInTheDocument();
        expect(screen.queryByRole('img')).not.toBeInTheDocument();
        expect(screen.getByText('front')).toBeInTheDocument();
        expect(screen.getByText('rear')).toBeInTheDocument();
    });

    describe('open camera dialog', () => {
        const cameraChannels = [
            { channel_id: 1, group_component_name: 'CAM_A', group_component_index: 0 },
            { channel_id: 2, group_component_name: 'CAM_B', group_component_index: 1 },
            { channel_id: 3, group_component_name: 'CAM_C', group_component_index: 2 }
        ];
        const camera = (id: number, name: string) => ({
            channel_id: id,
            group_component_name: name,
            log_time_ns: '2000',
            keyframe_log_time_ns: '1500'
        });
        const cameraProps = {
            ...defaultProps,
            cameraChannels,
            selectedChannelIds: [1, 2, 3]
        };

        beforeEach(() => {
            tickDetailsResult.data = {
                ...tickDetails,
                camera_channels: {
                    CAM_A: camera(1, 'CAM_A'),
                    CAM_B: camera(2, 'CAM_B'),
                    CAM_C: camera(3, 'CAM_C')
                }
            };
            cameraFramesResult.data = { 1: frontImage, 2: rearImage, 3: rearImage };
        });

        it('opens a camera from its tile', async () => {
            const onOpenCameraChange = vi.fn();
            render(CameraProjectionStrip, { props: { ...cameraProps, onOpenCameraChange } });

            await fireEvent.click(screen.getByRole('button', { name: 'Enlarge CAM_B' }));

            expect(onOpenCameraChange).toHaveBeenCalledWith('CAM_B', 'push');
        });

        it('toggles playback on Space after opening from a tile without switching camera', async () => {
            const onOpenCameraChange = vi.fn();
            const onPlaybackToggle = vi.fn();
            const props = { ...cameraProps, onOpenCameraChange, onPlaybackToggle };
            const { rerender } = render(CameraProjectionStrip, { props });
            const tile = screen.getByRole('button', { name: 'Enlarge CAM_B' });
            tile.focus();
            await fireEvent.click(tile);
            onOpenCameraChange.mockClear();

            await rerender({ ...props, openCamera: 'CAM_B' });

            await waitFor(() => expect(document.activeElement).toBe(screen.getByRole('dialog')));
            await fireEvent.keyDown(document.activeElement as HTMLElement, {
                key: ' ',
                code: 'Space'
            });
            expect(onPlaybackToggle).toHaveBeenCalledTimes(1);
            expect(onOpenCameraChange).not.toHaveBeenCalled();
        });

        it('shows one dialog for the open camera with its position', () => {
            render(CameraProjectionStrip, { props: { ...cameraProps, openCamera: 'CAM_B' } });

            expect(screen.getAllByRole('dialog')).toHaveLength(1);
            expect(screen.getByText('Camera: CAM_B · 2 / 3')).toBeInTheDocument();
        });

        it('switches to the next camera and wraps around', async () => {
            const onOpenCameraChange = vi.fn();
            const { rerender } = render(CameraProjectionStrip, {
                props: { ...cameraProps, openCamera: 'CAM_B', onOpenCameraChange }
            });

            await fireEvent.click(screen.getByRole('button', { name: 'Next camera' }));
            expect(onOpenCameraChange).toHaveBeenLastCalledWith('CAM_C', 'replace');

            await rerender({ ...cameraProps, openCamera: 'CAM_C', onOpenCameraChange });
            await fireEvent.click(screen.getByRole('button', { name: 'Next camera' }));
            expect(onOpenCameraChange).toHaveBeenLastCalledWith('CAM_A', 'replace');
        });

        it('closes the dialog through the route', async () => {
            const onOpenCameraChange = vi.fn();
            render(CameraProjectionStrip, {
                props: { ...cameraProps, openCamera: 'CAM_B', onOpenCameraChange }
            });

            await fireEvent.click(screen.getByRole('button', { name: 'Close' }));

            expect(onOpenCameraChange).toHaveBeenCalledWith(undefined, 'replace');
        });

        it('closes when the open camera is deselected', async () => {
            const onOpenCameraChange = vi.fn();
            const { rerender } = render(CameraProjectionStrip, {
                props: { ...cameraProps, openCamera: 'CAM_B', onOpenCameraChange }
            });
            expect(onOpenCameraChange).not.toHaveBeenCalled();

            await rerender({
                ...cameraProps,
                selectedChannelIds: [1, 3],
                openCamera: 'CAM_B',
                onOpenCameraChange
            });

            expect(onOpenCameraChange).toHaveBeenCalledWith(undefined, 'replace');
        });

        it('keeps the open camera while channels are loading', () => {
            const onOpenCameraChange = vi.fn();
            render(CameraProjectionStrip, {
                props: {
                    ...cameraProps,
                    cameraChannels: [],
                    openCamera: 'CAM_B',
                    onOpenCameraChange
                }
            });

            expect(onOpenCameraChange).not.toHaveBeenCalled();
        });

        it('follows the tick in the same dialog and image', async () => {
            const { rerender } = render(CameraProjectionStrip, {
                props: { ...cameraProps, openCamera: 'CAM_B' }
            });
            const dialog = screen.getByRole('dialog');
            const image = screen.getByRole('img', { name: 'CAM_B enlarged' });
            expect(image.getAttribute('src')).toContain('log_time_ns=2000');

            tickDetailsResult.data = {
                ...tickDetails,
                camera_channels: {
                    CAM_A: camera(1, 'CAM_A'),
                    CAM_B: { ...camera(2, 'CAM_B'), log_time_ns: '3000' },
                    CAM_C: camera(3, 'CAM_C')
                }
            };
            await rerender({
                ...cameraProps,
                cameraChannels: cameraChannels.map((channel) => ({ ...channel })),
                openCamera: 'CAM_B',
                seqNumber: 1
            });

            expect(screen.getByRole('dialog')).toBe(dialog);
            expect(screen.getByRole('img', { name: 'CAM_B enlarged' })).toBe(image);
            expect(image.getAttribute('src')).toContain('log_time_ns=3000');
        });

        it('disables switching with a single selected camera', () => {
            render(CameraProjectionStrip, {
                props: { ...cameraProps, selectedChannelIds: [2], openCamera: 'CAM_B' }
            });

            expect(screen.getByRole('button', { name: 'Previous camera' })).toBeDisabled();
            expect(screen.getByRole('button', { name: 'Next camera' })).toBeDisabled();
        });

        it('opens the camera of a digit key', async () => {
            const onOpenCameraChange = vi.fn();
            render(CameraProjectionStrip, { props: { ...cameraProps, onOpenCameraChange } });

            await fireEvent.keyDown(document.body, { key: '2' });

            expect(onOpenCameraChange).toHaveBeenCalledWith('CAM_B', 'push');
        });

        it('replaces the open camera on a digit key', async () => {
            const onOpenCameraChange = vi.fn();
            render(CameraProjectionStrip, {
                props: { ...cameraProps, openCamera: 'CAM_A', onOpenCameraChange }
            });

            await fireEvent.keyDown(document.body, { key: '3' });

            expect(onOpenCameraChange).toHaveBeenCalledWith('CAM_C', 'replace');
        });

        it('ignores digit keys typed in an input', async () => {
            const onOpenCameraChange = vi.fn();
            render(CameraProjectionStrip, { props: { ...cameraProps, onOpenCameraChange } });
            const input = document.createElement('input');
            document.body.appendChild(input);

            await fireEvent.keyDown(input, { key: '2' });

            expect(onOpenCameraChange).not.toHaveBeenCalled();
            input.remove();
        });

        it('ignores digit keys from another dialog', async () => {
            const onOpenCameraChange = vi.fn();
            render(CameraProjectionStrip, { props: { ...cameraProps, onOpenCameraChange } });
            const otherDialog = document.createElement('div');
            otherDialog.setAttribute('role', 'dialog');
            document.body.appendChild(otherDialog);

            await fireEvent.keyDown(otherDialog, { key: '2' });

            expect(onOpenCameraChange).not.toHaveBeenCalled();
            otherDialog.remove();
        });

        it('switches cameras with digit keys inside the camera dialog', async () => {
            const onOpenCameraChange = vi.fn();
            render(CameraProjectionStrip, {
                props: { ...cameraProps, openCamera: 'CAM_A', onOpenCameraChange }
            });

            await fireEvent.keyDown(screen.getByRole('dialog'), { key: '3' });

            expect(onOpenCameraChange).toHaveBeenCalledWith('CAM_C', 'replace');
        });

        it('switches cameras with keys while focus is outside the dialog', async () => {
            const onOpenCameraChange = vi.fn();
            render(CameraProjectionStrip, {
                props: { ...cameraProps, openCamera: 'CAM_C', onOpenCameraChange }
            });
            expect(screen.getByRole('dialog')).not.toContainElement(
                document.activeElement as HTMLElement
            );

            await fireEvent.keyDown(document.body, { key: ']' });
            expect(onOpenCameraChange).toHaveBeenLastCalledWith('CAM_A', 'replace');

            await fireEvent.keyDown(document.body, { key: '[' });
            expect(onOpenCameraChange).toHaveBeenLastCalledWith('CAM_B', 'replace');

            await fireEvent.keyDown(document.body, { key: 'ArrowRight', shiftKey: true });
            expect(onOpenCameraChange).toHaveBeenCalledTimes(3);
        });

        it('switches once when the key is pressed inside the dialog', async () => {
            const onOpenCameraChange = vi.fn();
            render(CameraProjectionStrip, {
                props: { ...cameraProps, openCamera: 'CAM_A', onOpenCameraChange }
            });

            await fireEvent.keyDown(screen.getByRole('dialog'), { key: ']' });

            expect(onOpenCameraChange).toHaveBeenCalledTimes(1);
        });

        it('ignores camera keys when no camera is open', async () => {
            const onOpenCameraChange = vi.fn();
            render(CameraProjectionStrip, { props: { ...cameraProps, onOpenCameraChange } });

            await fireEvent.keyDown(document.body, { key: ']' });

            expect(onOpenCameraChange).not.toHaveBeenCalled();
        });
    });
});
