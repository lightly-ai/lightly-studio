import { describe, expect, it } from 'vitest';
import { pickSmallestFromIntersections } from './cuboidSelection';

describe('pickSmallestFromIntersections', () => {
    it('returns null when there are no intersections', () => {
        expect(pickSmallestFromIntersections([])).toBeNull();
    });

    it('returns the annotation ID of the only intersected cuboid', () => {
        expect(pickSmallestFromIntersections([{ annotationId: 'cuboid-1', volume: 8 }])).toBe(
            'cuboid-1'
        );
    });

    it('returns the smallest-volume cuboid when multiple cuboids are hit', () => {
        expect(
            pickSmallestFromIntersections([
                { annotationId: 'outer', volume: 100 },
                { annotationId: 'inner', volume: 4 }
            ])
        ).toBe('inner');
    });

    it('returns the smallest-volume cuboid regardless of intersection order', () => {
        expect(
            pickSmallestFromIntersections([
                { annotationId: 'inner', volume: 4 },
                { annotationId: 'outer', volume: 100 }
            ])
        ).toBe('inner');
    });
});
