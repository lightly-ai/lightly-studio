interface GetPreviewPositionParams {
    /** Hovered point in plot pixel coordinates. */
    point: { x: number; y: number };
    plotWidth: number;
    cardSize: number;
    /** Minimum distance to the plot edges. */
    margin?: number;
    /** Vertical gap between the point and the card. */
    offset?: number;
}

/**
 * Positions the preview card directly above the hovered point: horizontally
 * centered on it (clamped just enough to stay inside the plot) and never
 * flipped below or pushed beside the point.
 *
 * Returns the pixel position of the card's top-center (render with
 * `translateX(-50%)`).
 */
export function getPreviewPosition({
    point,
    plotWidth,
    cardSize,
    margin = 4,
    offset = 10
}: GetPreviewPositionParams): { left: number; top: number } {
    const halfCard = cardSize / 2;
    const minLeft = margin + halfCard;
    const maxLeft = plotWidth - margin - halfCard;
    const left = Math.min(Math.max(point.x, minLeft), Math.max(maxLeft, minLeft));
    const top = Math.max(margin, point.y - offset - cardSize);
    return { left, top };
}
