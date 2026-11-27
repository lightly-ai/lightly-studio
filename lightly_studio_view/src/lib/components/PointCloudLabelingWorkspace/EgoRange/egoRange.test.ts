import { describe, expect, it } from 'vitest';
import { formatDistance, getFlatDistance, isBeyondRange } from './egoRange';

describe('getFlatDistance', () => {
    it('ignores the height difference', () => {
        expect(getFlatDistance([3, 4, 10], [0, 0, 0])).toBe(5);
    });

    it('measures from the ego position', () => {
        expect(getFlatDistance([13, 4, 0], [10, 0, -2])).toBe(5);
    });
});

describe('isBeyondRange', () => {
    it('keeps a distance equal to the radius within the range', () => {
        expect(isBeyondRange(40, 40)).toBe(false);
    });

    it('marks a distance above the radius as beyond the range', () => {
        expect(isBeyondRange(40.01, 40)).toBe(true);
    });
});

describe('formatDistance', () => {
    it('formats meters with one decimal', () => {
        expect(formatDistance(38.24)).toBe('38.2 m');
        expect(formatDistance(0)).toBe('0.0 m');
    });
});
