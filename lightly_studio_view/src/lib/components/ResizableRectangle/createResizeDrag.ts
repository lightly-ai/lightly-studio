import type { BoundingBox } from '$lib/types';
import { drag } from 'd3-drag';

export function createResizeDrag({
    handle,
    getCurrentBbox,
    onResize,
    onDragEnd,
    onInteractionStart,
    onInteractionEnd
}: {
    handle: string;
    getCurrentBbox: () => BoundingBox;
    onResize?: (newBbox: BoundingBox) => void;
    onDragEnd?: (newBbox: BoundingBox) => void;
    onInteractionStart?: () => void;
    onInteractionEnd?: () => void;
}) {
    let dragStartBbox: BoundingBox;

    return drag()
        .on('start', () => {
            // Capture the current bbox when drag starts
            dragStartBbox = getCurrentBbox();
            onInteractionStart?.();
        })
        .on('drag', (event) => {
            let newX = dragStartBbox.x;
            let newY = dragStartBbox.y;
            let newWidth = dragStartBbox.width;
            let newHeight = dragStartBbox.height;

            // Update based on accumulated drag distance
            const totalDx = event.x - event.subject.x;
            const totalDy = event.y - event.subject.y;

            switch (handle) {
                case 'nw': // Top-left
                    newX = dragStartBbox.x + totalDx;
                    newY = dragStartBbox.y + totalDy;
                    newWidth = dragStartBbox.width - totalDx;
                    newHeight = dragStartBbox.height - totalDy;
                    break;
                case 'ne': // Top-right
                    newY = dragStartBbox.y + totalDy;
                    newWidth = dragStartBbox.width + totalDx;
                    newHeight = dragStartBbox.height - totalDy;
                    break;
                case 'sw': // Bottom-left
                    newX = dragStartBbox.x + totalDx;
                    newWidth = dragStartBbox.width - totalDx;
                    newHeight = dragStartBbox.height + totalDy;
                    break;
                case 'se': // Bottom-right
                    newWidth = dragStartBbox.width + totalDx;
                    newHeight = dragStartBbox.height + totalDy;
                    break;
                case 'n': // Top
                    newY = dragStartBbox.y + totalDy;
                    newHeight = dragStartBbox.height - totalDy;
                    break;
                case 's': // Bottom
                    newHeight = dragStartBbox.height + totalDy;
                    break;
                case 'w': // Left
                    newX = dragStartBbox.x + totalDx;
                    newWidth = dragStartBbox.width - totalDx;
                    break;
                case 'e': // Right
                    newWidth = dragStartBbox.width + totalDx;
                    break;
            }

            // Ensure minimum size and prevent jumping
            const minSize = 1;

            if (newWidth < minSize) {
                newWidth = minSize;
                if (handle.includes('w')) {
                    // When resizing from west edge, keep the right edge fixed
                    newX = dragStartBbox.x + dragStartBbox.width - minSize;
                }
            }

            if (newHeight < minSize) {
                newHeight = minSize;
                if (handle.includes('n')) {
                    // When resizing from north edge, keep the bottom edge fixed
                    newY = dragStartBbox.y + dragStartBbox.height - minSize;
                }
            }
            const x = Math.round(newX);
            const y = Math.round(newY);
            const width = Math.round(newWidth);
            const height = Math.round(newHeight);

            if (onResize) {
                onResize({ x, y, width, height });
            }
        })
        .on('end', () => {
            const { x, y, width, height } = getCurrentBbox();
            const bboxChanged =
                x !== dragStartBbox.x ||
                y !== dragStartBbox.y ||
                width !== dragStartBbox.width ||
                height !== dragStartBbox.height;
            if (onDragEnd && bboxChanged) {
                onDragEnd({ x, y, width, height });
            }
            onInteractionEnd?.();
        });
}
