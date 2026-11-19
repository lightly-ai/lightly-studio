import type { TickView } from '$lib/api/lightly_studio_local/types.gen';

/** Consecutive tagged ticks, as inclusive tick indices. */
export interface TagRun {
    startIndex: number;
    endIndex: number;
}

/**
 * Groups the tagged ticks of one tag into runs of consecutive ticks.
 *
 * Adjacency follows the ordered tick list, so sparse seq numbers stay contiguous. Seq numbers
 * that are not in the tick list are ignored.
 */
export function buildTagRuns(ticks: readonly TickView[], seqNumbers: readonly number[]): TagRun[] {
    const indexBySeqNumber = new Map(ticks.map((tick, index) => [tick.seq_number, index]));
    const indices = seqNumbers
        .flatMap((seqNumber) => indexBySeqNumber.get(seqNumber) ?? [])
        .sort((a, b) => a - b);

    const runs: TagRun[] = [];
    for (const index of indices) {
        const last = runs.at(-1);
        if (last && index <= last.endIndex + 1) {
            last.endIndex = Math.max(last.endIndex, index);
        } else {
            runs.push({ startIndex: index, endIndex: index });
        }
    }
    return runs;
}
