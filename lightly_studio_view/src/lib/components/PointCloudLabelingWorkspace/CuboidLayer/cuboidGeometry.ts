import { BufferAttribute, BufferGeometry, Quaternion, Vector3 } from 'three';
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
    const [width, height, depth] = size;

    const hx = width / 2;
    const hy = height / 2;
    const hz = depth / 2;

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
export function createCuboidWireframeGeometry(size: DomainVector3): BufferGeometry {
    const vertices = computeCuboidVertices([0, 0, 0], size, [0, 0, 0, 1]);
    const positions = new Float32Array(EDGE_INDICES.length * 3);

    EDGE_INDICES.forEach((vertexIndex, index) => {
        positions.set(vertices[vertexIndex].toArray(), index * 3);
    });

    const geometry = new BufferGeometry();
    geometry.setAttribute('position', new BufferAttribute(positions, 3));
    geometry.computeBoundingSphere();
    return geometry;
}
