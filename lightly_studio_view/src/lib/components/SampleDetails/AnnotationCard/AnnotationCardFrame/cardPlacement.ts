import type { BoundingBox } from '$lib/types';

interface Rect {
    left: number;
    top: number;
    right: number;
    bottom: number;
}

interface PlacePanelParams {
    /** Screen rectangle of the selected box. */
    box: Rect;
    /** Screen rectangle of the visible canvas. */
    canvas: Rect;
    panel: { width: number; height: number };
    gap?: number;
}

/**
 * Places the panel beside the box, right of it if it fits, else left of it, and keeps it on the
 * canvas. The panel covers the box only when neither side has room.
 */
export const placePanel = ({ box, canvas, panel, gap = 8 }: PlacePanelParams) => {
    const rightLeft = box.right + gap;
    const leftLeft = box.left - gap - panel.width;
    let left: number;
    if (rightLeft + panel.width <= canvas.right) {
        left = rightLeft;
    } else if (leftLeft >= canvas.left) {
        left = leftLeft;
    } else {
        left = canvas.right - panel.width;
    }
    left = clamp(left, canvas.left, canvas.right - panel.width);
    const top = clamp(box.top, canvas.top, canvas.bottom - panel.height);
    return { left, top };
};

/** Maps an image-space box to screen pixels with the scale and translation of a DOM matrix. */
export const imageRectToScreen = (
    bbox: BoundingBox,
    matrix: Pick<DOMMatrix, 'a' | 'd' | 'e' | 'f'>
): Rect => ({
    left: bbox.x * matrix.a + matrix.e,
    top: bbox.y * matrix.d + matrix.f,
    right: (bbox.x + bbox.width) * matrix.a + matrix.e,
    bottom: (bbox.y + bbox.height) * matrix.d + matrix.f
});

/** Whether two rectangles overlap. Touching edges do not count. */
export const rectsIntersect = (a: Rect, b: Rect): boolean =>
    a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;

interface CardPlacement {
    left: number;
    top: number;
    /** False when the box is panned off the canvas. */
    isBoxOnCanvas: boolean;
}

/** Places the card beside an image-space box, on screen through the layer's screen matrix. */
export const placeCard = ({
    bbox,
    matrix,
    canvas,
    card
}: {
    bbox: BoundingBox;
    matrix: Pick<DOMMatrix, 'a' | 'd' | 'e' | 'f'>;
    canvas: Rect;
    card: { width: number; height: number };
}): CardPlacement => {
    const box = imageRectToScreen(bbox, matrix);
    return {
        ...placePanel({ box, canvas, panel: card }),
        isBoxOnCanvas: rectsIntersect(box, canvas)
    };
};

export const isSamePlacement = (a: CardPlacement | null, b: CardPlacement | null): boolean =>
    a === b ||
    (a !== null &&
        b !== null &&
        a.left === b.left &&
        a.top === b.top &&
        a.isBoxOnCanvas === b.isBoxOnCanvas);

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(value, max));
