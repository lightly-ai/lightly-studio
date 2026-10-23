import { Vector3, type Box3, type OrthographicCamera, type PerspectiveCamera } from 'three';
import type { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { computeCameraPlacement } from './pointCloudUtils';

export function fitCameraToBounds(
    camera: PerspectiveCamera | OrthographicCamera | undefined,
    controls: OrbitControls | undefined,
    bounds: Box3,
    mode: 'perspective' | 'top' | 'side' | 'front' = 'perspective'
): void {
    if (!camera) return;

    if (mode !== 'perspective') {
        fitOrthographicCameraToBounds(camera as OrthographicCamera, controls, bounds, mode);
        return;
    }

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

function fitOrthographicCameraToBounds(
    camera: OrthographicCamera,
    controls: OrbitControls | undefined,
    bounds: Box3,
    mode: 'top' | 'side' | 'front'
): void {
    const center = bounds.getCenter(new Vector3());
    const size = bounds.getSize(new Vector3());
    const projectedWidth = mode === 'side' ? size.y : size.x;
    const projectedHeight = mode === 'top' ? size.y : size.z;
    const extent = Math.max(projectedWidth, projectedHeight, 1);
    const distance = extent * 2;
    const direction = {
        top: [0, 0, 1],
        side: [1, 0, 0],
        front: [0, -1, 0]
    }[mode];

    camera.position.set(
        center.x + direction[0] * distance,
        center.y + direction[1] * distance,
        center.z + direction[2] * distance
    );
    camera.zoom = 1.8 / extent;
    camera.updateProjectionMatrix();
    if (!controls) {
        camera.lookAt(center.x, center.y, center.z);
        return;
    }

    controls.target.copy(center);
    controls.update();
}
