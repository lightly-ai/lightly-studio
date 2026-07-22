import { createQuery } from '@tanstack/svelte-query';
import type { ImageFilter, MetadataValueCountsView } from '$lib/api/lightly_studio_local';
import { getMetadataValueCountsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getMetadataValueCounts } from '$lib/api/lightly_studio_local/sdk.gen';

export type CategoricalMetadataBucket =
    | {
          id: string;
          kind: 'value';
          value: string | boolean;
          label: string;
          count: number;
      }
    | { id: string; kind: 'missing'; value: null; label: string; count: number }
    | { id: string; kind: 'other'; label: string; count: number };

const valueBucketId = (value: string | boolean): string =>
    JSON.stringify(['value', typeof value, value]);

const getValueBucketLabel = (
    value: string | boolean,
    missingCount: number,
    otherCount: number
): string => {
    if (value === 'Missing' && missingCount > 0) {
        return 'Missing (value)';
    }
    if (value === 'Other' && otherCount > 0) {
        return 'Other (value)';
    }
    return String(value);
};

export const selectCategoricalDistributions = (
    response: Record<string, MetadataValueCountsView> | undefined
): Record<string, CategoricalMetadataBucket[]> =>
    Object.fromEntries(
        Object.entries(response ?? {}).map(([key, counts]) => {
            const hasLiteralMissing = counts.value_counts.some(({ value }) => value === 'Missing');
            const hasLiteralOther = counts.value_counts.some(({ value }) => value === 'Other');
            const buckets: CategoricalMetadataBucket[] = counts.value_counts.map(
                ({ value, count }) => ({
                    id: valueBucketId(value),
                    kind: 'value',
                    value,
                    label: getValueBucketLabel(value, counts.missing_count, counts.other_count),
                    count
                })
            );
            if (counts.missing_count > 0) {
                buckets.push({
                    id: JSON.stringify(['missing']),
                    kind: 'missing',
                    value: null,
                    label: hasLiteralMissing ? 'Missing (no value)' : 'Missing',
                    count: counts.missing_count
                });
            }
            if (counts.other_count > 0) {
                buckets.push({
                    id: JSON.stringify(['other']),
                    kind: 'other',
                    label: hasLiteralOther ? 'Other (aggregated)' : 'Other',
                    count: counts.other_count
                });
            }
            return [key, buckets];
        })
    );

export interface CategoricalMetadataDistributionOptions {
    collectionId: string;
    filter?: ImageFilter;
}

export const getCategoricalMetadataDistributionRequestOptions = ({
    collectionId,
    filter
}: CategoricalMetadataDistributionOptions) => ({
    path: { collection_id: collectionId },
    ...(filter ? { body: { filters: filter } } : {})
});

export const useCategoricalMetadataDistribution = (
    getOptions: () => CategoricalMetadataDistributionOptions & { enabled?: boolean }
) =>
    createQuery(() => {
        const { collectionId, filter, enabled = true } = getOptions();
        const requestOptions = getCategoricalMetadataDistributionRequestOptions({
            collectionId,
            filter
        });
        return {
            ...getMetadataValueCountsOptions(requestOptions),
            enabled,
            select: selectCategoricalDistributions,
            placeholderData: (previous: Record<string, MetadataValueCountsView> | undefined) =>
                previous,
            queryFn: async ({ signal }: { signal: AbortSignal }) => {
                const { data } = await getMetadataValueCounts({
                    ...requestOptions,
                    signal,
                    throwOnError: true
                });
                return data;
            }
        };
    });
