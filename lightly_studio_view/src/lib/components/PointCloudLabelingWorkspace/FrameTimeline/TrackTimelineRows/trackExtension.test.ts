import { describe, expect, it } from 'vitest';
import type { TickView } from '$lib/api/lightly_studio_local/types.gen';
import { getTrackExtent, proposeExtent, tickIndexAt, toSeqNumberRange } from './trackExtension';

const ticks: TickView[] = [10, 11, 12, 13, 14].map((seq_number) => ({
    seq_number,
    timestamp_ns: seq_number
}));
const extent = { first: 1, last: 2 };

describe('trackExtension', () => {
    it('reads the extent from the first and last run', () => {
        expect(getTrackExtent([])).toBeNull();
        expect(
            getTrackExtent([
                { startIndex: 1, endIndex: 1, interpolated: false },
                { startIndex: 3, endIndex: 4, interpolated: true }
            ])
        ).toEqual({ first: 1, last: 4 });
    });

    it('snaps the pointer to a tick and clamps to the bar', () => {
        const bar = { left: 100, width: 500 };
        expect(tickIndexAt(100, bar, 5)).toBe(0);
        expect(tickIndexAt(350, bar, 5)).toBe(2);
        expect(tickIndexAt(9999, bar, 5)).toBe(4);
        expect(tickIndexAt(0, bar, 5)).toBe(0);
    });

    it('only proposes outward changes', () => {
        expect(proposeExtent(extent, 'start', 0)).toEqual({ first: 0, last: 2 });
        expect(proposeExtent(extent, 'start', 2)).toEqual(extent);
        expect(proposeExtent(extent, 'end', 4)).toEqual({ first: 1, last: 4 });
        expect(proposeExtent(extent, 'end', 1)).toEqual(extent);
    });

    it('maps a proposal to seq numbers, or null when nothing changes', () => {
        expect(toSeqNumberRange(ticks, extent, { first: 0, last: 4 })).toEqual({
            start: 10,
            end: 14
        });
        expect(toSeqNumberRange(ticks, extent, extent)).toBeNull();
    });
});
