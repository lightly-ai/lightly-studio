import { Vector3 } from 'three';
import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';
import type { CameraMode } from '$lib/components/PointCloudLabelingWorkspace/domain';
import { createCuboidRectangleGeometry, createCuboidWireframeGeometry } from './cuboidGeometry';

/** Local cuboid axis pointing along each object-view direction. */
const DEPTH_AXIS = { top: 2, side: 1, front: 0 } as const;

interface CuboidRenderItem {
    annotation: CuboidAnnotation;
    geometry: ReturnType<typeof createCuboidWireframeGeometry>;
    /** Local axis flattened in an orthographic view, or null for the full cuboid. */
    depthAxis: 0 | 1 | 2 | null;
    headingOrigin: Vector3;
    arrowLength: number;
}

/**
 * Builds the Three.js resources required to render a collection of cuboids.
 *
 * @param cuboids - Annotations to render in the active point-cloud frame.
 * @param cameraMode - Orthographic modes render a single rectangle instead of the 3D wireframe.
 * @returns Render items with local geometry and heading metadata.
 */
export function createCuboidRenderItems(
    cuboids: readonly CuboidAnnotation[],
    cameraMode: CameraMode = 'perspective'
): CuboidRenderItem[] {
    return cuboids.map((annotation) => {
        const depthAxis = cameraMode === 'perspective' ? null : DEPTH_AXIS[cameraMode];
        return {
            annotation,
            depthAxis,
            geometry:
                depthAxis === null
                    ? createCuboidWireframeGeometry(annotation.size)
                    : createCuboidRectangleGeometry(annotation.size, depthAxis),
            headingOrigin: new Vector3(annotation.size[0] / 2, 0, 0),
            arrowLength: Math.max(annotation.size[0] * 0.35, 0.75)
        };
    });
}

/**
 * Releases the GPU resources created for cuboid wireframes.
 *
 * @param items - Render items previously created by {@link createCuboidRenderItems}.
 * @returns Nothing.
 */
export function disposeCuboidRenderItems(items: ReturnType<typeof createCuboidRenderItems>): void {
    items.forEach(({ geometry }) => geometry.dispose());
}
