import * as THREE from 'three';

type SceneCamera = THREE.PerspectiveCamera | THREE.OrthographicCamera;

/** Resolves pan axes in the projection plane or the perspective ground plane. */
export function getMovementAxes(
    camera: SceneCamera,
    position: THREE.Vector3,
    center: THREE.Vector3
) {
    if (camera instanceof THREE.OrthographicCamera) {
        return {
            direction: new THREE.Vector3(0, 1, 0).applyQuaternion(camera.quaternion),
            right: new THREE.Vector3(1, 0, 0).applyQuaternion(camera.quaternion)
        };
    }
    const direction = center.clone().sub(position);
    direction.z = 0;
    direction.normalize();
    const right = direction
        .clone()
        .cross(new THREE.Vector3(0, 0, 1))
        .normalize();
    return { direction, right };
}

/** Uses visible height for orthographic movement and target distance for perspective movement. */
export function getNavigationDistance(camera: SceneCamera, center: THREE.Vector3): number {
    return camera instanceof THREE.OrthographicCamera
        ? (camera.top - camera.bottom) / camera.zoom
        : camera.position.distanceTo(center);
}

/** Rotates a camera position around its current target. */
export function rotatePosition(position: THREE.Vector3, center: THREE.Vector3, angle: number) {
    const spherical = new THREE.Spherical().setFromVector3(position.clone().sub(center));
    spherical.theta += angle;
    position.copy(center).add(new THREE.Vector3().setFromSpherical(spherical));
}
