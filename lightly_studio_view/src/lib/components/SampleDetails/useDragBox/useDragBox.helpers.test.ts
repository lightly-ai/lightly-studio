import { describe, expect, it } from 'vitest';
import { boxFromPoints, isDragBox, normalizedPointFromEvent } from './useDragBox.helpers';

describe('useDragBox.helpers', () => {
    it('normalizes and clamps pointer positions to the image', () => {
        const rect = { left: 10, top: 20, width: 100, height: 50 };
        expect(normalizedPointFromEvent({ clientX: 60, clientY: 45 }, rect)).toEqual({
            x: 0.5,
            y: 0.5
        });
        expect(normalizedPointFromEvent({ clientX: 0, clientY: 100 }, rect)).toEqual({
            x: 0,
            y: 1
        });
    });

    it('builds a box from any two corners and ignores tiny drags', () => {
        const box = boxFromPoints({ x: 0.6, y: 0.2 }, { x: 0.1, y: 0.5 });
        expect(box.x).toBeCloseTo(0.1);
        expect(box.y).toBeCloseTo(0.2);
        expect(box.width).toBeCloseTo(0.5);
        expect(box.height).toBeCloseTo(0.3);
        expect(isDragBox(box)).toBe(true);
        expect(isDragBox(boxFromPoints({ x: 0.5, y: 0.5 }, { x: 0.501, y: 0.6 }))).toBe(false);
    });
});
