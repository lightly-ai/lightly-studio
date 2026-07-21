/** A single category (e.g. a class name) with its count. */
export interface CategoryCount {
    /** Stable identity when multiple bars share the same display label. */
    id?: string;
    label: string;
    count: number;
    /**
     * Count after the active sidebar filters are applied. When set, a grey
     * background bar shows the full `count` while a coloured foreground bar
     * shows this filtered portion, giving a stable distribution context.
     * Omit (or set equal to `count`) when no filter is active.
     */
    filteredCount?: number;
    /** Whether the category is active in a controlled selection. */
    selected?: boolean;
    /** Whether clicking the bar can change selection. */
    selectable?: boolean;
    /** Keeps semantic buckets visible when a top-N view is applied. */
    pinned?: boolean;
}

/** One named set of counts rendered against a shared category axis. */
export interface CategoryCountSeries {
    /** Stable identity used to derive the series colour. */
    id: string;
    label: string;
    data: CategoryCount[];
}
