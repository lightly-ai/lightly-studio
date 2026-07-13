/** A single category (e.g. a class name) with its count. */
export interface CategoryCount {
    label: string;
    count: number;
}

/**
 * One overlaid series in a multi-series distribution chart (e.g. one tag).
 * A single series renders identically to the legacy single-`data` bar chart.
 */
export interface ChartSeries {
    /** Stable id (e.g. tag id) used for keying. */
    id: string;
    /** Legend/tooltip name. Empty for an unlabelled single series. */
    label: string;
    /** Series color; falls back to the shared series palette by index. */
    color?: string;
    /** Category counts for this series. */
    data: CategoryCount[];
}

/**
 * Chart form: `bar` = categorical (grouped bars across series); `histogram` =
 * numeric bins (a single filled series, step-line density curves when >1).
 */
export type ChartMode = 'bar' | 'histogram';

/** Values as raw counts or as a percentage normalized within each series. */
export type ChartNormalize = 'count' | 'percentage';
