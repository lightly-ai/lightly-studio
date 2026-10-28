"""Rasterization of polygons to run-length encoded masks.

The algorithm is the one of `rleFrPoly` in pycocotools, so the masks are the same as the
masks of the COCO tools.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

# pycocotools walks the polygon edges on a grid that is this many times finer than the pixels.
_UPSAMPLE = 5


def polygons_to_rle(
    polygons: Sequence[Sequence[tuple[float, float]]], width: int, height: int
) -> list[int]:
    """Rasterizes polygons and returns the union as a row-wise run-length encoding.

    Args:
        polygons: Polygons as lists of (x, y) vertices in pixel coordinates.
        width: Width of the mask in pixels.
        height: Height of the mask in pixels.

    Returns:
        Row-wise run-length encoding of the mask. The first count is the number of 0
        pixels at the start of the mask. It is 0 if the mask starts with a 1 pixel.
    """
    crossings = [_column_crossings(polygon=p, width=width, height=height) for p in polygons]
    crossings = [(columns, rows) for columns, rows in crossings if columns.size > 0]
    if not crossings:
        return [width * height]
    first_column = min(int(columns.min()) for columns, _ in crossings)
    end_column = max(int(columns.max()) for columns, _ in crossings) + 1
    first_row = min(int(rows.min()) for _, rows in crossings)
    end_row = max(int(rows.max()) for _, rows in crossings) + 1
    block = np.zeros((end_column - first_column, end_row - first_row), dtype=bool)
    for columns, rows in crossings:
        block |= _fill(columns=columns - first_column, rows=rows - first_row, shape=block.shape)
    # A crossing at row `height` closes a run at the bottom border and has no pixel.
    block = block[:, : min(end_row, height) - first_row]
    return _row_wise_rle(
        block=block.T, first_row=first_row, first_column=first_column, width=width, height=height
    )


def _column_crossings(
    polygon: Sequence[tuple[float, float]], width: int, height: int
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Returns the pixel columns and rows where the mask changes between 0 and 1.

    The rows are in the range [0, height]. A closed polygon crosses each pixel column an
    even number of times.
    """
    u, v = _boundary_points(polygon=polygon)
    # Keep the points where the boundary goes to the next upsampled column.
    moves = u[1:] != u[:-1]
    u_current, u_previous = u[1:][moves], u[:-1][moves]
    v_current, v_previous = v[1:][moves], v[:-1][moves]
    x = (np.where(u_current < u_previous, u_current, u_current - 1) + 0.5) / _UPSAMPLE - 0.5
    on_pixel_column = (np.floor(x) == x) & (x >= 0) & (x <= width - 1)
    y = (np.minimum(v_current, v_previous) + 0.5) / _UPSAMPLE - 0.5
    y = np.ceil(np.clip(y, 0.0, float(height)))
    return x[on_pixel_column].astype(np.int64), y[on_pixel_column].astype(np.int64)


def _boundary_points(
    polygon: Sequence[tuple[float, float]],
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Returns the points of the closed polygon boundary on the upsampled grid."""
    vertices = np.array(polygon, dtype=np.float64).reshape(-1, 2)
    # The truncation toward zero is the same as the C cast in pycocotools.
    xs = (_UPSAMPLE * vertices[:, 0] + 0.5).astype(np.int64).tolist()
    ys = (_UPSAMPLE * vertices[:, 1] + 0.5).astype(np.int64).tolist()
    xs.append(xs[0])
    ys.append(ys[0])
    edges = [
        _edge_points(x_start=xs[i], y_start=ys[i], x_end=xs[i + 1], y_end=ys[i + 1])
        for i in range(len(xs) - 1)
    ]
    return np.concatenate([u for u, _ in edges]), np.concatenate([v for _, v in edges])


def _edge_points(
    x_start: int, y_start: int, x_end: int, y_end: int
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Returns one point per step along the longer axis of the edge, both ends included."""
    dx, dy = abs(x_end - x_start), abs(y_end - y_start)
    flip = (dx >= dy and x_start > x_end) or (dx < dy and y_start > y_end)
    if flip:
        x_start, x_end, y_start, y_end = x_end, x_start, y_end, y_start
    if dx >= dy:
        slope = (y_end - y_start) / dx if dx > 0 else 0.0
        t = np.arange(dx + 1, dtype=np.int64)
        t = dx - t if flip else t
        return t + x_start, (y_start + slope * t + 0.5).astype(np.int64)
    slope = (x_end - x_start) / dy
    t = np.arange(dy + 1, dtype=np.int64)
    t = dy - t if flip else t
    return (x_start + slope * t + 0.5).astype(np.int64), t + y_start


def _fill(
    columns: NDArray[np.int64], rows: NDArray[np.int64], shape: tuple[int, ...]
) -> NDArray[np.bool_]:
    """Fills one polygon from its column crossings.

    Args:
        columns: Column of each crossing, relative to the block.
        rows: Row of each crossing, relative to the block.
        shape: Shape (C, R) of the block.

    Returns:
        Boolean block of shape (C, R). A pixel is 1 if an odd number of crossings is
        above it in its column.
    """
    num_columns, num_rows = shape
    counts = np.bincount(columns * num_rows + rows, minlength=num_columns * num_rows)
    filled: NDArray[np.bool_] = np.cumsum(counts.reshape(num_columns, num_rows), axis=1) % 2 == 1
    return filled


def _row_wise_rle(
    block: NDArray[np.bool_], first_row: int, first_column: int, width: int, height: int
) -> list[int]:
    """Encodes a block of the mask as a row-wise RLE of the full mask.

    Args:
        block: Boolean block of shape (R, C) with the mask rows from `first_row` on and
            the mask columns from `first_column` on.
        first_row: Index of the first row of the block in the full mask.
        first_column: Index of the first column of the block in the full mask.
        width: Width of the full mask.
        height: Height of the full mask.

    Returns:
        Row-wise run-length encoding of the full mask of shape (height, width).
    """
    if not block.any():
        return [width * height]
    band = np.zeros((block.shape[0], width), dtype=bool)
    band[:, first_column : first_column + block.shape[1]] = block
    pixels = band.ravel()
    changes = np.flatnonzero(pixels[1:] != pixels[:-1]) + 1
    counts = np.diff(np.concatenate(([0], changes, [pixels.size]))).tolist()
    # Add the rows above and below the band to the first and the last run of 0 pixels.
    if pixels[0]:
        counts.insert(0, 0)
    counts[0] += first_row * width
    trailing_zeros = (height - first_row - block.shape[0]) * width
    if not pixels[-1]:
        counts[-1] += trailing_zeros
    elif trailing_zeros > 0:
        counts.append(trailing_zeros)
    return [int(count) for count in counts]
