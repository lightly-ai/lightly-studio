interface SelectionClassCount {
    className: string;
    sampleCount: number;
}

interface ApplySummaryParams {
    className: string;
    selectedCount: number;
    selectionClassCounts: SelectionClassCount[];
}

interface ApplySummary {
    /** Selected images that already carry `className` and are therefore left untouched. */
    skippedCount: number;
    /** Selected images that gain the annotation class. */
    affectedCount: number;
}

/**
 * Split the selection into the images an apply would change and the ones it skips.
 *
 * The skip count comes from the entry of `selectionClassCounts` matching `className`
 * (counted in distinct-samples mode), clamped to the selection size so a stale count
 * can never produce a negative number of affected images.
 */
export function summarizeApply({
    className,
    selectedCount,
    selectionClassCounts
}: ApplySummaryParams): ApplySummary {
    const match = selectionClassCounts.find((entry) => entry.className === className);
    const skippedCount = Math.min(Math.max(match?.sampleCount ?? 0, 0), selectedCount);
    return { skippedCount, affectedCount: selectedCount - skippedCount };
}

/**
 * Merge `selected` into `options` so a name the user just typed stays listed and
 * selected until the (later) data layer reports it back.
 */
export function withSelectedOption(options: string[], selected: string): string[] {
    if (!selected) return options;
    return [...new Set([...options, selected])];
}
