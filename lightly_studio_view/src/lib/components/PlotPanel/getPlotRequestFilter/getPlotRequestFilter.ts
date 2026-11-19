const PLOT_IGNORED_SAMPLE_FILTER_KEYS = ['sample_ids', 'embedding_region'];

const isEmptyValue = (value: unknown): boolean => {
    if (value === undefined || value === null) return true;
    if (Array.isArray(value)) return value.length === 0;
    if (typeof value === 'object') return Object.keys(value).length === 0;
    return false;
};

/**
 * Builds the filter for the embeddings request. The plot shows every point and only
 * highlights a region or picks, so they are not sent. The request then stays the same
 * when the user draws, picks or clears a selection, and the plot does not refetch.
 */
export function getPlotRequestFilter<T extends { sample_filter?: object | null }>(
    filter: T | null
): T | null {
    if (filter === null) return null;

    const { sample_filter: sampleFilter, ...rest } = filter;
    const keptEntries = Object.entries(sampleFilter ?? {}).filter(
        ([key, value]) => !PLOT_IGNORED_SAMPLE_FILTER_KEYS.includes(key) && !isEmptyValue(value)
    );
    // The image and video filters have an optional sample_filter, so the filter without it is
    // still a valid T. TypeScript cannot prove this for a generic T.
    if (keptEntries.length === 0) return rest as T;

    return { ...rest, sample_filter: Object.fromEntries(keptEntries) } as T;
}
