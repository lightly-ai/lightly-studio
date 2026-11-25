import { Quaternion, Vector2, Vector3, type Camera, type Object3D } from 'three';
import { captureTransformSnapshot } from '../cuboidTransform';

interface MoveDragParams {
    object: Object3D;
    camera: Camera;
    canvas: HTMLCanvasElement;
    event: PointerEvent;
}

export function createMoveDrag({ object, camera, canvas, event }: MoveDragParams) {
    const rect = canvas.getBoundingClientRect();
    const depth = object.getWorldPosition(new Vector3()).project(camera).z;
    const origin = new Vector3(0, 0, depth).unproject(camera);
    return {
        object,
        pointerId: event.pointerId,
        snapshot: captureTransformSnapshot(object),
        start: new Vector2(event.clientX, event.clientY),
        // World motion for one pixel of pointer motion to the right and upward.
        right: new Vector3(2 / rect.width, 0, depth).unproject(camera).sub(origin),
        up: new Vector3(0, 2 / rect.height, depth).unproject(camera).sub(origin),
        parentInverse:
            object.parent?.getWorldQuaternion(new Quaternion()).invert() ?? new Quaternion()
    };
}

/** Moves the cuboid in the screen plane so that it follows the pointer. */
export function applyMoveDrag(
    drag: ReturnType<typeof createMoveDrag>,
    event: PointerEvent
): boolean {
    const dx = event.clientX - drag.start.x;
    const dy = drag.start.y - event.clientY;
    const offset = drag.right
        .clone()
        .multiplyScalar(dx)
        .addScaledVector(drag.up, dy)
        .applyQuaternion(drag.parentInverse);
    drag.object.position.copy(drag.snapshot.position).add(offset);
    return dx !== 0 || dy !== 0;
}
