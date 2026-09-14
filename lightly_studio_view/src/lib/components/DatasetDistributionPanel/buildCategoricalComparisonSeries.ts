import type { CategoryCountSeries } from '$lib/components/BarChart';
import type { CategoricalMetadataBucket } from '$lib/hooks/useCategoricalMetadataDistribution';

export interface CategoricalComparison {
    id: string;
    label: string;
    categorical: Record<string, CategoricalMetadataBucket[]>;
}

const comparisonLabel = (
    bucket: CategoricalMetadataBucket,
    hasLiteralMissing: boolean,
    hasLiteralOther: boolean
): string => {
    if (bucket.kind === 'missing') return hasLiteralMissing ? 'Missing (no value)' : 'Missing';
    if (bucket.kind === 'other') return hasLiteralOther ? 'Other (aggregated)' : 'Other';
    if (bucket.value === 'Missing' && hasLiteralMissing) return 'Missing (value)';
    if (bucket.value === 'Other' && hasLiteralOther) return 'Other (value)';
    return String(bucket.value);
};

export const buildCategoricalComparisonSeries = (
    comparisons: CategoricalComparison[],
    metadataKey: string
): CategoryCountSeries[] => {
    const allBuckets = comparisons.flatMap(({ categorical }) => categorical[metadataKey] ?? []);
    const hasLiteralMissing = allBuckets.some(
        (bucket) => bucket.kind === 'value' && bucket.value === 'Missing'
    );
    const hasLiteralOther = allBuckets.some(
        (bucket) => bucket.kind === 'value' && bucket.value === 'Other'
    );

    return comparisons.map(({ id, label, categorical }) => {
        const buckets = categorical[metadataKey] ?? [];
        return {
            id,
            label,
            data: buckets.map((bucket) => ({
                id: bucket.id,
                label: comparisonLabel(bucket, hasLiteralMissing, hasLiteralOther),
                count: bucket.count
            })),
            // The percentage denominator, set here so a top-N view cannot shrink
            // it. The backend closes the gap between its top values and the
            // tag's sample count with the `other` and `missing` buckets, so this
            // sums to every sample the tag holds.
            totalCount: buckets.reduce((sum, bucket) => sum + bucket.count, 0)
        };
    });
};

/**
 * The distinct buckets the comparison tags contribute for a metadata key.
 *
 * A tag can hold a value the current view has filtered away entirely. Its bar
 * still appears on the shared category axis, but the panel resolves a bar click
 * against the base buckets, which do not describe that value. Exposing the
 * comparison buckets alongside them keeps those bars filterable: the bucket id
 * is derived from the value itself, so the same value yields the same id in
 * every tag's response.
 *
 * Counts are summed across tags. They are not rendered - the panel ranks the
 * shared axis by its own aggregate - but a bucket without a coherent count
 * would be a trap for the next reader.
 */
export const buildCategoricalComparisonBuckets = (
    comparisons: CategoricalComparison[],
    metadataKey: string
): CategoricalMetadataBucket[] => {
    const allBuckets = comparisons.flatMap(({ categorical }) => categorical[metadataKey] ?? []);
    const hasLiteralMissing = allBuckets.some(
        (bucket) => bucket.kind === 'value' && bucket.value === 'Missing'
    );
    const hasLiteralOther = allBuckets.some(
        (bucket) => bucket.kind === 'value' && bucket.value === 'Other'
    );

    const byId = new Map<string, CategoricalMetadataBucket>();
    for (const bucket of allBuckets) {
        const existing = byId.get(bucket.id);
        if (existing) {
            existing.count += bucket.count;
            continue;
        }
        byId.set(bucket.id, {
            ...bucket,
            label: comparisonLabel(bucket, hasLiteralMissing, hasLiteralOther)
        });
    }
    return [...byId.values()];
};
