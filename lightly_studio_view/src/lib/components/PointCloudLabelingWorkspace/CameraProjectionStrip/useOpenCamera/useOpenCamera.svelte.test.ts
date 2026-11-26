import { flushSync } from 'svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useOpenCamera } from './useOpenCamera.svelte';

const CAMERA_CHANNELS = [
    { channel_id: 1, group_component_name: 'CAM_A', group_component_index: 0 },
    { channel_id: 2, group_component_name: 'CAM_B', group_component_index: 1 },
    { channel_id: 3, group_component_name: 'CAM_C', group_component_index: 2 }
];

const disposers: (() => void)[] = [];
afterEach(() => disposers.splice(0).forEach((dispose) => dispose()));

function setup({ openCamera = undefined as string | undefined, selectedChannelIds = [1, 2, 3] }) {
    const input = $state({ cameraChannels: CAMERA_CHANNELS, selectedChannelIds, openCamera });
    const onOpenCameraChange = vi.fn();
    let cameras!: ReturnType<typeof useOpenCamera>;
    disposers.push(
        $effect.root(() => {
            cameras = useOpenCamera({
                getCameraChannels: () => input.cameraChannels,
                getSelectedChannelIds: () => input.selectedChannelIds,
                getOpenCamera: () => input.openCamera,
                onOpenCameraChange
            });
        })
    );
    flushSync();
    return { input, cameras, onOpenCameraChange };
}

const digitEvent = (key: string) => new KeyboardEvent('keydown', { key, cancelable: true });

describe('useOpenCamera', () => {
    it('opens a camera with a new history entry and switches with a replace', () => {
        const { input, cameras, onOpenCameraChange } = setup({});

        cameras.show('CAM_B');
        expect(onOpenCameraChange).toHaveBeenLastCalledWith('CAM_B', 'push');

        input.openCamera = 'CAM_B';
        cameras.show('CAM_C');
        expect(onOpenCameraChange).toHaveBeenLastCalledWith('CAM_C', 'replace');
    });

    it('does not report the camera that is already open', () => {
        const { cameras, onOpenCameraChange } = setup({ openCamera: 'CAM_B' });

        cameras.show('CAM_B');
        cameras.handleWindowKeydown(digitEvent('2'));

        expect(onOpenCameraChange).not.toHaveBeenCalled();
    });

    it('gives the position of the open camera', () => {
        expect(setup({ openCamera: 'CAM_B' }).cameras.position).toEqual({ index: 2, total: 3 });
        expect(setup({}).cameras.position).toEqual({ index: 0, total: 3 });
    });

    it('switches to the adjacent selected camera', () => {
        const { cameras, onOpenCameraChange } = setup({ openCamera: 'CAM_C' });

        cameras.switchCamera('next');

        expect(onOpenCameraChange).toHaveBeenCalledWith('CAM_A', 'replace');
    });

    it('allows switching only with more than one selected camera', () => {
        expect(setup({ selectedChannelIds: [2] }).cameras.canSwitch).toBe(false);
        expect(setup({}).cameras.canSwitch).toBe(true);
    });

    it('closes the dialog when the open camera is deselected', () => {
        const { input, onOpenCameraChange } = setup({ openCamera: 'CAM_B' });
        expect(onOpenCameraChange).not.toHaveBeenCalled();

        input.selectedChannelIds = [1, 3];
        flushSync();

        expect(onOpenCameraChange).toHaveBeenCalledWith(undefined, 'replace');
    });

    it('opens the camera of a digit key', () => {
        const { cameras, onOpenCameraChange } = setup({});
        const event = digitEvent('3');

        cameras.handleWindowKeydown(event);

        expect(onOpenCameraChange).toHaveBeenCalledWith('CAM_C', 'push');
        expect(event.defaultPrevented).toBe(true);
    });
});
