import { Quaternion, Vector2, Vector3, type Camera, type Object3D } from 'three';
import type * as Domain from '../../domain';
import { computeCuboidVertices } from '../cuboidGeometry';
import { captureTransformSnapshot } from '../cuboidTransform';

/** Radius of the projected corners, independent of viewport zoom. */
export function getProjectedCuboidRadius(
    size: Domain.Vector3,
    rotation: Quaternion,
    viewDirection: Vector3
): number {
    const corners = computeCuboidVertices([0, 0, 0], size, [
        rotation.x,
        rotation.y,
        rotation.z,
        rotation.w
    ]);
    return Math.sqrt(
        Math.max(...corners.map((corner) => corner.lengthSq() - corner.dot(viewDirection) ** 2))
    );
}

interface RotationDragParams {
    object: Object3D;
    camera: Camera;
    canvas: HTMLCanvasElement;
    event: PointerEvent;
}

export function createRotationDrag({ object, camera, canvas, event }: RotationDragParams) {
    const rect = canvas.getBoundingClientRect();
    const projected = object.getWorldPosition(new Vector3()).project(camera);
    const center = new Vector2(
        rect.left + ((projected.x + 1) * rect.width) / 2,
        rect.top + ((1 - projected.y) * rect.height) / 2
    );
    return {
        object,
        center,
        pointerId: event.pointerId,
        snapshot: captureTransformSnapshot(object),
        start: pointerOffset(event, center),
        axis: camera.getWorldDirection(new Vector3()).negate(),
        worldRotation: object.getWorldQuaternion(new Quaternion()),
        parentInverse:
            object.parent?.getWorldQuaternion(new Quaternion()).invert() ?? new Quaternion()
    };
}

/** Applies a screen-plane rotation while preserving the cuboid's center and size. */
export function applyRotationDrag(
    drag: ReturnType<typeof createRotationDrag>,
    event: PointerEvent
): boolean {
    const offset = pointerOffset(event, drag.center);
    if (offset.lengthSq() < 1 || drag.start.lengthSq() < 1) return false;
    const angle = Math.atan2(drag.start.cross(offset), drag.start.dot(offset));
    drag.object.quaternion
        .copy(drag.parentInverse)
        .multiply(new Quaternion().setFromAxisAngle(drag.axis, angle))
        .multiply(drag.worldRotation);
    return Math.abs(angle) > 1e-6;
}

function pointerOffset(event: PointerEvent, center: Vector2): Vector2 {
    return new Vector2(event.clientX - center.x, center.y - event.clientY);
}
