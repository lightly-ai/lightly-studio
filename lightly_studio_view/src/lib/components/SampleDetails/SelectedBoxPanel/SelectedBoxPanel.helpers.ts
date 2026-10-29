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

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(value, max));
