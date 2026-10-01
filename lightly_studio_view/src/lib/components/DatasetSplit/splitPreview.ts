interface Split {
    tag_name: string;
    relative_size: number;
}

interface SplitValidationParams {
    splits: Split[];
    sampleCount: number;
    existingTagNames: string[];
}

/** Return the first name, weight, or sample-count error, or undefined when valid. */
export function getSplitError({
    splits,
    sampleCount,
    existingTagNames
}: SplitValidationParams): string | undefined {
    if (splits.length < 2) return 'At least two splits are required.';
    const names = splits.map((split) => split.tag_name.trim());
    if (names.some((name) => !name)) return 'Enter a name for every split.';
    if (new Set(names).size !== names.length) return 'Use a different name for each split.';
    if (names.some((name) => existingTagNames.includes(name)))
        return 'A tag with this name already exists.';
    if (
        splits.some(
            ({ relative_size }) => !Number.isSafeInteger(relative_size) || relative_size <= 0
        )
    )
        return 'Weights must be positive whole numbers within the supported range.';
    if (!Number.isSafeInteger(sampleCount) || sampleCount < splits.length)
        return 'There must be at least as many matching samples as splits.';
    return undefined;
}

/**
 * Return sample counts in split order, matching the backend's weighted allocation.
 * Round shares down, then give leftover samples to the largest remainders; ties favor earlier rows.
 * Call only after getSplitError has validated the form.
 */
export function getSplitCounts(sampleCount: number, splits: Split[]): number[] {
    // Integer arithmetic keeps large weighted shares exact, matching the backend.
    const weights = splits.map((split) => BigInt(split.relative_size));
    const totalWeight = weights.reduce((total, weight) => total + weight, 0n);
    const shares = weights.map((weight) => BigInt(sampleCount) * weight);
    const counts = shares.map((share) => Number(share / totalWeight));
    const remaining = sampleCount - counts.reduce((total, count) => total + count, 0);
    const ranked = shares.map((share, index) => ({ index, remainder: share % totalWeight }));
    // Equal remainders favor earlier rows, as in the backend allocation.
    ranked.sort((a, b) =>
        a.remainder === b.remainder ? a.index - b.index : a.remainder > b.remainder ? -1 : 1
    );
    for (const { index } of ranked.slice(0, remaining)) counts[index] += 1;
    return counts;
}
