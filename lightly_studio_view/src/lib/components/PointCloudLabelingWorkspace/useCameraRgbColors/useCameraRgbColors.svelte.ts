import type { ColorMode } from '$lib/components/PointCloudViewer';
import type { PointBatch } from '$lib/components/PointCloudViewer/types';
import { createCameraRgbColorComputer, type CameraPair } from './createCameraRgbColorComputer';

interface UseCameraRgbColorsParams {
    getBatch: () => PointBatch | undefined;
    getColorMode: () => ColorMode;
    getCameraPairs: () => CameraPair[];
}

/**
 * Computes per-point RGB colors by back-projecting camera images onto the point cloud, off the
 * main thread. Only active when colorMode is 'camera-rgb'; otherwise exposes `null` so the
 * viewer falls back to its neutral color.
 */
export function useCameraRgbColors(params: UseCameraRgbColorsParams) {
    let colors = $state<Float32Array | null>(null);
    const computer = createCameraRgbColorComputer({ onColors: (next) => (colors = next) });

    $effect(() => {
        const batch = params.getColorMode() === 'camera-rgb' ? params.getBatch() : undefined;
        computer.request(batch, params.getCameraPairs());
    });

    $effect(() => () => computer.dispose());

    return {
        get colors() {
            return colors;
        }
    };
}
