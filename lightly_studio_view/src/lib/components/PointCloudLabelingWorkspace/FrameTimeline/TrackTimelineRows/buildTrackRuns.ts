import type { SequenceTrackView, TickView } from '$lib/api/lightly_studio_local/types.gen';

/** Consecutive ticks of a track with annotations of one kind, as inclusive tick indices. */
export interface TrackRun {
    startIndex: number;
    endIndex: number;
    /** Whether the annotations were generated, e.g. interpolated, rather than drawn. */
    interpolated: boolean;
}

/**
 * Groups a track's annotations into runs of consecutive ticks of the same kind.
 *
 * A run ends at a tick without an annotation, or where drawn and generated annotations meet.
 * Adjacency follows the ordered tick list, so sparse seq numbers stay contiguous. Annotations
 * whose seq number is not in the tick list are ignored.
 */
export function buildTrackRuns(
    ticks: readonly TickView[],
    annotations: SequenceTrackView['annotations']
): TrackRun[] {
    const indexBySeqNumber = new Map(ticks.map((tick, index) => [tick.seq_number, index]));
    const positioned = annotations
        .flatMap((annotation) => {
            const index = indexBySeqNumber.get(annotation.seq_number);
            return index === undefined ? [] : [{ index, interpolated: annotation.interpolated }];
        })
        .sort((a, b) => a.index - b.index);

    const runs: TrackRun[] = [];
    for (const { index, interpolated } of positioned) {
        const last = runs.at(-1);
        if (last && index === last.endIndex) continue;
        if (last && index === last.endIndex + 1 && interpolated === last.interpolated) {
            last.endIndex = index;
        } else {
            runs.push({ startIndex: index, endIndex: index, interpolated });
        }
    }
    return runs;
}
