import { describe, expect, it } from 'vitest';
import { getEgoDistanceLine } from './getEgoDistanceLine';

describe('getEgoDistanceLine', () => {
    it('draws a line from the ego origin to the target', () => {
        const line = getEgoDistanceLine([10, 0, -2], [13, 4, 1]);

        expect(line.start).toEqual([10, 0, -2]);
        expect(line.end).toEqual([13, 4, 1]);
    });

    it('puts the label at the middle of the line', () => {
        expect(getEgoDistanceLine([10, 0, -2], [13, 4, 1]).labelPosition).toEqual([11.5, 2, -0.5]);
    });

    it('measures the flat distance', () => {
        expect(getEgoDistanceLine([10, 0, -2], [13, 4, 1]).meters).toBe(5);
    });

    it('gives the drawn length of the line for the dashes', () => {
        expect(getEgoDistanceLine([10, 0, -2], [13, 4, 1]).length).toBeCloseTo(Math.sqrt(34));
    });
});
