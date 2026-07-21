/** A single category (e.g. a class name) with its count. */
export interface CategoryCount {
    label: string;
    count: number;
}

/** One named set of counts rendered against a shared category axis. */
export interface CategoryCountSeries {
    /** Stable identity used to derive the series colour. */
    id: string;
    label: string;
    data: CategoryCount[];
}
