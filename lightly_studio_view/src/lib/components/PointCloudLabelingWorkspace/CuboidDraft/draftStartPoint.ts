import { Plane, Raycaster, Vector2, Vector3 as ThreeVector3, type Camera } from 'three';
import type { PointBatch } from '$lib/components/PointCloudViewer';
import type { CameraMode, Vector3 } from '$lib/components/PointCloudLabelingWorkspace/domain';
import type { ScreenPoint } from './cuboidDraft';
import { estimateGroundHeight } from './fitCuboidToPoints';
import { pickFrontPoint } from './pickFrontPoint';

/** Ground search radius around a top-view click. */
const TOP_VIEW_GROUND_RADIUS = 1.5;

interface DraftStartParams {
    cameraMode: CameraMode;
    /** Pointer hit on the creation plane. */
    sceneHit: Vector3;
    batch: PointBatch | undefined;
    camera: Camera;
    viewport: DOMRect;
    pointer: ScreenPoint;
}

/**
 * First point of a draft: at the height of the point under the pointer in the 3D view, on the
 * local ground in the top view, else on the creation plane.
 */
export function getDraftStartPoint(params: DraftStartParams): Vector3 {
    const { cameraMode, sceneHit, batch } = params;
    if (cameraMode === 'perspective') return getPerspectiveStartPoint(params);
    if (cameraMode !== 'top') return sceneHit;
    const [x, y] = sceneHit;
    const groundZ = estimateGroundHeight(batch, x, y, TOP_VIEW_GROUND_RADIUS);
    return groundZ === null ? sceneHit : [x, y, groundZ];
}

/** Pointer ray hit at the height of the picked point, so the start stays under the pointer. */
function getPerspectiveStartPoint({
    sceneHit,
    batch,
    camera,
    viewport,
    pointer
}: DraftStartParams): Vector3 {
    const picked = pickFrontPoint(batch, camera, viewport, pointer);
    if (!picked) return sceneHit;
    const ndc = new Vector2(
        ((pointer.x - viewport.left) / viewport.width) * 2 - 1,
        1 - ((pointer.y - viewport.top) / viewport.height) * 2
    );
    const raycaster = new Raycaster();
    raycaster.setFromCamera(ndc, camera);
    const plane = new Plane(new ThreeVector3(0, 0, 1), -picked[2]);
    const hit = raycaster.ray.intersectPlane(plane, new ThreeVector3());
    return hit ? [hit.x, hit.y, hit.z] : picked;
}
