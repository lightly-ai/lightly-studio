import {
    boxFromPoints,
    isDragBox,
    normalizedPointFromEvent,
    type NormalizedBox,
    type NormalizedPoint
} from '$lib/components/SampleDetails/AnnotationPreview/annotationPreview.helpers';

type RectPointerEvent = PointerEvent & { currentTarget: SVGRectElement };

// Tracks a pointer drag on the interaction rect and tells a drawn box from a click.
export const useDragBox = (
    getParams: () => { interactionRect: SVGRectElement | null | undefined }
) => {
    let start = $state<NormalizedPoint | null>(null);
    let box = $state<NormalizedBox | null>(null);

    const pointFromEvent = (event: PointerEvent) => {
        const rect = getParams().interactionRect;
        return rect ? normalizedPointFromEvent(event, rect.getBoundingClientRect()) : null;
    };

    const onPointerDown = (event: RectPointerEvent) => {
        start = pointFromEvent(event);
        if (start) event.currentTarget.setPointerCapture(event.pointerId);
    };

    const onPointerMove = (event: PointerEvent) => {
        const point = pointFromEvent(event);
        if (!start || !point) return;
        const next = boxFromPoints(start, point);
        box = isDragBox(next) ? next : null;
    };

    const onPointerCancel = (event: RectPointerEvent) => {
        event.currentTarget.releasePointerCapture(event.pointerId);
        start = null;
        box = null;
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
        onPointerCancel
    };
};
