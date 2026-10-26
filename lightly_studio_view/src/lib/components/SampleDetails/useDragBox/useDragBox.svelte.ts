import { boxFromPoints, isDragBox, normalizedPointFromEvent } from './useDragBox.helpers';

type RectPointerEvent = PointerEvent & { currentTarget: SVGRectElement };

// Tracks a pointer drag on the interaction rect and tells a drawn box from a click.
export const useDragBox = (
    getParams: () => { interactionRect: SVGRectElement | null | undefined }
) => {
    let start = $state<ReturnType<typeof normalizedPointFromEvent> | null>(null);
    let box = $state<ReturnType<typeof boxFromPoints> | null>(null);

    const pointFromEvent = (event: PointerEvent) => {
        const rect = getParams().interactionRect;
        return rect ? normalizedPointFromEvent(event, rect.getBoundingClientRect()) : null;
    };

    const onPointerDown = (event: RectPointerEvent) => {
        if (event.button !== 0) return;
        start = pointFromEvent(event);
        if (start) event.currentTarget.setPointerCapture(event.pointerId);
    };

    const onPointerMove = (event: PointerEvent) => {
        const point = pointFromEvent(event);
        if (!start || !point) return;
        const next = boxFromPoints(start, point);
        box = isDragBox(next) ? next : null;
    };

    const cancel = () => {
        start = null;
        box = null;
    };

    const onPointerCancel = (event: RectPointerEvent) => {
        event.currentTarget.releasePointerCapture(event.pointerId);
        cancel();
    };

    // Returns the drawn box, or the start point if the drag was a click.
    const onPointerUp = (event: RectPointerEvent) => {
        const result = { start, box };
        onPointerCancel(event);
        return result;
    };

    return {
        get box() {
            return box;
        },
        onPointerDown,
        onPointerMove,
        onPointerUp,
        onPointerCancel,
        cancel
    };
};
