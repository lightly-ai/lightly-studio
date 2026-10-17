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

/**
 * Choose a drag plane that preserves the resize axis. The plane normal is the
 * component of {@link cameraDirection} perpendicular to {@link faceNormal}, so
 * the plane contains the face-normal direction and pointer movement maps to a
 * nonzero resize delta. When the camera looks along the face normal (within
 * ~6°), the perpendicular component vanishes; we fall back to a plane whose
 * normal is a stable tangent (cross product with world-up, or world-right when
 * the face normal is vertical) so the drag plane still contains the resize axis.
 */
export function computeDragPlane({
    cameraDirection,
    faceNormal,
    startPoint
}: {
    cameraDirection: Vector3;
    faceNormal: Vector3;
    startPoint: Vector3;
}): Plane {
    const NEAR_ZERO = 0.01;
    const perpendicular = cameraDirection
        .clone()
        .addScaledVector(faceNormal, -cameraDirection.dot(faceNormal));
    let planeNormal: Vector3;
    if (perpendicular.lengthSq() > NEAR_ZERO) {
        planeNormal = perpendicular.normalize();
    } else {
        const up = new Vector3(0, 1, 0);
        const tangent = new Vector3().crossVectors(faceNormal, up);
        if (tangent.lengthSq() < NEAR_ZERO) {
            tangent.crossVectors(faceNormal, new Vector3(1, 0, 0));
        }
        planeNormal = tangent.normalize();
    }
    return new Plane().setFromNormalAndCoplanarPoint(planeNormal, startPoint);
}

export function createFaceDrag({ event, face, annotation, camera }: FaceDragParams): FaceDrag {
    const startPoint = new Vector3(event.point.x, event.point.y, event.point.z);
    const cameraDirection = camera.getWorldDirection(new Vector3());
    const faceNormalWorld = computeFaceNormalWorld({
        axis: face.axis,
        sign: face.sign,
        rotation: annotation.rotation
    });
    return {
        face,
        faceNormalWorld,
        originalCenter: annotation.center,
        originalSize: annotation.size,
        dragPlane: computeDragPlane({
            cameraDirection,
            faceNormal: new Vector3(...faceNormalWorld),
            startPoint
        }),
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
