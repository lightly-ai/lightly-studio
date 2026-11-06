import { describe, expect, it } from 'vitest';
import { getReadableTextColor } from './ClassPredictionStrip.helpers';

describe('getReadableTextColor', () => {
    it('returns black on light colors and white on dark colors', () => {
        expect(getReadableTextColor('rgba(250, 220, 90, 1)')).toBe('black');
        expect(getReadableTextColor('rgba(0, 221, 255, 1)')).toBe('black');
        expect(getReadableTextColor('rgba(40, 30, 120, 1)')).toBe('white');
        expect(getReadableTextColor('rgba(200, 0, 40, 1)')).toBe('white');
    });
});
