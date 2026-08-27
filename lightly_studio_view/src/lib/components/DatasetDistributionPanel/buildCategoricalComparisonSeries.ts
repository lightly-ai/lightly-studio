import type { CategoryCountSeries } from '$lib/components/BarChart';
import type { CategoricalMetadataBucket } from '$lib/hooks/useCategoricalMetadataDistribution';

interface CategoricalComparison {
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

    return comparisons.map(({ id, label, categorical }) => ({
        id,
        label,
        data: (categorical[metadataKey] ?? []).map((bucket) => ({
            id: bucket.id,
            label: comparisonLabel(bucket, hasLiteralMissing, hasLiteralOther),
            count: bucket.count
        }))
    }));
};
