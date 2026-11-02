import { getContext, setContext } from 'svelte';

const CAMERA_RGB_KEY = Symbol('camera-rgb-colors');

/**
 * Provides computed camera RGB colors to the scene subtree.
 * Called in PointCloudWorkspaceMainColumn; consumed in PointCloudPoints.
 */
export function provideCameraRgbColors(getColors: () => Float32Array | null): void {
    setContext(CAMERA_RGB_KEY, getColors);
}

/**
 * Returns the camera RGB color getter from context, or a no-op getter if not provided.
 * Safe to call outside the workspace (returns null).
 */
export function getCameraRgbColors(): () => Float32Array | null {
    return getContext<(() => Float32Array | null) | undefined>(CAMERA_RGB_KEY) ?? (() => null);
}
