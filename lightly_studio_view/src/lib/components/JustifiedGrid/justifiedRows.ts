export interface JustifiedTile {
    /** Index into the caller's item list. */
    index: number;
    width: number;
    height: number;
}

export interface JustifiedRow {
    tiles: JustifiedTile[];
    height: number;
    /** Distance from the top of the scroll content to this row's top edge. */
    top: number;
}

interface BuildJustifiedRowsParams {
    /** Width / height of each item, in item order. Non-finite values fall back to 1. */
    aspectRatios: number[];
    containerWidth: number;
    /** Row height before justification; rows scale around it to fill the width. */
    targetRowHeight: number;
    gap: number;
}

/**
 * Lay items out in justified rows, the way a photo gallery does: every image keeps its true
 * aspect ratio, and each row is scaled so it exactly fills the container width.
 *
 * The last row is left at `targetRowHeight` instead of being stretched — a short final row
 * blown up to full width is the classic giveaway of a naive implementation.
 */
export function buildJustifiedRows({
    aspectRatios,
    containerWidth,
    targetRowHeight,
    gap
}: BuildJustifiedRowsParams): JustifiedRow[] {
    if (containerWidth <= 0 || targetRowHeight <= 0 || aspectRatios.length === 0) return [];

    const rows: JustifiedRow[] = [];
    let top = 0;
    let rowIndices: number[] = [];
    let rowAspectSum = 0;

    const closeRow = (justify: boolean) => {
        if (rowIndices.length === 0) return;
        const totalGap = gap * (rowIndices.length - 1);
        const height = justify
            ? Math.max(1, (containerWidth - totalGap) / rowAspectSum)
            : targetRowHeight;
        rows.push({
            top,
            height,
            tiles: rowIndices.map((index) => ({
                index,
                width: normalizeAspectRatio(aspectRatios[index]) * height,
                height
            }))
        });
        top += height + gap;
        rowIndices = [];
        rowAspectSum = 0;
    };

    aspectRatios.forEach((_, index) => {
        const aspectRatio = normalizeAspectRatio(aspectRatios[index]);
        const widthWithItem =
            (rowAspectSum + aspectRatio) * targetRowHeight + gap * rowIndices.length;
        // Always keep at least one tile per row, however wide the container is not.
        if (rowIndices.length > 0 && widthWithItem > containerWidth) {
            closeRow(true);
        }
        rowIndices.push(index);
        rowAspectSum += aspectRatio;
    });
    closeRow(false);

    return rows;
}

/** Total scroll height for a laid-out set of rows, stopping at the last row's bottom edge. */
export function getJustifiedContentHeight(rows: JustifiedRow[]): number {
    const lastRow = rows[rows.length - 1];
    return lastRow ? lastRow.top + lastRow.height : 0;
}

interface VisibleRowRangeParams {
    rows: JustifiedRow[];
    scrollTop: number;
    viewportHeight: number;
    /** Extra rows rendered above and below the viewport. */
    overscan: number;
}

/** First and last row index to render for the current scroll position. */
export function getVisibleRowRange({
    rows,
    scrollTop,
    viewportHeight,
    overscan
}: VisibleRowRangeParams): { start: number; end: number } {
    if (rows.length === 0) return { start: 0, end: 0 };

    let start = rows.findIndex((row) => row.top + row.height >= scrollTop);
    if (start === -1) start = rows.length - 1;

    // Look at the *next* row's top: testing the current row's own top would advance one row
    // past the viewport before noticing.
    let end = start;
    const bottom = scrollTop + viewportHeight;
    while (end < rows.length - 1 && rows[end + 1].top <= bottom) end++;

    return {
        start: Math.max(0, start - overscan),
        end: Math.min(rows.length - 1, end + overscan)
    };
}

function normalizeAspectRatio(aspectRatio: number | undefined): number {
    return aspectRatio && Number.isFinite(aspectRatio) && aspectRatio > 0 ? aspectRatio : 1;
}
