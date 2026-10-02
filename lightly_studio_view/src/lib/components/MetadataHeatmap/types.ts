/** A heatmap cell, given as the bucket indices of both axes. */
export interface HeatmapCell {
    x: number;
    y: number;
}

/** A rectangle of cells. Both bounds of each axis are included. */
export interface HeatmapCellRect {
    x0: number;
    x1: number;
    y0: number;
    y1: number;
}

/**
 * The selected bucket indices of each axis. `null` selects every bucket of the axis.
 * A cell is selected when the buckets of both axes are selected.
 */
export interface HeatmapSelection {
    x: number[] | null;
    y: number[] | null;
}

export interface HeatmapAxis {
    /** The axis name, for example the metadata key. */
    name: string;
    /** One label per bucket, in axis order. */
    labels: string[];
}
