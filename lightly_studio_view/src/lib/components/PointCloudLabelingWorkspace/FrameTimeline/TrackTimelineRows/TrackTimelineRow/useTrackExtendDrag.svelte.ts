import type { TickView } from '$lib/api/lightly_studio_local/types.gen';
import { proposeExtent, tickIndexAt, toSeqNumberRange, type ExtendEdge } from '../trackExtension';

interface Extent {
    first: number;
    last: number;
}

interface Params {
    getTicks: () => TickView[];
    getExtent: () => Extent | null;
    getBar: () => HTMLElement | null;
    /** Called when a drag begins, e.g. to pause playback. */
    onStart: () => void;
    /** Called when a drag ends, whether or not it changed anything. */
    onEnd: () => void;
    /** Called on release with the tick numbers the track should now cover. */
    onCommit: (range: { start: number; end: number }) => void;
}

/** Drags a track range handle, snapping to ticks and previewing the new coverage. */
export function useTrackExtendDrag({
    getTicks,
    getExtent,
    getBar,
    onStart,
    onEnd,
    onCommit
}: Params) {
    let edge = $state<ExtendEdge | null>(null);
    let proposed = $state<Extent | null>(null);

    function start(event: PointerEvent, nextEdge: ExtendEdge) {
        const extent = getExtent();
        if (!extent || edge) return;
        event.preventDefault();
        (event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId);
        edge = nextEdge;
        proposed = extent;
        onStart();
    }

    function move(event: PointerEvent) {
        const extent = getExtent();
        const bar = getBar();
        if (!edge || !extent || !bar) return;
        const rect = bar.getBoundingClientRect();
        proposed = proposeExtent(extent, edge, tickIndexAt(event.clientX, rect, getTicks().length));
    }

    function finish(commit: boolean) {
        const extent = getExtent();
        const range =
            commit && extent && proposed ? toSeqNumberRange(getTicks(), extent, proposed) : null;
        edge = null;
        proposed = null;
        onEnd();
        if (range) onCommit(range);
    }

    return {
        start,
        move,
        finish,
        get edge() {
            return edge;
        },
        /** The coverage the drag would produce, or null while idle. */
        get proposed() {
            return proposed;
        }
    };
}
