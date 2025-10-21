import type { BoundingBox } from '$lib/types';
import { drag } from 'd3-drag';

export function createMoveDrag({
    getCurrentBbox,
    onMove,
    onDragEnd,
    onInteractionStart,
    onInteractionEnd
}: {
    getCurrentBbox: () => BoundingBox;
    onMove?: (newBbox: BoundingBox) => void;
    onDragEnd?: (newBbox: BoundingBox) => void;
    onInteractionStart?: () => void;
    onInteractionEnd?: () => void;
}) {
    let dragStartBbox: BoundingBox;

    return drag()
        .on('start', () => {
            dragStartBbox = getCurrentBbox();
            onInteractionStart?.();
        })
        .on('drag', (event) => {
            const totalDx = event.x - event.subject.x;
            const totalDy = event.y - event.subject.y;

            const newX = Math.round(dragStartBbox.x + totalDx);
            const newY = Math.round(dragStartBbox.y + totalDy);

            if (onMove) {
                onMove({
                    x: newX,
                    y: newY,
                    width: dragStartBbox.width,
                    height: dragStartBbox.height
                });
            }
        })
        .on('end', () => {
            const currentBbox = getCurrentBbox();
            if (onDragEnd) {
                onDragEnd(currentBbox);
            }
            onInteractionEnd?.();
        });
}
