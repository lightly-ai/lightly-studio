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
    let pointerOffset = 0;

    function start(event: PointerEvent, nextEdge: ExtendEdge) {
        const extent = getExtent();
        const bar = getBar();
        const ticks = getTicks();
        if (!extent || !bar || ticks.length === 0 || edge) return;
        event.preventDefault();
        (event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId);
        const rect = bar.getBoundingClientRect();
        const handleIndex =
            nextEdge === 'start'
                ? extent.first
                : nextEdge === 'end'
                  ? extent.last + 1
                  : extent.first + 0.5;
        pointerOffset = event.clientX - (rect.left + (handleIndex / ticks.length) * rect.width);
        edge = nextEdge;
        proposed = extent;
        onStart();
    }

    function move(event: PointerEvent) {
        const extent = getExtent();
        const bar = getBar();
        if (!edge || !extent || !bar) return;
        const rect = bar.getBoundingClientRect();
        const count = getTicks().length;
        const index = tickIndexAt(event.clientX - pointerOffset, rect, count);
        proposed = proposeExtent(extent, edge, edge === 'end' ? index : Math.min(count - 1, index));
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
