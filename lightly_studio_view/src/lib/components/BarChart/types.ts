/** A single category (e.g. a class name) with its count. */
export interface CategoryCount {
    /** Stable identifier used to correlate back to the original data item (e.g. a bucket id). */
    id?: string;
    label: string;
    count: number;
    /** When true the bar renders with a selection border. */
    selected?: boolean;
}
