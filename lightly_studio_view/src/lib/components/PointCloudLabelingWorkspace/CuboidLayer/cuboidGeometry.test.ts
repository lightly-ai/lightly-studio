import { describe, expect, it } from 'vitest';
import { computeCuboidVertices, createCuboidWireframeGeometry } from './cuboidGeometry';

describe('cuboidGeometry', () => {
    it('computes world-space vertices from centre, size, and rotation', () => {
        const vertices = computeCuboidVertices([10, -2, 1], [4, 2, 2], [0, 0, 0, 1]);

        expect(vertices.map((vertex) => vertex.toArray())).toEqual([
            [8, -3, 0],
            [12, -3, 0],
            [8, -1, 0],
            [12, -1, 0],
            [8, -3, 2],
            [12, -3, 2],
            [8, -1, 2],
            [12, -1, 2]
        ]);
    });

    it('creates twelve edge line segments from the local cuboid vertices', () => {
        const geometry = createCuboidWireframeGeometry([4, 2, 2]);
        const position = geometry.getAttribute('position');

        expect(position.count).toBe(24);
        expect(position.array).toEqual(expect.any(Float32Array));
        expect(geometry.boundingSphere).not.toBeNull();

        geometry.dispose();
    });

    it('preserves all twelve edges', () => {
        const geometry = createCuboidWireframeGeometry([4, 2, 6]);
        const position = geometry.getAttribute('position');
        const edges = new Set<string>();

        try {
            for (let index = 0; index < position.count; index += 2) {
                const start = [position.getX(index), position.getY(index), position.getZ(index)];
                const end = [
                    position.getX(index + 1),
                    position.getY(index + 1),
                    position.getZ(index + 1)
                ];
                const segment = [start.join(','), end.join(',')].sort().join(':');
                edges.add(segment);
            }
            expect(edges.size).toBe(12);
        } finally {
            geometry.dispose();
        }
    });
});

