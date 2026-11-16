import { getContext, setContext } from 'svelte';

/** Fewest ticks that may be visible at once; bounds how far the timeline can zoom in. */
const MIN_VISIBLE_TICKS = 10;
const CONTEXT_KEY = Symbol('timelineViewport');

/**
 * The window of the timeline that is currently visible.
 *
 * `zoom` is the factor by which the timeline is enlarged (1 shows every tick) and `offset` is the
 * fraction of the whole timeline that lies to the left of the window (0 to `1 - 1 / zoom`).
 */
export function useTimelineViewport(getTickCount: () => number, getCurrentIndex = () => -1) {
    let zoomState = $state(1);
    let offsetState = $state(0);

    const maxZoom = () => Math.max(1, getTickCount() / MIN_VISIBLE_TICKS);
    const clampZoom = (value: number) => Math.min(maxZoom(), Math.max(1, value));
    const clampOffset = (value: number, zoom: number) =>
        Math.min(Math.max(0, value), Math.max(0, 1 - 1 / zoom));

    const zoom = () => clampZoom(zoomState);
    const offset = () => clampOffset(offsetState, zoom());

    /** Keeps the current frame, or an explicit window anchor (0 to 1), fixed while zooming. */
    function zoomBy(factor: number, anchor?: number) {
        const current = zoom();
        const framePosition = (getCurrentIndex() + 0.5) / getTickCount();
        const frameAnchor = (framePosition - offset()) * current;
        const position = anchor ?? (frameAnchor >= 0 && frameAnchor <= 1 ? frameAnchor : 0.5);
        const focus = offset() + position / current;
        const next = clampZoom(current * factor);
        zoomState = next;
        offsetState = clampOffset(focus - position / next, next);
    }

    /** Moves the window by a fraction of the whole timeline. */
    function panBy(fraction: number) {
        offsetState = clampOffset(offset() + fraction, zoom());
    }

    /** Sets the left edge of the visible timeline window as a fraction of the full sequence. */
    function setOffset(value: number) {
        offsetState = clampOffset(value, zoom());
    }

    /** Pans just enough to bring the tick at `index` into the window, centering it if hidden. */
    function reveal(index: number) {
        const count = getTickCount();
        if (count === 0) return;
        const start = offset() * count;
        const end = start + count / zoom();
        if (index >= start && index + 1 <= end) return;
        offsetState = clampOffset((index + 0.5) / count - 0.5 / zoom(), zoom());
    }

    /** Shows the part of the timeline between two fractions, at least the most-zoomed width. */
    function setWindow(start: number, end: number) {
        const width = Math.min(1, Math.max(1 / maxZoom(), end - start));
        zoomState = 1 / width;
        offsetState = clampOffset(start, 1 / width);
    }

    function reset() {
        zoomState = 1;
        offsetState = 0;
    }

    return {
        get zoom() {
            return zoom();
        },
        get offset() {
            return offset();
        },
        get canZoomIn() {
            return zoom() < maxZoom();
        },
        get canZoomOut() {
            return zoom() > 1;
        },
        zoomBy,
        panBy,
        setOffset,
        setWindow,
        reveal,
        reset
    };
}

export type TimelineViewport = ReturnType<typeof useTimelineViewport>;

const unzoomedViewport = useTimelineViewport(() => 0);

export function setTimelineViewport(viewport: TimelineViewport) {
    setContext(CONTEXT_KEY, viewport);
}

/** The viewport shared by the timeline parts; unzoomed when none was provided. */
export function getTimelineViewport(): TimelineViewport {
    return getContext<TimelineViewport | undefined>(CONTEXT_KEY) ?? unzoomedViewport;
}
