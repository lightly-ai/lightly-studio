import { describe, expect, it } from 'vitest';
import { buildTrackRuns } from './buildTrackRuns';

const ticks = [0, 1, 2, 5, 6, 7].map((seq_number) => ({ seq_number, timestamp_ns: null }));

function annotations(seqNumbers: number[], generated: number[] = []) {
    return seqNumbers.map((seq_number) => ({
        seq_number,
        annotation_id: `annotation-${seq_number}`,
        annotation_source_id: 'source',
        frame_id: 'odom',
        interpolated: generated.includes(seq_number)
    }));
}

describe('buildTrackRuns', () => {
    it('groups consecutive ticks and keeps gaps', () => {
        expect(buildTrackRuns(ticks, annotations([0, 1, 6, 7]))).toEqual([
            { startIndex: 0, endIndex: 1, interpolated: false },
            { startIndex: 4, endIndex: 5, interpolated: false }
        ]);
    });

    it('splits where drawn and generated annotations meet', () => {
        expect(buildTrackRuns(ticks, annotations([0, 1, 2, 5, 6], [1, 2]))).toEqual([
            { startIndex: 0, endIndex: 0, interpolated: false },
            { startIndex: 1, endIndex: 2, interpolated: true },
            { startIndex: 3, endIndex: 4, interpolated: false }
        ]);
    });

    it('treats sparse seq numbers that are adjacent in the tick list as consecutive', () => {
        expect(buildTrackRuns(ticks, annotations([2, 5]))).toEqual([
            { startIndex: 2, endIndex: 3, interpolated: false }
        ]);
    });

    it('ignores annotations outside the tick list and returns no runs without annotations', () => {
        expect(buildTrackRuns(ticks, annotations([3]))).toEqual([]);
        expect(buildTrackRuns(ticks, [])).toEqual([]);
    });
});
