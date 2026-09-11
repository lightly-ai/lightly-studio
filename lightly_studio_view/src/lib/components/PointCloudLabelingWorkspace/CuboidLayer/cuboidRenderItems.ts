import { Vector3 } from 'three';
import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';
import { createCuboidWireframeGeometry } from './cuboidGeometry';

interface CuboidRenderItem {
    annotation: CuboidAnnotation;
    geometry: ReturnType<typeof createCuboidWireframeGeometry>;
    headingOrigin: Vector3;
    arrowLength: number;
}

/**
 * Builds the Three.js resources required to render a collection of cuboids.
 *
 * @param cuboids - Annotations to render in the active point-cloud frame.
 * @returns Render items with local geometry and heading metadata.
 */
export function createCuboidRenderItems(cuboids: readonly CuboidAnnotation[]): CuboidRenderItem[] {
    return cuboids.map((annotation) => ({
        annotation,
        geometry: createCuboidWireframeGeometry(annotation.size),
        headingOrigin: new Vector3(annotation.size[0] / 2, 0, 0),
        arrowLength: Math.max(annotation.size[0] * 0.35, 0.75)
    }));
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
