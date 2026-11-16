import type { CategoricalMetadataBucket } from '$lib/hooks/useCategoricalMetadataDistribution/types';

/**
 * The filtered buckets followed by every other value of the field with a count of 0.
 *
 * Other filters narrow the filtered buckets, so listing only those would let "Select all"
 * miss values that come back once the other filters are removed.
 */
export const withAllValues = (
    filtered: CategoricalMetadataBucket[],
    all: CategoricalMetadataBucket[]
): CategoricalMetadataBucket[] => {
    const filteredIds = new Set(filtered.map((bucket) => bucket.id));
    return [
        ...filtered,
        ...all
            .filter((bucket) => !filteredIds.has(bucket.id))
            .map((bucket) => ({ ...bucket, count: 0 }))
    ];
};
