import { describe, expect, it, vi } from 'vitest';
import { useOpenCameraState } from './useOpenCameraState.svelte';

describe('useOpenCameraState', () => {
    it('reports the open camera to a host that controls it', () => {
        const onOpenCameraChange = vi.fn();
        const state = useOpenCameraState(() => ({ openCamera: 'CAM_A', onOpenCameraChange }));

        state.setOpenCamera('CAM_B', 'replace');

        expect(onOpenCameraChange).toHaveBeenCalledWith('CAM_B', 'replace');
        expect(state.openCamera).toBe('CAM_A');
    });

    it('keeps the open camera itself without a host callback', () => {
        const state = useOpenCameraState(() => ({ openCamera: 'CAM_A' }));
        expect(state.openCamera).toBeUndefined();

        state.setOpenCamera('CAM_B', 'push');
        expect(state.openCamera).toBe('CAM_B');

        state.setOpenCamera(undefined, 'replace');
        expect(state.openCamera).toBeUndefined();
    });
});
