import { describe, expect, it } from 'vitest';
import { formatTimestampS, getUniformTimestamps } from './captionSegmentRibbon.helpers';

describe('getUniformTimestamps', () => {
    it('spreads samples evenly including both interval ends', () => {
        expect(getUniformTimestamps({ startTimeS: 10, endTimeS: 20, sampleCount: 5 })).toEqual([
            10, 12.5, 15, 17.5, 20
        ]);
    });

    it('places a single sample in the middle of the interval', () => {
        expect(getUniformTimestamps({ startTimeS: 4, endTimeS: 8, sampleCount: 1 })).toEqual([6]);
    });

    it('repeats the timestamp for a zero-length interval', () => {
        expect(getUniformTimestamps({ startTimeS: 3, endTimeS: 3, sampleCount: 3 })).toEqual([
            3, 3, 3
        ]);
    });

    it('normalizes reversed and negative bounds', () => {
        expect(getUniformTimestamps({ startTimeS: 20, endTimeS: 10, sampleCount: 3 })).toEqual([
            10, 15, 20
        ]);
        expect(getUniformTimestamps({ startTimeS: -5, endTimeS: 2, sampleCount: 3 })).toEqual([
            0, 1, 2
        ]);
    });

    it('returns nothing when no samples are requested', () => {
        expect(getUniformTimestamps({ startTimeS: 0, endTimeS: 10, sampleCount: 0 })).toEqual([]);
    });
});

describe('formatTimestampS', () => {
    it('formats seconds as minutes and one decimal', () => {
        expect(formatTimestampS(0)).toBe('0:00.0');
        expect(formatTimestampS(65.42)).toBe('1:05.4');
        expect(formatTimestampS(-1)).toBe('0:00.0');
    });
});
