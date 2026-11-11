export const MIN_TRACK_ROWS_HEIGHT = 48;
export const MAX_TRACK_ROWS_HEIGHT = 560;
export const DEFAULT_TRACK_ROWS_HEIGHT = 160;
const STORAGE_KEY = 'lightlyStudio_trackTimelineRowsHeight';

const clamp = (value: number) =>
    Math.min(MAX_TRACK_ROWS_HEIGHT, Math.max(MIN_TRACK_ROWS_HEIGHT, Math.round(value)));

const read = (): number => {
    try {
        const value = Number(localStorage.getItem(STORAGE_KEY));
        return Number.isFinite(value) && value > 0 ? clamp(value) : DEFAULT_TRACK_ROWS_HEIGHT;
    } catch {
        return DEFAULT_TRACK_ROWS_HEIGHT;
    }
};

/** The height the track rows may grow to, remembered across reloads. */
export function useTrackRowsHeight() {
    let height = $state(read());
    let dragStart: { pointerY: number; height: number } | null = null;

    function setHeight(value: number) {
        height = clamp(value);
        try {
            localStorage.setItem(STORAGE_KEY, String(height));
        } catch {
            // Storage can be unavailable; the height then lasts until the page reloads.
        }
    }

    return {
        get height() {
            return height;
        },
        get isDragging() {
            return dragStart !== null;
        },
        setHeight,
        /**
         * Dragging the handle up makes the rows taller. The drag starts from the height the
         * rows really have, because a short list is smaller than the limit and shrinking the
         * limit would otherwise show no change at first.
         */
        startDrag(event: PointerEvent, renderedHeight?: number) {
            event.preventDefault();
            (event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId);
            dragStart = {
                pointerY: event.clientY,
                height: clamp(Math.min(height, renderedHeight || height))
            };
        },
        drag(event: PointerEvent) {
            if (dragStart) setHeight(dragStart.height + (dragStart.pointerY - event.clientY));
        },
        endDrag() {
            dragStart = null;
        }
    };
}
