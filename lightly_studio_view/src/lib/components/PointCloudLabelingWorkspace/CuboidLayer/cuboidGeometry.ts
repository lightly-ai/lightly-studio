import { Quaternion, Vector3 } from 'three';
import { LineSegmentsGeometry } from 'three/examples/jsm/lines/LineSegmentsGeometry.js';
import type { Quaternion as DomainQuaternion, Vector3 as DomainVector3 } from '../domain';

// Vertices are ordered by x, then y, then z; each face perimeter is 0 → 1 → 3 → 2.
const EDGE_INDICES = [0, 1, 1, 3, 3, 2, 2, 0, 4, 5, 5, 7, 7, 6, 6, 4, 0, 4, 1, 5, 2, 6, 3, 7];

/**
 * Computes the eight world-space vertices of a cuboid.
 *
 * @param center - Cuboid centre in the canonical coordinate frame.
 * @param size - Full local-axis extents in metres.
 * @param rotation - Unit quaternion in xyzw order.
 * @returns Cuboid vertices in a stable bottom-to-top, min-to-max order.
 */
export function computeCuboidVertices(
    center: DomainVector3,
    size: DomainVector3,
    rotation: DomainQuaternion
): Vector3[] {
    const [cx, cy, cz] = center;
    const [length, width, height] = size;

    const hx = length / 2;
    const hy = width / 2;
    const hz = height / 2;

    const orientation = new Quaternion(...rotation);
    const centerVector = new Vector3(cx, cy, cz);

    const vertices: Vector3[] = [];

    for (const z of [-hz, hz]) {
        for (const y of [-hy, hy]) {
            for (const x of [-hx, hx]) {
                vertices.push(new Vector3(x, y, z).applyQuaternion(orientation).add(centerVector));
            }
        }
    }

    return vertices;
}

/**
 * Creates the twelve wireframe edges of a cuboid.
 *
 * @param size - Full local-axis extents in metres.
 * @returns Disposable Three.js line geometry centred at the origin.
 */
export function createCuboidWireframeGeometry(size: DomainVector3): LineSegmentsGeometry {
    const vertices = computeCuboidVertices([0, 0, 0], size, [0, 0, 0, 1]);
    const positions = new Float32Array(EDGE_INDICES.length * 3);

    EDGE_INDICES.forEach((vertexIndex, index) => {
        positions.set(vertices[vertexIndex].toArray(), index * 3);
    });

    const geometry = new LineSegmentsGeometry();
    geometry.setPositions(positions);
    return geometry;
}

/**
 * Creates the four edges of the cuboid cross-section perpendicular to one local axis.
 *
 * @param size - Full local-axis extents in metres.
 * @param depthAxis - Local axis (0 = x, 1 = y, 2 = z) that points along the view direction.
 * @returns Disposable Three.js line geometry of a rectangle centred at the origin.
 */
export function createCuboidRectangleGeometry(
    size: DomainVector3,
    depthAxis: 0 | 1 | 2
): LineSegmentsGeometry {
    const [a, b] = ([0, 1, 2] as const).filter((axis) => axis !== depthAxis);
    const corners = [
        [-1, -1],
        [1, -1],
        [1, 1],
        [-1, 1]
    ].map(([u, v]) => {
        const point = [0, 0, 0];
        point[a] = (u * size[a]) / 2;
        point[b] = (v * size[b]) / 2;
        return point;
    });
    const positions = new Float32Array(
        corners.flatMap((corner, index) => [...corner, ...corners[(index + 1) % 4]])
    );

    const geometry = new LineSegmentsGeometry();
    geometry.setPositions(positions);
    return geometry;
}
