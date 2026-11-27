import { describe, expect, it } from 'vitest';
import { toPolygonInput } from './AnnotationCanvas.helpers';

describe('toPolygonInput', () => {
    it('makes the stroke opaque and gives the fill alpha only to the fill', () => {
        const polygons: Array<Array<[number, number]>> = [
            [
                [0, 0],
                [4, 0],
                [4, 4]
            ]
        ];

        const input = toPolygonInput(polygons, (colorAlpha) => [
            10,
            20,
            30,
            Math.round(colorAlpha * 100)
        ]);

        expect(input).toEqual({
            parts: polygons,
            strokeColor: [10, 20, 30, 255],
            fillColor: [10, 20, 30, 40]
        });
        expect(input.parts[0]).not.toBe(polygons[0]);
    });
});
