import { Group, Raycaster, Vector2 } from 'three';
import type { Camera, Ray, WebGLRenderer } from 'three';
import type { CuboidHandle, Vector3 as DomainVector3 } from '$lib/components/PointCloudLabelingWorkspace/domain';

/** Face handle order — index matches the child order inside the face-planes group. */
export const FACE_HANDLES: readonly CuboidHandle[] = [
    'max-x',
    'min-x',
    'max-y',
    'min-y',
    'max-z',
    'min-z'
] as const;

/** Geometry and transform for one face plane. */
export interface FaceConfig {
    readonly handle: CuboidHandle;
    readonly position: [number, number, number];
    /** Euler XYZ angles in radians. */
    readonly euler: [number, number, number];
    /** PlaneGeometry args [width, height] in local pre-rotation space. */
    readonly dims: [number, number];
}

const HALF_PI = Math.PI / 2;

/**
 * Computes the six face plane configs for a cuboid of the given size.
 *
 * Rotation conventions (PlaneGeometry default normal = +Z):
 * - max-x / min-x: Ry(±π/2) → local X→world Z, local Y→world Y
 *   dims[0]=Z extent=size[2], dims[1]=Y extent=size[1]
 * - max-y / min-y: Rx(∓π/2) → local X→world X, local Y→world ∓Z
 *   dims[0]=X extent=size[0], dims[1]=Z extent=size[2]
 * - max-z / min-z: no / π rotation → local X→world X, local Y→world Y
 *   dims[0]=X extent=size[0], dims[1]=Y extent=size[1]
 *
 * @param size - Cuboid full extents [x, y, z] in metres.
 * @returns Array of six face configs in FACE_HANDLES order.
 */
export function computeFaceConfigs(size: DomainVector3): FaceConfig[] {
    const [sx, sy, sz] = size;
    return [
        { handle: 'max-x', position: [sx / 2, 0, 0], euler: [0, HALF_PI, 0], dims: [sz, sy] },
        { handle: 'min-x', position: [-sx / 2, 0, 0], euler: [0, -HALF_PI, 0], dims: [sz, sy] },
        { handle: 'max-y', position: [0, sy / 2, 0], euler: [-HALF_PI, 0, 0], dims: [sx, sz] },
        { handle: 'min-y', position: [0, -sy / 2, 0], euler: [HALF_PI, 0, 0], dims: [sx, sz] },
        { handle: 'max-z', position: [0, 0, sz / 2], euler: [0, 0, 0], dims: [sx, sy] },
        { handle: 'min-z', position: [0, 0, -sz / 2], euler: [Math.PI, 0, 0], dims: [sx, sy] }
    ];
}

/**
 * Returns the highlight opacity for a face plane.
 *
 * @param handle - The face handle to query.
 * @param hoveredHandle - Currently hovered face, or null.
 * @param activeDragHandle - Currently dragged face, or null.
 * @returns 0.4 when dragging, 0.25 when hovered, 0 otherwise.
 */
export function getFaceOpacity(
    handle: CuboidHandle,
    hoveredHandle: CuboidHandle | null,
    activeDragHandle: CuboidHandle | null
): number {
    if (activeDragHandle === handle) return 0.4;
    if (hoveredHandle === handle) return 0.25;
    return 0;
}

/**
 * Creates a world-space ray from a pointer event using the current camera.
 *
 * @param event - Native pointer event.
 * @param camera - Active Three.js camera.
 * @param renderer - WebGL renderer whose canvas the event was fired on.
 * @returns Cloned world-space ray.
 */
export function buildPointerRay(event: PointerEvent, camera: Camera, renderer: WebGLRenderer): Ray {
    const rect = renderer.domElement.getBoundingClientRect();
    const ndc = new Vector2(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        -((event.clientY - rect.top) / rect.height) * 2 + 1
    );
    const raycaster = new Raycaster();
    raycaster.setFromCamera(ndc, camera);
    return raycaster.ray.clone();
}

/**
 * Raycasts the face plane group and returns the closest hit face handle.
 *
 * Children of the group must be in FACE_HANDLES order.
 *
 * @param group - Three.js Group containing only the six face plane meshes.
 * @param event - Native pointer event used for NDC calculation.
 * @param camera - Active Three.js camera.
 * @param renderer - WebGL renderer.
 * @returns The hit face handle, or null if no face was hit.
 */
export function hitFacePlane(
    group: Group,
    event: PointerEvent,
    camera: Camera,
    renderer: WebGLRenderer
): CuboidHandle | null {
    if (group.children.length === 0) return null;
    const raycaster = new Raycaster();
    raycaster.ray.copy(buildPointerRay(event, camera, renderer));
    group.updateWorldMatrix(true, true);
    const hits = raycaster.intersectObjects(group.children, false);
    if (hits.length === 0) return null;
    const index = group.children.indexOf(hits[0].object);
    return index === -1 ? null : FACE_HANDLES[index];
}
