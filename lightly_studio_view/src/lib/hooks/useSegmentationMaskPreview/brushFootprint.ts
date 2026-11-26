import type { BrushPoint } from './types';

/** One row of brush pixels: `width` pixels from `xStart` in row `y`. */
export interface BrushSpan {
    y: number;
    xStart: number;
    width: number;
}

/**
 * Snap the cursor to the pixel grid. An odd size centers on the pixel under the cursor,
 * an even size centers on the nearest pixel corner. The size rounds to whole pixels.
 */
export function getBrushAnchor(point: BrushPoint, size: number): BrushPoint {
    if (isOdd(toWholePixels(size))) {
        return { x: Math.floor(point.x), y: Math.floor(point.y) };
    }
    return { x: Math.round(point.x), y: Math.round(point.y) };
}

/**
 * Return the pixels of a round, hard-edged disc of `size` pixels as row spans.
 * The size rounds to whole pixels.
 */
export function getBrushSpans(anchor: BrushPoint, size: number): BrushSpan[] {
    return getDiscOffsets(toWholePixels(size)).map((offset) => ({
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

/** A stroke of a round brush from `from` to `to` on an image of `width` x `height` pixels. */
export interface BrushStroke {
    from: BrushPoint;
    to: BrushPoint;
    size: number;
    width: number;
    height: number;
}

/**
 * Return the image pixels that a brush stroke paints, as row spans that do not overlap.
 * The pixels are the union of the brush disc at each anchor of the stroke. Spans are ordered
 * top to bottom, then left to right.
 */
export function getStrokeSpans(stroke: BrushStroke): BrushSpan[] {
    return toMergedSpans(collectRowRanges(stroke));
}

/** Return an SVG path that outlines the pixels the brush paints at `point`. */
export function getBrushOutlinePath(point: BrushPoint, size: number): string {
    return toOutlinePath(getBrushSpans(getBrushAnchor(point, size), size));
}

// Spans are ordered top to bottom.
function toOutlinePath(spans: BrushSpan[]): string {
    if (spans.length === 0) return '';

    const rightEdge = spans.map((span) => `H${span.xStart + span.width}V${span.y + 1}`).join('');
    const leftEdge = [...spans]
        .reverse()
        .map((span) => `H${span.xStart}V${span.y}`)
        .join('');
    return `M${spans[0].xStart} ${spans[0].y}${rightEdge}${leftEdge}Z`;
}

/** A range of pixels in one row, from `xStart` up to but not including `xEnd`. */
interface PixelRange {
    xStart: number;
    xEnd: number;
}

// The disc offsets are computed once for the stroke, and pixels outside the image are dropped.
// Neighbor anchors usually cover touching ranges, so a range joins the last range of its row
// when possible. This keeps the number of stored ranges small for long strokes.
function collectRowRanges({
    from,
    to,
    size,
    width,
    height
}: BrushStroke): Map<number, PixelRange[]> {
    const discOffsets = getDiscOffsets(toWholePixels(size));
    const rangesByRow = new Map<number, PixelRange[]>();

    for (const anchor of getStrokeAnchors(from, to)) {
        for (const offset of discOffsets) {
            const y = anchor.y + offset.y;
            const xStart = Math.max(0, anchor.x + offset.xStart);
            const xEnd = Math.min(width, anchor.x + offset.xStart + offset.width);
            const isInsideImage = y >= 0 && y < height && xStart < xEnd;
            if (!isInsideImage) continue;

            addRange(rangesByRow, y, { xStart, xEnd });
        }
    }
    return rangesByRow;
}

function addRange(rangesByRow: Map<number, PixelRange[]>, y: number, range: PixelRange) {
    const rowRanges = rangesByRow.get(y);
    if (!rowRanges) {
        rangesByRow.set(y, [range]);
        return;
    }
    const lastRange = rowRanges[rowRanges.length - 1];
    if (rangesTouch(lastRange, range)) {
        lastRange.xStart = Math.min(lastRange.xStart, range.xStart);
        lastRange.xEnd = Math.max(lastRange.xEnd, range.xEnd);
        return;
    }
    rowRanges.push(range);
}

function toMergedSpans(rangesByRow: Map<number, PixelRange[]>): BrushSpan[] {
    const rows = [...rangesByRow.keys()].sort((a, b) => a - b);
    return rows.flatMap((y) =>
        mergeRanges(rangesByRow.get(y) ?? []).map((range) => ({
            y,
            xStart: range.xStart,
            width: range.xEnd - range.xStart
        }))
    );
}

function mergeRanges(ranges: PixelRange[]): PixelRange[] {
    const sortedRanges = [...ranges].sort((a, b) => a.xStart - b.xStart);
    const mergedRanges: PixelRange[] = [];
    for (const range of sortedRanges) {
        const lastRange = mergedRanges[mergedRanges.length - 1];
        if (lastRange && rangesTouch(lastRange, range)) {
            lastRange.xEnd = Math.max(lastRange.xEnd, range.xEnd);
            continue;
        }
        mergedRanges.push({ ...range });
    }
    return mergedRanges;
}

function rangesTouch(first: PixelRange, second: PixelRange): boolean {
    return first.xStart <= second.xEnd && second.xStart <= first.xEnd;
}

const discOffsetsBySize = new Map<number, BrushSpan[]>();

function getDiscOffsets(size: number): BrushSpan[] {
    const cachedOffsets = discOffsetsBySize.get(size);
    if (cachedOffsets) return cachedOffsets;

    const offsets = computeDiscOffsets(size);
    discOffsetsBySize.set(size, offsets);
    return offsets;
}

// A pixel is in the disc when its center lies within size / 2 of the disc center.
// Distances are doubled so that the check stays in exact integer math.
function computeDiscOffsets(size: number): BrushSpan[] {
    const firstOffset = -Math.floor(size / 2);
    const centerShift = isOdd(size) ? 0 : 1;
    const doubledDistance = (offset: number) => 2 * offset + centerShift;
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

// The disc math needs a whole number. A fractional size makes a row that never fits.
function toWholePixels(size: number): number {
    return Math.max(1, Math.round(size));
}

function isOdd(size: number): boolean {
    return size % 2 === 1;
}
