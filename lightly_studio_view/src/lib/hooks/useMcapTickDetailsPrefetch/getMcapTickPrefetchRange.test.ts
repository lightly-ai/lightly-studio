import { describe, expect, it } from 'vitest';
import { getMcapTickPrefetchRange } from './getMcapTickPrefetchRange';

describe('getMcapTickPrefetchRange', () => {
    it('buffers the neighbors needed by accumulated frames, clamping at sequence boundaries', () => {
        expect(
            getMcapTickPrefetchRange({
                activeIndex: 5,
                tickCount: 20,
                prefetchTickCount: 3,
                accumulationRadius: 2
            })
        ).toEqual([{ startIndex: 3, endIndex: 9 }]);
        expect(
            getMcapTickPrefetchRange({
                activeIndex: 1,
                tickCount: 5,
                prefetchTickCount: 3,
                accumulationRadius: 2
            })
        ).toEqual([{ startIndex: 0, endIndex: 4 }]);
    });
    it('starts at the active tick and looks ahead by the configured count', () => {
        expect(
            getMcapTickPrefetchRange({ activeIndex: 3, tickCount: 20, prefetchTickCount: 5 })
        ).toEqual([{ startIndex: 3, endIndex: 7 }]);
    });

    it('does not go past the end of the sequence', () => {
        expect(
            getMcapTickPrefetchRange({ activeIndex: 8, tickCount: 10, prefetchTickCount: 5 })
        ).toEqual([{ startIndex: 8, endIndex: 9 }]);
    });

    it('returns no range when the active tick is not available', () => {
        expect(
            getMcapTickPrefetchRange({ activeIndex: -1, tickCount: 10, prefetchTickCount: 5 })
        ).toEqual([]);
    });
});
