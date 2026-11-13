import { MathUtils, Matrix4, Ray, Vector3 } from 'three';
import type { Camera, Object3D, Points } from 'three';
import type { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

/** Slope of the cone around the view axis whose points give the view depth. */
const VIEW_CONE_SLOPE = Math.tan(MathUtils.degToRad(3));

/** Shortest distance to the orbit target. Zooming and panning stall when the target is closer. */
const MIN_TARGET_DISTANCE = 1;

/** Fewest points that make a surface. Fewer points at one depth are stray points. */
const MIN_SURFACE_POINTS = 5;

/** Depth range of one surface, as a fraction of its depth. */
const SURFACE_DEPTH_FRACTION = 0.1;

/**
 * Find the distance from the camera to the points at the center of the view.
 *
 * The result is the depth of the nearest surface in a narrow cone around the view axis.
 * An object in front of the background sets the depth, also when the background has more
 * points. One stray point between the camera and the scene does not set the depth.
 *
 * @returns The depth, or undefined when no point is at the center of the view.
 */
export function findViewDepth(camera: Camera, scene: Object3D): number | undefined {
    const viewRay = new Ray(
        camera.getWorldPosition(new Vector3()),
        camera.getWorldDirection(new Vector3())
    );
    const depths: number[] = [];
    scene.traverseVisible((object) => {
        if ('isPoints' in object) collectConeDepths(object as Points, viewRay, depths);
    });
    if (depths.length === 0) return undefined;
    return findNearestSurfaceDepth(depths.sort((a, b) => a - b));
}

/**
 * Return the median depth of the nearest group of points that is a surface.
 *
 * @returns The median of all depths when no group has enough points.
 */
function findNearestSurfaceDepth(sortedDepths: readonly number[]): number {
    let end = 0;
    for (let start = 0; start < sortedDepths.length; start++) {
        const surfaceEnd = sortedDepths[start] * (1 + SURFACE_DEPTH_FRACTION);
        end = Math.max(end, start);
        while (end < sortedDepths.length && sortedDepths[end] <= surfaceEnd) end++;
        const isSurface = end - start >= MIN_SURFACE_POINTS;
        if (isSurface) return sortedDepths[(start + end - 1) >> 1];
    }
    return sortedDepths[sortedDepths.length >> 1];
}

/** Append the depth of each point of the point cloud that lies in the cone around the ray. */
function collectConeDepths(pointCloud: Points, viewRay: Ray, depths: number[]): void {
    const positions = pointCloud.geometry.getAttribute('position');
    if (!positions) return;
    const { origin, direction } = viewRay
        .clone()
        .applyMatrix4(new Matrix4().copy(pointCloud.matrixWorld).invert());
    const count = Math.min(positions.count, pointCloud.geometry.drawRange.count);
    const { array, itemSize } = positions;
    for (let i = 0; i < count; i++) {
        const x = array[i * itemSize] - origin.x;
        const y = array[i * itemSize + 1] - origin.y;
        const z = array[i * itemSize + 2] - origin.z;
        const depth = x * direction.x + y * direction.y + z * direction.z;
        if (depth <= 0) continue;
        const axisDistanceSquared = x * x + y * y + z * z - depth * depth;
        if (axisDistanceSquared <= (depth * VIEW_CONE_SLOPE) ** 2) depths.push(depth);
    }
}

/**
 * Keep the orbit target on the points at the center of the view.
 *
 * Before each gesture, the target moves along the view axis, which does not change the
 * view. The camera then rotates around the part of the scene that it looks at, and the
 * zoom and pan speeds follow the distance to that part.
 *
 * @returns `anchor`, for navigation that does not start a gesture of the controls, and
 * `dispose`, which stops the anchoring.
 */
export function createOrbitTargetAnchor(controls: OrbitControls, scene: Object3D) {
    const camera = controls.object;
    const forward = new Vector3();

    function anchor() {
        const depth = findViewDepth(camera, scene) ?? camera.position.distanceTo(controls.target);
        camera.getWorldDirection(forward);
        controls.target
            .copy(camera.position)
            .addScaledVector(forward, Math.max(depth, MIN_TARGET_DISTANCE));
    }

    controls.addEventListener('start', anchor);
    return { anchor, dispose: () => controls.removeEventListener('start', anchor) };
}
