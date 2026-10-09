import { describe, expect, it } from 'vitest';
import { computeCuboidVertices, createCuboidWireframeGeometry } from './cuboidGeometry';

describe('cuboidGeometry', () => {
    it('computes world-space vertices from centre, size, and rotation', () => {
        // 180° around z: x → -x, y → -y, z → z.
        const vertices = computeCuboidVertices([10, -2, 1], [4, 2, 2], [0, 0, 1, 0]);

        expect(vertices.map((vertex) => vertex.toArray())).toEqual([
            [12, -1, 0],
            [8, -1, 0],
            [12, -3, 0],
            [8, -3, 0],
            [12, -1, 2],
            [8, -1, 2],
            [12, -3, 2],
            [8, -3, 2]
        ]);
    });

    it('creates twelve edge line segments from the local cuboid vertices', () => {
        const geometry = createCuboidWireframeGeometry([4, 2, 2]);
        const instanceStart = geometry.getAttribute('instanceStart');

        expect(instanceStart.count).toBe(12);
        expect(geometry.boundingSphere).not.toBeNull();

        geometry.dispose();
    });

    it('preserves all twelve edges', () => {
        const geometry = createCuboidWireframeGeometry([4, 2, 6]);
        const instanceStart = geometry.getAttribute('instanceStart');
        const instanceEnd = geometry.getAttribute('instanceEnd');
        const edges = new Set<string>();

        try {
            for (let i = 0; i < instanceStart.count; i++) {
                const start = [instanceStart.getX(i), instanceStart.getY(i), instanceStart.getZ(i)];
                const end = [instanceEnd.getX(i), instanceEnd.getY(i), instanceEnd.getZ(i)];
                const segment = [start.join(','), end.join(',')].sort().join(':');
                edges.add(segment);
            }
            expect(edges.size).toBe(12);
        } finally {
            geometry.dispose();
        }
    });
});
