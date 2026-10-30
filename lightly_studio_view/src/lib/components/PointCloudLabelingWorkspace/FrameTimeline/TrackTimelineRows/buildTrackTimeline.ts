import type { SequenceTrackView, TickView } from '$lib/api/lightly_studio_local/types.gen';

interface TrackRun {
    startIndex: number;
    endIndex: number;
    interpolated: boolean;
}

/** Use ordered tick positions so sparse sequence numbers do not stretch or collapse a span. */
export function buildTrackTimeline(track: SequenceTrackView, ticks: TickView[]) {
    const positions = new Map(ticks.map((tick, index) => [tick.seq_number, index]));
    const annotations = track.annotations
        .map((annotation) => ({ ...annotation, index: positions.get(annotation.seq_number) }))
        .filter((annotation) => annotation.index !== undefined)
        .sort((a, b) => a.index! - b.index!);
    const runs: TrackRun[] = [];
    for (const annotation of annotations) {
        const index = annotation.index!;
        const last = runs.at(-1);
        if (last && last.endIndex + 1 === index && last.interpolated === annotation.interpolated) {
            last.endIndex = index;
        } else {
            runs.push({
                startIndex: index,
                endIndex: index,
                interpolated: annotation.interpolated
            });
        }
    }
    return { annotations, runs };
}
