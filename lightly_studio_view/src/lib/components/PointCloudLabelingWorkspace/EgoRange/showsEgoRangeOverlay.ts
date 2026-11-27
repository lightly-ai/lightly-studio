import type { CameraMode } from '../domain';

/** The Side and Front views see the overlay edge-on. */
export function showsEgoRangeOverlay(cameraMode: CameraMode): boolean {
    return cameraMode === 'perspective' || cameraMode === 'top';
}
