import type { BoundingBox } from '$lib/types';

export function getConstrainedCoordinates(
    newBbox: BoundingBox,
    constraintBox: BoundingBox,
    preserveSize = false
): BoundingBox {
    const MIN_SIZE_OF_BBOX_DIMENSION = 1;
    const constrainedBbox = { ...newBbox };

    if (preserveSize) {
        // Ensure bbox stays within constraint bounds while preserving size
        constrainedBbox.x = Math.round(
            Math.max(
                constraintBox.x,
                Math.min(
                    constrainedBbox.x,
                    constraintBox.x + constraintBox.width - constrainedBbox.width
                )
            )
        );
        constrainedBbox.y = Math.round(
            Math.max(
                constraintBox.y,
                Math.min(
                    constrainedBbox.y,
                    constraintBox.y + constraintBox.height - constrainedBbox.height
                )
            )
        );

        return constrainedBbox;
    } else {
        const left = newBbox.x;
        const top = newBbox.y;
        const right = newBbox.x + newBbox.width;
        const bottom = newBbox.y + newBbox.height;

        const constrainedLeft = Math.max(constraintBox.x, left);
        const constrainedTop = Math.max(constraintBox.y, top);
        const constrainedRight = Math.min(constraintBox.x + constraintBox.width, right);
        const constrainedBottom = Math.min(constraintBox.y + constraintBox.height, bottom);

        const constrainedBbox: BoundingBox = {
            x: Math.round(constrainedLeft),
            y: Math.round(constrainedTop),
            width: Math.round(constrainedRight - constrainedLeft),
            height: Math.round(constrainedBottom - constrainedTop)
        };

        // Ensure minimum size constraints
        constrainedBbox.width = Math.max(MIN_SIZE_OF_BBOX_DIMENSION, constrainedBbox.width);
        constrainedBbox.height = Math.max(MIN_SIZE_OF_BBOX_DIMENSION, constrainedBbox.height);

        return constrainedBbox;
    }
}
