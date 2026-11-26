import type { BrushPoint } from './types';

/** One row of brush pixels: `width` pixels from `xStart` in row `y`. */
export interface BrushSpan {
    y: number;
    xStart: number;
    width: number;
}

/**
 * Snap the cursor to the pixel grid. An odd size centres on the pixel under the cursor,
 * an even size centres on the nearest pixel corner.
 */
export function getBrushAnchor(point: BrushPoint, size: number): BrushPoint {
    if (isOdd(size)) {
        return { x: Math.floor(point.x), y: Math.floor(point.y) };
    }
    return { x: Math.round(point.x), y: Math.round(point.y) };
}

/** Return the pixels of a round, hard-edged disc of `size` pixels as row spans. */
export function getBrushSpans(anchor: BrushPoint, size: number): BrushSpan[] {
    return getDiscOffsets(size).map((offset) => ({
        y: anchor.y + offset.y,
        xStart: anchor.x + offset.xStart,
        width: offset.width
    }));
}

/** Return every integer point on the line from `from` to `to`, both ends included. */
export function getStrokeAnchors(from: BrushPoint, to: BrushPoint): BrushPoint[] {
    const deltaX = Math.abs(to.x - from.x);
    const deltaY = -Math.abs(to.y - from.y);
    const stepX = from.x < to.x ? 1 : -1;
    const stepY = from.y < to.y ? 1 : -1;
    const anchors: BrushPoint[] = [];
    let { x, y } = from;
    let error = deltaX + deltaY;

    while (true) {
        anchors.push({ x, y });
        if (x === to.x && y === to.y) return anchors;

        const doubledError = 2 * error;
        if (doubledError >= deltaY) {
            error += deltaY;
            x += stepX;
        }
        if (doubledError <= deltaX) {
            error += deltaX;
            y += stepY;
        }
    }
}

/** Return an SVG path that outlines the pixels of the spans, ordered top to bottom. */
export function getBrushOutlinePath(spans: BrushSpan[]): string {
    if (spans.length === 0) return '';

    const rightEdge = spans.map((span) => `H${span.xStart + span.width}V${span.y + 1}`).join('');
    const leftEdge = [...spans]
        .reverse()
        .map((span) => `H${span.xStart}V${span.y}`)
        .join('');
    return `M${spans[0].xStart} ${spans[0].y}${rightEdge}${leftEdge}Z`;
}

const discOffsetsBySize = new Map<number, BrushSpan[]>();

function getDiscOffsets(size: number): BrushSpan[] {
    const cachedOffsets = discOffsetsBySize.get(size);
    if (cachedOffsets) return cachedOffsets;

    const offsets = computeDiscOffsets(size);
    discOffsetsBySize.set(size, offsets);
    return offsets;
}

// A pixel is in the disc when its centre lies within size / 2 of the disc centre.
// Distances are doubled so that the check stays in exact integer math.
function computeDiscOffsets(size: number): BrushSpan[] {
    const firstOffset = -Math.floor(size / 2);
    const centreShift = isOdd(size) ? 0 : 1;
    const doubledDistance = (offset: number) => 2 * offset + centreShift;
    const squaredSize = size * size;
    const offsets: BrushSpan[] = [];

    for (let y = firstOffset; y < firstOffset + size; y++) {
        const squaredDistanceY = doubledDistance(y) ** 2;
        let xStart = firstOffset;
        while (doubledDistance(xStart) ** 2 + squaredDistanceY > squaredSize) {
            xStart++;
        }
        const width = 2 * -xStart + (isOdd(size) ? 1 : 0);
        offsets.push({ y, xStart, width });
    }
    return offsets;
}

function isOdd(size: number): boolean {
    return size % 2 === 1;
}
