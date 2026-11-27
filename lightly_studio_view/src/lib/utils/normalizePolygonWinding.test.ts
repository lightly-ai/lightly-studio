import { describe, expect, it } from 'vitest';
import { normalizePolygonWinding, type PolygonPart } from './normalizePolygonWinding';

describe('normalizePolygonWinding', () => {
    it('reverses a part wound against the others', () => {
        const positive: PolygonPart = [
            [0, 0],
            [4, 0],
            [4, 4],
            [0, 4]
        ];
        const negative: PolygonPart = [
            [2, 2],
            [2, 6],
            [6, 6],
            [6, 2]
        ];
        expect(normalizePolygonWinding([positive, negative])).toEqual([
            positive,
            [
                [6, 2],
                [6, 6],
                [2, 6],
                [2, 2]
            ]
        ]);
    });

    it('does not mutate the input', () => {
        const parts: PolygonPart[] = [
            [
                [0, 0],
                [0, 4],
                [4, 4]
            ]
        ];
        const copy = structuredClone(parts);
        normalizePolygonWinding(parts);
        expect(parts).toEqual(copy);
    });
});
