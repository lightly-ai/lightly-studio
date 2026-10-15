import type { IntersectionEvent } from '@threlte/extras';
import { Plane, Vector2, Vector3, type Camera, type Object3D, type Raycaster } from 'three';
import type * as Domain from '$lib/components/PointCloudLabelingWorkspace/domain';
import {
    FACE_DEFINITIONS,
    MIN_CUBOID_SIZE,
    computeFaceNormalWorld,
    computeResizedCuboid
} from '../cuboidFaceResize';

interface FaceDragParams {
    event: IntersectionEvent<PointerEvent>;
    face: (typeof FACE_DEFINITIONS)[number];
    annotation: Pick<Domain.CuboidAnnotation, 'center' | 'rotation' | 'size'>;
    camera: Camera;
}

interface FaceDrag {
    face: FaceDragParams['face'];
    faceNormalWorld: Domain.Vector3;
    originalCenter: Domain.Vector3;
    originalSize: Domain.Vector3;
    dragPlane: Plane;
    startPoint: Vector3;
    pointerId: number;
}

export function createFaceDrag({ event, face, annotation, camera }: FaceDragParams): FaceDrag {
    const startPoint = new Vector3(event.point.x, event.point.y, event.point.z);
    const cameraDirection = camera.getWorldDirection(new Vector3());
    return {
        face,
        faceNormalWorld: computeFaceNormalWorld({
            axis: face.axis,
            sign: face.sign,
            rotation: annotation.rotation
        }),
        originalCenter: annotation.center,
        originalSize: annotation.size,
        dragPlane: new Plane().setFromNormalAndCoplanarPoint(cameraDirection, startPoint),
        startPoint,
        pointerId: event.nativeEvent.pointerId
    };
}

interface PointerResizeParams {
    event: PointerEvent;
    canvas: HTMLCanvasElement;
    camera: Camera;
    drag: FaceDrag;
    raycaster: Raycaster;
}

export function computePointerResize({
    event,
    canvas,
    camera,
    drag,
    raycaster
}: PointerResizeParams): ReturnType<typeof computeResizedCuboid> | null {
    const rect = canvas.getBoundingClientRect();
    const pointer = new Vector2(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        -((event.clientY - rect.top) / rect.height) * 2 + 1
    );
    raycaster.setFromCamera(pointer, camera);
    const hitPoint = raycaster.ray.intersectPlane(drag.dragPlane, new Vector3());
    if (!hitPoint) return null;
    const normal = new Vector3(...drag.faceNormalWorld);
    return computeResizedCuboid({
        originalCenter: drag.originalCenter,
        originalSize: drag.originalSize,
        axis: drag.face.axis,
        faceNormalWorld: drag.faceNormalWorld,
        delta: hitPoint.sub(drag.startPoint).dot(normal)
    });
}

interface ResizeTransformParams {
    object: Object3D;
    originalSize: Domain.Vector3;
}

export function readResizeTransform({
    object,
    originalSize
}: ResizeTransformParams): ReturnType<typeof computeResizedCuboid> {
    return {
        center: [object.position.x, object.position.y, object.position.z],
        size: [
            Math.max(originalSize[0] * object.scale.x, MIN_CUBOID_SIZE),
            Math.max(originalSize[1] * object.scale.y, MIN_CUBOID_SIZE),
            Math.max(originalSize[2] * object.scale.z, MIN_CUBOID_SIZE)
        ]
    };
}
