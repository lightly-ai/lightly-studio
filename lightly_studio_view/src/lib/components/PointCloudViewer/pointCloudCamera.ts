import {
    Box3,
    Quaternion,
    Sphere,
    Vector3,
    type OrthographicCamera,
    type PerspectiveCamera
} from 'three';
import type { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { computeCameraPlacement } from './pointCloudUtils';
import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';

export function fitCameraToBounds(
    camera: PerspectiveCamera | OrthographicCamera | undefined,
    controls: OrbitControls | undefined,
    bounds: Box3,
    mode: 'perspective' | 'top' | 'side' | 'front' = 'perspective',
    viewportAspect = 1
): void {
    if (!camera) return;

    if (mode !== 'perspective') {
        fitOrthographicCameraToBounds(
            camera as OrthographicCamera,
            controls,
            bounds,
            mode,
            viewportAspect
        );
        return;
    }

    const placement = computeCameraPlacement(bounds);
    const perspectiveCamera = camera as PerspectiveCamera;
    const aspect = Number.isFinite(viewportAspect) && viewportAspect > 0 ? viewportAspect : 1;
    const verticalHalfFov = (perspectiveCamera.fov * Math.PI) / 360;
    const horizontalHalfFov = Math.atan(Math.tan(verticalHalfFov) * aspect);
    const fittingHalfFov = Math.min(verticalHalfFov, horizontalHalfFov);
    const sphere = bounds.getBoundingSphere(new Sphere());
    const distance = (Math.max(sphere.radius, 1) / Math.tan(fittingHalfFov)) * 1.1;
    const direction = new Vector3(...placement.position)
        .sub(new Vector3(...placement.target))
        .normalize();
    const position = new Vector3(...placement.target).add(direction.multiplyScalar(distance));
    camera.position.copy(position);
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
    mode: 'top' | 'side' | 'front',
    viewportAspect: number
): void {
    const center = bounds.getCenter(new Vector3());
    const size = bounds.getSize(new Vector3());
    const projectedWidth = mode === 'side' ? size.y : size.x;
    const projectedHeight = mode === 'top' ? size.y : size.z;
    const aspect = Number.isFinite(viewportAspect) && viewportAspect > 0 ? viewportAspect : 1;
    const projectedExtent = Math.max(projectedHeight, projectedWidth / aspect, 1);
    const depthExtent = mode === 'top' ? size.z : mode === 'side' ? size.x : size.y;
    const distance = depthExtent / 2 + projectedExtent * 2;
    const direction = {
        top: [0, 0, 1],
        side: [1, 0, 0],
        front: [0, -1, 0]
    }[mode];

    camera.left = -aspect;
    camera.right = aspect;
    camera.top = 1;
    camera.bottom = -1;
    camera.position.set(
        center.x + direction[0] * distance,
        center.y + direction[1] * distance,
        center.z + direction[2] * distance
    );
    camera.zoom = 1.8 / projectedExtent;
    camera.updateProjectionMatrix();
    if (!controls) {
        camera.lookAt(center.x, center.y, center.z);
        return;
    }

    controls.target.copy(center);
    controls.update();
}

/** Fits an object view in the selected cuboid's local coordinate frame. */
export function fitCameraToCuboid(
    camera: OrthographicCamera,
    controls: OrbitControls,
    cuboid: CuboidAnnotation,
    mode: 'top' | 'side' | 'front',
    aspect: number
): void {
    const halfSize = new Vector3(...cuboid.size).multiplyScalar(0.5);
    // The heading points along local +X: front looks along -X, side along +Y.
    const localMode = mode === 'front' ? 'side' : mode === 'side' ? 'front' : 'top';
    camera.up.set(0, mode === 'top' ? 1 : 0, mode === 'top' ? 0 : 1);
    fitCameraToBounds(
        camera,
        undefined,
        new Box3(halfSize.clone().negate(), halfSize),
        localMode,
        aspect
    );
    const rotation = new Quaternion(...cuboid.rotation);
    camera.position.applyQuaternion(rotation).add(new Vector3(...cuboid.center));
    camera.up.applyQuaternion(rotation);
    const wasDamping = controls.enableDamping;
    controls.enableDamping = false;
    controls.target.set(...cuboid.center);
    controls.update();
    controls.enableDamping = wasDamping;
}
