import { createQuery } from '@tanstack/svelte-query';
import type { ImageFilter, MetadataValueCountsView } from '$lib/api/lightly_studio_local';
import { getMetadataValueCountsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getMetadataValueCounts } from '$lib/api/lightly_studio_local/sdk.gen';
import { MISSING_CATEGORICAL_VALUE, OTHER_CATEGORICAL_VALUE } from '$lib/services/types';
import type { CategoricalMetadataBucket } from './types';

const valueBucketId = (value: string | boolean): string =>
    JSON.stringify(['value', typeof value, value]);

export const selectCategoricalDistributions = (
    response: Record<string, MetadataValueCountsView> | undefined
): Record<string, CategoricalMetadataBucket[]> =>
    Object.fromEntries(
        Object.entries(response ?? {}).map(([key, counts]) => {
            const hasLiteralMissing = counts.value_counts.some(({ value }) => value === 'Missing');
            const hasLiteralOther = counts.value_counts.some(({ value }) => value === 'Other');
            const buckets: CategoricalMetadataBucket[] = [];
            for (const { value, count } of counts.value_counts) {
                if (value === MISSING_CATEGORICAL_VALUE) {
                    buckets.push({
                        id: JSON.stringify(['missing']),
                        kind: 'missing',
                        value: null,
                        label: hasLiteralMissing ? 'Missing (no value)' : 'Missing',
                        count
                    });
                } else if (value === OTHER_CATEGORICAL_VALUE) {
                    buckets.push({
                        id: JSON.stringify(['other']),
                        kind: 'other',
                        label: hasLiteralOther ? 'Other (aggregated)' : 'Other',
                        count
                    });
                } else {
                    buckets.push({
                        id: valueBucketId(value),
                        kind: 'value',
                        value,
                        label:
                            value === 'Missing' &&
                            counts.value_counts.some((e) => e.value === MISSING_CATEGORICAL_VALUE)
                                ? 'Missing (value)'
                                : value === 'Other' &&
                                    counts.value_counts.some(
                                        (e) => e.value === OTHER_CATEGORICAL_VALUE
                                    )
                                  ? 'Other (value)'
                                  : String(value),
                        count
                    });
                }
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
