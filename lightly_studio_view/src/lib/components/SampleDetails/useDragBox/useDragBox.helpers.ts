// Drags shorter than this fraction of the image count as clicks.
const MIN_DRAG_SIZE = 0.005;

const clamp01 = (value: number) => Math.max(0, Math.min(1, value));

export const normalizedPointFromEvent = (
    event: { clientX: number; clientY: number },
    rect: { left: number; top: number; width: number; height: number }
): { x: number; y: number } => ({
    x: clamp01((event.clientX - rect.left) / rect.width),
    y: clamp01((event.clientY - rect.top) / rect.height)
});

type NormalizedPoint = ReturnType<typeof normalizedPointFromEvent>;

export const boxFromPoints = (
    start: NormalizedPoint,
    end: NormalizedPoint
): { x: number; y: number; width: number; height: number } => ({
    x: Math.min(start.x, end.x),
    y: Math.min(start.y, end.y),
    width: Math.abs(end.x - start.x),
    height: Math.abs(end.y - start.y)
});

export const isDragBox = (box: ReturnType<typeof boxFromPoints>): boolean =>
    box.width > MIN_DRAG_SIZE && box.height > MIN_DRAG_SIZE;
