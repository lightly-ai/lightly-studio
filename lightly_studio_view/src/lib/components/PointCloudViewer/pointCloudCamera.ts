import type { Box3, PerspectiveCamera } from 'three';
import type { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { computeCameraPlacement } from './pointCloudUtils';

export function fitCameraToBounds(
    camera: PerspectiveCamera | undefined,
    controls: OrbitControls | undefined,
    bounds: Box3
): void {
    if (!camera) return;

    const placement = computeCameraPlacement(bounds);
    camera.position.set(...placement.position);
    if (!controls) {
        camera.lookAt(...placement.target);
        return;
    }

    const wasDamping = controls.enableDamping;
    controls.enableDamping = false;
    controls.target.set(...placement.target);
    controls.update();
    controls.enableDamping = wasDamping;
}
