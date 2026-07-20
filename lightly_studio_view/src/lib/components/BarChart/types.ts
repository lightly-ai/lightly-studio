/** A single category (e.g. a class name) with its count. */
export interface CategoryCount {
    /** Stable identity when multiple bars share the same display label. */
    id?: string;
    label: string;
    count: number;
    /** Whether the category is active in a controlled selection. */
    selected?: boolean;
    /** Whether clicking the bar can change selection. */
    selectable?: boolean;
    /** Keeps semantic buckets visible when a top-N view is applied. */
    pinned?: boolean;
}
